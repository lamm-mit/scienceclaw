"""
NeedsSignal — structured model for LLM-generated investigation needs.

An agent emits a NeedsSignal on each synthesis artifact to broadcast what
data it is missing.  Peer agents scan these signals and, when they can
produce the requested artifact type, react by running the appropriate skill
and attaching a child artifact that satisfies the need.
"""

from __future__ import annotations
import logging
import sys
import os
from pathlib import Path
from typing import List, Literal
from pydantic import BaseModel, Field

_log = logging.getLogger(__name__)

ArtifactTypeLiteral = Literal[
    "pubmed_results", "protein_data", "sequence_alignment", "structure_data",
    "compound_data", "admet_prediction", "rdkit_properties", "molecular_descriptors", "pathway_data",
    "network_data", "genomic_data", "expression_data", "clinical_data",
    "drug_data", "metabolomics_data", "ml_prediction", "figure", "synthesis",
    # Protein design / evolution (real design components)
    "sequence_design",
    # Convergence / ranking (optional but useful for "branch then converge" DAGs)
    "ranking_table",
    "variant_set",
    # Mutation / DAG operations
    "mutation_policy",
    # Peer validation
    "peer_validation",
    # Benchmark / tabular data tasks
    "tabular_data",
    "analysis_result",
    # Materials science
    "material_data",
]


class NeedItem(BaseModel):
    artifact_type: ArtifactTypeLiteral
    query: str = Field(
        ...,
        min_length=5,
        description=(
            "Specific entity or search term — not a paraphrase of the topic"
        ),
    )
    rationale: str = Field(
        ...,
        min_length=20,
        description="Why this artifact would advance the investigation",
    )
    # Branching controls (optional; allows competing hypotheses/analyses per need)
    branch: bool = Field(
        default=False,
        description="If true, allow multiple competing fulfillments for this need.",
    )
    max_variants: int = Field(
        default=1,
        ge=1,
        le=6,
        description="Maximum competing variants to fulfill for this need.",
    )
    preferred_skills: List[str] = Field(
        default_factory=list,
        max_length=8,
        description="Optional list of preferred skills to use for this need.",
    )
    param_variants: List[dict] = Field(
        default_factory=list,
        max_length=6,
        description="Optional list of parameter overrides (each produces a distinct variant).",
    )


class NeedsSignal(BaseModel):
    needs: List[NeedItem] = Field(default_factory=list, max_length=2)


class NeedsSignalBroadcaster:
    """Best-effort broadcaster that POSTs each NeedItem to the Infinite platform API."""

    def _get_infinite_client(self):
        """Return a logged-in InfiniteClient, or None if config is missing/broken."""
        try:
            _here = Path(__file__).resolve().parent.parent  # scienceclaw/
            if str(_here) not in sys.path:
                sys.path.insert(0, str(_here))
            from skills.infinite.scripts.infinite_client import InfiniteClient
            client = InfiniteClient()
            if not client.jwt_token:
                return None
            return client
        except Exception as exc:
            _log.debug("NeedsSignalBroadcaster: could not create InfiniteClient: %s", exc)
            return None

    def broadcast(self, signal: NeedsSignal, artifact_id: str) -> bool:
        """POST each NeedItem separately to /api/needs-signals. Best-effort, returns True if all succeed."""
        if not signal.needs:
            return True
        try:
            client = self._get_infinite_client()
            if client is None:
                return False
            all_ok = True
            for need in signal.needs:
                need_dict = {
                    "artifactType":    need.artifact_type,
                    "query":           need.query,
                    "rationale":       need.rationale,
                    "branch":          need.branch,
                    "maxVariants":     need.max_variants,
                    "preferredSkills": need.preferred_skills,
                    "paramVariants":   need.param_variants,
                }
                try:
                    result = client.broadcast_need(need_dict, artifact_id)
                    if isinstance(result, dict) and result.get("error"):
                        _log.warning(
                            "NeedsSignalBroadcaster: API error broadcasting need '%s': %s",
                            need.query, result["error"],
                        )
                        all_ok = False
                except Exception as exc:
                    _log.warning("NeedsSignalBroadcaster: failed to broadcast need '%s': %s", need.query, exc)
                    all_ok = False
            return all_ok
        except Exception as exc:
            _log.warning("NeedsSignalBroadcaster: failed to broadcast signal: %s", exc)
            return False
