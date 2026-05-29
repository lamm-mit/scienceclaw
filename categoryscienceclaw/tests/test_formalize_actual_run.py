from pathlib import Path

from categoryscienceclaw.audit import audit_run
from categoryscienceclaw.formalize import formalize_actual_run
from categoryscienceclaw.runtime.store import RunStore


ACTUAL_RUN = Path(
    "/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10"
)


def test_formalize_actual_7t10_run_preserves_trace_and_needs(tmp_path):
    output = tmp_path / "formalized"

    counts = formalize_actual_run(actual_run_dir=ACTUAL_RUN, output_run_dir=output)

    assert counts["artifacts"] == 32
    assert counts["open_needs"] == 6
    assert counts["certificates"] == 31

    store = RunStore(output)
    report = audit_run(store)
    assert report.ok, report.errors

    artifact_ids = {artifact.id for artifact in store.list_artifacts()}
    assert "contact_graph_7T10" in artifact_ids
    assert "mechanics_claim_7T10" in artifact_ids
    assert "atomistic_villin_smd_claim_1L2Y" in artifact_ids

    open_needs = {need.id: need for need in store.open_needs()}
    assert set(open_needs) == {
        "need_prepare_7t10_atomistic_complex",
        "need_receptor_bound_smd_ensemble",
        "need_hotspot_mutation_mechanics",
        "need_rupture_pathway_graph",
        "need_experimental_anchor",
        "need_integrated_mechanics_synthesis",
    }
    assert open_needs["need_prepare_7t10_atomistic_complex"].required_type == "PreparedAtomisticComplex"
    assert "openmm" in open_needs["need_receptor_bound_smd_ensemble"].metadata["preferred_skills"]


def test_formalize_completed_only_session_has_no_downstream_artifact_nodes_but_keeps_open_needs(tmp_path):
    output = tmp_path / "formalized_completed"

    counts = formalize_actual_run(
        actual_run_dir=ACTUAL_RUN,
        output_run_dir=output,
        session_filename="generated_session_with_atomistic_smd.json",
    )

    assert counts["artifacts"] == 20
    assert counts["open_needs"] == 6

    store = RunStore(output)
    report = audit_run(store)
    assert report.ok, report.errors

    artifact_ids = {artifact.id for artifact in store.list_artifacts()}
    assert "need_prepare_7t10_atomistic_complex" not in artifact_ids
    assert "atomistic_villin_smd_claim_1L2Y" in artifact_ids
