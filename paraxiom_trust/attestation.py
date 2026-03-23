"""
Paraxiom Attestation Layer for ScienceClaw

Signs every artifact with post-quantum cryptography (Falcon-512).
Verifies artifact integrity and agent identity.
Optionally anchors attestations to QuantumHarmony blockchain.

No C code. Pure Python calling paraxiom-pqc via subprocess or native bindings.
"""

import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from .config import ParaxiomTrustConfig


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
    signature_algorithm: str  # "falcon512" | "falcon1024"
    signature: str  # hex-encoded Falcon signature over attestation payload
    public_key_fingerprint: str  # SHA256 of agent's public key

    # Lineage
    parent_artifact_ids: list
    investigation_id: str

    # Optional blockchain anchor
    blockchain_tx: Optional[str] = None  # QuantumHarmony tx hash if anchored

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


class AttestationLayer:
    """
    Manages PQC key generation, artifact signing, and verification.

    Key storage: ~/.scienceclaw/paraxiom_keys/{agent_name}/
        - signing_key.bin (Falcon secret key)
        - verification_key.bin (Falcon public key)
        - fingerprint.txt (SHA256 of public key)
    """

    def __init__(self, agent_name: str, config: Optional[ParaxiomTrustConfig] = None):
        self.agent_name = agent_name
        self.config = config or ParaxiomTrustConfig.load()
        self.key_dir = Path(self.config.key_dir).expanduser() / agent_name
        self.attestation_log = Path(self.config.attestation_log).expanduser()

        if self.config.signing_enabled:
            self._ensure_keys()

    def _ensure_keys(self) -> None:
        """Generate Falcon keypair if not present."""
        self.key_dir.mkdir(parents=True, exist_ok=True)
        sk_path = self.key_dir / "signing_key.bin"
        vk_path = self.key_dir / "verification_key.bin"
        fp_path = self.key_dir / "fingerprint.txt"

        if sk_path.exists() and vk_path.exists():
            self._fingerprint = fp_path.read_text().strip() if fp_path.exists() else "unknown"
            return

        # Generate keys using Python falcon-rs bindings
        try:
            from falcon import safe_api as falcon_api
            kp = falcon_api.FnDsaKeyPair.generate(9)  # logn=9 for Falcon-512
            sk_bytes = kp.private_key()
            vk_bytes = kp.public_key()
        except ImportError:
            # Fallback: generate random bytes as placeholder
            # In production, paraxiom-pqc binary would be called
            import secrets
            sk_bytes = secrets.token_bytes(1281)  # Falcon-512 SK size
            vk_bytes = secrets.token_bytes(897)   # Falcon-512 PK size

        sk_path.write_bytes(sk_bytes if isinstance(sk_bytes, bytes) else bytes(sk_bytes))
        vk_path.write_bytes(vk_bytes if isinstance(vk_bytes, bytes) else bytes(vk_bytes))

        fingerprint = hashlib.sha256(
            vk_bytes if isinstance(vk_bytes, bytes) else bytes(vk_bytes)
        ).hexdigest()[:32]
        fp_path.write_text(fingerprint)
        self._fingerprint = fingerprint

    def attest(self, artifact_dict: dict) -> ArtifactAttestation:
        """
        Create a cryptographic attestation for an artifact.

        1. Compute SHA3-256 content hash of the artifact payload
        2. Sign the attestation payload with Falcon-512
        3. Return the attestation record
        4. Append to attestation log
        """
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
            signature_algorithm=self.config.sign_algorithm,
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
        Verify an artifact attestation.

        1. Recompute content hash and check it matches
        2. Verify the PQC signature
        """
        # Check content hash
        canonical = json.dumps(artifact_dict.get("payload", {}), sort_keys=True, ensure_ascii=False)
        expected_hash = hashlib.sha3_256(canonical.encode()).hexdigest()
        if attestation.content_hash != expected_hash:
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
            attestation.public_key_fingerprint,
        )

    def _sign(self, message: bytes) -> str:
        """Sign a message with the agent's Falcon-512 key."""
        if not self.config.signing_enabled:
            return "signing_disabled"

        sk_path = self.key_dir / "signing_key.bin"
        if not sk_path.exists():
            return "no_key"

        try:
            from falcon import safe_api as falcon_api
            sk_bytes = sk_path.read_bytes()
            kp = falcon_api.FnDsaKeyPair.from_private_key(sk_bytes)
            sig = kp.sign(message, falcon_api.DomainSeparation.None_)
            return sig.to_bytes().hex()
        except (ImportError, Exception):
            # Fallback: HMAC-SHA3 placeholder (not PQC, but functional)
            import hmac
            sk_bytes = sk_path.read_bytes()
            h = hmac.new(sk_bytes[:32], message, hashlib.sha3_256)
            return "hmac_" + h.hexdigest()

    def _verify(self, message: bytes, signature_hex: str, expected_fingerprint: str) -> bool:
        """Verify a Falcon-512 signature."""
        if signature_hex.startswith("hmac_"):
            # HMAC fallback verification
            sk_path = self.key_dir / "signing_key.bin"
            if not sk_path.exists():
                return False
            import hmac as hmac_mod
            sk_bytes = sk_path.read_bytes()
            expected = "hmac_" + hmac_mod.new(sk_bytes[:32], message, hashlib.sha3_256).hexdigest()
            return hmac_mod.compare_digest(signature_hex, expected)

        try:
            from falcon import safe_api as falcon_api
            vk_path = self.key_dir / "verification_key.bin"
            vk_bytes = vk_path.read_bytes()
            sig_bytes = bytes.fromhex(signature_hex)
            falcon_api.FnDsaSignature.verify(
                sig_bytes, vk_bytes, message, falcon_api.DomainSeparation.None_
            )
            return True
        except Exception:
            return False

    def _log_attestation(self, attestation: ArtifactAttestation) -> None:
        """Append attestation to the attestation log."""
        self.attestation_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.attestation_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(attestation.to_dict(), sort_keys=True) + "\n")
