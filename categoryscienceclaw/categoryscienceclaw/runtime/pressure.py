"""Deterministic need pressure ranking.

This mirrors the ScienceClaw artifact pressure model locally: novelty,
centrality, depth, and age decide which needs are most urgent. Agent
compatibility is a filter layered on top, not a replacement for pressure.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Iterable

from categoryscienceclaw.kernel.models import Need

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _norm_tokens(text: str) -> tuple[str, ...]:
    return tuple(sorted(set(_TOKEN_RE.findall((text or "").lower()))))


@dataclass(frozen=True)
class NeedPressureRef:
    """Local equivalent of ScienceClaw artifacts.pressure.NeedRef."""

    id: str
    parent_artifact_id: str
    need_index: int
    required_type: str
    query: str
    rationale: str = ""
    allowed_morphisms: tuple[str, ...] = ()
    created_at: str = ""
    parent_depth: int = 0
    coverage: int = 0
    pressure: float = 0.0
    components: dict[str, float] = field(default_factory=dict)
    raw: Need | None = None

    @classmethod
    def from_need(
        cls,
        need: Need,
        *,
        parent_depth: int = 0,
        coverage: int = 0,
        created_at: str | None = None,
    ) -> "NeedPressureRef":
        return cls(
            id=need.id,
            parent_artifact_id=need.parent_artifact_id,
            need_index=need.need_index,
            required_type=need.required_type,
            query=need.query,
            rationale=need.rationale,
            allowed_morphisms=tuple(need.allowed_morphisms),
            created_at=created_at if created_at is not None else need.created_at,
            parent_depth=parent_depth,
            coverage=coverage,
            raw=need,
        )


def _as_ref(need: Need | NeedPressureRef) -> NeedPressureRef:
    if isinstance(need, NeedPressureRef):
        return need
    return NeedPressureRef.from_need(need)


def _centrality(need: NeedPressureRef, all_refs: list[NeedPressureRef]) -> float:
    target_tokens = set(_norm_tokens(need.query))
    if not target_tokens:
        return 0.0
    central = 0.0
    for other in all_refs:
        if other.required_type != need.required_type:
            continue
        other_tokens = set(_norm_tokens(other.query))
        if not other_tokens:
            continue
        if len(target_tokens & other_tokens) >= max(1, min(3, len(target_tokens))):
            central += 1.0
    return min(6.0, central)


def score_need(need: NeedPressureRef, *, all_needs: Iterable[NeedPressureRef] = ()) -> NeedPressureRef:
    refs = list(all_needs) or [need]
    novelty = 1.0 / (1.0 + float(max(0, need.coverage)))
    centrality = _centrality(need, refs)
    depth = float(max(0, need.parent_depth))
    age_minutes = 0.0
    ts = _parse_ts(need.created_at)
    if ts is not None:
        age_minutes = max(0.0, (_now_utc() - ts).total_seconds() / 60.0)
    age = math.log1p(age_minutes)
    pressure = float(2.0 * novelty + 1.0 * centrality + 0.5 * depth + 0.2 * age)
    return replace(
        need,
        pressure=pressure,
        components={
            "novelty": novelty,
            "centrality": centrality,
            "depth": depth,
            "age": age,
        },
    )


def rank_needs(
    needs: list[Need] | list[NeedPressureRef],
    *,
    agent_types: set[str] | None = None,
    agent_morphisms: set[str] | None = None,
) -> list[Any]:
    """Rank needs by ScienceClaw-style pressure, preserving input type.

    Existing workers pass `Need` objects and expect `Need` objects back. Tests and
    pressure diagnostics can pass `NeedPressureRef` and receive scored refs back.
    """

    refs = [_as_ref(need) for need in needs]
    if agent_types is not None:
        refs = [ref for ref in refs if ref.required_type in agent_types]
    if agent_morphisms is not None:
        refs = [
            ref
            for ref in refs
            if not ref.allowed_morphisms or set(ref.allowed_morphisms) & set(agent_morphisms)
        ]
    scored = [score_need(ref, all_needs=refs) for ref in refs]
    scored.sort(key=lambda ref: (ref.pressure, ref.id), reverse=True)
    if needs and isinstance(needs[0], NeedPressureRef):
        return scored
    by_id = {ref.id: ref for ref in scored}
    need_by_id = {need.id: need for need in needs if isinstance(need, Need)}
    return [need_by_id[ref.id] for ref in scored if ref.id in need_by_id]
