"""Post-run formalization for ScienceClaw actual-run directories."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from categoryscienceclaw.kernel.models import (
    AgentProfile,
    Artifact,
    MorphismSignature,
    Need,
    ObjectType,
    now_utc,
)
from categoryscienceclaw.proofs.hashing import canonical_hash
from categoryscienceclaw.proofs.postrun import build_postrun_certificate
from categoryscienceclaw.runtime.events import Event
from categoryscienceclaw.runtime.store import RunStore


BASE_OBJECTS = {
    "ResearchQuestion": "workflow",
    "OpenNeed": "workflow",
    "AgentProposal": "agent",
    "StructureMetadata": "artifact",
    "ContactGraph": "artifact",
    "SequenceDescriptor": "artifact",
    "MDTrajectory": "artifact",
    "ForceExtensionTrace": "artifact",
    "MechanicsModel": "artifact",
    "AtomisticStructure": "artifact",
    "Claim": "artifact",
    "ValidationMetric": "verifier",
    "ValidationRecord": "verifier",
    "DiscoursePost": "discourse",
}

SOURCE_ALIASES = {
    "contact_claim_7T10": "synthesized_claim_7T10.json",
    "atomistic_villin_structure_1L2Y": "atomistic_villin_prepared_1L2Y.pdb",
    "atomistic_villin_force_extension_1L2Y": "atomistic_villin_smd_force_extension_1L2Y.json",
}


def formalize_actual_run(
    *,
    actual_run_dir: str | Path,
    output_run_dir: str | Path,
    session_filename: str = "generated_session_with_downstream_needs.json",
) -> dict[str, int]:
    actual_dir = Path(actual_run_dir)
    session_path = actual_dir / session_filename
    session = json.loads(session_path.read_text(encoding="utf-8"))
    hashes = _load_hashes(actual_dir)

    store = RunStore(output_run_dir)
    store.init()

    objects = _objects_from_session(session)
    downstream_payload = _load_downstream_needs(actual_dir)
    for need in downstream_payload.get("open_needs", []):
        desired = need.get("desired_artifact_type")
        if desired:
            objects.setdefault(desired, ObjectType(name=desired, kind="artifact"))

    morphisms = _morphisms_from_session(session)
    store.write_schema(
        objects=objects.values(),
        morphisms=morphisms.values(),
        topic=session.get("question", {}).get("text", ""),
    )
    store.write_agents(_agents_from_session(session))

    artifacts: dict[str, Artifact] = {}
    question = _question_artifact(session)
    artifacts[question.id] = question
    store.append_artifact(question)
    store.append_event(
        Event(
            type="PostRunFormalized",
            agent="categoryscienceclaw",
            data={
                "source_dir": str(actual_dir),
                "session": session_filename,
                "question_artifact_id": question.id,
            },
        )
    )

    for raw in session.get("artifacts", []):
        artifact = _artifact_from_raw(raw, actual_dir, hashes)
        artifacts[artifact.id] = artifact
        store.append_artifact(artifact)
        store.append_event(
            Event(
                type="ArtifactImported",
                agent=artifact.producer_agent,
                data={"artifact_id": artifact.id, "type": artifact.type, "source": artifact.metadata.get("source_path", "")},
            )
        )

    for raw in session.get("validations", []):
        artifact = _validation_artifact(raw)
        artifacts[artifact.id] = artifact
        store.append_artifact(artifact)

    for raw in session.get("publications", []):
        artifact = _publication_artifact(raw)
        artifacts[artifact.id] = artifact
        store.append_artifact(artifact)

    certificates = []
    for artifact in artifacts.values():
        if not artifact.morphism:
            continue
        morphism = morphisms.get(artifact.morphism)
        if not morphism:
            continue
        cert = _execution_certificate(morphism, artifact, artifacts)
        certificates.append(cert)
        store.write_certificate(cert)
        store.append_event(
            Event(
                type="CertificateEmitted",
                agent="categoryscienceclaw",
                data={"certificate_id": cert.id, "artifact_id": artifact.id, "ok": cert.ok},
            )
        )

    open_needs = _append_downstream_needs(store, downstream_payload)
    return {
        "artifacts": len(artifacts),
        "certificates": len(certificates),
        "open_needs": open_needs,
        "objects": len(objects),
        "morphisms": len(morphisms),
    }


def _objects_from_session(session: dict[str, Any]) -> dict[str, ObjectType]:
    objects = {name: ObjectType(name=name, kind=kind) for name, kind in BASE_OBJECTS.items()}
    for raw in session.get("schema", {}).get("objects", []):
        objects[raw["name"]] = ObjectType(
            name=raw["name"],
            kind=raw.get("kind", "artifact"),
            description=raw.get("description", ""),
        )
    for raw in session.get("artifacts", []):
        objects.setdefault(raw["type"], ObjectType(name=raw["type"]))
    return objects


def _morphisms_from_session(session: dict[str, Any]) -> dict[str, MorphismSignature]:
    morphisms: dict[str, MorphismSignature] = {}
    for raw in session.get("schema", {}).get("morphisms", []):
        morphism = MorphismSignature(
            name=raw["name"],
            input_types=tuple(raw.get("input_types", [])),
            output_type=raw["output_type"],
            kind=raw.get("kind", "skill"),
            description=raw.get("description", ""),
            adapter="postrun",
            metadata={"source": "scienceclaw_actual_run"},
        )
        morphisms[morphism.name] = morphism
    morphisms.setdefault(
        "validate_claim",
        MorphismSignature(
            name="validate_claim",
            input_types=("Claim",),
            output_type="ValidationRecord",
            kind="validation",
            adapter="postrun",
        ),
    )
    morphisms.setdefault(
        "publish_claim",
        MorphismSignature(
            name="publish_claim",
            input_types=("Claim",),
            output_type="DiscoursePost",
            kind="publication",
            adapter="postrun",
        ),
    )
    return morphisms


def _agents_from_session(session: dict[str, Any]) -> list[AgentProfile]:
    producer_to_morphisms: dict[str, set[str]] = {}
    for raw in session.get("artifacts", []):
        producer = raw.get("producer") or "unknown"
        producer_to_morphisms.setdefault(producer, set())
        if raw.get("morphism"):
            producer_to_morphisms[producer].add(raw["morphism"])
    for raw in session.get("validations", []):
        producer_to_morphisms.setdefault(raw.get("validator") or "ValidatorAgent", set()).add("validate_claim")
    for raw in session.get("publications", []):
        producer_to_morphisms.setdefault(raw.get("producer") or "PublisherAgent", set()).add("publish_claim")
    return [
        AgentProfile(name=name, morphisms=tuple(sorted(morphisms)))
        for name, morphisms in sorted(producer_to_morphisms.items())
    ]


def _question_artifact(session: dict[str, Any]) -> Artifact:
    question = session.get("question", {})
    payload = {"text": question.get("text", ""), "session_id": session.get("id", "")}
    return Artifact(
        id=question.get("id", "question"),
        type="ResearchQuestion",
        payload=payload,
        producer_agent=session.get("created_by", "ScienceClaw"),
        timestamp=now_utc(),
        content_hash=canonical_hash(payload),
    )


def _artifact_from_raw(raw: dict[str, Any], actual_dir: Path, hashes: dict[str, str]) -> Artifact:
    source_name = _source_name_for_artifact(raw["id"], actual_dir, hashes)
    metadata = {key: value for key, value in raw.items() if key not in {"id", "type", "parents", "producer", "morphism"}}
    if source_name:
        metadata["source_path"] = str(actual_dir / source_name)
        metadata["source_name"] = source_name
        if source_name in hashes:
            metadata["source_sha256"] = hashes[source_name]
            metadata["source_sha256_verified"] = _sha256_file(actual_dir / source_name) == hashes[source_name]
    payload = {
        "summary": raw.get("summary", ""),
        "source_name": metadata.get("source_name", ""),
        "source_sha256": metadata.get("source_sha256", ""),
    }
    return Artifact(
        id=raw["id"],
        type=raw["type"],
        payload=payload,
        producer_agent=raw.get("producer") or "unknown",
        morphism=raw.get("morphism", ""),
        parent_ids=tuple(raw.get("parents", []) or []),
        timestamp=now_utc(),
        content_hash=canonical_hash(payload),
        metadata=metadata,
    )


def _validation_artifact(raw: dict[str, Any]) -> Artifact:
    target = raw.get("target", "")
    payload = {"status": raw.get("status", ""), "reasoning": raw.get("reasoning", "")}
    return Artifact(
        id=raw["id"],
        type="ValidationRecord",
        payload=payload,
        producer_agent=raw.get("validator") or raw.get("challenger") or "ValidatorAgent",
        morphism="validate_claim",
        parent_ids=(target,) if target else (),
        timestamp=now_utc(),
        content_hash=canonical_hash(payload),
        metadata=dict(raw),
    )


def _publication_artifact(raw: dict[str, Any]) -> Artifact:
    source = raw.get("source", "")
    payload = {"community": raw.get("community", ""), "url": raw.get("url", "")}
    return Artifact(
        id=raw["id"],
        type="DiscoursePost",
        payload=payload,
        producer_agent=raw.get("producer") or "PublisherAgent",
        morphism="publish_claim",
        parent_ids=(source,) if source else (),
        timestamp=now_utc(),
        content_hash=canonical_hash(payload),
        metadata=dict(raw),
    )


def _execution_certificate(
    morphism: MorphismSignature,
    artifact: Artifact,
    artifacts: dict[str, Artifact],
):
    inputs = [artifacts[parent_id] for parent_id in artifact.parent_ids if parent_id in artifacts]
    obligations: list[dict[str, Any]] = []
    obligations.append(
        {
            "name": "arity",
            "expected": len(morphism.input_types),
            "actual": len(inputs),
            "ok": len(morphism.input_types) == len(inputs),
        }
    )
    for index, expected_type in enumerate(morphism.input_types):
        actual_type = inputs[index].type if index < len(inputs) else None
        obligations.append(
            {
                "name": "input_type",
                "index": index,
                "expected": expected_type,
                "actual": actual_type,
                "ok": actual_type == expected_type,
            }
        )
    obligations.append(
        {
            "name": "output_type",
            "expected": morphism.output_type,
            "actual": artifact.type,
            "ok": artifact.type == morphism.output_type,
        }
    )
    obligations.append(
        {
            "name": "provenance",
            "expected_parent_ids": list(artifact.parent_ids),
            "actual_parent_ids": [input_artifact.id for input_artifact in inputs],
            "ok": tuple(input_artifact.id for input_artifact in inputs) == tuple(artifact.parent_ids),
        }
    )
    if artifact.metadata.get("source_sha256"):
        obligations.append(
            {
                "name": "recorded_source_sha256",
                "source": artifact.metadata.get("source_name", ""),
                "expected": artifact.metadata["source_sha256"],
                "actual": artifact.metadata["source_sha256"],
                "verified_against_current_file": bool(artifact.metadata.get("source_sha256_verified")),
                "ok": bool(artifact.metadata.get("source_sha256")) and bool(artifact.metadata.get("source_path")),
            }
        )
    return build_postrun_certificate(
        kind=f"postrun.{morphism.kind}",
        obligations=obligations,
        conclusion={
            "morphism": morphism.name,
            "input_artifact_ids": list(artifact.parent_ids),
            "output_artifact_id": artifact.id,
            "output_content_hash": artifact.content_hash,
        },
        metadata={"producer_agent": artifact.producer_agent, "source_path": artifact.metadata.get("source_path", "")},
    )


def _append_downstream_needs(store: RunStore, downstream_payload: dict[str, Any]) -> int:
    count = 0
    for index, raw in enumerate(downstream_payload.get("open_needs", [])):
        parent = raw.get("parent_claim_or_artifact", "")
        desired_type = raw.get("desired_artifact_type", "")
        if not parent or not desired_type:
            continue
        need = Need(
            id=raw.get("id") or f"need:{parent}:{index}",
            parent_artifact_id=parent,
            need_index=index,
            required_type=desired_type,
            query=raw.get("query", ""),
            rationale="; ".join(raw.get("acceptance_criteria", []) or []),
            allowed_morphisms=(),
            status=raw.get("status", "open"),
            created_at=now_utc(),
            metadata={
                "producer": raw.get("producer", ""),
                "preferred_skills": raw.get("preferred_skills", []),
                "acceptance_criteria": raw.get("acceptance_criteria", []),
                "source": "downstream_agent_open_needs.json",
            },
        )
        store.append_need(need)
        store.append_event(
            Event(
                type="NeedAdvertised",
                agent=raw.get("producer", "categoryscienceclaw"),
                data={"need_id": need.id, "parent_artifact_id": parent, "required_type": desired_type},
            )
        )
        count += 1
    return count


def _load_hashes(actual_dir: Path) -> dict[str, str]:
    path = actual_dir / "artifact_hashes.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_downstream_needs(actual_dir: Path) -> dict[str, Any]:
    path = actual_dir / "downstream_agent_open_needs.json"
    if not path.exists():
        return {"open_needs": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _source_name_for_artifact(artifact_id: str, actual_dir: Path, hashes: dict[str, str]) -> str:
    if artifact_id in SOURCE_ALIASES:
        return SOURCE_ALIASES[artifact_id]
    candidates = [
        f"{artifact_id}.json",
        f"{artifact_id}.csv",
        f"{artifact_id}.pdb",
        artifact_id.replace("contact_claim", "synthesized_claim") + ".json",
    ]
    for candidate in candidates:
        if candidate in hashes or (actual_dir / candidate).exists():
            return candidate
    return ""


def _sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
