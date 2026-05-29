import json

from categoryscienceclaw.example_runs import EXAMPLE_RUN_DIRS, run_examples_a_to_d


PLACEHOLDER_MARKERS = (
    "basic sympy demonstration",
    "placeholder demonstration",
    "see skill.md",
    "template/scaffold",
    '"status": "available"',
)


def _produced_artifacts(run_dir):
    return [
        json.loads(line)
        for line in (run_dir / "artifacts.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("morphism")
    ]


def test_presentable_reports_do_not_present_placeholder_outputs_as_results(tmp_path):
    out_root = tmp_path / "runs"
    summaries = run_examples_a_to_d(out_root, cycles=30, complexity="high", use_scienceclaw=True)

    for example, summary in summaries.items():
        run_dir = out_root / EXAMPLE_RUN_DIRS[example]
        report = (run_dir / "presentable_results" / "INVESTIGATION_RESULTS.md").read_text(encoding="utf-8").lower()
        assert "## valid results" in report
        assert "act like a mechanics investigator, not a generic data analyzer" in report
        assert "## mechanics investigation question" in report
        assert "## evidence plan and skill routing" in report
        assert "## quantitative computational mechanics results" in report
        assert "## validation and diagnostics" in report
        assert "## computational input needs" in report
        assert "## quantitative experimental results" not in report
        assert "## blocked experimental data needs" not in report
        assert "## formal/symbolic results" in report
        assert "## blocked or missing data" in report
        assert "## rejected placeholder outputs" in report
        for marker in PLACEHOLDER_MARKERS:
            assert marker not in report
        assert summary["audit_status"] == "pass"


def test_every_presented_formal_result_has_substantive_fields(tmp_path):
    out_root = tmp_path / "runs"
    run_examples_a_to_d(out_root, cycles=30, complexity="high", use_scienceclaw=True)

    for run_name in EXAMPLE_RUN_DIRS.values():
        run_dir = out_root / run_name
        for artifact in _produced_artifacts(run_dir):
            payload = artifact["payload"]
            if payload.get("result_classification") == "blocked_missing_data":
                assert payload.get("blocked_reason")
                assert payload.get("missing_input_needed")
                continue
            if payload.get("result_classification") == "categorical_discovery_artifact":
                assert artifact["type"].startswith("Mechanics")
                assert artifact.get("morphism") in {
                    "instantiate_mechanics_candidate_models",
                    "accept_mechanics_model",
                    "reject_mechanics_model",
                    "apply_model_selection_gate",
                    "run_mechanics_stress_test",
                    "audit_mechanics_regime_transition",
                    "synthesize_categorical_mechanics_claim",
                }
                assert artifact.get("content_hash")
                continue
            assert payload.get("result_classification") == "formal_symbolic_result"
            formal_result = payload.get("formal_result")
            assert isinstance(formal_result, dict) and formal_result
            assert formal_result.get("kind")
            assert payload.get("valid_result_basis")
            scienceclaw = payload.get("scienceclaw", {})
            if scienceclaw.get("accepted_as_substantive"):
                assert scienceclaw.get("result_summary", {}).get("source_data_analyzed") is True
            else:
                assert payload.get("source_content_features")
            text = json.dumps(payload).lower()
            for marker in PLACEHOLDER_MARKERS:
                assert marker not in text


def test_smart_mechanics_investigation_has_quantitative_provenance_or_blocks(tmp_path):
    out_root = tmp_path / "runs"
    run_examples_a_to_d(out_root, cycles=30, complexity="high", use_scienceclaw=True)

    findings = (out_root / "ACTUAL_MECHANICS_FINDINGS.md").read_text(encoding="utf-8")
    assert "Actual Mechanics Investigation Findings" in findings
    assert "Hotspot positions: `[8, 9, 6, 7, 1, 11]`" in findings
    assert "Peak force: `766.98959` pN at `2.4` nm" in findings
    assert "Linear force-extension slope: `253.068938` pN/nm" in findings
    assert "Fiber orientation order: `0.673115`" in findings
    assert "Mean load-path score: `4.421814` Pa/um" in findings
    assert "RMS curvature: `0.15471241` 1/um" in findings
    assert "Synthetic fiber-network anisotropy and stiffness computation" in findings
    assert "Synthetic mechanobiology force-path load score computation" in findings
    assert "Synthetic membrane curvature-energy computation" in findings
    assert "Scientific meaning:" in findings
    assert "dominant orientation near 48 degrees" in findings
    assert "adhesion alone does not explain the load distribution" in findings
    assert "curvature-energy interpretation" in findings

    for run_name in EXAMPLE_RUN_DIRS.values():
        run_dir = out_root / run_name
        investigation_path = run_dir / "presentable_results" / "MECHANICS_INVESTIGATION.json"
        assert investigation_path.exists()
        investigation = json.loads(investigation_path.read_text(encoding="utf-8"))
        assert investigation["investigator_principle"] == "Act like a mechanics investigator, not a generic data analyzer."
        assert "quantitative_experimental_results" not in investigation
        assert "blocked_experimental_data_needs" not in investigation
        assert investigation.get("mechanical_hypothesis")
        assert investigation.get("mechanical_question")
        assert investigation.get("evidence_plan", {}).get("required_evidence")
        assert investigation.get("evidence_plan", {}).get("skill_routing")

        quantitative = investigation.get("quantitative_computational_mechanics_results", [])
        executions = investigation.get("scienceclaw_skill_executions", [])
        assert quantitative, f"{run_name} lacks quantitative computational mechanics results"
        assert investigation.get("validation_and_diagnostics", {}).get("quantitative_result_count") >= 1
        for result in quantitative:
            assert result.get("input_artifact")
            assert result.get("input_file")
            assert result.get("method_or_skill_used")
            assert result.get("units")
            assert result.get("computed_values")
            assert result.get("diagnostic")
            assert result.get("scientific_interpretation")
            assert result.get("uncertainty_or_limitation")
            assert result.get("evidence_class") != "experimental"
            assert result.get("input_origin") != "experimental"
            text = json.dumps(result).lower()
            assert "quantitative experimental" not in text
            if result.get("input_origin") == "synthetic_computational":
                assert "synthetic" in result.get("input_artifact", "").lower()
                assert "not a measured" in result.get("uncertainty_or_limitation", "").lower() or "not a biological measurement" in result.get("uncertainty_or_limitation", "").lower()
            if "csv-read" in result.get("method_or_skill_used", ""):
                assert result.get("scienceclaw_skill_execution_ids")
                execution_ids = {execution["execution_id"] for execution in executions}
                assert set(result["scienceclaw_skill_execution_ids"]) <= execution_ids

        needs = investigation.get("computational_input_needs", [])
        if not quantitative:
            assert needs
        for item in needs:
            assert item.get("need_type") == "ComputationalMechanicsInputNeed"
            assert item.get("missing_input_needed")
            assert item.get("would_enable")
            assert item.get("reason")
