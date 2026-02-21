#!/usr/bin/env python3
"""
Artifact layer for the scienceclaw agent system.

Every skill invocation produces an Artifact — a versioned, addressable,
content-hashed record of what a specific skill returned for a specific agent
during a specific investigation.

Artifacts are appended to:
    ~/.scienceclaw/artifacts/{agent_name}/store.jsonl

Pattern mirrors memory/journal.py (JSONL append-only, one JSON object per line).

Address scheme: artifact://{agent_name}/{artifact_id}
"""

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4


# ---------------------------------------------------------------------------
# Skill domain map
# One entry per skill family (covering all 173 skills).
# Keys are the skill names as used in agent profiles ("preferred_tools").
# Values are the artifact types that skill family may produce.
# ---------------------------------------------------------------------------
SKILL_DOMAIN_MAP: Dict[str, List[str]] = {
    # Literature
    "pubmed":              ["pubmed_results"],
    "arxiv":               ["pubmed_results"],
    "europe-pmc":          ["pubmed_results"],
    "semantic-scholar":    ["pubmed_results"],
    # Protein / sequence
    "uniprot":             ["protein_data"],
    "uniprot-database":    ["protein_data"],
    "blast":               ["sequence_alignment"],
    "pdb":                 ["structure_data"],
    "alphafold":           ["structure_data"],
    "interpro":            ["protein_data"],
    "pfam":                ["protein_data"],
    "string-database":     ["protein_data"],
    # Chemistry / compounds
    "pubchem":             ["compound_data"],
    "pubchem-database":    ["compound_data"],
    "chembl":              ["compound_data"],
    "chembl-database":     ["compound_data"],
    "cas":                 ["compound_data"],
    "nist-webbook":        ["compound_data"],
    # ADMET / drug properties
    "tdc":                 ["admet_prediction"],
    "pytdc":               ["admet_prediction"],
    "admet-ai":            ["admet_prediction"],
    # Cheminformatics
    "rdkit":               ["rdkit_properties"],
    "openbabel":           ["rdkit_properties"],
    # Pathways / networks
    "kegg-database":       ["pathway_data"],
    "reactome-database":   ["pathway_data"],
    "go-database":         ["pathway_data"],
    # Genomics / variants
    "ensembl":             ["genomic_data"],
    "clinvar":             ["genomic_data"],
    "gnomad":              ["genomic_data"],
    "dbsnp":               ["genomic_data"],
    # Materials science
    "materials-project":   ["materials_data"],
    "aflow":               ["materials_data"],
    # Visualization
    "datavis":             ["figure"],
    "pymol":               ["figure"],
    # Synthesis (cross-tool)
    "_synthesis":          ["synthesis"],
    # Peer validation
    "_validation":         ["peer_validation"],
}


class ArtifactDomainError(Exception):
    """Raised when an agent tries to claim an artifact outside its skill domain."""


@dataclass
class Artifact:
    """
    Versioned, addressable wrapper around a single skill invocation's output.

    Fields are immutable after creation. The content_hash ensures integrity.
    """
    artifact_id: str
    artifact_type: str       # from SKILL_DOMAIN_MAP values
    producer_agent: str      # agent name from config
    skill_used: str          # e.g. "pubmed", "tdc", "blast"
    schema_version: str      # bump when Artifact fields change
    payload: dict            # unchanged skill JSON output
    investigation_id: str    # links to InvestigationTracker entry (or topic slug)
    timestamp: str           # ISO 8601 UTC
    content_hash: str        # sha256(canonical JSON of payload)
    parent_artifact_ids: List[str] = field(default_factory=list)  # DAG lineage

    @staticmethod
    def _hash_payload(payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        artifact_type: str,
        producer_agent: str,
        skill_used: str,
        payload: dict,
        investigation_id: str = "",
        parent_artifact_ids: Optional[List[str]] = None,
    ) -> "Artifact":
        """Factory: generates id, timestamp, and hash automatically."""
        return cls(
            artifact_id=str(uuid4()),
            artifact_type=artifact_type,
            producer_agent=producer_agent,
            skill_used=skill_used,
            schema_version="1.0",
            payload=payload,
            investigation_id=investigation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content_hash=cls._hash_payload(payload),
            parent_artifact_ids=parent_artifact_ids or [],
        )

    def address(self) -> str:
        """Return the canonical address for this artifact."""
        return f"artifact://{self.producer_agent}/{self.artifact_id}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Artifact":
        d = dict(d)
        d.setdefault("parent_artifact_ids", [])
        return cls(**d)


class ArtifactStore:
    """
    Append-only JSONL store for artifacts.

    Storage: ~/.scienceclaw/artifacts/{agent_name}/store.jsonl
    One JSON object per line (same pattern as AgentJournal).
    """

    SCHEMA_VERSION = "1.0"

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        base = Path(os.path.expanduser("~/.scienceclaw"))
        self.store_path = base / "artifacts" / agent_name / "store.jsonl"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._global_index_path = base / "artifacts" / "global_index.jsonl"

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, artifact: Artifact) -> str:
        """Append artifact to per-agent store and global index. Returns artifact_id."""
        line = json.dumps(artifact.to_dict(), ensure_ascii=False) + "\n"
        with open(self.store_path, "a", encoding="utf-8") as fh:
            fh.write(line)
        self._append_global_index(artifact)
        return artifact.artifact_id

    def _append_global_index(self, artifact: Artifact) -> None:
        """
        Append a minimal index entry to the global cross-agent index.

        Only the fields needed for discovery are stored — not the full payload —
        keeping the index fast to scan even with thousands of artifacts.
        """
        entry = {
            "artifact_id":        artifact.artifact_id,
            "artifact_type":      artifact.artifact_type,
            "producer_agent":     artifact.producer_agent,
            "skill_used":         artifact.skill_used,
            "investigation_id":   artifact.investigation_id,
            "timestamp":          artifact.timestamp,
            "content_hash":       artifact.content_hash,
            "parent_artifact_ids": artifact.parent_artifact_ids,
        }
        with open(self._global_index_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def create_and_save(
        self,
        skill_used: str,
        payload: dict,
        investigation_id: str = "",
        parent_artifact_ids: Optional[List[str]] = None,
    ) -> Artifact:
        """
        Convenience: build Artifact from skill name + payload, save, return it.

        Looks up artifact_type from SKILL_DOMAIN_MAP; falls back to "raw_output".
        """
        artifact_type = SKILL_DOMAIN_MAP.get(skill_used, ["raw_output"])[0]
        artifact = Artifact.create(
            artifact_type=artifact_type,
            producer_agent=self.agent_name,
            skill_used=skill_used,
            payload=payload,
            investigation_id=investigation_id,
            parent_artifact_ids=parent_artifact_ids or [],
        )
        self.save(artifact)
        return artifact

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def _iter_lines(self):
        if not self.store_path.exists():
            return
        with open(self.store_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        pass

    def get(self, artifact_id: str) -> Optional[Artifact]:
        """Retrieve artifact by ID (linear scan — store is typically small)."""
        for record in self._iter_lines():
            if record.get("artifact_id") == artifact_id:
                return Artifact.from_dict(record)
        return None

    def list(
        self,
        artifact_type: Optional[str] = None,
        skill_used: Optional[str] = None,
        investigation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Artifact]:
        """Return artifacts matching all provided filters (AND semantics)."""
        results = []
        for record in self._iter_lines():
            if artifact_type and record.get("artifact_type") != artifact_type:
                continue
            if skill_used and record.get("skill_used") != skill_used:
                continue
            if investigation_id and record.get("investigation_id") != investigation_id:
                continue
            results.append(Artifact.from_dict(record))
            if len(results) >= limit:
                break
        return results

    # ------------------------------------------------------------------
    # Domain gating helpers
    # ------------------------------------------------------------------

    @staticmethod
    def allowed_artifact_types_for_agent(agent_profile: dict) -> List[str]:
        """
        Derive the set of artifact types this agent is allowed to produce/claim,
        based on preferred_tools in agent_profile.json.

        An agent with no preferred_tools gets all artifact types (no restriction).
        """
        preferred = agent_profile.get("preferred_tools", [])
        if not preferred:
            # No restriction — all types allowed
            return list({t for types in SKILL_DOMAIN_MAP.values() for t in types})
        allowed = set()
        for tool in preferred:
            for t in SKILL_DOMAIN_MAP.get(tool, []):
                allowed.add(t)
        # Always permit synthesis and validation artifacts regardless of profile
        allowed.update(["synthesis", "peer_validation", "raw_output"])
        return list(allowed)

    def assert_agent_can_claim(
        self,
        artifact_id: str,
        agent_profile: dict,
    ) -> Artifact:
        """
        Load artifact and verify the agent's domain covers it.

        Returns the Artifact on success, raises ArtifactDomainError otherwise.
        """
        artifact = self.get(artifact_id)
        if artifact is None:
            raise ArtifactDomainError(f"Artifact {artifact_id} not found in store")
        allowed = self.allowed_artifact_types_for_agent(agent_profile)
        if artifact.artifact_type not in allowed:
            raise ArtifactDomainError(
                f"Agent '{self.agent_name}' (tools: "
                f"{agent_profile.get('preferred_tools', [])}) cannot claim "
                f"artifact type '{artifact.artifact_type}' "
                f"(artifact {artifact_id})"
            )
        return artifact
