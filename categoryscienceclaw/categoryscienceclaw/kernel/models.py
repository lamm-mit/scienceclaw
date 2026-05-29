"""Core categorical data structures.

The kernel intentionally uses small dataclasses and explicit dictionaries. This
keeps the v1 runtime easy to inspect and avoids framework lock-in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from categoryscienceclaw.proofs.hashing import canonical_hash


SCHEMA_VERSION = "categoryscienceclaw.v1"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ObjectType:
    name: str
    kind: str = "artifact"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "kind": self.kind,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObjectType":
        return cls(
            name=str(data["name"]),
            kind=str(data.get("kind", "artifact")),
            description=str(data.get("description", "")),
        )


@dataclass(frozen=True)
class MorphismSignature:
    name: str
    input_types: tuple[str, ...]
    output_type: str
    kind: str = "skill"
    description: str = ""
    adapter: str = "local"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "input_types": list(self.input_types),
            "output_type": self.output_type,
            "kind": self.kind,
            "description": self.description,
            "adapter": self.adapter,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MorphismSignature":
        return cls(
            name=str(data["name"]),
            input_types=tuple(str(v) for v in data.get("input_types", [])),
            output_type=str(data["output_type"]),
            kind=str(data.get("kind", "skill")),
            description=str(data.get("description", "")),
            adapter=str(data.get("adapter", "local")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class Artifact:
    id: str
    type: str
    payload: dict[str, Any]
    producer_agent: str
    morphism: str = ""
    parent_ids: tuple[str, ...] = ()
    timestamp: str = field(default_factory=now_utc)
    content_hash: str = ""
    needs: tuple["Need", ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        artifact_type: str,
        payload: dict[str, Any],
        producer_agent: str,
        morphism: str = "",
        parent_ids: tuple[str, ...] | list[str] = (),
        needs: tuple["Need", ...] | list["Need"] = (),
        metadata: dict[str, Any] | None = None,
    ) -> "Artifact":
        artifact_id = f"art-{uuid4().hex}"
        chash = canonical_hash(payload)
        return cls(
            id=artifact_id,
            type=artifact_type,
            payload=dict(payload),
            producer_agent=producer_agent,
            morphism=morphism,
            parent_ids=tuple(parent_ids),
            content_hash=chash,
            needs=tuple(needs),
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "type": self.type,
            "payload": self.payload,
            "producer_agent": self.producer_agent,
            "morphism": self.morphism,
            "parent_ids": list(self.parent_ids),
            "timestamp": self.timestamp,
            "content_hash": self.content_hash,
            "needs": [need.to_dict() for need in self.needs],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Artifact":
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            payload=dict(data.get("payload", {})),
            producer_agent=str(data.get("producer_agent", "")),
            morphism=str(data.get("morphism", "")),
            parent_ids=tuple(str(v) for v in data.get("parent_ids", [])),
            timestamp=str(data.get("timestamp", "")) or now_utc(),
            content_hash=str(data.get("content_hash", "")),
            needs=tuple(Need.from_dict(v) for v in data.get("needs", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class Need:
    id: str
    parent_artifact_id: str
    need_index: int
    required_type: str
    query: str
    rationale: str = ""
    allowed_morphisms: tuple[str, ...] = ()
    status: str = "open"
    created_at: str = field(default_factory=now_utc)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        parent_artifact_id: str,
        need_index: int,
        required_type: str,
        query: str,
        rationale: str = "",
        allowed_morphisms: tuple[str, ...] | list[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> "Need":
        return cls(
            id=f"need:{parent_artifact_id}:{need_index}",
            parent_artifact_id=parent_artifact_id,
            need_index=need_index,
            required_type=required_type,
            query=query,
            rationale=rationale,
            allowed_morphisms=tuple(allowed_morphisms),
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "parent_artifact_id": self.parent_artifact_id,
            "need_index": self.need_index,
            "required_type": self.required_type,
            "query": self.query,
            "rationale": self.rationale,
            "allowed_morphisms": list(self.allowed_morphisms),
            "status": self.status,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Need":
        return cls(
            id=str(data["id"]),
            parent_artifact_id=str(data["parent_artifact_id"]),
            need_index=int(data["need_index"]),
            required_type=str(data["required_type"]),
            query=str(data.get("query", "")),
            rationale=str(data.get("rationale", "")),
            allowed_morphisms=tuple(str(v) for v in data.get("allowed_morphisms", [])),
            status=str(data.get("status", "open")),
            created_at=str(data.get("created_at", "")) or now_utc(),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class AgentProfile:
    name: str
    morphisms: tuple[str, ...] = ()
    preferred_types: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "morphisms": list(self.morphisms),
            "preferred_types": list(self.preferred_types),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentProfile":
        return cls(
            name=str(data["name"]),
            morphisms=tuple(str(v) for v in data.get("morphisms", [])),
            preferred_types=tuple(str(v) for v in data.get("preferred_types", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    payload: dict[str, Any]
    error: str = ""


@dataclass
class CategoricalState:
    objects: dict[str, ObjectType] = field(default_factory=dict)
    morphisms: dict[str, MorphismSignature] = field(default_factory=dict)
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    needs: dict[str, Need] = field(default_factory=dict)

    def add_object(self, obj: ObjectType) -> None:
        self.objects[obj.name] = obj

    def add_morphism(self, morphism: MorphismSignature) -> None:
        self.morphisms[morphism.name] = morphism

    def add_artifact(self, artifact: Artifact) -> None:
        self.artifacts[artifact.id] = artifact
        for need in artifact.needs:
            self.needs[need.id] = need

    def artifact_type(self, artifact_id: str) -> str | None:
        artifact = self.artifacts.get(artifact_id)
        return artifact.type if artifact else None
