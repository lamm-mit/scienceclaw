"""
Configuration for Paraxiom trust layer.
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class ParaxiomTrustConfig:
    """Configuration for the Paraxiom trust layer."""

    # Enable PQC artifact signing (opt-in; needs `pip install pqcrypto==1.0.0`)
    signing_enabled: bool = False

    # Signature algorithm: "ml-dsa-87" (FIPS 204)
    sign_algorithm: str = "ml-dsa-87"

    # Key storage directory
    key_dir: str = "~/.scienceclaw/paraxiom_keys"

    # Route LLM calls through the Coherence Shield proxy
    coherence_shield_enabled: bool = False
    coherence_shield_url: str = "http://127.0.0.1:3080"

    # Reserved: QuantumHarmony anchoring is not implemented yet, so this has no effect
    blockchain_enabled: bool = False
    blockchain_ws_url: str = "ws://127.0.0.1:9944"

    # Attestation log (append-only JSONL alongside global_index.jsonl)
    attestation_log: str = "~/.scienceclaw/artifacts/attestations.jsonl"

    @classmethod
    def load(cls, path: str = "~/.scienceclaw/paraxiom_trust.json") -> "ParaxiomTrustConfig":
        p = Path(path).expanduser()
        if p.exists():
            with open(p) as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()

    def save(self, path: str = "~/.scienceclaw/paraxiom_trust.json") -> None:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(asdict(self), f, indent=2)
