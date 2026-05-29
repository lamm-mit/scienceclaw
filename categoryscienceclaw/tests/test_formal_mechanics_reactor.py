import json

from categoryscienceclaw.audit import audit_run
from categoryscienceclaw.example_runs import run_example
from categoryscienceclaw.reactor import ReactionRecord
from categoryscienceclaw.runtime.pressure import NeedPressureRef, rank_needs
from categoryscienceclaw.runtime.store import RunStore
from categoryscienceclaw.kernel.models import Need


def test_pressure_mirrors_scienceclaw_novelty_centrality_depth_age():
    old = NeedPressureRef.from_need(
        Need.create(
            parent_artifact_id="seed",
            need_index=0,
            required_type="Descriptor",
            query="central parity descriptor shared shared",
            allowed_morphisms=["make_descriptor"],
        ),
        parent_depth=3,
        created_at="2020-01-01T00:00:00+00:00",
    )
    young = NeedPressureRef.from_need(
        Need.create(
            parent_artifact_id="seed",
            need_index=1,
            required_type="Descriptor",
            query="isolated unrelated request",
            allowed_morphisms=["make_descriptor"],
        ),
        parent_depth=0,
        created_at="2999-01-01T00:00:00+00:00",
    )

    ranked = rank_needs([young, old])

    assert ranked[0].id == old.id
    assert ranked[0].pressure > ranked[1].pressure
    assert {"novelty", "centrality", "depth", "age"}.issubset(ranked[0].components)


def test_reactor_trace_and_certificates_reference_real_outputs(tmp_path):
    run_dir = tmp_path / "fiber"
    summary = run_example("biomechanics-fiber-network", run_dir, cycles=30, complexity="high")
    store = RunStore(run_dir)

    assert summary["audit_status"] == "pass"
    assert summary["open_needs_remaining"] == 0
    trace = [json.loads(line) for line in (run_dir / "reactor_trace.jsonl").read_text().splitlines()]
    artifact_ids = {artifact.id for artifact in store.list_artifacts()}
    cert_outputs = {cert.conclusion["output_artifact_id"] for cert in store.list_certificates()}

    assert trace
    assert all(record["output_artifact_id"] in artifact_ids for record in trace)
    assert all(record["output_artifact_id"] in cert_outputs for record in trace)
    assert audit_run(store).ok


def test_formal_certificate_obligations_are_recorded(tmp_path):
    run_dir = tmp_path / "membrane"
    run_example("membrane-biophysics", run_dir, cycles=30, complexity="high")
    store = RunStore(run_dir)
    names = {obligation["name"] for cert in store.list_certificates() for obligation in cert.obligations}

    assert "formal_metadata_present" in names
    assert "invariants_present" in names
    assert "source_parent_ids_present" in names
    assert "symbolic_status_declared_when_no_real_data" in names
    assert "composition_path_valid" in names


def test_reaction_record_serializes_coordination_facts():
    record = ReactionRecord(
        cycle=2,
        agent="ParityDescriptorAgent",
        output_artifact_id="art-x",
        output_type="ContactParityDescriptor",
        fulfilled_need_id="need-x",
        morphism="compute_7t10_contact_parity",
        parent_artifact_ids=("contact_graph_7T10",),
    )

    assert record.to_dict()["cycle"] == 2
    assert record.to_dict()["parent_artifact_ids"] == ["contact_graph_7T10"]


def test_scienceclaw_mode_records_skill_evidence(tmp_path):
    run_dir = tmp_path / "scienceclaw-fiber"
    summary = run_example("biomechanics-fiber-network", run_dir, cycles=30, complexity="high", use_scienceclaw=True)
    store = RunStore(run_dir)
    produced = [artifact for artifact in store.list_artifacts() if artifact.morphism]

    assert summary["executor_backend"] == "scienceclaw"
    assert summary["scienceclaw_agents_used"] is True
    assert produced
    assert all(artifact.payload.get("execution_backend") == "scienceclaw" for artifact in produced)
    assert {artifact.payload.get("scienceclaw", {}).get("skill_name") for artifact in produced} >= {"networkx", "scientific-critical-thinking", "scientific-writing"}


def test_reactor_trace_records_plan_fields(tmp_path):
    run_dir = tmp_path / "scienceclaw-membrane"
    run_example("membrane-biophysics", run_dir, cycles=30, complexity="high", use_scienceclaw=True)
    trace = [json.loads(line) for line in (run_dir / "reactor_trace.jsonl").read_text().splitlines()]

    assert trace
    for record in trace:
        assert record["need_id"]
        assert record["input_artifact_ids"] == record["parent_artifact_ids"]
        assert record["certificate_id"].startswith("cert-")
        assert record["status"] == "fulfilled"
