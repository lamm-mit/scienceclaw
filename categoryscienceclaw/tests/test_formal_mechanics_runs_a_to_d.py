import json

from categoryscienceclaw.audit import audit_run
from categoryscienceclaw.example_runs import EXAMPLES, EXAMPLE_RUN_DIRS, run_example, run_examples_a_to_d
from categoryscienceclaw.runtime.store import RunStore


def _artifact_types(run_dir):
    return [artifact.type for artifact in RunStore(run_dir).list_artifacts()]


def test_example_b_fiber_network_run_completes_by_heartbeat(tmp_path):
    run_dir = tmp_path / "fiber"
    summary = run_example("biomechanics-fiber-network", run_dir, cycles=30, complexity="high")
    store = RunStore(run_dir)
    types = _artifact_types(run_dir)

    assert summary["audit_status"] == "pass"
    assert summary["open_needs_remaining"] == 0
    assert "OrientationParityDescriptor" in types
    assert "AnisotropyTensor" in types
    assert "BiomechanicsClaim" in types
    assert summary["blocked_needs"], "missing empirical boundary conditions should be explicit, not faked"
    assert audit_run(store).ok


def test_example_c_membrane_run_completes_by_heartbeat(tmp_path):
    run_dir = tmp_path / "membrane"
    summary = run_example("membrane-biophysics", run_dir, cycles=30, complexity="high")
    store = RunStore(run_dir)
    types = _artifact_types(run_dir)

    assert summary["audit_status"] == "pass"
    assert "CurvatureDescriptor" in types
    assert "EnergyFunctional" in types
    assert "BiophysicsClaim" in types
    energy = next(artifact for artifact in store.list_artifacts() if artifact.type == "EnergyFunctional")
    assert energy.payload["data_status"] == "formal_descriptor_only"
    assert audit_run(store).ok


def test_example_d_mechanobiology_run_completes_by_heartbeat(tmp_path):
    run_dir = tmp_path / "mechanobio"
    summary = run_example("mechanobiology-force-paths", run_dir, cycles=30, complexity="high")
    store = RunStore(run_dir)
    types = _artifact_types(run_dir)

    assert summary["audit_status"] == "pass"
    assert "ForcePathDescriptor" in types
    assert "MechanotransductionModel" in types
    assert "MechanobiologyClaim" in types
    force_path = next(artifact for artifact in store.list_artifacts() if artifact.type == "ForcePathDescriptor")
    assert force_path.payload["data_status"] == "formal_descriptor_only"
    assert "force_magnitude" not in json.dumps(force_path.payload).lower()
    assert audit_run(store).ok


def test_run_examples_a_to_d_writes_expected_run_directories(tmp_path):
    out_root = tmp_path / "runs"
    summaries = run_examples_a_to_d(out_root, cycles=30, complexity="high")

    assert set(summaries) == set(EXAMPLES)
    for example, summary in summaries.items():
        run_dir = out_root / EXAMPLE_RUN_DIRS[example]
        assert summary["audit_status"] == "pass"
        assert (run_dir / "schema.json").exists()
        assert (run_dir / "agents.json").exists()
        assert (run_dir / "reactor_trace.jsonl").exists()
        assert (run_dir / "run_summary.json").exists()
