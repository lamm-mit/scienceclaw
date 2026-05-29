from categoryscienceclaw.audit import audit_run
from categoryscienceclaw.example_runs import run_example
from categoryscienceclaw.runtime.store import RunStore


def test_7t10_reactor_extension_imports_baseline_sources_and_fulfills_formal_needs(tmp_path):
    run_dir = tmp_path / "7t10"
    summary = run_example("7t10-formal-extension", run_dir, cycles=30, complexity="high")
    store = RunStore(run_dir)
    artifacts = store.list_artifacts()
    by_id = {artifact.id: artifact for artifact in artifacts}
    types = [artifact.type for artifact in artifacts]

    assert summary["audit_status"] == "pass"
    assert summary["formal_extension_needs_fulfilled"] == 5
    assert summary["inherited_7t10_needs_remaining"] == 6
    assert by_id["contact_graph_7T10"].type == "ContactGraph"
    assert by_id["force_extension_7T10"].type == "ForceExtensionTrace"
    assert by_id["mechanics_claim_7T10"].type == "MechanicsClaim"
    assert by_id["contact_graph_7T10"].metadata["imported_from"] == "structure_contact_7T10_formalized_20260528"
    assert "ContactParityDescriptor" in types
    assert "MechanicsFunctorDescriptor" in types
    assert "CompositionAuditRecord" in types
    assert "OpenNeedDependencyGraph" in types
    assert "RupturePathwayFormalization" in types
    assert "FormalMechanicsExtensionClaim" in types
    assert "contact_claim_7T10" not in [artifact.id for artifact in artifacts if artifact.producer_agent != "7T10BaselineImportAgent"]
    assert audit_run(store).ok


def test_7t10_extension_does_not_invent_new_peak_force_values(tmp_path):
    run_dir = tmp_path / "7t10"
    run_example("7t10-formal-extension", run_dir, cycles=30, complexity="high")
    store = RunStore(run_dir)

    produced = [artifact for artifact in store.list_artifacts() if artifact.producer_agent != "7T10BaselineImportAgent"]
    produced_text = "\n".join(str(artifact.payload) for artifact in produced)
    assert "peak_force_pN" not in produced_text
    assert "766.98959" not in produced_text
