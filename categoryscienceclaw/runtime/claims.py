"""Atomic local claims over needs."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


class ClaimRegistry:
    def __init__(self, claims_path: str | Path):
        self.claims_path = Path(claims_path)
        self.claims_path.parent.mkdir(parents=True, exist_ok=True)
        self.claims_path.touch(exist_ok=True)

    def try_claim(self, need_id: str, agent_name: str) -> str | None:
        claim_id = f"claim:{need_id}:{agent_name}"
        record = {
            "claim_id": claim_id,
            "need_id": need_id,
            "agent": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "released": False,
        }
        fd = os.open(str(self.claims_path), os.O_RDWR | os.O_CREAT)
        try:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_EX)
            claims = self._active_claims_unlocked()
            holder = claims.get(need_id)
            if holder and holder != agent_name:
                return None
            with open(fd, "a", encoding="utf-8", closefd=False) as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
            return claim_id
        finally:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def release(self, need_id: str, agent_name: str) -> None:
        record = {
            "claim_id": f"claim:{need_id}:{agent_name}",
            "need_id": need_id,
            "agent": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "released": True,
        }
        with open(self.claims_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def active_claims(self) -> dict[str, str]:
        return self._active_claims_unlocked()

    def _active_claims_unlocked(self) -> dict[str, str]:
        claims: dict[str, str] = {}
        for line in self.claims_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            need_id = str(record.get("need_id", ""))
            if not need_id:
                continue
            if record.get("released"):
                claims.pop(need_id, None)
            else:
                claims[need_id] = str(record.get("agent", ""))
        return claims
