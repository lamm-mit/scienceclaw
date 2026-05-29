"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from categoryscienceclaw.adapters.scienceclaw import ScienceClawSkillExecutor
from categoryscienceclaw.audit import audit_run
from categoryscienceclaw.defaults import default_morphisms, default_objects
from categoryscienceclaw.formalize import formalize_actual_run
from categoryscienceclaw.example_runs import run_example, run_examples_a_to_d
from categoryscienceclaw.kernel.models import AgentProfile, Artifact, Need
from categoryscienceclaw.runtime import ExecutorRegistry, RunStore, Worker
from categoryscienceclaw.runtime.events import Event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="categoryscienceclaw")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("run_dir")
    p_init.add_argument("--topic", required=True)
    p_init.add_argument("--agents", required=True)

    p_worker = sub.add_parser("worker")
    p_worker.add_argument("run_dir")
    p_worker.add_argument("--agent", required=True)
    p_worker.add_argument("--cycles", type=int, default=1)
    p_worker.add_argument("--scienceclaw", action="store_true")

    p_run = sub.add_parser("run")
    p_run.add_argument("run_dir")
    p_run.add_argument("--agents", required=True)
    p_run.add_argument("--cycles", type=int, default=4)
    p_run.add_argument("--scienceclaw", action="store_true")

    p_audit = sub.add_parser("audit")
    p_audit.add_argument("run_dir")
    p_audit.add_argument("--json", action="store_true")

    p_replay = sub.add_parser("replay")
    p_replay.add_argument("run_dir")

    p_formalize = sub.add_parser("formalize-actual-run")
    p_formalize.add_argument("actual_run_dir")
    p_formalize.add_argument("output_run_dir")
    p_formalize.add_argument("--session", default="generated_session_with_downstream_needs.json")

    p_run_example = sub.add_parser("run-example")
    p_run_example.add_argument("example")
    p_run_example.add_argument("--cycles", type=int, default=30)
    p_run_example.add_argument("--complexity", choices=("minimal", "branching", "high"), default="high")
    p_run_example.add_argument("--out", required=True)
    p_run_example.add_argument("--scienceclaw", action="store_true")

    p_run_examples = sub.add_parser("run-examples-a-to-d")
    p_run_examples.add_argument("--cycles", type=int, default=30)
    p_run_examples.add_argument("--complexity", choices=("minimal", "branching", "high"), default="high")
    p_run_examples.add_argument("--out-root", required=True)
    p_run_examples.add_argument("--scienceclaw", action="store_true")

    p_figures = sub.add_parser("figure-mechanics-runs")
    p_figures.add_argument("root_dir")

    p_discovery = sub.add_parser("discovery-mechanics-runs")
    p_discovery.add_argument("root_dir")

    args = parser.parse_args(argv)

    if args.command == "init":
        return _init(args.run_dir, args.topic, args.agents)
    if args.command == "worker":
        return _worker(args.run_dir, args.agent, args.cycles, args.scienceclaw)
    if args.command == "run":
        return _run(args.run_dir, args.agents, args.cycles, args.scienceclaw)
    if args.command == "audit":
        return _audit(args.run_dir, args.json)
    if args.command == "replay":
        return _replay(args.run_dir)
    if args.command == "formalize-actual-run":
        return _formalize_actual_run(args.actual_run_dir, args.output_run_dir, args.session)
    if args.command == "run-example":
        return _run_example(args.example, args.out, args.cycles, args.complexity, args.scienceclaw)
    if args.command == "run-examples-a-to-d":
        return _run_examples_a_to_d(args.out_root, args.cycles, args.complexity, args.scienceclaw)
    if args.command == "figure-mechanics-runs":
        return _figure_mechanics_runs(args.root_dir)
    if args.command == "discovery-mechanics-runs":
        return _discovery_mechanics_runs(args.root_dir)
    return 2


def _load_agents(path: str | Path) -> list[AgentProfile]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [AgentProfile.from_dict(raw) for raw in data.get("agents", [])]


def _init(run_dir: str, topic: str, agents_path: str) -> int:
    store = RunStore(run_dir)
    store.init()
    agents = _load_agents(agents_path)
    store.write_agents(agents)
    store.write_schema(objects=default_objects(), morphisms=default_morphisms(), topic=topic)

    question = Artifact.create(
        artifact_type="ResearchQuestion",
        payload={"topic": topic},
        producer_agent="human",
    )
    seed_need = Need.create(
        parent_artifact_id=question.id,
        need_index=0,
        required_type="LiteratureEvidence",
        query=topic,
        rationale="Seed the decentralized run with literature evidence.",
        allowed_morphisms=["literature_search"],
    )
    question = replace(question, needs=(seed_need,))
    store.append_artifact(question)
    store.append_event(Event(type="RunInitialized", agent="human", data={"topic": topic, "agents": [a.name for a in agents]}))
    print(f"initialized {run_dir}")
    return 0


def _executors(use_scienceclaw: bool) -> ExecutorRegistry:
    registry = ExecutorRegistry()
    if use_scienceclaw:
        registry.register("scienceclaw", ScienceClawSkillExecutor())
    return registry


def _worker(run_dir: str, agent_name: str, cycles: int, use_scienceclaw: bool) -> int:
    store = RunStore(run_dir)
    agents = store.read_agents()
    if agent_name not in agents:
        print(f"unknown agent: {agent_name}", file=sys.stderr)
        return 2
    worker = Worker(store=store, agent=agents[agent_name], executors=_executors(use_scienceclaw))
    produced_count = 0
    for _ in range(max(1, cycles)):
        produced_count += len(worker.heartbeat())
    print(f"{agent_name}: produced {produced_count} artifact(s)")
    return 0


def _run(run_dir: str, agents_path: str, cycles: int, use_scienceclaw: bool) -> int:
    del agents_path
    store = RunStore(run_dir)
    agents = store.read_agents()
    executors = _executors(use_scienceclaw)
    produced = 0
    for _ in range(max(1, cycles)):
        cycle_produced = 0
        for agent in agents.values():
            cycle_produced += len(Worker(store=store, agent=agent, executors=executors).heartbeat())
        produced += cycle_produced
        if cycle_produced == 0:
            break
    print(f"run complete: produced {produced} artifact(s)")
    return 0


def _audit(run_dir: str, as_json: bool) -> int:
    report = audit_run(RunStore(run_dir))
    if as_json:
        print(json.dumps({"ok": report.ok, "errors": report.errors, "warnings": report.warnings, "counts": report.counts}, indent=2))
    else:
        print(f"Categorical audit: {'PASS' if report.ok else 'FAIL'}")
        print("Counts:")
        for key, value in sorted(report.counts.items()):
            print(f"  {key}: {value}")
        for error in report.errors:
            print(f"ERROR: {error}")
    return 0 if report.ok else 1


def _replay(run_dir: str) -> int:
    store = RunStore(run_dir)
    events = store.list_events()
    artifacts = store.list_artifacts()
    print(f"Replay summary: {len(events)} event(s), {len(artifacts)} artifact(s), {len(store.open_needs())} open need(s)")
    for event in events:
        print(f"{event.get('timestamp', '')} {event.get('type', '')} {event.get('agent', '')}")
    return 0


def _formalize_actual_run(actual_run_dir: str, output_run_dir: str, session: str) -> int:
    counts = formalize_actual_run(
        actual_run_dir=actual_run_dir,
        output_run_dir=output_run_dir,
        session_filename=session,
    )
    print(json.dumps(counts, indent=2, sort_keys=True))
    return 0


def _run_example(example: str, out: str, cycles: int, complexity: str, use_scienceclaw: bool) -> int:
    summary = run_example(example, out, cycles=cycles, complexity=complexity, use_scienceclaw=use_scienceclaw)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("audit_status") == "pass" else 1


def _run_examples_a_to_d(out_root: str, cycles: int, complexity: str, use_scienceclaw: bool) -> int:
    summaries = run_examples_a_to_d(out_root, cycles=cycles, complexity=complexity, use_scienceclaw=use_scienceclaw)
    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 0 if all(summary.get("audit_status") == "pass" for summary in summaries.values()) else 1


def _figure_mechanics_runs(root_dir: str) -> int:
    from categoryscienceclaw.figure_agent import generate_mechanics_figures

    manifest = generate_mechanics_figures(root_dir)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def _discovery_mechanics_runs(root_dir: str) -> int:
    from categoryscienceclaw.discovery_reports import generate_mechanics_discovery_reports

    manifest = generate_mechanics_discovery_reports(root_dir)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
