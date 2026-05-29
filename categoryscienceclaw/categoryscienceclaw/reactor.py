"""Artifact reactor for decentralized heartbeat cycles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from categoryscienceclaw.kernel.models import AgentProfile
from categoryscienceclaw.runtime.executors import ExecutorRegistry
from categoryscienceclaw.runtime.store import RunStore
from categoryscienceclaw.runtime.worker import Worker
from categoryscienceclaw.runtime.events import Event


@dataclass(frozen=True)
class ReactionRecord:
    cycle: int
    agent: str
    output_artifact_id: str
    output_type: str
    fulfilled_need_id: str
    morphism: str
    parent_artifact_ids: tuple[str, ...]
    certificate_id: str = ""
    status: str = "fulfilled"

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "agent": self.agent,
            "output_artifact_id": self.output_artifact_id,
            "output_type": self.output_type,
            "fulfilled_need_id": self.fulfilled_need_id,
            "need_id": self.fulfilled_need_id,
            "morphism": self.morphism,
            "parent_artifact_ids": list(self.parent_artifact_ids),
            "input_artifact_ids": list(self.parent_artifact_ids),
            "certificate_id": self.certificate_id,
            "status": self.status,
        }


@dataclass(frozen=True)
class ReactorSummary:
    cycles_requested: int
    cycles_completed: int
    artifacts_emitted: int
    needs_fulfilled: int
    open_needs_remaining: int
    records: tuple[ReactionRecord, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycles_requested": self.cycles_requested,
            "cycles_completed": self.cycles_completed,
            "artifacts_emitted": self.artifacts_emitted,
            "needs_fulfilled": self.needs_fulfilled,
            "open_needs_remaining": self.open_needs_remaining,
            "records": [record.to_dict() for record in self.records],
        }


class ArtifactReactor:
    """Heartbeat harness, not a central planner.

    Each cycle lets every agent independently run one Worker heartbeat. Needs are
    ranked inside the worker by the local ScienceClaw-style pressure function.
    """

    def __init__(
        self,
        *,
        store: RunStore,
        agents: dict[str, AgentProfile],
        executors: ExecutorRegistry,
        max_cycles: int = 10,
    ):
        self.store = store
        self.agents = agents
        self.executors = executors
        self.max_cycles = max(1, max_cycles)
        self.trace_path = self.store.run_dir / "reactor_trace.jsonl"

    def heartbeat_cycle(self, cycle_index: int) -> list[ReactionRecord]:
        records: list[ReactionRecord] = []
        for agent in self.agents.values():
            produced = Worker(store=self.store, agent=agent, executors=self.executors).heartbeat()
            for artifact in produced:
                record = ReactionRecord(
                    cycle=cycle_index,
                    agent=agent.name,
                    output_artifact_id=artifact.id,
                    output_type=artifact.type,
                    fulfilled_need_id=str(artifact.metadata.get("fulfilled_need_id", "")),
                    morphism=artifact.morphism,
                    parent_artifact_ids=tuple(artifact.parent_ids),
                    certificate_id=str(artifact.metadata.get("certificate_id", "")),
                )
                records.append(record)
                self._append_trace(record.to_dict())
        self.store.append_event(
            Event(
                type="ReactorCycleCompleted",
                agent="ArtifactReactor",
                data={
                    "cycle": cycle_index,
                    "produced": [record.output_artifact_id for record in records],
                    "count": len(records),
                },
            )
        )
        return records

    def run_until_quiescent(self) -> ReactorSummary:
        all_records: list[ReactionRecord] = []
        completed = 0
        for cycle in range(self.max_cycles):
            completed = cycle + 1
            records = self.heartbeat_cycle(cycle)
            all_records.extend(records)
            if not records:
                break
        return ReactorSummary(
            cycles_requested=self.max_cycles,
            cycles_completed=completed,
            artifacts_emitted=len(all_records),
            needs_fulfilled=len([r for r in all_records if r.fulfilled_need_id]),
            open_needs_remaining=len(self.store.open_needs()),
            records=tuple(all_records),
        )

    def _append_trace(self, record: dict[str, Any]) -> None:
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.trace_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")
