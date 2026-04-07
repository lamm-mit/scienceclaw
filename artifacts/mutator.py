#!/usr/bin/env python3
"""
Artifact Graph Mutation Operator

Introduces a minimal mutation layer that lets the artifact DAG self-modify
its topology, increasing the space of emergent states without hardcoding
any domain logic.

Four atomic operations:
  fork          — 1 parent → 2 children (disjoint key subsets)
  prune         — 1 parent → 1 child (drop keys shared with siblings)
  graft         — rewire parent edge A→B to A→C (cycle-safe)
  merge_conflict — 2 conflicting nodes → 1 synthesis

Triggers checked once per reactor react() call:
  stagnation    — artifact has 0 children after K cycles
  redundancy    — two artifacts share > P% of payload keys in same investigation
  conflict      — two children of same parent have same key with different values

Mutation thresholds are stored as first-class mutation_policy artifacts in the
DAG. Thresholds drift stochastically to avoid fixed-point convergence.
"""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from artifacts.artifact import Artifact, ArtifactStore, SKILL_DOMAIN_MAP


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MutationTrigger:
    trigger_type: str          # "stagnation" | "redundancy" | "conflict"
    artifact_ids: List[str]    # artifacts involved
    investigation_id: str


@dataclass
class MutationPolicy:
    stagnation_cycles: int = 3
    redundancy_threshold: float = 0.7
    max_mutations_per_cycle: int = 2
    policy_generation: int = 0
    policy_artifact_id: Optional[str] = None  # id in store (if saved)

    def to_payload(self, pressure: dict) -> dict:
        return {
            "stagnation_cycles": self.stagnation_cycles,
            "redundancy_threshold": self.redundancy_threshold,
            "max_mutations_per_cycle": self.max_mutations_per_cycle,
            "policy_generation": self.policy_generation,
            "pressure_signal": pressure,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "MutationPolicy":
        return cls(
            stagnation_cycles=payload.get("stagnation_cycles", 3),
            redundancy_threshold=payload.get("redundancy_threshold", 0.7),
            max_mutations_per_cycle=payload.get("max_mutations_per_cycle", 2),
            policy_generation=payload.get("policy_generation", 0),
        )


# ---------------------------------------------------------------------------
# ArtifactMutator
# ---------------------------------------------------------------------------

class ArtifactMutator:
    """
    Detects topology conditions (stagnation, redundancy, conflict) in the
    artifact DAG and applies atomic mutation operations to produce new child
    artifacts that expand the reaction space.
    """

    def __init__(self, agent_name: str, store: ArtifactStore):
        self.agent_name = agent_name
        self._store = store
        self._base = Path.home() / ".scienceclaw" / "artifacts"
        self._global_index_path = self._base / "global_index.jsonl"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_triggers(
        self, investigation_id: str, index_lines: Optional[List[dict]] = None
    ) -> List[MutationTrigger]:
        """
        Scan global_index.jsonl for topology conditions.

        Reads only index entries (no payloads) for speed. Payloads are loaded
        only when a trigger fires.

        Args:
            index_lines: Pre-loaded global index entries (filtered to this
                investigation). If None, reads from disk (backwards-compatible).
        """
        if index_lines is not None:
            index = [e for e in index_lines if e.get("investigation_id") == investigation_id]
        else:
            index = self._read_index(investigation_id)

        # Load policy once and pass to all helpers to avoid 3× store.list() calls.
        policy = self._load_policy(investigation_id)

        triggers: List[MutationTrigger] = []
        triggers.extend(self._detect_stagnation(index, investigation_id, policy=policy))
        triggers.extend(self._detect_redundancy(index, investigation_id, policy=policy))
        triggers.extend(self._detect_conflict(index, investigation_id, policy=policy))

        return triggers

    def apply(self, trigger: MutationTrigger) -> Optional[Artifact]:
        """
        Apply one trigger → produce ≤ 1 new artifact (or 2 for fork).

        Returns the primary new artifact, or None if the operation fails.
        For fork(), only the first child is returned; both are saved.
        """
        if trigger.trigger_type == "stagnation":
            artifact = self._store.get(trigger.artifact_ids[0])
            if artifact is None:
                return None
            children = self._fork(artifact)
            return children[0] if children else None

        if trigger.trigger_type == "redundancy":
            if len(trigger.artifact_ids) < 2:
                return None
            a = self._store.get(trigger.artifact_ids[0])
            b = self._store.get(trigger.artifact_ids[1])
            if a is None or b is None:
                return None
            return self._merge_conflict(a, b)

        if trigger.trigger_type == "conflict":
            if len(trigger.artifact_ids) < 2:
                return None
            a = self._store.get(trigger.artifact_ids[0])
            b = self._store.get(trigger.artifact_ids[1])
            if a is None or b is None:
                return None
            # For conflict, try graft first then merge
            if len(trigger.artifact_ids) >= 3:
                # artifact_ids[2] is the new parent for graft
                new_parent = self._store.get(trigger.artifact_ids[2])
                if new_parent and not self._would_cycle(
                    a.artifact_id, new_parent.artifact_id
                ):
                    return self._graft(a, new_parent)
            return self._merge_conflict(a, b)

        return None

    def maybe_update_policy(
        self, investigation_id: str, pressure: dict
    ) -> Optional[Artifact]:
        """
        Stochastically update the mutation_policy artifact for this investigation
        if pressure signals warrant it.

        Returns a new policy artifact if thresholds changed, else None.
        """
        policy = self._load_policy(investigation_id)
        conflict_rate = pressure.get("conflict_rate", 0.0)
        redundancy_rate = pressure.get("redundancy_rate", 0.0)

        if conflict_rate <= 0.5 and redundancy_rate <= 0.5:
            return None

        old_threshold = policy.redundancy_threshold
        old_stagnation = policy.stagnation_cycles

        delta = random.uniform(0.02, 0.08)
        new_threshold = max(0.3, min(0.95, old_threshold - delta))

        new_stagnation = old_stagnation
        if random.random() < 0.15:
            new_stagnation = min(old_stagnation + 1, 8)

        if new_threshold == old_threshold and new_stagnation == old_stagnation:
            return None

        policy.redundancy_threshold = new_threshold
        policy.stagnation_cycles = new_stagnation
        policy.policy_generation += 1

        parent_ids = (
            [policy.policy_artifact_id] if policy.policy_artifact_id else []
        )
        payload = policy.to_payload(pressure)
        artifact = Artifact.create(
            artifact_type="mutation_policy",
            producer_agent=self.agent_name,
            skill_used="_mutation_policy",
            payload=payload,
            investigation_id=investigation_id,
            parent_artifact_ids=parent_ids,
        )
        self._store.save(artifact)
        return artifact

    # ------------------------------------------------------------------
    # Atomic operations
    # ------------------------------------------------------------------

    def _fork(self, artifact: Artifact) -> Tuple[Artifact, Artifact]:
        """
        Split artifact into two children with disjoint key subsets.

        Keys are split at the midpoint of the sorted key list.
        Both children get the original artifact as parent.
        """
        keys = sorted(artifact.payload.keys())
        if len(keys) < 2:
            # Can't split a single-key payload — duplicate with provenance
            keys = keys + keys  # allow overlap when minimal

        mid = max(1, len(keys) // 2)
        keys_a = keys[:mid]
        keys_b = keys[mid:] if len(keys) > mid else keys[mid - 1:]

        payload_a = {k: artifact.payload[k] for k in keys_a}
        payload_a["mutation_provenance"] = {
            "mutation_type": "fork",
            "trigger": "stagnation",
            "source_ids": [artifact.artifact_id],
            "delta": {
                "added_keys": [],
                "removed_keys": [k for k in keys if k not in keys_a],
                "rewired_from": [],
                "conflict_resolutions": {},
            },
        }

        payload_b = {k: artifact.payload[k] for k in keys_b}
        payload_b["mutation_provenance"] = {
            "mutation_type": "fork",
            "trigger": "stagnation",
            "source_ids": [artifact.artifact_id],
            "delta": {
                "added_keys": [],
                "removed_keys": [k for k in keys if k not in keys_b],
                "rewired_from": [],
                "conflict_resolutions": {},
            },
        }

        child_a = Artifact.create(
            artifact_type=artifact.artifact_type,
            producer_agent=self.agent_name,
            skill_used=artifact.skill_used,
            payload=payload_a,
            investigation_id=artifact.investigation_id,
            parent_artifact_ids=[artifact.artifact_id],
        )
        child_b = Artifact.create(
            artifact_type=artifact.artifact_type,
            producer_agent=self.agent_name,
            skill_used=artifact.skill_used,
            payload=payload_b,
            investigation_id=artifact.investigation_id,
            parent_artifact_ids=[artifact.artifact_id],
        )

        self._store.save(child_a)
        self._store.save(child_b)
        # Prefer returning the "most informative" fork child to keep the main
        # investigation path meaningful, while still preserving emergence via
        # the sibling branch.
        preferred_keys_by_type: Dict[str, List[str]] = {
            "pubmed_results": ["papers", "items", "articles", "pmids", "total", "count"],
            "structure_data": ["items", "pdb_id", "chains", "entities", "resolution"],
            "sequence_alignment": ["alignment", "msa", "hits", "top_hit", "sequences"],
            "conservation_map": ["conservation", "scores", "positions", "sequence"],
            "binding_hotspots": [
                "peptide_sequence",
                "binding_hotspots",
                "hotspot_positions",
                "per_position_contacts",
            ],
            "mutation_space": ["mutations", "positions", "variants", "protected_positions"],
            "sequence_design": ["final", "final_sequence", "trace", "variants", "start_sequence"],
            "stability_scores": ["scores", "candidates", "top", "ranking"],
            "ranked_candidates": ["candidates", "ranked", "table", "top_candidates"],
        }

        preferred = preferred_keys_by_type.get(artifact.artifact_type, [])

        def _score(a: Artifact) -> tuple:
            keys = set(a.payload.keys()) if isinstance(a.payload, dict) else set()
            keys_no_prov = {k for k in keys if k != "mutation_provenance"}
            # Weighted preference: earlier keys in the list are more important.
            preferred_score = 0
            for i, k in enumerate(preferred):
                if k in keys:
                    preferred_score += max(1, (len(preferred) - i))
            return (preferred_score, len(keys_no_prov), len(keys))

        if _score(child_b) > _score(child_a):
            return child_b, child_a
        return child_a, child_b

    def _prune(self, artifact: Artifact, siblings: List[Artifact]) -> Artifact:
        """
        Remove keys present in >= half of siblings to reduce redundancy.
        """
        if not siblings:
            return artifact

        # Count key frequency across siblings
        key_counts: Dict[str, int] = {}
        for sib in siblings:
            for k in sib.payload:
                if k != "mutation_provenance":
                    key_counts[k] = key_counts.get(k, 0) + 1

        threshold_count = max(1, len(siblings) // 2)
        removed_keys = [k for k, cnt in key_counts.items() if cnt >= threshold_count]

        pruned_payload = {
            k: v
            for k, v in artifact.payload.items()
            if k not in removed_keys and k != "mutation_provenance"
        }
        pruned_payload["mutation_provenance"] = {
            "mutation_type": "prune",
            "trigger": "redundancy",
            "source_ids": [artifact.artifact_id],
            "delta": {
                "added_keys": [],
                "removed_keys": removed_keys,
                "rewired_from": [],
                "conflict_resolutions": {},
            },
        }

        child = Artifact.create(
            artifact_type=artifact.artifact_type,
            producer_agent=self.agent_name,
            skill_used=artifact.skill_used,
            payload=pruned_payload,
            investigation_id=artifact.investigation_id,
            parent_artifact_ids=[artifact.artifact_id],
        )
        self._store.save(child)
        return child

    def _graft(self, artifact: Artifact, new_parent: Artifact) -> Optional[Artifact]:
        """
        Rewire artifact to have new_parent as its parent (replaces old parents).

        Cycle-safe: checks _would_cycle before proceeding.
        """
        if self._would_cycle(artifact.artifact_id, new_parent.artifact_id):
            return None

        old_parents = list(artifact.parent_artifact_ids)
        grafted_payload = dict(artifact.payload)
        grafted_payload.pop("mutation_provenance", None)
        grafted_payload["mutation_provenance"] = {
            "mutation_type": "graft",
            "trigger": "conflict",
            "source_ids": [artifact.artifact_id, new_parent.artifact_id],
            "delta": {
                "added_keys": [],
                "removed_keys": [],
                "rewired_from": old_parents,
                "conflict_resolutions": {},
            },
        }

        child = Artifact.create(
            artifact_type=artifact.artifact_type,
            producer_agent=self.agent_name,
            skill_used=artifact.skill_used,
            payload=grafted_payload,
            investigation_id=artifact.investigation_id,
            parent_artifact_ids=[new_parent.artifact_id],
        )
        self._store.save(child)
        return child

    def _merge_conflict(self, a: Artifact, b: Artifact) -> Artifact:
        """
        Merge two conflicting artifacts into one synthesis.

        Union keys; when both have the same key with different values,
        the value from whichever artifact was produced more recently wins.
        Provenance records which agent won each conflict.
        """
        # Determine winner by timestamp (newer wins)
        if a.timestamp >= b.timestamp:
            winner, loser = a, b
        else:
            winner, loser = b, a

        merged_payload: Dict = {}
        conflict_resolutions: Dict[str, str] = {}

        # Start with loser keys, then overwrite with winner (winner wins conflicts)
        for k, v in loser.payload.items():
            if k != "mutation_provenance":
                merged_payload[k] = v

        for k, v in winner.payload.items():
            if k == "mutation_provenance":
                continue
            if k in merged_payload and merged_payload[k] != v:
                conflict_resolutions[k] = winner.producer_agent
            merged_payload[k] = v

        merged_payload["mutation_provenance"] = {
            "mutation_type": "merge_conflict",
            "trigger": "conflict",
            "source_ids": [a.artifact_id, b.artifact_id],
            "delta": {
                "added_keys": [k for k in b.payload if k not in a.payload],
                "removed_keys": [],
                "rewired_from": [],
                "conflict_resolutions": conflict_resolutions,
            },
        }

        # Shared investigation_id if both share one
        inv_ids = {a.investigation_id, b.investigation_id} - {""}
        investigation_id = inv_ids.pop() if len(inv_ids) == 1 else "cross_investigation"

        child = Artifact.create(
            artifact_type="synthesis",
            producer_agent=self.agent_name,
            skill_used="_synthesis",
            payload=merged_payload,
            investigation_id=investigation_id,
            parent_artifact_ids=[a.artifact_id, b.artifact_id],
        )
        self._store.save(child)
        return child

    # ------------------------------------------------------------------
    # DAG safety
    # ------------------------------------------------------------------

    def _would_cycle(self, node_id: str, proposed_parent_id: str) -> bool:
        """
        Return True if making proposed_parent_id a parent of node_id would
        introduce a cycle (i.e. node_id is already an ancestor of proposed_parent_id).

        Implemented as: does a path exist from proposed_parent_id → node_id?
        """
        if node_id == proposed_parent_id:
            return True

        # BFS from proposed_parent upward — if we reach node_id, it's a cycle
        visited: Set[str] = set()
        queue = [proposed_parent_id]
        while queue:
            current = queue.pop()
            if current == node_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            parents = self._store.get_parent_ids(current)
            queue.extend(p for p in parents if p not in visited)
        return False

    # ------------------------------------------------------------------
    # Trigger detection helpers
    # ------------------------------------------------------------------

    def _read_index(self, investigation_id: str) -> List[dict]:
        """Read global index, filtering to the given investigation_id."""
        if not self._global_index_path.exists():
            return []
        try:
            lines = self._global_index_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []

        entries = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("investigation_id") == investigation_id:
                entries.append(entry)
        return entries

    # Minimum age before a leaf artifact is considered stagnant (24 hours)
    _STAGNATION_AGE_SECONDS: float = 86_400.0

    def _detect_stagnation(
        self, index: List[dict], investigation_id: str, *, policy: Optional[MutationPolicy] = None
    ) -> List[MutationTrigger]:
        """
        Find leaf artifacts (0 children) that are older than _STAGNATION_AGE_SECONDS.

        Only leaf artifacts that have been waiting long enough without producing
        children are considered stagnant — this avoids flagging freshly created
        artifacts that simply haven't been reacted to yet.
        """
        if policy is None:
            policy = self._load_policy(investigation_id)
        import datetime as _dt

        now = _dt.datetime.utcnow()

        # Collect all artifact IDs that appear as parents
        has_children: Set[str] = set()
        entries_by_id: Dict[str, dict] = {}

        for entry in index:
            aid = entry.get("artifact_id", "")
            if aid:
                entries_by_id[aid] = entry
            for pid in entry.get("parent_artifact_ids", []):
                has_children.add(pid)

        stagnant = []
        for aid, entry in entries_by_id.items():
            if aid in has_children:
                continue
            # Age check: skip if timestamp is recent or unparseable
            ts_raw = entry.get("timestamp", "")
            try:
                ts = _dt.datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                age_seconds = (now - ts).total_seconds()
            except (ValueError, AttributeError):
                # If we can't parse the timestamp, skip rather than false-positive
                continue
            if age_seconds < self._STAGNATION_AGE_SECONDS:
                continue
            stagnant.append(aid)

        triggers = []
        for aid in stagnant[:policy.max_mutations_per_cycle]:
            triggers.append(
                MutationTrigger(
                    trigger_type="stagnation",
                    artifact_ids=[aid],
                    investigation_id=investigation_id,
                )
            )
        return triggers

    def _detect_redundancy(
        self, index: List[dict], investigation_id: str, *, policy: Optional[MutationPolicy] = None
    ) -> List[MutationTrigger]:
        """
        Find pairs of artifacts that share > P% of their payload keys.

        Uses content_hash as a proxy when available; for full key overlap
        we'd need to load payloads. Here we detect *identical* hashes
        (complete redundancy) as a conservative trigger. True key-overlap
        triggers fire when two artifacts from the same investigation share
        the same artifact_type (strong signal of structural redundancy).
        """
        if policy is None:
            policy = self._load_policy(investigation_id)

        # Group by artifact_type
        by_type: Dict[str, List[dict]] = {}
        for entry in index:
            atype = entry.get("artifact_type", "")
            if atype and atype not in ("mutation_policy", "synthesis"):
                by_type.setdefault(atype, []).append(entry)

        triggers = []
        for atype, entries in by_type.items():
            if len(entries) < 2:
                continue

            # Check for identical hashes (full redundancy)
            seen_hashes: Dict[str, str] = {}
            for entry in entries:
                h = entry.get("content_hash", "")
                aid = entry.get("artifact_id", "")
                if h and h in seen_hashes:
                    triggers.append(
                        MutationTrigger(
                            trigger_type="redundancy",
                            artifact_ids=[seen_hashes[h], aid],
                            investigation_id=investigation_id,
                        )
                    )
                elif h:
                    seen_hashes[h] = aid

            # Also trigger if there are many same-type artifacts (structural proxy)
            if len(entries) >= 3:
                # Take the two oldest as candidates for merge
                sorted_entries = sorted(entries, key=lambda e: e.get("timestamp", ""))
                pair = [sorted_entries[0]["artifact_id"], sorted_entries[1]["artifact_id"]]
                triggers.append(
                    MutationTrigger(
                        trigger_type="redundancy",
                        artifact_ids=pair,
                        investigation_id=investigation_id,
                    )
                )

        return triggers[: policy.max_mutations_per_cycle]

    def _detect_conflict(
        self, index: List[dict], investigation_id: str, *, policy: Optional[MutationPolicy] = None
    ) -> List[MutationTrigger]:
        """
        Find pairs of sibling artifacts (same parent) — signal of potential
        conflict. Full key-value conflict detection requires loading payloads,
        so we conservatively flag any two children of the same parent.
        """
        if policy is None:
            policy = self._load_policy(investigation_id)

        # Build parent → [child_ids] map from index
        parent_to_children: Dict[str, List[str]] = {}
        for entry in index:
            for pid in entry.get("parent_artifact_ids", []):
                parent_to_children.setdefault(pid, []).append(
                    entry.get("artifact_id", "")
                )

        triggers = []
        for parent_id, children in parent_to_children.items():
            children = [c for c in children if c]
            if len(children) >= 2:
                triggers.append(
                    MutationTrigger(
                        trigger_type="conflict",
                        artifact_ids=[children[0], children[1], parent_id],
                        investigation_id=investigation_id,
                    )
                )

        return triggers[: policy.max_mutations_per_cycle]

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def _load_policy(self, investigation_id: str) -> MutationPolicy:
        """
        Load the most recent mutation_policy artifact for this investigation.

        Falls back to defaults if none found.
        """
        candidates = self._store.list(
            artifact_type="mutation_policy",
            investigation_id=investigation_id,
        )
        if not candidates:
            return MutationPolicy()

        # Most recent by timestamp
        candidates.sort(key=lambda a: a.timestamp, reverse=True)
        latest = candidates[0]
        policy = MutationPolicy.from_payload(latest.payload)
        policy.policy_artifact_id = latest.artifact_id
        return policy
