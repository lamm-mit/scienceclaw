"""Proof certificates for categorical execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from categoryscienceclaw.kernel.models import Artifact, MorphismSignature, SCHEMA_VERSION
from categoryscienceclaw.proofs.hashing import canonical_hash


@dataclass(frozen=True)
class Certificate:
    id: str
    kind: str
    ok: bool
    obligations: tuple[dict[str, Any], ...]
    conclusion: dict[str, Any]
    errors: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "kind": self.kind,
            "ok": self.ok,
            "obligations": list(self.obligations),
            "conclusion": self.conclusion,
            "errors": list(self.errors),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Certificate":
        return cls(
            id=str(data["id"]),
            kind=str(data["kind"]),
            ok=bool(data["ok"]),
            obligations=tuple(dict(v) for v in data.get("obligations", [])),
            conclusion=dict(data.get("conclusion", {})),
            errors=tuple(str(v) for v in data.get("errors", [])),
            metadata=dict(data.get("metadata", {})),
        )


def build_execution_certificate(
    *,
    morphism: MorphismSignature,
    inputs: list[Artifact],
    output: Artifact,
    claim_id: str,
) -> Certificate:
    obligations: list[dict[str, Any]] = []
    errors: list[str] = []

    obligations.append(
        {
            "name": "arity",
            "expected": len(morphism.input_types),
            "actual": len(inputs),
            "ok": len(morphism.input_types) == len(inputs),
        }
    )
    if len(morphism.input_types) != len(inputs):
        errors.append("arity mismatch")

    for index, expected_type in enumerate(morphism.input_types):
        actual_type = inputs[index].type if index < len(inputs) else None
        ok = actual_type == expected_type
        obligations.append(
            {
                "name": "input_type",
                "index": index,
                "expected": expected_type,
                "actual": actual_type,
                "ok": ok,
            }
        )
        if not ok:
            errors.append(f"input {index} type mismatch: expected {expected_type}, got {actual_type}")

    output_ok = output.type == morphism.output_type
    obligations.append(
        {
            "name": "output_type",
            "expected": morphism.output_type,
            "actual": output.type,
            "ok": output_ok,
        }
    )
    if not output_ok:
        errors.append(f"output type mismatch: expected {morphism.output_type}, got {output.type}")

    parent_ids = tuple(artifact.id for artifact in inputs)
    parent_ok = tuple(output.parent_ids) == parent_ids
    obligations.append(
        {
            "name": "provenance",
            "expected_parent_ids": list(parent_ids),
            "actual_parent_ids": list(output.parent_ids),
            "ok": parent_ok,
        }
    )
    if not parent_ok:
        errors.append("output parent provenance does not match morphism inputs")

    for artifact in inputs:
        expected_hash = canonical_hash(artifact.payload)
        hash_ok = not artifact.content_hash or artifact.content_hash == expected_hash
        obligations.append(
            {
                "name": "input_hash_matches",
                "artifact_id": artifact.id,
                "expected": expected_hash,
                "actual": artifact.content_hash,
                "ok": hash_ok,
            }
        )
        if not hash_ok:
            errors.append(f"input artifact {artifact.id} content hash mismatch")

    output_hash_ok = not output.content_hash or output.content_hash == canonical_hash(output.payload)
    obligations.append(
        {
            "name": "output_hash_matches",
            "artifact_id": output.id,
            "ok": output_hash_ok,
        }
    )
    if not output_hash_ok:
        errors.append("output content hash mismatch")

    formal = morphism.metadata.get("formal") or {}
    if formal or morphism.kind == "formal_mechanics":
        formal_ok = isinstance(output.payload.get("formal"), dict) and bool(output.payload.get("formal"))
        obligations.append({"name": "formal_metadata_present", "ok": formal_ok})
        if not formal_ok:
            errors.append("formal metadata missing from output payload")

        invariants_ok = bool(output.payload.get("invariants"))
        obligations.append({"name": "invariants_present", "ok": invariants_ok})
        if not invariants_ok:
            errors.append("formal invariants missing from output payload")

        parity_expected = any(
            token in " ".join([morphism.name, morphism.output_type, str(output.payload.get("descriptor_type", ""))]).lower()
            for token in ("parity", "symmetry", "invariance")
        )
        parity_ok = bool(output.payload.get("symmetry") or output.payload.get("parity") or output.payload.get("invariants"))
        obligations.append({"name": "symmetry_or_parity_present", "expected": parity_expected, "ok": (not parity_expected) or parity_ok})
        if parity_expected and not parity_ok:
            errors.append("symmetry/parity metadata missing from output payload")

        source_ids_ok = output.payload.get("source_parent_ids") == [artifact.id for artifact in inputs]
        obligations.append({"name": "source_parent_ids_present", "ok": source_ids_ok})
        if not source_ids_ok:
            errors.append("source_parent_ids missing or inconsistent")

        symbolic_ok = bool(output.payload.get("data_status"))
        obligations.append({"name": "symbolic_status_declared_when_no_real_data", "ok": symbolic_ok})
        if not symbolic_ok:
            errors.append("symbolic/formal data status missing")

        composition_ok = all(parent_id in output.parent_ids for parent_id in [artifact.id for artifact in inputs])
        obligations.append({"name": "composition_path_valid", "ok": composition_ok})
        if not composition_ok:
            errors.append("composition path does not include all inputs")

    conclusion = {
        "morphism": morphism.name,
        "input_artifact_ids": [artifact.id for artifact in inputs],
        "output_artifact_id": output.id,
        "output_content_hash": output.content_hash,
        "claim_id": claim_id,
    }
    raw = {
        "kind": "execution",
        "obligations": obligations,
        "conclusion": conclusion,
        "errors": errors,
    }
    return Certificate(
        id=f"cert-{canonical_hash(raw)}",
        kind="execution",
        ok=not errors,
        obligations=tuple(obligations),
        conclusion=conclusion,
        errors=tuple(errors),
    )


def check_certificate(certificate: Certificate) -> list[str]:
    errors = list(certificate.errors)
    for obligation in certificate.obligations:
        if not obligation.get("ok", False):
            errors.append(f"failed obligation: {obligation.get('name', 'unknown')}")
    if certificate.ok and errors:
        errors.append("certificate claims ok=true but has failed obligations")
    if not certificate.ok and not errors:
        errors.append("certificate claims ok=false but has no failed obligations")
    return errors
