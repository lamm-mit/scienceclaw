"""
Paraxiom Trust Layer for ScienceClaw

Post-quantum cryptographic attestation for autonomous scientific agents.
A signed artifact can be checked later for changes to its content or lineage.

Integration points:
- Artifact signing: ML-DSA-87 (FIPS 204) signatures, opt-in via paraxiom_trust.json
- Content attestation: SHA3-256 content hash + PQC signature
- Blockchain anchoring: QuantumHarmony on-chain attestation (planned, not implemented)
- Coherence Shield: optional routing of LLM calls through the Shield proxy

Paraxiom Technologies Inc. — Montreal
https://paraxiom.org
"""

from .attestation import AttestationLayer, ArtifactAttestation, TrustLayerError
from .config import ParaxiomTrustConfig

__all__ = ["AttestationLayer", "ArtifactAttestation", "ParaxiomTrustConfig", "TrustLayerError"]
