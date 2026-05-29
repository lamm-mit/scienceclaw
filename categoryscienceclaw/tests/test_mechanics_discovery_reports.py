import json

from categoryscienceclaw.audit import audit_run
from categoryscienceclaw.discovery_reports import RUN_ORDER, generate_mechanics_discovery_reports
from categoryscienceclaw.example_runs import run_examples_a_to_d
from categoryscienceclaw.runtime import RunStore


def test_mechanics_discovery_reports_add_publication_depth(tmp_path):
    out_root = tmp_path / "runs"
    run_examples_a_to_d(out_root, cycles=30, complexity="high", use_scienceclaw=True)
    manifest = generate_mechanics_discovery_reports(out_root)

    assert set(manifest["runs"]) == set(RUN_ORDER)
    assert (out_root / "MECHANICS_DISCOVERY_SYNTHESIS.md").exists()
    synthesis = (out_root / "MECHANICS_DISCOVERY_SYNTHESIS.md").read_text(encoding="utf-8")
    assert "contact-supported tensile response" in synthesis
    assert "anisotropic network stiffness" in synthesis
    assert "graph-mediated load routing" in synthesis
    assert "curvature-dependent membrane energy" in synthesis

    for run_name in RUN_ORDER:
        report_path = out_root / run_name / "presentable_results" / "DISCOVERY_REPORT.md"
        sidecar_path = out_root / run_name / "presentable_results" / "MECHANICS_INVESTIGATION.json"
        assert report_path.exists(), run_name
        report_text = report_path.read_text(encoding="utf-8").lower()
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        discovery = sidecar.get("discovery_report", {})

        for section in (
            "## scientific hypothesis",
            "## typed artifact schema",
            "## specific problem scope",
            "## mechanics equations and formal descriptors",
            "## candidate models and gate",
            "## categorical provenance graph",
            "## deeper mechanics analysis",
            "## rejected alternatives",
            "## stress test or ablation",
            "## regime-transition audit",
            "## mechanics claim",
            "## limitations",
        ):
            assert section in report_text, (run_name, section)

        assert discovery.get("model_selection_gate", {}).get("accepted_model")
        scope = discovery.get("problem_scope", {})
        assert scope.get("specific_question")
        assert scope.get("system_boundary")
        assert scope.get("candidate_scope")
        assert scope.get("input_scope")
        assert scope.get("observable_scope")
        assert scope.get("out_of_scope")
        registry = discovery.get("candidate_model_registry", [])
        assert len(registry) >= 2
        for model in registry:
            assert model.get("model_id")
            assert model.get("formal_type")
            assert model.get("input_artifacts")
            assert model.get("mechanical_commitment")
        categorical = discovery.get("categorical_provenance", {})
        assert categorical.get("graph_type") == "categorical_mechanics_discovery_subgraph"
        assert categorical.get("objects")
        assert categorical.get("morphisms")
        assert categorical.get("artifacts")
        assert categorical.get("problem_scope", {}).get("specific_question") == scope["specific_question"]
        assert categorical.get("candidate_model_registry") == registry
        graph_path = out_root / run_name / "presentable_results" / "categorical_discovery_graph.json"
        assert graph_path.exists()
        artifact_types = {artifact["type"] for artifact in categorical["artifacts"]}
        assert {"MechanicsCandidateModelSet", "MechanicsAcceptedModel", "MechanicsRejectedModel", "MechanicsModelSelectionGate", "MechanicsStressTest", "MechanicsRegimeTransition", "MechanicsDiscoveryClaim"} <= artifact_types
        morphism_names = {morphism["name"] for morphism in categorical["morphisms"]}
        assert "apply_model_selection_gate" in morphism_names
        assert "audit_mechanics_regime_transition" in morphism_names
        assert "synthesize_categorical_mechanics_claim" in morphism_names
        assert audit_run(RunStore(out_root / run_name)).ok
        assert discovery.get("rejected_alternatives")
        assert discovery.get("stress_test_or_ablation")
        assert discovery.get("regime_transition_audit", {}).get("residual_content_added_by_new_regime")
        claim = discovery.get("scientific_claim", "")
        assert len(claim.split()) > 15
        assert "mechanics" in claim.lower() or "tensile" in claim.lower() or "load" in claim.lower()

        combined = json.dumps(discovery).lower()
        assert "placeholder demonstration" not in combined
        assert "basic sympy demonstration" not in combined
        assert "synthetic experimental" not in combined
        assert "quantitative experimental" not in combined


def test_mechanics_discovery_reports_include_requested_deeper_analyses(tmp_path):
    out_root = tmp_path / "runs"
    run_examples_a_to_d(out_root, cycles=30, complexity="high", use_scienceclaw=True)

    by_run = {}
    for run_name in RUN_ORDER:
        sidecar = json.loads((out_root / run_name / "presentable_results" / "MECHANICS_INVESTIGATION.json").read_text(encoding="utf-8"))
        by_run[run_name] = sidecar["discovery_report"]["deeper_analysis"]

    assert {"contact_entropy_nats", "contact_gini", "hotspot_load_anchor_index", "stiffness_pN_per_nm"} <= set(by_run["7t10_formal_extension"])
    assert {"orientation_tensor", "orientation_eigenvalues", "anisotropy_ratio", "stiffness_kpa"} <= set(by_run["biomechanics_fiber_network"])
    assert {"degree_centrality", "load_concentration", "full_model_coefficients", "strongest_path_id"} <= set(by_run["mechanobiology_force_paths"])
    assert {"curvature_energy_localization_top10_fraction", "bending_modulus_sensitivity", "total_grid_energy_proxy_kbt"} <= set(by_run["membrane_biophysics"])

    assert 0.0 <= by_run["7t10_formal_extension"]["contact_gini"] <= 1.0
    assert by_run["biomechanics_fiber_network"]["anisotropy_ratio"] > 1.0
    assert by_run["mechanobiology_force_paths"]["load_concentration"] > 0.0
    assert by_run["membrane_biophysics"]["bending_modulus_sensitivity"]["kappa_2x_total_kbt"] > by_run["membrane_biophysics"]["bending_modulus_sensitivity"]["kappa_1x_total_kbt"]



def test_bcd_problem_scopes_are_specific_not_topic_labels(tmp_path):
    out_root = tmp_path / "runs"
    run_examples_a_to_d(out_root, cycles=30, complexity="high", use_scienceclaw=True)

    expected = {
        "biomechanics_fiber_network": {
            "question_tokens": ["12-fiber", "11-point", "isotropic scalar descriptor"],
            "model_ids": {"fiber_M0_isotropic_count_scalar", "fiber_M1_orientation_tensor_stiffness"},
            "inputs": {"fiber_network_synthetic.csv", "fiber_stress_strain_synthetic.csv", "fiber_computational_model.json"},
        },
        "mechanobiology_force_paths": {
            "question_tokens": ["12-path", "four-feature", "adhesion-only ablation"],
            "model_ids": {"mechbio_M0_adhesion_only_ablation", "mechbio_M1_graph_conditioned_force_path_regression"},
            "inputs": {"force_paths_synthetic.csv", "adhesion_cytoskeleton_graph_synthetic.json"},
        },
        "membrane_biophysics": {
            "question_tokens": ["7x7", "Helfrich-style", "curvature-only shape descriptor"],
            "model_ids": {"membrane_M0_curvature_only_shape", "membrane_M1_helfrich_quadratic_energy_proxy"},
            "inputs": {"membrane_curvature_field_synthetic.csv", "membrane_material_model.json"},
        },
    }

    for run_name, spec in expected.items():
        sidecar = json.loads((out_root / run_name / "presentable_results" / "MECHANICS_INVESTIGATION.json").read_text(encoding="utf-8"))
        discovery = sidecar["discovery_report"]
        question = discovery["problem_scope"]["specific_question"]
        for token in spec["question_tokens"]:
            assert token in question
        model_ids = {model["model_id"] for model in discovery["candidate_model_registry"]}
        assert spec["model_ids"] <= model_ids
        scoped_inputs = set(discovery["problem_scope"]["input_scope"])
        assert spec["inputs"] <= scoped_inputs
        graph = json.loads((out_root / run_name / "presentable_results" / "categorical_discovery_graph.json").read_text(encoding="utf-8"))
        assert graph["candidate_model_registry"] == discovery["candidate_model_registry"]
        candidate_artifacts = [artifact for artifact in graph["artifacts"] if artifact["type"] == "MechanicsCandidateModelSet"]
        assert len(candidate_artifacts) == 1
