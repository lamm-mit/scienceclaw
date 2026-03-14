#!/usr/bin/env python3
"""
Artifact Pressure — a simple, deterministic prioritizer for branching investigation DAGs.

Pressure answers: “Which open needs should we pursue next?”

Design goals:
  - No hardcoded workflows
  - No LLM dependency
  - Deterministic scoring (stable demos)
  - Works off global_index metadata when available, but degrades gracefully
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _norm_tokens(text: str) -> Tuple[str, ...]:
    return tuple(sorted(set(_TOKEN_RE.findall((text or "").lower()))))


@dataclass(frozen=True)
class NeedRef:
    parent_artifact_id: str
    need_index: int
    producer_agent: str
    investigation_id: str
    artifact_type: str
    query: str
    rationale: str
    parent_timestamp: str


def iter_open_needs(
    *,
    global_index_path: Optional[Path] = None,
    investigation_id: str = "",
    partner_agents: Optional[Iterable[str]] = None,
    exclude_agent: str = "",
) -> List[Tuple[dict, int, NeedRef]]:
    """
    Return list of (index_entry, need_index, NeedRef) for all needs in the global index.
    """
    base = Path.home() / ".scienceclaw" / "artifacts"
    idx = global_index_path or (base / "global_index.jsonl")
    if not idx.exists():
        return []

    partners = set(partner_agents) if partner_agents else None
    out: List[Tuple[dict, int, NeedRef]] = []

    for line in idx.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if exclude_agent and entry.get("producer_agent") == exclude_agent:
            continue
        if investigation_id and entry.get("investigation_id") != investigation_id:
            continue
        if partners is not None and entry.get("producer_agent") not in partners:
            continue

        needs = entry.get("needs") or []
        if not isinstance(needs, list) or not needs:
            continue

        for i, n in enumerate(needs):
            if not isinstance(n, dict):
                continue
            atype = str(n.get("artifact_type") or "")
            query = str(n.get("query") or "")
            rationale = str(n.get("rationale") or "")
            if not atype or not query:
                continue
            ref = NeedRef(
                parent_artifact_id=str(entry.get("artifact_id") or ""),
                need_index=int(i),
                producer_agent=str(entry.get("producer_agent") or ""),
                investigation_id=str(entry.get("investigation_id") or ""),
                artifact_type=atype,
                query=query,
                rationale=rationale,
                parent_timestamp=str(entry.get("timestamp") or ""),
            )
            out.append((entry, i, ref))

    return out


def _coverage_count(
    *,
    global_index_lines: List[dict],
    parent_artifact_id: str,
    need_index: int,
) -> int:
    """
    Count how many fulfillment artifacts already exist for this (parent, need_index).

    Prefers explicit fulfillment metadata in global_index entries (added by ArtifactStore),
    otherwise falls back to counting child edges from parent.
    """
    count = 0
    for e in global_index_lines:
        if e.get("fulfilled_need_parent_id") == parent_artifact_id and e.get("fulfilled_need_index") == need_index:
            count += 1
    if count:
        return count

    # Fallback: edge-based coverage (counts *any* child artifacts)
    for e in global_index_lines:
        parents = e.get("parent_artifact_ids") or []
        if parent_artifact_id in parents:
            count += 1
    return count


def score_need(
    *,
    need: NeedRef,
    depth: int = 0,
    global_index_lines: Optional[List[dict]] = None,
    _precomputed_centrality: Optional[float] = None,
) -> float:
    """
    Deterministic pressure score. Higher = more urgent to pursue.

    Components:
      - novelty: fewer prior fulfillments => higher pressure
      - centrality: many similar needs (same atype + overlapping tokens) => higher pressure
      - depth: deeper parents => slightly higher pressure (more context accumulated)
      - age: older needs drift upward slowly (prevents starvation)
    """
    lines = global_index_lines or []
    coverage = _coverage_count(
        global_index_lines=lines,
        parent_artifact_id=need.parent_artifact_id,
        need_index=need.need_index,
    )
    novelty = 1.0 / (1.0 + float(coverage))

    if _precomputed_centrality is not None:
        centrality = _precomputed_centrality
    else:
        target_tokens = _norm_tokens(need.query)
        centrality = 0.0
        for e in lines:
            needs = e.get("needs") or []
            if not isinstance(needs, list):
                continue
            for n in needs:
                if not isinstance(n, dict):
                    continue
                if str(n.get("artifact_type") or "") != need.artifact_type:
                    continue
                qt = _norm_tokens(str(n.get("query") or ""))
                if qt and target_tokens and len(set(qt) & set(target_tokens)) >= max(1, min(3, len(target_tokens))):
                    centrality += 1.0
        centrality = min(6.0, centrality)  # cap

    age_minutes = 0.0
    ts = _parse_ts(need.parent_timestamp)
    if ts is not None:
        age_minutes = max(0.0, (_now_utc() - ts).total_seconds() / 60.0)
    age_term = math.log1p(age_minutes)

    return float(2.0 * novelty + 1.0 * centrality + 0.5 * float(depth) + 0.2 * age_term)


def rank_needs(
    *,
    needs: List[NeedRef],
    depth_map: Optional[Dict[str, int]] = None,
    global_index_path: Optional[Path] = None,
) -> List[NeedRef]:
    base = Path.home() / ".scienceclaw" / "artifacts"
    idx = global_index_path or (base / "global_index.jsonl")
    lines: List[dict] = []
    if idx.exists():
        for l in idx.read_text(encoding="utf-8").splitlines():
            l = l.strip()
            if not l:
                continue
            try:
                lines.append(json.loads(l))
            except Exception:
                continue

    depth_map = depth_map or {}

    # Pre-compute centrality for each need to avoid O(n²) inner loop.
    def _compute_centrality(need: NeedRef) -> float:
        target_tokens = _norm_tokens(need.query)
        centrality = 0.0
        for e in lines:
            e_needs = e.get("needs") or []
            if not isinstance(e_needs, list):
                continue
            for n in e_needs:
                if not isinstance(n, dict):
                    continue
                if str(n.get("artifact_type") or "") != need.artifact_type:
                    continue
                qt = _norm_tokens(str(n.get("query") or ""))
                if qt and target_tokens and len(set(qt) & set(target_tokens)) >= max(1, min(3, len(target_tokens))):
                    centrality += 1.0
        return min(6.0, centrality)

    centrality_cache = {n.parent_artifact_id + str(n.need_index): _compute_centrality(n) for n in needs}

    scored = []
    for n in needs:
        key = n.parent_artifact_id + str(n.need_index)
        scored.append((
            score_need(
                need=n,
                depth=int(depth_map.get(n.parent_artifact_id, 0)),
                global_index_lines=lines,
                _precomputed_centrality=centrality_cache[key],
            ),
            n,
        ))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [n for _, n in scored]

