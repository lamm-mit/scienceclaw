"""Presentation exports for formal mechanics runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from categoryscienceclaw.mechanics_investigation import build_mechanics_investigation


RUN_TITLES = {
    "7t10_formal_extension": "Example A: 7T10 formal descriptor extension",
    "biomechanics_fiber_network": "Example B: fiber-network biomechanics",
    "membrane_biophysics": "Example C: membrane curvature biophysics",
    "mechanobiology_force_paths": "Example D: mechanobiology force paths",
}


PLACEHOLDER_MARKERS = (
    "basic sympy demonstration",
    "placeholder demonstration",
    "see skill.md",
    "template/scaffold",
    '"status": "available"',
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def contains_placeholder(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True).lower()
    return any(marker in text for marker in PLACEHOLDER_MARKERS)


def classify_artifact(artifact: dict[str, Any]) -> str:
    payload = artifact.get("payload", {})
    if payload.get("result_classification") == "blocked_missing_data" or artifact.get("type") == "BlockedRealDataNeed":
        return "blocked"
    if payload.get("result_classification") == "formal_symbolic_result" and payload.get("formal_result"):
        return "formal"
    scienceclaw = payload.get("scienceclaw", {})
    if scienceclaw.get("accepted_as_substantive") and scienceclaw.get("result_summary"):
        return "valid"
    return "rejected"


def export_presentable_results(run_dir: str | Path) -> Path:
    run_path = Path(run_dir)
    export_dir = run_path / "presentable_results"
    payload_dir = export_dir / "artifact_payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)
    for old in payload_dir.glob("*.json"):
        old.unlink()

    summary = json.loads((run_path / "run_summary.json").read_text(encoding="utf-8"))
    artifacts = load_jsonl(run_path / "artifacts.jsonl")
    produced = [artifact for artifact in artifacts if artifact.get("morphism")]

    grouped: dict[str, list[dict[str, Any]]] = {"valid": [], "formal": [], "blocked": [], "rejected": []}
    for artifact in produced:
        grouped[classify_artifact(artifact)].append(artifact)

    title = RUN_TITLES.get(run_path.name, run_path.name)
    investigation = build_mechanics_investigation(run_path, artifacts)
    investigation_path = export_dir / "MECHANICS_INVESTIGATION.json"
    investigation_path.write_text(json.dumps(investigation, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        f"# {title}",
        "",
        "> Act like a mechanics investigator, not a generic data analyzer.",
        "",
        "## Run Summary",
        "",
        f"- Audit status: `{summary.get('audit_status')}`",
        f"- Executor backend: `{summary.get('executor_backend')}`",
        f"- ScienceClaw agents used: `{summary.get('scienceclaw_agents_used')}`",
        f"- Artifacts emitted: `{summary.get('artifacts_emitted')}`",
        f"- Needs fulfilled: `{summary.get('needs_fulfilled')}`",
        f"- Open needs remaining: `{summary.get('open_needs_remaining')}`",
        f"- Data honesty status: `{summary.get('data_honesty_status')}`",
        "",
    ]

    lines.extend(_investigation_overview(investigation))
    lines.extend(_evidence_plan_section(investigation))
    lines.extend(_quantitative_computational_section(investigation))
    lines.extend(_validation_diagnostics_section(investigation))
    lines.extend(_computational_input_needs_section(investigation))

    if run_path.name == "7t10_formal_extension":
        lines += [
            "## 7T10 Baseline Handling",
            "",
            f"- Formal extension needs fulfilled: `{summary.get('formal_extension_needs_fulfilled')}`",
            f"- Inherited 7T10 science needs remaining: `{summary.get('inherited_7t10_needs_remaining')}`",
            "- Imported baseline artifacts: `contact_graph_7T10`, `force_extension_7T10`, `mechanics_claim_7T10`.",
            "- The run does not rerun hotspot detection or force-extension simulation.",
            "",
        ]

    lines.extend(_section("Valid Results", grouped["valid"], payload_dir, produced))
    lines.extend(_section("Formal/Symbolic Results", grouped["formal"], payload_dir, produced))
    lines.extend(_section("Blocked or Missing Data", grouped["blocked"], payload_dir, produced))
    if grouped["rejected"]:
        lines.extend(_section("Rejected Placeholder Outputs", grouped["rejected"], payload_dir, produced))
    else:
        lines += ["## Rejected Placeholder Outputs", "", "None. Placeholder ScienceClaw outputs were rejected at runtime and replaced with formal results or blocked records.", ""]

    report_path = export_dir / "INVESTIGATION_RESULTS.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def export_presentation_index(root_dir: str | Path) -> Path:
    root = Path(root_dir)
    lines = [
        "# Formal Mechanics Investigation Results",
        "",
        "Presentation-ready reports exported from heartbeat-produced artifacts.",
        "Each report separates valid data-backed results, formal/symbolic results, blocked steps, and rejected placeholder outputs.",
        "",
    ]
    for run_name, title in RUN_TITLES.items():
        run_dir = root / run_name
        if not run_dir.exists():
            continue
        summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
        lines += [
            f"## {title}",
            "",
            f"- Presentation report: `{run_name}/presentable_results/INVESTIGATION_RESULTS.md`",
            f"- Full exported artifact payloads: `{run_name}/presentable_results/artifact_payloads/`",
            f"- Summary: audit `{summary.get('audit_status')}`, backend `{summary.get('executor_backend')}`, artifacts `{summary.get('artifacts_emitted')}`.",
            "",
        ]
    path = root / "PRESENTATION_INDEX.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    export_actual_mechanics_findings(root)
    return path


def export_actual_mechanics_findings(root_dir: str | Path) -> Path:
    root = Path(root_dir)
    lines = [
        "# Actual Mechanics Investigation Findings",
        "",
        "> Act like a mechanics investigator, not a generic data analyzer.",
        "",
        "This file is the presentation-level answer from the four mechanics investigations. It separates quantitative computational mechanics supported by available inputs from formal-only results and additional computational input needs.",
        "",
    ]
    for run_name, title in RUN_TITLES.items():
        sidecar = root / run_name / "presentable_results" / "MECHANICS_INVESTIGATION.json"
        if not sidecar.exists():
            continue
        investigation = json.loads(sidecar.read_text(encoding="utf-8"))
        lines += [
            f"## {title}",
            "",
            f"**Question.** {investigation.get('mechanical_question', '')}",
            "",
        ]
        q_comp = investigation.get("quantitative_computational_mechanics_results", [])
        if q_comp:
            lines += ["**Quantitative computational mechanics findings:**", ""]
            for result in q_comp:
                lines.extend(_finding_result_lines(result))
        else:
            lines += ["**Quantitative computational mechanics findings:** None.", ""]
        lines += [
            "**Formal/symbolic result classes:**",
            "",
            ", ".join(sorted({item.get("formal_result_kind", "") for item in investigation.get("formal_symbolic_result_summary", []) if item.get("formal_result_kind")})) or "None",
            "",
            "**Additional computational input needs:**",
            "",
        ]
        for blocked in investigation.get("computational_input_needs", []):
            lines.append(f"- {blocked.get('missing_input_needed')}: {blocked.get('would_enable')}")
        if not investigation.get("computational_input_needs"):
            lines.append("- None.")
        lines.append("")
    path = root / "ACTUAL_MECHANICS_FINDINGS.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _finding_result_lines(result: dict[str, Any]) -> list[str]:
    lines = [
        f"- {result.get('name', 'Mechanics result')}",
        f"  - Evidence class: `{result.get('evidence_class', '')}`",
        f"  - Input origin: `{result.get('input_origin', '')}`",
        f"  - Method: {result.get('method_or_skill_used', '')}",
        f"  - Input: `{result.get('input_file', '')}`",
    ]
    values = result.get("computed_values", {})
    if "hotspot_positions" in values:
        lines.append(f"  - Hotspot positions: `{values.get('hotspot_positions')}`")
    if "peak_force_pN" in values:
        lines.append(f"  - Peak force: `{values.get('peak_force_pN')}` pN at `{values.get('peak_extension_nm')}` nm")
    if "linear_force_extension_slope_pN_per_nm" in values:
        lines.append(f"  - Linear force-extension slope: `{values.get('linear_force_extension_slope_pN_per_nm')}` pN/nm")
    if "orientation_order_parameter" in values:
        lines.append(
            f"  - Fiber orientation order: `{values.get('orientation_order_parameter')}`; "
            f"principal orientation `{values.get('principal_orientation_deg')}` deg; "
            f"linear stiffness `{values.get('linear_stiffness_kpa')}` kPa"
        )
    if "mean_load_path_score_pa_per_um" in values:
        lines.append(
            f"  - Mean load-path score: `{values.get('mean_load_path_score_pa_per_um')}` Pa/um; "
            f"max traction `{values.get('max_traction_pa')}` Pa on path `{values.get('max_traction_path_id')}`"
        )
    if "rms_curvature_1_um" in values:
        lines.append(
            f"  - RMS curvature: `{values.get('rms_curvature_1_um')}` 1/um; "
            f"mean energy proxy `{values.get('mean_energy_density_proxy_kbt_per_um2')}` kBT/um^2; "
            f"total grid energy proxy `{values.get('total_grid_energy_proxy_kbt')}` kBT"
        )
    diagnostic = result.get("diagnostic", {})
    if "linear_fit_r_squared" in diagnostic:
        lines.append(f"  - Linear fit R^2: `{diagnostic.get('linear_fit_r_squared')}`")
    if result.get("scientific_interpretation"):
        lines.append(f"  - Scientific meaning: {result.get('scientific_interpretation')}")
    lines += [f"  - Limitation: {result.get('uncertainty_or_limitation', '')}", ""]
    return lines


def _investigation_overview(investigation: dict[str, Any]) -> list[str]:
    return [
        "## Mechanics Investigation Question",
        "",
        f"- Mechanical hypothesis: {investigation.get('mechanical_hypothesis', '')}",
        f"- Mechanical question: {investigation.get('mechanical_question', '')}",
        f"- Full smart-investigation payload: `presentable_results/MECHANICS_INVESTIGATION.json`",
        "",
    ]


def _evidence_plan_section(investigation: dict[str, Any]) -> list[str]:
    plan = investigation.get("evidence_plan", {})
    lines = ["## Evidence Plan and Skill Routing", ""]
    lines += ["**Required evidence:**", ""]
    for item in plan.get("required_evidence", []):
        lines.append(f"- {item}")
    lines += ["", "**ScienceClaw skill routing:**", ""]
    for route in plan.get("skill_routing", []):
        lines.append(f"- `{route.get('skill')}`: {route.get('purpose')} Status: `{route.get('status')}`")
    inventory = investigation.get("quantitative_input_search", {})
    lines += [
        "",
        "**Quantitative input search:**",
        "",
        f"- Available input kinds: `{', '.join(inventory.get('available_input_kinds', [])) or 'none'}`",
        f"- Candidate files found: `{len(inventory.get('candidate_files', []))}`",
        "",
    ]
    for item in inventory.get("candidate_files", [])[:8]:
        lines.append(f"- `{Path(item.get('path', '')).name}` from `{item.get('source', '')}`")
    executions = investigation.get("scienceclaw_skill_executions", [])
    lines += ["", "**ScienceClaw skill executions:**", ""]
    if not executions:
        lines.append("- None run; no quantitative input file was eligible for a concrete skill execution.")
    for execution in executions:
        summary = execution.get("result_summary", {})
        lines.append(
            f"- `{execution.get('execution_id')}` used `{execution.get('skill')}` on `{Path(execution.get('input_file', '')).name}`; "
            f"status `{execution.get('status')}`, shape `{summary.get('shape', [])}`."
        )
    return lines + [""]


def _quantitative_computational_section(investigation: dict[str, Any]) -> list[str]:
    lines = ["## Quantitative Computational Mechanics Results", ""]
    results = investigation.get("quantitative_computational_mechanics_results", [])
    if not results:
        return lines + ["None.", ""]
    for result in results:
        lines.extend(_quantitative_result_lines(result))
    return lines


def _quantitative_result_lines(result: dict[str, Any]) -> list[str]:
    return [
        f"### {result.get('name', 'Quantitative mechanics result')}",
        "",
        f"- Evidence class: `{result.get('evidence_class', '')}`",
        f"- Input artifact: `{result.get('input_artifact', '')}`",
        f"- Input file: `{result.get('input_file', '')}`",
        f"- Method/skill used: {result.get('method_or_skill_used', '')}",
        "",
        "**Computed values:**",
        "",
        "```json",
        json.dumps(result.get("computed_values", {}), indent=2, sort_keys=True),
        "```",
        "",
        "**Units:**",
        "",
        "```json",
        json.dumps(result.get("units", {}), indent=2, sort_keys=True),
        "```",
        "",
        "**Diagnostic:**",
        "",
        "```json",
        json.dumps(result.get("diagnostic", {}), indent=2, sort_keys=True),
        "```",
        "",
        f"**Scientific interpretation:** {result.get('scientific_interpretation', '')}",
        "",
        f"**Uncertainty or limitation:** {result.get('uncertainty_or_limitation', '')}",
        "",
    ]


def _validation_diagnostics_section(investigation: dict[str, Any]) -> list[str]:
    return [
        "## Validation and Diagnostics",
        "",
        "```json",
        json.dumps(investigation.get("validation_and_diagnostics", {}), indent=2, sort_keys=True),
        "```",
        "",
    ]


def _computational_input_needs_section(investigation: dict[str, Any]) -> list[str]:
    lines = ["## Computational Input Needs", ""]
    blocked = investigation.get("computational_input_needs", [])
    if not blocked:
        return lines + ["None.", ""]
    for item in blocked:
        lines += [
            f"### {item.get('missing_input_needed', 'Missing input')}",
            "",
            f"- Need type: `{item.get('need_type')}`",
            f"- Would enable: {item.get('would_enable')}",
            f"- Reason: {item.get('reason')}",
            f"- Current available input kinds: `{', '.join(item.get('current_available_input_kinds', [])) or 'none'}`",
            "",
        ]
    return lines


def _section(title: str, artifacts: list[dict[str, Any]], payload_dir: Path, produced: list[dict[str, Any]]) -> list[str]:
    lines = [f"## {title}", ""]
    if not artifacts:
        return lines + ["None.", ""]
    for artifact in artifacts:
        index = produced.index(artifact) + 1
        payload = artifact.get("payload", {})
        scienceclaw = payload.get("scienceclaw", {})
        payload_file = payload_dir / f"{index:02d}_{artifact['id']}_{artifact['type']}.json"
        payload_file.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")

        lines += [
            f"### {index}. {artifact['type']}",
            "",
            f"- Artifact ID: `{artifact['id']}`",
            f"- Morphism: `{artifact.get('morphism', '')}`",
            f"- Agent: `{artifact.get('producer_agent', '')}`",
            f"- Full payload: `presentable_results/artifact_payloads/{payload_file.name}`",
            f"- Result classification: `{payload.get('result_classification', 'unknown')}`",
            "",
        ]
        if scienceclaw:
            lines += [
                "**ScienceClaw execution audit:**",
                "",
                f"- Skill attempted: `{scienceclaw.get('skill_name', '')}`",
                f"- Accepted as substantive: `{scienceclaw.get('accepted_as_substantive', False)}`",
                "",
            ]
        if payload.get("formal_result"):
            lines += ["**Formal result:**", "", "```json", json.dumps(payload["formal_result"], indent=2, sort_keys=True), "```", ""]
        elif scienceclaw.get("result_summary"):
            lines += ["**ScienceClaw result:**", "", "```json", json.dumps(scienceclaw["result_summary"], indent=2, sort_keys=True), "```", ""]
        if payload.get("blocked_reason"):
            lines += ["**Blocked reason:**", "", payload["blocked_reason"], ""]
            lines += ["**Missing input needed:**", "", payload.get("missing_input_needed", "unspecified external data"), ""]
        if scienceclaw.get("rejected_placeholder_summary"):
            lines += [
                "**Rejected ScienceClaw output:**",
                "",
                "The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.",
                "",
            ]
    return lines
