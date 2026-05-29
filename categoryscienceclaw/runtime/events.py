"""Append-only event records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from categoryscienceclaw.kernel.models import SCHEMA_VERSION, now_utc
from categoryscienceclaw.proofs.hashing import canonical_hash


@dataclass(frozen=True)
class Event:
    type: str
    data: dict[str, Any]
    agent: str = ""
    timestamp: str = field(default_factory=now_utc)
    id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": SCHEMA_VERSION,
            "id": self.id or f"evt-{uuid4().hex}",
            "type": self.type,
            "agent": self.agent,
            "timestamp": self.timestamp,
            "data": self.data,
        }
        data["event_hash"] = canonical_hash({k: v for k, v in data.items() if k != "event_hash"})
        return data
