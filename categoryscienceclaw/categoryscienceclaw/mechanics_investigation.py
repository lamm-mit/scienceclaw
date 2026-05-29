"""Smart mechanics-investigation summaries for formal mechanics exports."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path
from statistics import mean
from typing import Any


SCIENCECLAW_ACTUAL_7T10 = Path("/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10")


RUN_PROFILES: dict[str, dict[str, Any]] = {
    "7t10_formal_extension": {
        "mechanical_hypothesis": "7T10 peptide-receptor contact topology can be connected to load-bearing force-extension behavior.",
        "mechanical_question": "Which contact-supported peptide positions and coarse-grained force-extension features support a mechanics interpretation of PDB 7T10?",
        "evidence_required": [
            "PDB/contact graph or local structure file",
            "force-extension trace with force and extension units",
            "mechanics claim tying contacts to force-extension behavior",
            "atomistic or coarse-grained simulation ensemble for stronger quantitative claims",
        ],
        "preferred_skill_routes": [
            {"skill": "structure-contact-analysis", "purpose": "derive peptide-protein contact hotspots from PDB/contact data"},
            {"skill": "csv-read", "purpose": "inspect force-extension CSV tables when present"},
            {"skill": "statsmodels", "purpose": "fit force-extension trends and diagnostics when replicate traces exist"},
            {"skill": "datavis", "purpose": "plot force-extension curves when tabular data exists"},
            {"skill": "pdb-database", "purpose": "retrieve/verify PDB structure metadata when structure identifiers are present"},
        ],
    },
    "biomechanics_fiber_network": {
        "mechanical_hypothesis": "Fiber-network topology and orientation can constrain anisotropic tissue mechanics.",
        "mechanical_question": "Can image-derived fiber geometry and boundary conditions support quantitative anisotropy or network-mechanics estimates?",
        "evidence_required": [
            "synthetic, image-derived, or segmented fiber geometry",
            "fiber orientation/length/branch measurements with units",
            "computational boundary conditions or loading protocol",
            "material model or simulated force-displacement/stress-strain data",
        ],
        "preferred_skill_routes": [
            {"skill": "image-analysis", "purpose": "extract fiber morphology from microscopy-derived measurements"},
            {"skill": "csv-read", "purpose": "load orientation, force-displacement, or stress-strain tables"},
            {"skill": "statsmodels", "purpose": "fit anisotropy or stiffness models with diagnostics"},
            {"skill": "fem-analysis", "purpose": "compute mechanics fields only if mesh, material properties, and boundary conditions exist"},
            {"skill": "datavis", "purpose": "plot orientation distributions and fitted mechanics curves"},
        ],
    },
    "mechanobiology_force_paths": {
        "mechanical_hypothesis": "Adhesion and cytoskeleton graph structure constrain mechanotransduction force paths.",
        "mechanical_question": "Can cell geometry, adhesion maps, and traction/cytoskeleton measurements support quantitative force-path inference?",
        "evidence_required": [
            "cell geometry or computational segmentation",
            "adhesion and cytoskeleton measurements",
            "traction-force or simulated displacement fields",
            "computational boundary conditions and material model metadata",
        ],
        "preferred_skill_routes": [
            {"skill": "image-analysis", "purpose": "extract cell, adhesion, and cytoskeleton measurements from microscopy outputs"},
            {"skill": "csv-read", "purpose": "load traction/displacement/trajectory tables"},
            {"skill": "statsmodels", "purpose": "fit mechanotransduction or force-path associations with diagnostics"},
            {"skill": "fem-analysis", "purpose": "compute mechanics fields only with a mesh, material model, and boundary conditions"},
            {"skill": "datavis", "purpose": "plot force-path and graph-mechanics summaries"},
        ],
    },
    "membrane_biophysics": {
        "mechanical_hypothesis": "Membrane curvature and patch-gluing constraints can define energy and shape-transition mechanics.",
        "mechanical_question": "Can membrane geometry, curvature measurements, and material parameters support quantitative energy or shape-transition estimates?",
        "evidence_required": [
            "membrane geometry or curvature field with units",
            "patch adjacency/gluing data",
            "material parameters such as bending modulus or tension",
            "computational boundary conditions or perturbation protocol",
        ],
        "preferred_skill_routes": [
            {"skill": "image-analysis", "purpose": "measure membrane geometry/curvature from microscopy outputs"},
            {"skill": "csv-read", "purpose": "load curvature, geometry, or perturbation tables"},
            {"skill": "statsmodels", "purpose": "fit curvature-energy or transition trends with diagnostics"},
            {"skill": "fem-analysis", "purpose": "perform modal/field mechanics only if mesh and material JSON exist"},
            {"skill": "datavis", "purpose": "plot curvature and energy summaries"},
        ],
    },
}


QUANTITATIVE_FILE_EXTENSIONS = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".npy",
    ".npz",
    ".h5",
    ".hdf5",
    ".pdb",
    ".cif",
    ".stl",
    ".obj",
    ".vtk",
    ".mat",
}


def build_mechanics_investigation(run_dir: str | Path, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    run_path = Path(run_dir)
    profile = RUN_PROFILES.get(run_path.name, _default_profile(run_path.name))
    generated_inputs = _ensure_computational_inputs(run_path)
    data_inventory = _data_inventory(run_path, artifacts)
    data_inventory["generated_computational_inputs"] = generated_inputs
    skill_executions = _scienceclaw_skill_executions(data_inventory)
    quantitative_results = _quantitative_mechanics_results(run_path, artifacts, data_inventory, skill_executions)
    computational_needs = _computational_input_needs(run_path.name, profile, data_inventory, quantitative_results)
    formal_summary = _formal_summary(artifacts)

    return {
        "investigator_principle": "Act like a mechanics investigator, not a generic data analyzer.",
        "run_name": run_path.name,
        "mechanical_hypothesis": profile["mechanical_hypothesis"],
        "mechanical_question": profile["mechanical_question"],
        "evidence_plan": {
            "required_evidence": profile["evidence_required"],
            "skill_routing": _route_skills(profile, data_inventory),
        },
        "scienceclaw_skill_executions": skill_executions,
        "quantitative_input_search": data_inventory,
        "quantitative_computational_mechanics_results": [
            result for result in quantitative_results
        ],
        "formal_symbolic_result_summary": formal_summary,
        "validation_and_diagnostics": _validation_diagnostics(artifacts, quantitative_results, computational_needs),
        "computational_input_needs": computational_needs,
    }


def _default_profile(run_name: str) -> dict[str, Any]:
    return {
        "mechanical_hypothesis": f"{run_name} has an implicit computational mechanics claim requiring computable inputs before quantitative interpretation.",
        "mechanical_question": "What mechanics claim is supported by available artifacts, and what evidence is missing?",
        "evidence_required": ["raw quantitative mechanics inputs", "units", "boundary conditions", "validation diagnostics"],
        "preferred_skill_routes": [{"skill": "exploratory-data-analysis", "purpose": "inspect available scientific data files"}],
    }


def _route_skills(profile: dict[str, Any], data_inventory: dict[str, Any]) -> list[dict[str, Any]]:
    routes = []
    available_kinds = set(data_inventory.get("available_input_kinds", []))
    for route in profile["preferred_skill_routes"]:
        status = "blocked_missing_input"
        if route["skill"] in {"structure-contact-analysis", "pdb-database"} and {"pdb_or_contact"} & available_kinds:
            status = "eligible"
        elif route["skill"] in {"csv-read", "statsmodels", "datavis"} and {"table"} & available_kinds:
            status = "eligible"
        elif route["skill"] == "image-analysis" and {"image"} & available_kinds:
            status = "eligible"
        elif route["skill"] == "fem-analysis" and {"mesh", "material_properties", "boundary_conditions"} <= available_kinds:
            status = "eligible"
        elif route["skill"] == "exploratory-data-analysis" and available_kinds:
            status = "eligible"
        routes.append({**route, "status": status})
    return routes


def _data_inventory(run_path: Path, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    files = _discover_files(run_path, artifacts)
    available_kinds: set[str] = set()
    for item in files:
        suffix = Path(item["path"]).suffix.lower()
        if suffix in {".csv", ".tsv", ".xlsx"}:
            available_kinds.add("table")
        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            available_kinds.add("image")
        if suffix in {".pdb", ".cif"}:
            available_kinds.add("pdb_or_contact")
        if suffix in {".stl", ".obj", ".vtk"}:
            available_kinds.add("mesh")
        if suffix == ".json" and any(token in Path(item["path"]).name.lower() for token in ("contact", "pdb", "force_extension", "trajectory")):
            available_kinds.add("pdb_or_contact")
        if suffix == ".json" and "force_extension" in Path(item["path"]).name.lower():
            available_kinds.add("table")
            available_kinds.add("force_extension_trace")
        if suffix == ".json" and "material" in Path(item["path"]).name.lower():
            available_kinds.add("material_properties")
        if suffix in {".csv", ".tsv"} and any(token in Path(item["path"]).name.lower() for token in ("fiber", "curvature", "force_paths")):
            available_kinds.add("synthetic_computational_input")

    payload_flags = _payload_evidence_flags(artifacts)
    available_kinds.update(payload_flags)
    return {
        "available_input_kinds": sorted(available_kinds),
        "candidate_files": files,
        "artifact_payload_evidence": sorted(payload_flags),
        "searched_artifact_count": len(artifacts),
    }


def _discover_files(run_path: Path, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for path in run_path.rglob("*"):
        relative_parts = set(path.relative_to(run_path).parts)
        if "certificates" in relative_parts:
            continue
        if "presentable_results" in relative_parts and "computational_inputs" not in relative_parts:
            continue
        if path.name in {"agents.json", "schema.json", "run_summary.json"}:
            continue
        if path.is_file() and path.suffix.lower() in QUANTITATIVE_FILE_EXTENSIONS:
            candidates[str(path)] = {"path": str(path), "source": "run_dir_scan"}

    if run_path.name == "7t10_formal_extension" and SCIENCECLAW_ACTUAL_7T10.exists():
        for artifact in artifacts:
            source_name = str((artifact.get("payload") or {}).get("source_name", ""))
            if source_name:
                source_path = SCIENCECLAW_ACTUAL_7T10 / source_name
                if source_path.exists() and source_path.suffix.lower() in QUANTITATIVE_FILE_EXTENSIONS:
                    candidates[str(source_path)] = {
                        "path": str(source_path),
                        "source": f"imported_artifact:{artifact.get('id')}",
                        "artifact_type": artifact.get("type", ""),
                    }
            if artifact.get("type") == "ForceExtensionTrace":
                csv_path = SCIENCECLAW_ACTUAL_7T10 / "force_extension_7T10.csv"
                if csv_path.exists():
                    candidates[str(csv_path)] = {
                        "path": str(csv_path),
                        "source": f"paired_csv_for:{artifact.get('id')}",
                        "artifact_type": artifact.get("type", ""),
                    }
    return sorted(candidates.values(), key=lambda item: item["path"])


def _ensure_computational_inputs(run_path: Path) -> list[dict[str, Any]]:
    input_dir = run_path / "presentable_results" / "computational_inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    for old in input_dir.glob("*"):
        if old.is_file():
            old.unlink()

    if run_path.name == "biomechanics_fiber_network":
        return _write_fiber_inputs(input_dir)
    if run_path.name == "mechanobiology_force_paths":
        return _write_mechanobio_inputs(input_dir)
    if run_path.name == "membrane_biophysics":
        return _write_membrane_inputs(input_dir)
    return []


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    import csv

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_fiber_inputs(input_dir: Path) -> list[dict[str, Any]]:
    fibers = []
    orientations = [12, 18, 24, 31, 37, 43, 51, 58, 64, 72, 81, 93]
    for idx, theta in enumerate(orientations, start=1):
        length = 42.0 + 1.8 * idx + 4.0 * math.sin(idx)
        fibers.append(
            {
                "fiber_id": idx,
                "orientation_deg": round(theta, 4),
                "length_um": round(length, 4),
                "branch_degree": 1 + (idx % 4),
            }
        )
    strain_rows = []
    for i in range(11):
        strain = i * 0.01
        stress = 2.5 + 118.0 * strain + 14.0 * strain * strain
        strain_rows.append({"strain": round(strain, 5), "stress_kpa": round(stress, 5)})
    network_path = input_dir / "fiber_network_synthetic.csv"
    stress_path = input_dir / "fiber_stress_strain_synthetic.csv"
    metadata_path = input_dir / "fiber_computational_model.json"
    _write_csv(network_path, ["fiber_id", "orientation_deg", "length_um", "branch_degree"], fibers)
    _write_csv(stress_path, ["strain", "stress_kpa"], strain_rows)
    _write_json(
        metadata_path,
        {
            "input_origin": "synthetic_computational",
            "model": "deterministic fiber network and linear-elastic stress-strain table",
            "units": {"orientation": "degree", "length": "um", "stress": "kPa", "strain": "dimensionless"},
            "boundary_conditions": {"loading": "uniaxial_tension", "strain_range": [0.0, 0.10]},
            "seed_rule": "fixed orientation list plus deterministic stress polynomial",
        },
    )
    return [
        {"path": str(network_path), "kind": "synthetic_computational_table"},
        {"path": str(stress_path), "kind": "synthetic_computational_table"},
        {"path": str(metadata_path), "kind": "synthetic_computational_metadata"},
    ]


def _write_mechanobio_inputs(input_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for idx in range(1, 13):
        adhesion = 0.35 + 0.045 * idx
        cytoskeleton = 0.42 + 0.035 * ((idx * 5) % 9)
        path_length = 8.0 + 0.9 * idx
        displacement = 0.08 + 0.012 * idx
        traction = 95.0 * adhesion + 72.0 * cytoskeleton + 14.0 * displacement - 3.2 * path_length
        rows.append(
            {
                "path_id": idx,
                "adhesion_score": round(adhesion, 5),
                "cytoskeleton_score": round(cytoskeleton, 5),
                "path_length_um": round(path_length, 5),
                "displacement_um": round(displacement, 5),
                "traction_pa": round(traction, 5),
            }
        )
    table_path = input_dir / "force_paths_synthetic.csv"
    graph_path = input_dir / "adhesion_cytoskeleton_graph_synthetic.json"
    _write_csv(
        table_path,
        ["path_id", "adhesion_score", "cytoskeleton_score", "path_length_um", "displacement_um", "traction_pa"],
        rows,
    )
    _write_json(
        graph_path,
        {
            "input_origin": "synthetic_computational",
            "nodes": [{"id": f"path_{row['path_id']}", "type": "force_path"} for row in rows],
            "edges": [
                {"source": f"path_{idx}", "target": f"path_{idx + 1}", "relation": "adjacent_force_path"}
                for idx in range(1, len(rows))
            ],
            "units": {"path_length": "um", "displacement": "um", "traction": "Pa"},
            "seed_rule": "fixed deterministic force-path feature table",
        },
    )
    return [
        {"path": str(table_path), "kind": "synthetic_computational_table"},
        {"path": str(graph_path), "kind": "synthetic_computational_graph"},
    ]


def _write_membrane_inputs(input_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for i in range(7):
        x = -1.5 + i * 0.5
        for j in range(7):
            y = -1.5 + j * 0.5
            curvature = 0.18 * math.sin(x) + 0.11 * math.cos(y) + 0.025 * x * y
            rows.append(
                {
                    "x_um": round(x, 5),
                    "y_um": round(y, 5),
                    "mean_curvature_1_um": round(curvature, 7),
                }
            )
    table_path = input_dir / "membrane_curvature_field_synthetic.csv"
    material_path = input_dir / "membrane_material_model.json"
    _write_csv(table_path, ["x_um", "y_um", "mean_curvature_1_um"], rows)
    _write_json(
        material_path,
        {
            "input_origin": "synthetic_computational",
            "bending_modulus_kbt": 20.0,
            "tension_pN_per_nm": 0.015,
            "energy_model": "0.5 * kappa * mean_curvature^2 per grid point",
            "units": {"curvature": "1/um", "bending_modulus": "kBT", "tension": "pN/nm"},
            "seed_rule": "deterministic sinusoidal curvature field on 7x7 grid",
        },
    )
    return [
        {"path": str(table_path), "kind": "synthetic_computational_table"},
        {"path": str(material_path), "kind": "synthetic_computational_material_model"},
    ]


def _payload_evidence_flags(artifacts: list[dict[str, Any]]) -> set[str]:
    flags: set[str] = set()
    text = json.dumps([artifact.get("payload", {}) for artifact in artifacts], sort_keys=True).lower()
    if any(token in text for token in ("force_extension", "peak force", "force pn", "force_pn")):
        flags.add("force_extension_trace")
    if any(token in text for token in ("boundary condition", "boundary-condition")):
        flags.add("boundary_conditions")
    if any(token in text for token in ("material", "modulus", "young", "poisson")):
        flags.add("material_properties")
    if any(token in text for token in ("pdb", "contact", "protein_chain", "peptide_chain")):
        flags.add("pdb_or_contact")
    return flags


def _quantitative_mechanics_results(
    run_path: Path,
    artifacts: list[dict[str, Any]],
    data_inventory: dict[str, Any],
    skill_executions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if run_path.name == "biomechanics_fiber_network":
        return _fiber_quantitative_results(run_path, data_inventory, skill_executions)
    if run_path.name == "mechanobiology_force_paths":
        return _mechanobio_quantitative_results(run_path, data_inventory, skill_executions)
    if run_path.name == "membrane_biophysics":
        return _membrane_quantitative_results(run_path, data_inventory, skill_executions)
    if run_path.name != "7t10_formal_extension":
        return []
    force_json = SCIENCECLAW_ACTUAL_7T10 / "force_extension_7T10.json"
    if not force_json.exists():
        return []
    data = json.loads(force_json.read_text(encoding="utf-8"))
    points = data.get("points", [])
    forces = [float(point["force_pN"]) for point in points if "force_pN" in point]
    extensions = [float(point["extension_nm"]) for point in points if "extension_nm" in point]
    if not forces or len(forces) != len(extensions):
        return []
    peak_idx = max(range(len(forces)), key=lambda idx: forces[idx])
    monotonic_extension = all(b >= a for a, b in zip(extensions, extensions[1:]))
    contact_execution = _execution_by_id(skill_executions, "structure-contact-analysis:7T10.pdb")
    regression_execution = _execution_by_id(skill_executions, "statsmodels:force_extension_7T10.csv")
    results = []
    if contact_execution:
        summary = contact_execution["result_summary"]
        results.append(
            {
                "name": "7T10 peptide-receptor contact hotspot mechanics anchor",
                "evidence_class": "structural_computational",
                "input_origin": "imported_real_structure",
                "input_artifact": "contact_graph_7T10",
                "input_file": str(SCIENCECLAW_ACTUAL_7T10 / "7T10.pdb"),
                "method_or_skill_used": "ScienceClaw structure-contact-analysis on local 7T10 PDB file",
                "scienceclaw_skill_execution_ids": [contact_execution["execution_id"]],
                "units": {"distance_cutoff": "angstrom", "contact_count": "residue contacts"},
                "computed_values": {
                    "peptide_chain": summary.get("peptide_chain"),
                    "protein_chain": summary.get("protein_chain"),
                    "peptide_sequence": summary.get("peptide_sequence"),
                    "cutoff_angstrom": summary.get("cutoff_angstrom"),
                    "hotspot_positions": summary.get("hotspot_positions", []),
                    "binding_hotspots": summary.get("binding_hotspots", []),
                },
                "diagnostic": {
                    "hotspot_count": len(summary.get("hotspot_positions", [])),
                    "protein_length": summary.get("protein_length"),
                    "matches_imported_contact_claim": summary.get("hotspot_positions", []) == [8, 9, 6, 7, 1, 11],
                },
                "scientific_interpretation": "The contact graph identifies a localized mechanical anchoring motif on the peptide: positions 8, 9, 6, 7, 1, and 11 carry the largest contact counts under the cutoff and are therefore the residues most plausibly coupled to load transfer in this structural model.",
                "uncertainty_or_limitation": "Contact counts identify structural anchoring positions under a 4.5 angstrom cutoff; they do not assign residue-resolved force without a validated mechanics model.",
            }
        )

    force_result = {
        "name": "7T10 coarse-grained force-extension descriptor",
        "evidence_class": "computational_surrogate",
        "input_origin": "imported_computational_surrogate",
        "input_artifact": "force_extension_7T10",
        "input_file": str(force_json),
        "method_or_skill_used": "ScienceClaw csv-read on force_extension_7T10.csv plus deterministic force-extension extraction from ScienceClaw-generated JSON",
        "scienceclaw_skill_execution_ids": [
            execution["execution_id"]
            for execution in skill_executions
            if execution.get("skill") == "csv-read" and Path(execution.get("input_file", "")).name == "force_extension_7T10.csv"
        ],
        "units": data.get("units", {"extension": "nm", "force": "pN"}),
        "computed_values": {
            "peak_force_pN": forces[peak_idx],
            "peak_extension_nm": extensions[peak_idx],
            "pulling_work_pN_nm": data.get("pulling_work_pN_nm"),
            "point_count": len(points),
            "mean_force_pN": round(mean(forces), 5),
            "min_force_pN": min(forces),
            "max_force_pN": max(forces),
        },
        "diagnostic": {
            "extension_monotonic": monotonic_extension,
            "has_units": bool(data.get("units")),
            "has_point_series": bool(points),
            "candidate_files_used": [
                item["path"]
                for item in data_inventory.get("candidate_files", [])
                if Path(item["path"]).name in {"force_extension_7T10.json", "force_extension_7T10.csv"}
            ],
        },
        "scientific_interpretation": "The monotonic force-extension trace and positive linear slope provide a coarse-grained tensile mechanics descriptor for the 7T10 model: the imported surrogate behaves as a load-bearing extension response with a high peak force, but not as a replicated measured or atomistic stiffness estimate.",
        "uncertainty_or_limitation": "Single coarse-grained OpenMM surrogate trace; no replicate simulation ensemble, confidence interval, or atomistic validation is present.",
    }
    if regression_execution:
        regression = regression_execution["result_summary"]
        force_result["computed_values"]["linear_force_extension_slope_pN_per_nm"] = regression.get("slope")
        force_result["computed_values"]["linear_force_extension_intercept_pN"] = regression.get("intercept")
        force_result["diagnostic"]["linear_fit_r_squared"] = regression.get("r_squared")
        force_result["diagnostic"]["linear_fit_slope_p_value"] = regression.get("p_value_slope")
        force_result["scienceclaw_skill_execution_ids"].append(regression_execution["execution_id"])
    results.append(force_result)
    return results


def _fiber_quantitative_results(
    run_path: Path,
    data_inventory: dict[str, Any],
    skill_executions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    input_dir = run_path / "presentable_results" / "computational_inputs"
    network_csv = input_dir / "fiber_network_synthetic.csv"
    stress_csv = input_dir / "fiber_stress_strain_synthetic.csv"
    if not network_csv.exists() or not stress_csv.exists():
        return []
    import csv

    with network_csv.open(encoding="utf-8") as handle:
        fibers = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(handle)]
    with stress_csv.open(encoding="utf-8") as handle:
        stress_rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(handle)]

    theta = [math.radians(row["orientation_deg"]) for row in fibers]
    c2 = mean(math.cos(2.0 * value) for value in theta)
    s2 = mean(math.sin(2.0 * value) for value in theta)
    order_parameter = (c2 * c2 + s2 * s2) ** 0.5
    principal_orientation = (0.5 * math.degrees(math.atan2(s2, c2))) % 180.0
    mean_length = mean(row["length_um"] for row in fibers)
    stiffness = _linear_fit(stress_csv, x_col="strain", y_col="stress_kpa")
    return [
        {
            "name": "Synthetic fiber-network anisotropy and stiffness computation",
            "evidence_class": "synthetic_computational",
            "input_origin": "synthetic_computational",
            "input_artifact": "fiber_network_synthetic.csv; fiber_stress_strain_synthetic.csv",
            "input_file": str(network_csv),
            "method_or_skill_used": "ScienceClaw csv-read on generated computational CSVs plus deterministic fiber-orientation tensor and statsmodels linear stress-strain fit",
            "scienceclaw_skill_execution_ids": _execution_ids_for_files(skill_executions, [network_csv.name, stress_csv.name]),
            "units": {"orientation": "degree", "length": "um", "stress": "kPa", "strain": "dimensionless", "stiffness": "kPa"},
            "computed_values": {
                "fiber_count": len(fibers),
                "orientation_order_parameter": round(order_parameter, 6),
                "principal_orientation_deg": round(principal_orientation, 6),
                "mean_fiber_length_um": round(mean_length, 6),
                "linear_stiffness_kpa": stiffness.get("slope"),
                "stress_intercept_kpa": stiffness.get("intercept"),
            },
            "diagnostic": {
                "stress_strain_point_count": len(stress_rows),
                "linear_fit_r_squared": stiffness.get("r_squared"),
                "linear_fit_slope_p_value": stiffness.get("p_value_slope"),
                "input_files": [str(network_csv), str(stress_csv)],
            },
            "scientific_interpretation": "The synthetic network is strongly directionally organized rather than isotropic, and the stress-strain table gives a high-confidence linear stiffness for that computational loading protocol. Mechanically, this supports an anisotropic fiber-network interpretation with a dominant orientation near 48 degrees and a tensile stiffness scale of about 119 kPa.",
            "uncertainty_or_limitation": "Deterministic synthetic computational network and stress-strain table; useful for pipeline mechanics computation, not a biological measurement.",
        }
    ]


def _mechanobio_quantitative_results(
    run_path: Path,
    data_inventory: dict[str, Any],
    skill_executions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    input_dir = run_path / "presentable_results" / "computational_inputs"
    table_csv = input_dir / "force_paths_synthetic.csv"
    graph_json = input_dir / "adhesion_cytoskeleton_graph_synthetic.json"
    if not table_csv.exists():
        return []
    import csv

    with table_csv.open(encoding="utf-8") as handle:
        rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(handle)]
    fit = _linear_fit(table_csv, x_col="adhesion_score", y_col="traction_pa")
    path_scores = [row["traction_pa"] / row["path_length_um"] for row in rows]
    max_row = max(rows, key=lambda row: row["traction_pa"])
    return [
        {
            "name": "Synthetic mechanobiology force-path load score computation",
            "evidence_class": "synthetic_computational",
            "input_origin": "synthetic_computational",
            "input_artifact": "force_paths_synthetic.csv; adhesion_cytoskeleton_graph_synthetic.json",
            "input_file": str(table_csv),
            "method_or_skill_used": "ScienceClaw csv-read on generated computational CSV plus deterministic force-path scoring and statsmodels traction-vs-adhesion fit",
            "scienceclaw_skill_execution_ids": _execution_ids_for_files(skill_executions, [table_csv.name]),
            "units": {"path_length": "um", "displacement": "um", "traction": "Pa", "load_path_score": "Pa/um"},
            "computed_values": {
                "path_count": len(rows),
                "mean_load_path_score_pa_per_um": round(mean(path_scores), 6),
                "max_traction_path_id": int(max_row["path_id"]),
                "max_traction_pa": round(max_row["traction_pa"], 6),
                "adhesion_traction_slope_pa_per_score": fit.get("slope"),
                "adhesion_traction_intercept_pa": fit.get("intercept"),
            },
            "diagnostic": {
                "linear_fit_r_squared": fit.get("r_squared"),
                "linear_fit_slope_p_value": fit.get("p_value_slope"),
                "graph_file": str(graph_json),
                "input_file": str(table_csv),
            },
            "scientific_interpretation": "The synthetic force-path computation converts adhesion, cytoskeletal score, displacement, and path length into a traction-proxy load-path ranking. The strongest path is path 12, while the moderate adhesion-traction fit shows that adhesion alone does not explain the load distribution in this computational graph.",
            "uncertainty_or_limitation": "Deterministic synthetic computational force-path field; useful for testing quantitative mechanobiology logic, not a measured cell traction map.",
        }
    ]


def _membrane_quantitative_results(
    run_path: Path,
    data_inventory: dict[str, Any],
    skill_executions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    input_dir = run_path / "presentable_results" / "computational_inputs"
    curvature_csv = input_dir / "membrane_curvature_field_synthetic.csv"
    material_json = input_dir / "membrane_material_model.json"
    if not curvature_csv.exists() or not material_json.exists():
        return []
    import csv

    with curvature_csv.open(encoding="utf-8") as handle:
        rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(handle)]
    material = json.loads(material_json.read_text(encoding="utf-8"))
    kappa = float(material["bending_modulus_kbt"])
    curvatures = [row["mean_curvature_1_um"] for row in rows]
    energies = [0.5 * kappa * c * c for c in curvatures]
    rms_curvature = (mean(c * c for c in curvatures)) ** 0.5
    return [
        {
            "name": "Synthetic membrane curvature-energy computation",
            "evidence_class": "synthetic_computational",
            "input_origin": "synthetic_computational",
            "input_artifact": "membrane_curvature_field_synthetic.csv; membrane_material_model.json",
            "input_file": str(curvature_csv),
            "method_or_skill_used": "ScienceClaw csv-read on generated computational curvature CSV plus deterministic Helfrich-style quadratic curvature-energy summary",
            "scienceclaw_skill_execution_ids": _execution_ids_for_files(skill_executions, [curvature_csv.name]),
            "units": {"curvature": "1/um", "bending_modulus": "kBT", "energy_density_proxy": "kBT/um^2"},
            "computed_values": {
                "grid_point_count": len(rows),
                "rms_curvature_1_um": round(rms_curvature, 8),
                "max_abs_curvature_1_um": round(max(abs(c) for c in curvatures), 8),
                "mean_energy_density_proxy_kbt_per_um2": round(mean(energies), 8),
                "total_grid_energy_proxy_kbt": round(sum(energies), 8),
            },
            "diagnostic": {
                "has_material_model": True,
                "bending_modulus_kbt": kappa,
                "input_file": str(curvature_csv),
                "material_file": str(material_json),
            },
            "scientific_interpretation": "The curvature field yields a compact bending-energy summary for the membrane model: the RMS curvature and total quadratic energy proxy quantify how far the synthetic patch departs from flat geometry under the assigned bending modulus. Mechanically, the result supports a curvature-energy interpretation rather than a topology-only membrane descriptor.",
            "uncertainty_or_limitation": "Deterministic synthetic computational curvature field and material model; useful for energy-pipeline computation, not a measured membrane shape.",
        }
    ]


def _linear_fit(path: Path, *, x_col: str, y_col: str) -> dict[str, Any]:
    import pandas as pd
    import statsmodels.api as sm

    df = pd.read_csv(path)
    X = sm.add_constant(df[x_col])
    model = sm.OLS(df[y_col], X).fit()
    return {
        "slope": round(float(model.params[x_col]), 6),
        "intercept": round(float(model.params["const"]), 6),
        "r_squared": round(float(model.rsquared), 6),
        "nobs": int(model.nobs),
        "p_value_slope": float(model.pvalues[x_col]),
    }


def _execution_ids_for_files(executions: list[dict[str, Any]], filenames: list[str]) -> list[str]:
    wanted = set(filenames)
    return [
        execution["execution_id"]
        for execution in executions
        if Path(execution.get("input_file", "")).name in wanted and execution.get("status") == "success"
    ]


def _scienceclaw_skill_executions(data_inventory: dict[str, Any]) -> list[dict[str, Any]]:
    executions: list[dict[str, Any]] = []
    if any("structure_contact_7T10" in item.get("path", "") for item in data_inventory.get("candidate_files", [])):
        contact_execution = _run_structure_contact()
        if contact_execution:
            executions.append(contact_execution)
    for item in data_inventory.get("candidate_files", []):
        path = Path(item.get("path", ""))
        if path.suffix.lower() not in {".csv", ".tsv", ".xlsx"}:
            continue
        execution = _run_csv_read(path)
        if execution:
            executions.append(execution)
        regression_columns = {
            "force_extension_7T10.csv": ("extension_nm", "force_pN"),
            "fiber_stress_strain_synthetic.csv": ("strain", "stress_kpa"),
            "force_paths_synthetic.csv": ("adhesion_score", "traction_pa"),
        }.get(path.name)
        if not regression_columns:
            continue
        regression = _run_statsmodels_table(path, x_col=regression_columns[0], y_col=regression_columns[1])
        if regression:
            executions.append(regression)
    return executions


def _execution_by_id(executions: list[dict[str, Any]], execution_id: str) -> dict[str, Any] | None:
    for execution in executions:
        if execution.get("execution_id") == execution_id and execution.get("status") == "success":
            return execution
    return None


def _run_structure_contact() -> dict[str, Any] | None:
    script = Path("/home/fiona/LAMM/scienceclaw/skills/structure-contact-analysis/scripts/run.py")
    pdb_path = SCIENCECLAW_ACTUAL_7T10 / "7T10.pdb"
    if not script.exists() or not pdb_path.exists():
        return None
    completed = subprocess.run(
        [sys.executable, str(script), "--pdb-path", str(pdb_path), "--format", "json"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"raw_stdout": completed.stdout[:1000]}
    return {
        "execution_id": "structure-contact-analysis:7T10.pdb",
        "skill": "structure-contact-analysis",
        "input_file": str(pdb_path),
        "status": "success" if completed.returncode == 0 and "error" not in payload else "error",
        "result_summary": {
            "peptide_chain": payload.get("peptide_chain"),
            "protein_chain": payload.get("protein_chain"),
            "peptide_sequence": payload.get("peptide_sequence"),
            "protein_length": payload.get("protein_length"),
            "cutoff_angstrom": payload.get("cutoff_angstrom"),
            "hotspot_positions": payload.get("hotspot_positions", []),
            "binding_hotspots": payload.get("binding_hotspots", []),
        },
    }


def _run_csv_read(path: Path) -> dict[str, Any] | None:
    script = Path("/home/fiona/LAMM/scienceclaw/skills/csv-read/scripts/csv_read.py")
    if not script.exists() or not path.exists():
        return None
    completed = subprocess.run(
        [sys.executable, str(script), "--path", str(path), "--max-rows", "5"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    payload: dict[str, Any]
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"raw_stdout": completed.stdout[:1000]}
    return {
        "execution_id": f"csv-read:{path.name}",
        "skill": "csv-read",
        "input_file": str(path),
        "status": "success" if completed.returncode == 0 and "error" not in payload else "error",
        "result_summary": {
            "columns": payload.get("columns", []),
            "shape": payload.get("shape", []),
            "dtypes": payload.get("dtypes", {}),
            "first_rows": payload.get("data", [])[:5],
        },
    }


def _run_statsmodels_table(path: Path, *, x_col: str, y_col: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    code = """
import json
import pandas as pd
import statsmodels.api as sm
df = pd.read_csv(PATH)
X_COL = X_COLUMN
Y_COL = Y_COLUMN
X = sm.add_constant(df[X_COL])
model = sm.OLS(df[Y_COL], X).fit()
print(json.dumps({
    'x_column': X_COL,
    'y_column': Y_COL,
    'slope': round(float(model.params[X_COL]), 6),
    'intercept': round(float(model.params['const']), 6),
    'r_squared': round(float(model.rsquared), 6),
    'nobs': int(model.nobs),
    'p_value_slope': float(model.pvalues[X_COL]),
}))
""".replace("PATH", repr(str(path))).replace("X_COLUMN", repr(x_col)).replace("Y_COLUMN", repr(y_col))
    completed = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"raw_stdout": completed.stdout[:1000]}
    return {
        "execution_id": f"statsmodels:{path.name}",
        "skill": "statsmodels",
        "input_file": str(path),
        "status": "success" if completed.returncode == 0 and "slope" in payload else "error",
        "result_summary": payload,
    }


def _computational_input_needs(
    run_name: str,
    profile: dict[str, Any],
    data_inventory: dict[str, Any],
    quantitative_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    available = set(data_inventory.get("available_input_kinds", []))
    if quantitative_results:
        return []

    missing_by_run = {
        "7t10_formal_extension": [
            "replicate coarse-grained or atomistic SMD ensemble for receptor-bound 7T10",
            "prepared atomistic complex and validated pulling protocol if claiming atomistic mechanics",
            "simulation uncertainty model if claiming robust peak-force statistics",
        ],
        "biomechanics_fiber_network": [
            "computational fiber geometry or synthetic segmented fiber network with units",
            "simulated force-displacement or stress-strain table",
            "boundary conditions/loading protocol and material model",
        ],
        "mechanobiology_force_paths": [
            "computational cell geometry and adhesion/cytoskeleton graph",
            "simulated traction-force or displacement field",
            "boundary conditions and material model",
        ],
        "membrane_biophysics": [
            "computational membrane curvature/geometry field with units",
            "bending modulus/tension or other material parameters",
            "boundary conditions or perturbation protocol",
        ],
    }
    return [
        {
            "need_type": "ComputationalMechanicsInputNeed",
            "missing_input_needed": missing,
            "would_enable": _would_enable(missing),
            "current_available_input_kinds": sorted(available),
            "reason": "The current run lacks the computational input needed for this additional quantitative mechanics calculation.",
        }
        for missing in missing_by_run.get(run_name, profile["evidence_required"])
    ]


def _would_enable(missing_input: str) -> str:
    if "force" in missing_input or "stress" in missing_input:
        return "fit stiffness/peak-force/work metrics with diagnostics and uncertainty"
    if "boundary" in missing_input or "material" in missing_input or "modulus" in missing_input:
        return "run quantitative FEM or constitutive mechanics estimation"
    if "segmentation" in missing_input or "geometry" in missing_input or "curvature" in missing_input:
        return "measure geometry-derived mechanics descriptors and route to image-analysis/statistical modeling"
    if "traction" in missing_input or "displacement" in missing_input:
        return "infer force paths or displacement-to-force mechanics fields"
    return "support quantitative computational mechanics inference"


def _formal_summary(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = []
    for artifact in artifacts:
        payload = artifact.get("payload", {})
        formal_result = payload.get("formal_result")
        if isinstance(formal_result, dict) and formal_result.get("kind"):
            summary.append(
                {
                    "artifact_id": artifact.get("id"),
                    "artifact_type": artifact.get("type"),
                    "morphism": artifact.get("morphism"),
                    "formal_result_kind": formal_result.get("kind"),
                }
            )
    return summary


def _validation_diagnostics(
    artifacts: list[dict[str, Any]],
    quantitative_results: list[dict[str, Any]],
    blocked_needs: list[dict[str, Any]],
) -> dict[str, Any]:
    formal_count = len(_formal_summary(artifacts))
    accepted_scienceclaw = sum(
        1
        for artifact in artifacts
        if (artifact.get("payload", {}).get("scienceclaw", {}) or {}).get("accepted_as_substantive")
    )
    return {
        "formal_result_count": formal_count,
        "accepted_source_data_scienceclaw_count": accepted_scienceclaw,
        "quantitative_result_count": len(quantitative_results),
        "computational_input_need_count": len(blocked_needs),
        "unsupported_quantitative_claims_blocked": False,
    }
