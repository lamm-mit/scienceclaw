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


class NeedsSignal(BaseModel):
    needs: List[NeedItem] = Field(default_factory=list, max_length=2)
