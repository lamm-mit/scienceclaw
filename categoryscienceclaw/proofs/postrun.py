"""Certificates for post-run imported ScienceClaw traces."""

from __future__ import annotations

from typing import Any

from categoryscienceclaw.proofs.certificates import Certificate
from categoryscienceclaw.proofs.hashing import canonical_hash


def build_postrun_certificate(
    *,
    kind: str,
    obligations: list[dict[str, Any]],
    conclusion: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> Certificate:
    errors = [
        str(obligation.get("error") or f"failed obligation: {obligation.get('name', 'unknown')}")
        for obligation in obligations
        if not obligation.get("ok", False)
    ]
    raw = {
        "kind": kind,
        "obligations": obligations,
        "conclusion": conclusion,
        "errors": errors,
        "metadata": metadata or {},
    }
    return Certificate(
        id=f"cert-{canonical_hash(raw)}",
        kind=kind,
        ok=not errors,
        obligations=tuple(obligations),
        conclusion=conclusion,
        errors=tuple(errors),
        metadata=dict(metadata or {}),
    )
