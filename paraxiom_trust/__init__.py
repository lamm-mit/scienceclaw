"""
Paraxiom Trust Layer for ScienceClaw

Post-quantum cryptographic attestation for autonomous scientific agents.
Every artifact is signed, every claim is verifiable, every lineage is immutable.

Integration points:
- Artifact signing: Falcon-512 signatures on every skill invocation
- Content attestation: SHA3-256 content hash + PQC signature
- Blockchain anchoring: QuantumHarmony on-chain attestation (optional)
- Coherence Shield: LLM output filtering for agent synthesis steps

Paraxiom Technologies Inc. — Montreal
https://paraxiom.org
"""

from .attestation import AttestationLayer, ArtifactAttestation
from .config import ParaxiomTrustConfig

__all__ = ["AttestationLayer", "ArtifactAttestation", "ParaxiomTrustConfig"]
