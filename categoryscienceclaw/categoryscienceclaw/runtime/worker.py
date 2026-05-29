"""Decentralized heartbeat worker."""

from __future__ import annotations

from dataclasses import replace

from categoryscienceclaw.kernel.models import AgentProfile, Artifact, MorphismSignature, Need
from categoryscienceclaw.proofs.certificates import build_execution_certificate
from categoryscienceclaw.runtime.claims import ClaimRegistry
from categoryscienceclaw.runtime.events import Event
from categoryscienceclaw.runtime.executors import ExecutorRegistry
from categoryscienceclaw.runtime.pressure import rank_needs
from categoryscienceclaw.runtime.store import RunStore


class Worker:
    def __init__(
        self,
        *,
        store: RunStore,
        agent: AgentProfile,
        executors: ExecutorRegistry,
    ):
        self.store = store
        self.agent = agent
        self.executors = executors
        self.claims = ClaimRegistry(store.claims_path)

    def heartbeat(self) -> list[Artifact]:
        objects, morphisms, _topic = self.store.read_schema()
        del objects
        open_needs = self.store.open_needs()
        agent_morphisms = {
            name: morphisms[name]
            for name in self.agent.morphisms
            if name in morphisms
        }
        output_types = {morphism.output_type for morphism in agent_morphisms.values()}
        ranked = rank_needs(
            open_needs,
            agent_types=output_types,
            agent_morphisms=set(agent_morphisms),
        )
        produced: list[Artifact] = []

        for need in ranked:
            morphism = self._choose_morphism(need, agent_morphisms)
            if morphism is None:
                continue
            claim_id = self.claims.try_claim(need.id, self.agent.name)
            if not claim_id:
                continue
            self.store.append_event(
                Event(
                    type="MorphismClaimed",
                    agent=self.agent.name,
                    data={"need_id": need.id, "claim_id": claim_id, "morphism": morphism.name},
                )
            )
            try:
                artifact = self._execute_need(need, morphism, claim_id)
            except Exception as exc:
                self.claims.release(need.id, self.agent.name)
                self.store.append_event(
                    Event(
                        type="ClaimReleased",
                        agent=self.agent.name,
                        data={"need_id": need.id, "claim_id": claim_id, "error": str(exc)},
                    )
                )
                continue
            produced.append(artifact)
            break

        if produced:
            self.store.append_event(
                Event(type="AgentActive", agent=self.agent.name, data={"produced": [a.id for a in produced]})
            )
        else:
            self.store.append_event(Event(type="AgentIdle", agent=self.agent.name, data={}))
        return produced

    def _choose_morphism(
        self,
        need: Need,
        morphisms: dict[str, MorphismSignature],
    ) -> MorphismSignature | None:
        allowed = set(need.allowed_morphisms)
        for morphism in morphisms.values():
            if allowed and morphism.name not in allowed:
                continue
            if morphism.output_type == need.required_type:
                return morphism
        return None

    def _execute_need(
        self,
        need: Need,
        morphism: MorphismSignature,
        claim_id: str,
    ) -> Artifact:
        inputs = self._load_inputs(need, morphism)
        self.store.append_event(
            Event(
                type="MorphismStarted",
                agent=self.agent.name,
                data={
                    "need_id": need.id,
                    "claim_id": claim_id,
                    "morphism": morphism.name,
                    "input_artifact_ids": [artifact.id for artifact in inputs],
                },
            )
        )
        executor = self.executors.get(morphism.adapter)
        result = executor.execute(
            morphism=morphism,
            inputs=inputs,
            query=need.query,
            agent_name=self.agent.name,
        )
        if result.status != "success":
            raise RuntimeError(result.error or f"morphism {morphism.name} failed")

        output = Artifact.create(
            artifact_type=morphism.output_type,
            payload=result.payload,
            producer_agent=self.agent.name,
            morphism=morphism.name,
            parent_ids=[artifact.id for artifact in inputs],
            metadata={"fulfilled_need_id": need.id, "claim_id": claim_id},
        )
        child_needs = self._needs_from_payload(result.payload, output.id)
        if child_needs:
            output = replace(output, needs=child_needs)
        cert = build_execution_certificate(
            morphism=morphism,
            inputs=inputs,
            output=output,
            claim_id=claim_id,
        )
        output = replace(output, metadata={**output.metadata, "certificate_id": cert.id})
        self.store.append_artifact(output)
        self.store.write_certificate(cert)
        self.store.close_need(need.id, output.id)
        self.store.append_event(
            Event(
                type="ArtifactProduced",
                agent=self.agent.name,
                data={
                    "artifact_id": output.id,
                    "need_id": need.id,
                    "certificate_id": cert.id,
                    "ok": cert.ok,
                },
            )
        )
        self.store.append_event(
            Event(
                type="CertificateEmitted",
                agent=self.agent.name,
                data={"certificate_id": cert.id, "artifact_id": output.id, "ok": cert.ok},
            )
        )
        if not cert.ok:
            raise RuntimeError("; ".join(cert.errors))
        return output

    def _load_inputs(self, need: Need, morphism: MorphismSignature) -> list[Artifact]:
        parent = self.store.get_artifact(need.parent_artifact_id)
        if parent is None:
            raise RuntimeError(f"Missing parent artifact {need.parent_artifact_id}")
        if not morphism.input_types:
            return []
        if parent.type != morphism.input_types[0]:
            raise RuntimeError(
                f"Need parent {parent.id} has type {parent.type}, but morphism {morphism.name} "
                f"expects first input {morphism.input_types[0]}"
            )
        inputs = [parent]
        artifacts = list(reversed(self.store.list_artifacts()))
        used = {parent.id}
        for expected in morphism.input_types[1:]:
            match = next((artifact for artifact in artifacts if artifact.id not in used and artifact.type == expected), None)
            if match is None:
                raise RuntimeError(f"Missing required input type {expected} for morphism {morphism.name}")
            inputs.append(match)
            used.add(match.id)
        return inputs

    @staticmethod
    def _needs_from_payload(payload: dict, parent_artifact_id: str) -> tuple[Need, ...]:
        raw_needs = payload.get("needs", [])
        if not isinstance(raw_needs, list):
            return ()
        needs = []
        for index, raw in enumerate(raw_needs):
            if not isinstance(raw, dict):
                continue
            required_type = raw.get("required_type") or raw.get("artifact_type")
            query = raw.get("query", "")
            if not required_type or not query:
                continue
            needs.append(
                Need.create(
                    parent_artifact_id=parent_artifact_id,
                    need_index=index,
                    required_type=str(required_type),
                    query=str(query),
                    rationale=str(raw.get("rationale", "")),
                    allowed_morphisms=tuple(str(v) for v in raw.get("allowed_morphisms", [])),
                )
            )
        return tuple(needs)
