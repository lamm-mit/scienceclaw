#!/usr/bin/env python3
"""
Artifact Reaction Layer

Enables emergent coordination: agents scan peer artifact stores, run compatible
skills on matching payloads, and produce child artifacts with parent lineage.

Compatibility is determined dynamically:
    skill.input_schema ∩ artifact.payload_schema ≠ ∅

Where:
    skill.input_schema  = CLI parameter names parsed from --help
    artifact.payload_schema = top-level keys of the artifact payload

No hardcoded type→skill mapping.  Adding a new skill or a new payload key
automatically makes it eligible for reactions without touching this file.

Loop prevention:
  1. consumed.txt — each artifact_id written once; never re-reacted
  2. producer_agent != self.agent_name — no self-loops
  3. limit=3 per heartbeat — caps fan-out per cycle

Execution path:
  Reactor → core.skill_executor.SkillExecutor  (same path as deep_investigation)
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from artifacts.artifact import Artifact, ArtifactStore
from core.skill_registry import get_registry
from core.skill_executor import get_executor


# ---------------------------------------------------------------------------
# Schema introspection helpers
# ---------------------------------------------------------------------------

# Module-level cache: skill_name -> frozenset of normalised param names
_SKILL_PARAM_CACHE: Dict[str, frozenset] = {}


def _skill_input_params(skill_name: str, skill_meta: dict) -> frozenset:
    """
    Return the set of CLI parameter names (snake_case) that `skill_name` accepts.

    Calls `python3 <script> --help` once and caches the result.  Falls back to
    empty set if the script is missing or crashes.
    """
    if skill_name in _SKILL_PARAM_CACHE:
        return _SKILL_PARAM_CACHE[skill_name]

    executables = skill_meta.get("executables", [])
    params: Set[str] = set()

    if executables:
        script = executables[0]
        try:
            proc = subprocess.run(
                ["python3", script, "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            help_text = proc.stdout + proc.stderr
            # Extract every --flag-name, normalise hyphens → underscores
            for m in re.finditer(r"--([a-z][a-z0-9_-]+)", help_text):
                params.add(m.group(1).replace("-", "_"))
        except Exception:
            pass

    result = frozenset(params)
    _SKILL_PARAM_CACHE[skill_name] = result
    return result


def _find_match(
    payload: dict,
    skill_params: frozenset,
) -> Optional[Tuple[str, str, object]]:
    """
    Return (payload_key, param_name, value) for the first payload key that
    overlaps with skill_params, or None.

    Skips keys whose values are empty, nested dicts, or otherwise un-passable
    as a single CLI string.
    """
    for raw_key, value in payload.items():
        # Normalise payload key to match CLI convention
        norm = raw_key.replace("-", "_").lower()
        if norm not in skill_params:
            continue
        # List: take first element as a representative value
        if isinstance(value, list):
            value = value[0] if value else None
        # Skip nested objects and empty values
        if value is None or isinstance(value, dict):
            continue
        return raw_key, norm, value
    return None


# ---------------------------------------------------------------------------
# Main reactor
# ---------------------------------------------------------------------------

class ArtifactReactor:
    """
    Scans all agents' artifact stores, finds peer artifacts whose payload keys
    overlap with the current agent's skills' accepted parameters, runs those
    skills, and saves child artifacts with parent lineage.
    """

    def __init__(
        self,
        agent_name: str,
        agent_profile: dict,
        artifact_store: ArtifactStore,
    ):
        self.agent_name = agent_name
        self.store = artifact_store
        self._base = Path.home() / ".scienceclaw" / "artifacts"
        self.consumed_path = self._base / agent_name / "consumed.txt"

        # Reuse the same registry and executor as deep_investigation
        self._registry = get_registry()
        self._executor = get_executor()

        # Restrict to agent's preferred_tools if specified
        preferred = agent_profile.get("preferred_tools", [])
        if preferred:
            self._allowed_skills: Optional[Set[str]] = set(preferred)
        else:
            self._allowed_skills = None  # unrestricted

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_available(self) -> List[Artifact]:
        """
        Return unclaimed peer artifacts compatible with at least one of this
        agent's skills.

        Reads from the global index (payload-free) for fast filtering, then
        loads the full artifact from the producer's per-agent store only for
        candidates that pass all filters.

        Compatibility = skill.input_params ∩ artifact.payload_keys ≠ ∅
        """
        global_index = self._base / "global_index.jsonl"
        if not global_index.exists():
            return []

        consumed = self._load_consumed()
        candidate_skills = self._candidate_skills()
        available = []

        try:
            lines = global_index.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("producer_agent") == self.agent_name:
                continue  # no self-loops
            if entry.get("artifact_id") in consumed:
                continue  # already reacted

            # Load full artifact (with payload) only for viable candidates
            producer = entry.get("producer_agent", "")
            artifact_id = entry.get("artifact_id", "")
            store_path = self._base / producer / "store.jsonl"
            art = self._load_artifact_from_store(store_path, artifact_id)
            if art is None:
                continue

            if self._is_compatible(art, candidate_skills):
                available.append(art)

        return available

    def _load_artifact_from_store(
        self, store_path: Path, artifact_id: str
    ) -> Optional[Artifact]:
        """Load a single artifact by ID from a per-agent store file."""
        if not store_path.exists():
            return None
        try:
            for line in store_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("artifact_id") == artifact_id:
                    return Artifact.from_dict(d)
        except OSError:
            pass
        return None

    def react(self, limit: int = 3) -> List[Artifact]:
        """
        React to up to `limit` compatible peer artifacts.

        Returns list of newly produced child artifacts.
        """
        available = self.scan_available()[:limit]
        children = []
        for parent in available:
            child = self._transform(parent)
            if child:
                children.append(child)
                self._mark_consumed(parent.artifact_id)
        return children

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _candidate_skills(self) -> Dict[str, dict]:
        """Return registry entries for skills this agent is allowed to run."""
        all_skills = self._registry.skills
        if self._allowed_skills is None:
            return all_skills
        return {k: v for k, v in all_skills.items() if k in self._allowed_skills}

    def _is_compatible(self, art: Artifact, candidate_skills: Dict[str, dict]) -> bool:
        """Return True if any candidate skill can accept a key from art.payload."""
        payload_norm = {k.replace("-", "_").lower() for k in art.payload}
        for skill_name, skill_meta in candidate_skills.items():
            params = _skill_input_params(skill_name, skill_meta)
            if params & payload_norm:
                return True
        return False

    def _transform(self, parent: Artifact) -> Optional[Artifact]:
        """
        Find the first compatible skill for `parent`, run it via SkillExecutor,
        and return the child artifact (or None on failure).
        """
        candidate_skills = self._candidate_skills()
        payload_keys = {k.replace("-", "_").lower(): k for k in parent.payload}

        for skill_name, skill_meta in candidate_skills.items():
            params = _skill_input_params(skill_name, skill_meta)
            overlap = params & set(payload_keys.keys())
            if not overlap:
                continue

            # Build parameter dict from all overlapping keys
            exec_params: Dict[str, object] = {}
            for norm_key in overlap:
                raw_key = payload_keys[norm_key]
                value = parent.payload[raw_key]
                if isinstance(value, list):
                    value = value[0] if value else None
                if value is None or isinstance(value, dict):
                    continue
                exec_params[norm_key] = value

            if not exec_params:
                continue

            result = self._executor.execute_skill(
                skill_name=skill_name,
                skill_metadata=skill_meta,
                parameters=exec_params,
                timeout=30,
            )

            if result.get("status") == "success":
                payload = result.get("result", {})
                if not isinstance(payload, dict):
                    payload = {"output": payload}
                child = self.store.create_and_save(
                    skill_used=skill_name,
                    payload=payload,
                    investigation_id=parent.investigation_id,
                    parent_artifact_ids=[parent.artifact_id],
                )
                return child

        return None

    def _load_consumed(self) -> Set[str]:
        if self.consumed_path.exists():
            return set(self.consumed_path.read_text(encoding="utf-8").splitlines())
        return set()

    def _mark_consumed(self, artifact_id: str) -> None:
        self.consumed_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.consumed_path, "a", encoding="utf-8") as fh:
            fh.write(artifact_id + "\n")


# ---------------------------------------------------------------------------
# Posting summary helper (used by loop_controller)
# ---------------------------------------------------------------------------

def summarise_reactions(children: List[Artifact], registry=None) -> str:
    """
    Build a human-readable summary of a batch of reaction artifacts for posting.

    Includes:
    - How many parents were consumed, from how many distinct agents
    - What skill produced each child and what artifact type resulted
    - Key payload values extracted from each child (compound name, prediction
      score, protein ID, top hit, etc.)
    """
    if not children:
        return "No reaction artifacts produced."

    parent_ids = [p for c in children for p in c.parent_artifact_ids]
    # parent agent names aren't stored on the child, but we can group by investigation
    inv_ids = list({c.investigation_id for c in children if c.investigation_id})

    lines = [
        f"Consumed {len(parent_ids)} peer artifact(s) → "
        f"produced {len(children)} derived artifact(s) "
        f"via {len({c.skill_used for c in children})} skill(s).",
        "",
    ]

    for child in children:
        key_values = _extract_key_values(child.payload, child.artifact_type)
        lines.append(
            f"  • [{child.artifact_type}] via {child.skill_used} "
            f"(parent: {child.parent_artifact_ids[0][:8]}…) — {key_values}"
        )

    if inv_ids:
        lines.append(f"\nLinked investigation(s): {', '.join(inv_ids[:3])}")
    lines.append(f"Artifact refs: {[c.artifact_id[:8] + '…' for c in children]}")

    return "\n".join(lines)


def _extract_key_values(payload: dict, artifact_type: str) -> str:
    """Pull a concise, human-readable value string from a payload dict."""
    # Ordered list of keys to try per artifact type
    TYPE_KEYS = {
        "admet_prediction": ["predictions", "BBB", "HIA", "solubility", "score"],
        "compound_data":    ["name", "iupac_name", "canonical_smiles", "molecular_formula"],
        "protein_data":     ["id", "accession", "gene_name", "protein_name", "organism"],
        "sequence_alignment": ["top_hit", "identity", "evalue", "hit_id"],
        "pubmed_results":   ["total", "count", "papers"],
        "rdkit_properties": ["molecular_weight", "logP", "tpsa", "hbd", "hba"],
    }

    candidates = TYPE_KEYS.get(artifact_type, [])
    # Fall back to first five non-empty scalar keys
    if not candidates:
        candidates = list(payload.keys())[:5]

    parts = []
    for k in candidates:
        v = payload.get(k)
        if v is None:
            continue
        if isinstance(v, dict):
            # One level deep: grab first scalar
            for sub_k, sub_v in v.items():
                if not isinstance(sub_v, (dict, list)):
                    parts.append(f"{sub_k}={sub_v}")
                    break
        elif isinstance(v, list):
            parts.append(f"{k}[{len(v)}]")
        else:
            parts.append(f"{k}={v}")
        if len(parts) >= 3:
            break

    return ", ".join(parts) if parts else "(no extractable values)"
