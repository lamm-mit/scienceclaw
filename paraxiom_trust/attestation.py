"""
Paraxiom Attestation Layer for ScienceClaw

Signs artifacts with ML-DSA-87 (FIPS 204), a post-quantum signature scheme,
through the pqcrypto package (pip install pqcrypto==1.0.0).
Verifies artifact integrity against the agent's own public key.

Signing is opt-in: set "signing_enabled": true in
~/.scienceclaw/paraxiom_trust.json. When it is enabled and the library is
missing, or a key is unusable, this module raises TrustLayerError instead of
writing a record that is not a real signature.
"""

import hashlib
import importlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import ParaxiomTrustConfig


# sign_algorithm value -> pqcrypto module
SUPPORTED_ALGORITHMS = {"ml-dsa-87": "pqcrypto.sign.ml_dsa_87"}

# FIPS 204 context string, bound into every signature so a ScienceClaw
# attestation can't be passed off as a signature over anything else.
SIGNING_CONTEXT = b"scienceclaw-attestation-v1"


class TrustLayerError(RuntimeError):
    """Signing was requested but cannot be done safely."""


@dataclass
class ArtifactAttestation:
    """Cryptographic attestation for a ScienceClaw artifact."""

    # What we're attesting
    artifact_id: str
    content_hash: str  # SHA3-256 of canonical artifact JSON
    producer_agent: str
    skill_used: str
    timestamp: str  # ISO 8601

    # PQC signature
    signature_algorithm: str  # "ml-dsa-87"
    signature: str  # hex-encoded ML-DSA signature over attestation payload
    public_key_fingerprint: str  # SHA256 of agent's public key

    # Lineage
    parent_artifact_ids: list
    investigation_id: str

    # Reserved for QuantumHarmony anchoring (not implemented yet)
    blockchain_tx: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


def _load_backend(algorithm: str):
    """Return the pqcrypto module for `algorithm`, or raise TrustLayerError."""
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise TrustLayerError(
            f"Unsupported sign_algorithm {algorithm!r} in paraxiom_trust.json "
            f"(supported: {', '.join(sorted(SUPPORTED_ALGORITHMS))})"
        )
    try:
        return importlib.import_module(SUPPORTED_ALGORITHMS[algorithm])
    except ImportError as e:
        raise TrustLayerError(
            "Artifact signing is enabled but pqcrypto is not installed. "
            "Run `pip install pqcrypto==1.0.0` or set signing_enabled to false."
        ) from e


class AttestationLayer:
    """
    Manages PQC key generation, artifact signing, and verification.

    Key storage: ~/.scienceclaw/paraxiom_keys/{agent_name}/
        - ml-dsa-87.sk (secret key, mode 0600)
        - ml-dsa-87.pk (public key)

    Key files from earlier versions (signing_key.bin, verification_key.bin)
    are never read.

    verify() checks records against this agent's own public key only.
    """

    def __init__(self, agent_name: str, config: Optional[ParaxiomTrustConfig] = None):
        self.agent_name = agent_name
        self.config = config or ParaxiomTrustConfig.load()
        self.key_dir = Path(self.config.key_dir).expanduser() / agent_name
        self.attestation_log = Path(self.config.attestation_log).expanduser()
        self.algorithm = self.config.sign_algorithm

        self._backend = None
        self._sk: Optional[bytes] = None
        self._pk: Optional[bytes] = None
        self._fingerprint: Optional[str] = None

        if self.config.signing_enabled:
            self._backend = _load_backend(self.algorithm)
            self._ensure_keys()

    def _ensure_keys(self) -> None:
        """Load this agent's key pair, generating it on first use."""
        self.key_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        sk_path = self.key_dir / f"{self.algorithm}.sk"
        pk_path = self.key_dir / f"{self.algorithm}.pk"

        if not sk_path.exists() and not pk_path.exists():
            pk, sk = self._backend.keygen()
            fd = os.open(sk_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(sk)
            pk_path.write_bytes(pk)

        try:
            sk, pk = sk_path.read_bytes(), pk_path.read_bytes()
        except FileNotFoundError as e:
            raise TrustLayerError(f"Incomplete key pair in {self.key_dir}: {e.filename} is missing") from e

        if len(sk) != self._backend.SECRET_KEY_SIZE or len(pk) != self._backend.PUBLIC_KEY_SIZE:
            raise TrustLayerError(f"Key files in {self.key_dir} have the wrong size for {self.algorithm}")

        # Check that the two halves belong together before signing real records.
        probe = b"scienceclaw key check"
        try:
            self._backend.verify(pk, probe, self._backend.sign(sk, probe, SIGNING_CONTEXT), SIGNING_CONTEXT)
        except Exception as e:
            raise TrustLayerError(f"Key pair in {self.key_dir} failed its self-check") from e

        self._sk, self._pk = sk, pk
        self._fingerprint = hashlib.sha256(pk).hexdigest()[:32]

    def _require_keys(self) -> None:
        if self._sk is None:
            raise TrustLayerError("Artifact signing is disabled (signing_enabled is false in paraxiom_trust.json)")

    def attest(self, artifact_dict: dict) -> ArtifactAttestation:
        """
        Create a cryptographic attestation for an artifact.

        1. Compute SHA3-256 content hash of the artifact payload
        2. Sign the attestation payload with ML-DSA
        3. Return the attestation record
        4. Append to attestation log
        """
        self._require_keys()

        # Content hash (SHA3-256 for quantum resistance)
        canonical = json.dumps(artifact_dict.get("payload", {}), sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha3_256(canonical.encode()).hexdigest()

        # Build attestation payload for signing
        attest_payload = {
            "artifact_id": artifact_dict["artifact_id"],
            "content_hash": content_hash,
            "producer_agent": artifact_dict["producer_agent"],
            "skill_used": artifact_dict["skill_used"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "parent_artifact_ids": artifact_dict.get("parent_artifact_ids", []),
        }

        # Sign
        sig_hex = self._sign(json.dumps(attest_payload, sort_keys=True).encode())

        attestation = ArtifactAttestation(
            artifact_id=artifact_dict["artifact_id"],
            content_hash=content_hash,
            producer_agent=artifact_dict["producer_agent"],
            skill_used=artifact_dict["skill_used"],
            timestamp=attest_payload["timestamp"],
            signature_algorithm=self.algorithm,
            signature=sig_hex,
            public_key_fingerprint=self._fingerprint,
            parent_artifact_ids=artifact_dict.get("parent_artifact_ids", []),
            investigation_id=artifact_dict.get("investigation_id", ""),
        )

        # Append to attestation log
        self._log_attestation(attestation)

        return attestation

    def verify(self, attestation: ArtifactAttestation, artifact_dict: dict) -> bool:
        """
        Verify an attestation made by this agent.

        1. Recompute content hash and check it matches
        2. Check the record names this agent's algorithm and key
        3. Verify the PQC signature
        """
        self._require_keys()

        # Check content hash
        canonical = json.dumps(artifact_dict.get("payload", {}), sort_keys=True, ensure_ascii=False)
        expected_hash = hashlib.sha3_256(canonical.encode()).hexdigest()
        if attestation.content_hash != expected_hash:
            return False

        # Records from earlier versions say "falcon512" but carry an HMAC tag
        # ("hmac_..."), which is not a signature; they fail here.
        if attestation.signature_algorithm != self.algorithm:
            return False
        if attestation.public_key_fingerprint != self._fingerprint:
            return False

        # Rebuild attestation payload
        attest_payload = {
            "artifact_id": attestation.artifact_id,
            "content_hash": attestation.content_hash,
            "producer_agent": attestation.producer_agent,
            "skill_used": attestation.skill_used,
            "timestamp": attestation.timestamp,
            "parent_artifact_ids": attestation.parent_artifact_ids,
        }

        # Verify signature
        return self._verify(
            json.dumps(attest_payload, sort_keys=True).encode(),
            attestation.signature,
        )

    def _sign(self, message: bytes) -> str:
        """Sign a message with the agent's ML-DSA key."""
        return self._backend.sign(self._sk, message, SIGNING_CONTEXT).hex()

    def _verify(self, message: bytes, signature_hex: str) -> bool:
        """Verify an ML-DSA signature against the agent's public key."""
        try:
            self._backend.verify(self._pk, message, bytes.fromhex(signature_hex), SIGNING_CONTEXT)
            return True
        except ValueError:
            # Bad hex, wrong length, or pqcrypto.InvalidSignatureError
            return False

    def _log_attestation(self, attestation: ArtifactAttestation) -> None:
        """Append attestation to the attestation log."""
        self.attestation_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.attestation_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(attestation.to_dict(), sort_keys=True) + "\n")
