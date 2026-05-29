import json
from pathlib import Path

from categoryscienceclaw.audit import audit_run
from categoryscienceclaw.example_runs import EXAMPLES, EXAMPLE_RUN_DIRS, run_example, run_examples_a_to_d
from categoryscienceclaw.kernel.models import AgentProfile, Artifact, MorphismSignature, Need, ObjectType
from categoryscienceclaw.reactor import ArtifactReactor
from categoryscienceclaw.runtime import ExecutorRegistry, RunStore
from categoryscienceclaw.runtime.pressure import NeedPressureRef, rank_needs


def _minimal_pressure_store(tmp_path):
    store = RunStore(tmp_path / "pressure")
    store.init()
    store.write_schema(
        objects=[
            ObjectType("Seed"),
            ObjectType("Descriptor"),
        ],
        morphisms=[
            MorphismSignature("make_descriptor", ("Seed",), "Descriptor"),
        ],
        topic="pressure ranking",
    )
    seed = Artifact.create(artifact_type="Seed", payload={"topic": "x"}, producer_agent="human")
    store.append_artifact(seed)
    old = Need.create(
        parent_artifact_id=seed.id,
        need_index=0,
        required_type="Descriptor",
        query="central parity descriptor shared shared",
        rationale="old central need",
        allowed_morphisms=["make_descriptor"],
    )
    young = Need.create(
        parent_artifact_id=seed.id,
        need_index=1,
        required_type="Descriptor",
        query="isolated unrelated request",
        rationale="young need",
        allowed_morphisms=["make_descriptor"],
    )
    # Force age difference without sleeping.
    old = NeedPressureRef.from_need(old, parent_depth=3, created_at="2020-01-01T00:00:00+00:00")
    young = NeedPressureRef.from_need(young, parent_depth=0, created_at="2999-01-01T00:00:00+00:00")
    return store, old, young


def test_pressure_mirrors_scienceclaw_novelty_centrality_depth_age(tmp_path):
    _store, old, young = _minimal_pressure_store(tmp_path)
    ranked = rank_needs([young, old])
    assert ranked[0].id == old.id
    assert ranked[0].pressure > ranked[1].pressure
    assert {"novelty", "centrality", "depth", "age"}.issubset(ranked[0].components)


def test_reactor_fulfills_need_produced_by_previous_cycle(tmp_path):
    run_dir = tmp_path / "reactor"
    result = run_example("biomechanics-fiber-network", run_dir, cycles=12, complexity="high")
    assert result["artifacts_emitted"] >= 10
    store = RunStore(run_dir)
    events = store.list_events()
    assert any(e["type"] == "ReactorCycleCompleted" for e in events)
    needs_lines = [json.loads(line) for line in store.needs_path.read_text().splitlines() if line.strip()]
    fulfilled = [n for n in needs_lines if n.get("status") == "fulfilled"]
    assert len(fulfilled) >= 8
    assert any(a.type == "PatchCompositionReplicationRecord" for a in store.list_artifacts())
    assert audit_run(store).ok


def test_7t10_high_complexity_preserves_inherited_open_needs(tmp_path):
    run_dir = tmp_path / "7t10"
    result = run_example("7t10-formal-extension", run_dir, cycles=30, complexity="high")
    assert result["formal_extension_needs_fulfilled"] >= 5
    assert result["inherited_7t10_needs_remaining"] >= 1
    store = RunStore(run_dir)
    artifact_types = [a.type for a in store.list_artifacts()]
    assert "ContactParityDescriptor" in artifact_types
    assert "FormalMechanicsExtensionClaim" in artifact_types
    assert "NeedClassificationRecord" in artifact_types
    assert "contact_claim_7T10" not in [a.id for a in store.list_artifacts() if a.morphism]
    assert audit_run(store).ok


def test_run_examples_a_to_d_high_complexity_reaches_goal(tmp_path):
    out_root = tmp_path / "runs"
    results = run_examples_a_to_d(out_root, cycles=30, complexity="high")
    assert set(results) == set(EXAMPLES)
    for name, summary in results.items():
        run_dir = out_root / EXAMPLE_RUN_DIRS[name]
        assert run_dir.exists(), name
        assert summary["audit_status"] == "pass", name
        assert summary["artifacts_emitted"] >= 8, name
        assert summary["needs_fulfilled"] >= 5, name
        assert (run_dir / "reactor_trace.jsonl").exists(), name
        assert (run_dir / "run_summary.json").exists(), name


def test_blocked_real_data_need_is_reported_not_faked(tmp_path):
    run_dir = tmp_path / "fiber"
    summary = run_example("biomechanics-fiber-network", run_dir, cycles=30, complexity="high")
    store = RunStore(run_dir)
    assert summary["blocked_needs"], "expected missing real boundary condition to be blocked, not faked"
    blocked_artifacts = [a for a in store.list_artifacts() if a.type == "BlockedRealDataNeed"]
    assert blocked_artifacts
    assert all("fake" not in json.dumps(a.payload).lower() for a in blocked_artifacts)
