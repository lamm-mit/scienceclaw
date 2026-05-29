"""Audit categorical runs and proof certificates."""

from __future__ import annotations

from dataclasses import dataclass, field

from categoryscienceclaw.proofs.certificates import check_certificate
from categoryscienceclaw.proofs.hashing import canonical_hash
from categoryscienceclaw.runtime.store import RunStore


@dataclass
class AuditReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


def audit_run(store: RunStore) -> AuditReport:
    errors: list[str] = []
    warnings: list[str] = []
    objects, morphisms, _topic = store.read_schema()
    artifacts = store.list_artifacts()
    artifact_by_id = {artifact.id: artifact for artifact in artifacts}

    for morphism in morphisms.values():
        for type_name in morphism.input_types:
            if type_name not in objects:
                errors.append(f"morphism {morphism.name} unknown input type {type_name}")
        if morphism.output_type not in objects:
            errors.append(f"morphism {morphism.name} unknown output type {morphism.output_type}")

    for artifact in artifacts:
        if artifact.type not in objects:
            errors.append(f"artifact {artifact.id} unknown type {artifact.type}")
        if artifact.content_hash and artifact.content_hash != canonical_hash(artifact.payload):
            errors.append(f"artifact {artifact.id} content hash mismatch")
        for parent_id in artifact.parent_ids:
            if parent_id not in artifact_by_id:
                errors.append(f"artifact {artifact.id} missing parent {parent_id}")
        if artifact.morphism:
            morphism = morphisms.get(artifact.morphism)
            if not morphism:
                errors.append(f"artifact {artifact.id} unknown morphism {artifact.morphism}")
            elif artifact.type != morphism.output_type:
                errors.append(f"artifact {artifact.id} output type does not match morphism {morphism.name}")

    for cert in store.list_certificates():
        errors.extend(f"{cert.id}: {error}" for error in check_certificate(cert))
        output_id = cert.conclusion.get("output_artifact_id")
        if output_id and output_id not in artifact_by_id:
            errors.append(f"{cert.id}: output artifact missing: {output_id}")

    return AuditReport(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        counts={
            "objects": len(objects),
            "morphisms": len(morphisms),
            "artifacts": len(artifacts),
            "open_needs": len(store.open_needs()),
            "certificates": len(store.list_certificates()),
            "events": len(store.list_events()),
        },
    )
