"""Run-directory storage for decentralized categorical execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from categoryscienceclaw.kernel.models import (
    AgentProfile,
    Artifact,
    MorphismSignature,
    Need,
    ObjectType,
)
from categoryscienceclaw.proofs.certificates import Certificate
from categoryscienceclaw.runtime.events import Event


class RunStore:
    """Small file-backed store rooted in one run directory."""

    def __init__(self, run_dir: str | Path):
        self.run_dir = Path(run_dir)
        self.events_path = self.run_dir / "events.jsonl"
        self.artifacts_path = self.run_dir / "artifacts.jsonl"
        self.needs_path = self.run_dir / "needs.index.jsonl"
        self.claims_path = self.run_dir / "claims.jsonl"
        self.certificates_dir = self.run_dir / "certificates"
        self.schema_path = self.run_dir / "schema.json"
        self.agents_path = self.run_dir / "agents.json"

    def init(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.certificates_dir.mkdir(parents=True, exist_ok=True)
        for path in (self.events_path, self.artifacts_path, self.needs_path, self.claims_path):
            path.touch(exist_ok=True)

    def write_schema(
        self,
        *,
        objects: Iterable[ObjectType],
        morphisms: Iterable[MorphismSignature],
        topic: str,
    ) -> None:
        data = {
            "topic": topic,
            "objects": [obj.to_dict() for obj in objects],
            "morphisms": [morphism.to_dict() for morphism in morphisms],
        }
        self.schema_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def read_schema(self) -> tuple[dict[str, ObjectType], dict[str, MorphismSignature], str]:
        data = json.loads(self.schema_path.read_text(encoding="utf-8"))
        objects = {raw["name"]: ObjectType.from_dict(raw) for raw in data.get("objects", [])}
        morphisms = {
            raw["name"]: MorphismSignature.from_dict(raw)
            for raw in data.get("morphisms", [])
        }
        return objects, morphisms, str(data.get("topic", ""))

    def write_agents(self, agents: Iterable[AgentProfile]) -> None:
        data = {"agents": [agent.to_dict() for agent in agents]}
        self.agents_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def read_agents(self) -> dict[str, AgentProfile]:
        data = json.loads(self.agents_path.read_text(encoding="utf-8"))
        return {raw["name"]: AgentProfile.from_dict(raw) for raw in data.get("agents", [])}

    def append_event(self, event: Event) -> dict[str, Any]:
        record = event.to_dict()
        self._append_jsonl(self.events_path, record)
        return record

    def append_artifact(self, artifact: Artifact) -> None:
        self._append_jsonl(self.artifacts_path, artifact.to_dict())
        for need in artifact.needs:
            self.append_need(need)

    def append_need(self, need: Need) -> None:
        self._append_jsonl(self.needs_path, need.to_dict())

    def close_need(self, need_id: str, fulfilled_by: str) -> None:
        self._append_jsonl(
            self.needs_path,
            {
                "id": need_id,
                "status": "fulfilled",
                "fulfilled_by_artifact_id": fulfilled_by,
            },
        )

    def write_certificate(self, certificate: Certificate) -> Path:
        path = self.certificates_dir / f"{certificate.id}.json"
        path.write_text(json.dumps(certificate.to_dict(), indent=2), encoding="utf-8")
        return path

    def list_events(self) -> list[dict[str, Any]]:
        return self._read_jsonl(self.events_path)

    def list_artifacts(self) -> list[Artifact]:
        return [Artifact.from_dict(raw) for raw in self._read_jsonl(self.artifacts_path)]

    def list_certificates(self) -> list[Certificate]:
        if not self.certificates_dir.exists():
            return []
        certs = []
        for path in sorted(self.certificates_dir.glob("cert-*.json")):
            certs.append(Certificate.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        return certs

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        for artifact in reversed(self.list_artifacts()):
            if artifact.id == artifact_id:
                return artifact
        return None

    def open_needs(self) -> list[Need]:
        latest: dict[str, dict[str, Any]] = {}
        for raw in self._read_jsonl(self.needs_path):
            if "id" in raw:
                latest[str(raw["id"])] = raw
        needs = []
        for raw in latest.values():
            if raw.get("status", "open") == "open" and "required_type" in raw:
                needs.append(Need.from_dict(raw))
        return needs

    @staticmethod
    def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records
