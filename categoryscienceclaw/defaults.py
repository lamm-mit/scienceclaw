"""Default objects and morphisms for the first vertical slice."""

from __future__ import annotations

from categoryscienceclaw.kernel.models import MorphismSignature, ObjectType


def default_objects() -> list[ObjectType]:
    return [
        ObjectType("ResearchQuestion", kind="workflow"),
        ObjectType("LiteratureEvidence"),
        ObjectType("ComputationalAnalysis"),
        ObjectType("Claim"),
    ]


def default_morphisms() -> list[MorphismSignature]:
    return [
        MorphismSignature(
            name="literature_search",
            input_types=("ResearchQuestion",),
            output_type="LiteratureEvidence",
            kind="skill",
            adapter="local",
            metadata={
                "emits_needs": [
                    {
                        "required_type": "ComputationalAnalysis",
                        "query": "analyze the same mechanism computationally",
                        "rationale": "A claim requires computational evidence in addition to literature evidence.",
                        "allowed_morphisms": ["computational_analysis"],
                    }
                ]
            },
        ),
        MorphismSignature(
            name="computational_analysis",
            input_types=("LiteratureEvidence",),
            output_type="ComputationalAnalysis",
            kind="skill",
            adapter="local",
            metadata={
                "emits_needs": [
                    {
                        "required_type": "Claim",
                        "query": "synthesize literature and computational evidence",
                        "rationale": "Produce a typed claim after both evidence streams exist.",
                        "allowed_morphisms": ["synthesize_claim"],
                    }
                ]
            },
        ),
        MorphismSignature(
            name="synthesize_claim",
            input_types=("ComputationalAnalysis", "LiteratureEvidence"),
            output_type="Claim",
            kind="synthesis",
            adapter="local",
        ),
    ]
