"""
NeedsSignal — structured model for LLM-generated investigation needs.

An agent emits a NeedsSignal on each synthesis artifact to broadcast what
data it is missing.  Peer agents scan these signals and, when they can
produce the requested artifact type, react by running the appropriate skill
and attaching a child artifact that satisfies the need.
"""

from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field

ArtifactTypeLiteral = Literal[
    "pubmed_results", "protein_data", "sequence_alignment", "structure_data",
    "compound_data", "admet_prediction", "rdkit_properties", "pathway_data",
    "network_data", "genomic_data", "expression_data", "clinical_data",
    "drug_data", "metabolomics_data", "ml_prediction", "figure", "synthesis",
    # Protein design / evolution (real design components)
    "sequence_design",
    # Convergence / ranking (optional but useful for “branch then converge” DAGs)
    "ranking_table",
    "variant_set",
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
