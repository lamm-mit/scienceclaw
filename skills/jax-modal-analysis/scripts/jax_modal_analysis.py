#!/usr/bin/env python3
"""
jax-modal-analysis skill: 3D tetrahedral FEM modal analysis via jax_modal_analysis repo.

Wraps `stl_modal_pipeline.run_modal_agent` (running inside the `jax_fem` conda env)
and emits a single artifact JSON to stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


CONDA_ENV = "jax_fem"


def _conda_python() -> list[str]:
    """Return prefix for running Python inside the jax_fem conda env."""
    return ["conda", "run", "-n", CONDA_ENV, "--no-capture-output", "python"]


def run_modal_agent(
    stl: Path,
    material: dict,
    num_modes: int,
    solver_backend: str,
    stl_length_scale: float,
    output_dir: Path,
) -> dict:
    """Call run_modal_agent inside the jax_fem conda env and return parsed JSON."""
    stl = Path(stl).resolve()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        *_conda_python(),
        "-m", "stl_modal_pipeline.run_modal_agent",
        "--stl-name", stl.name,
        "--stl-dir", str(stl.parent),
        "--density-kg-m3", str(material["rho_kg_m3"]),
        "--elastic-modulus-pa", str(material["E_Pa"]),
        "--poissons-ratio", str(material["nu"]),
        "--runs-dir", str(output_dir),
    ]

    env = os.environ.copy()
    env.update({
        "XLA_PYTHON_CLIENT_PREALLOCATE": "false",
        "XLA_PYTHON_CLIENT_ALLOCATOR": "platform",
        "JAX_ENABLE_X64": "1",
    })

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(
            f"run_modal_agent failed (rc={result.returncode}):\n"
            f"STDERR:\n{result.stderr[-3000:]}\n"
            f"STDOUT:\n{result.stdout[-1000:]}"
        )

    # run_modal_agent prints JSON to stdout; find the JSON block
    stdout = result.stdout.strip()
    # The output may have non-JSON preamble lines (pyfiglet banner etc.)
    # Find the first '{' that starts the JSON object
    json_start = stdout.find("{")
    if json_start == -1:
        raise RuntimeError(f"No JSON found in run_modal_agent output:\n{stdout[-2000:]}")
    return json.loads(stdout[json_start:])


def _read_csv_frequencies(csv_path: str) -> list:
    """Read eigenfrequencies from modal_comprehensive_report.csv if available."""
    import csv as _csv
    p = Path(csv_path)
    if not p.exists():
        return []
    freqs = []
    with open(p, newline="") as f:
        reader = _csv.DictReader(f)
        for row in reader:
            for key in ("natural_frequency_hz", "frequency_hz", "eigenfreq_hz", "freq_hz"):
                if key in row:
                    try:
                        freqs.append(float(row[key]))
                    except ValueError:
                        pass
                    break
    return freqs


def build_artifact(
    agent_output: dict,
    stl: Path,
    material: dict,
    num_modes: int,
    solver_backend: str,
    target_min_hz: float,
    target_max_hz: float,
) -> dict:
    """Convert run_modal_agent JSON into skill artifact JSON."""
    topology = stl.stem  # e.g. "v1_cricket_fine"

    # Extract eigenfrequencies from mode_preview.first_modes
    run_sum = agent_output.get("run_summary", {})
    mode_preview = agent_output.get("mode_preview", {})
    modes_list = mode_preview.get("first_modes", [])

    freqs_hz = [m["natural_frequency_hz"] for m in modes_list]

    # If CSV is available read fuller frequency list from it
    csv_path_candidate = (
        agent_output.get("csv_path")
        or run_sum.get("csv_path", "")
    )
    if csv_path_candidate:
        csv_freqs = _read_csv_frequencies(csv_path_candidate)
        if len(csv_freqs) > len(freqs_hz):
            freqs_hz = csv_freqs

    freqs_khz = [f / 1000.0 for f in freqs_hz]

    modes_in_range_hz = [f for f in freqs_hz if target_min_hz <= f <= target_max_hz]
    modes_in_range_khz = [f / 1000.0 for f in modes_in_range_hz]

    # Determine actual solver used
    actual_backend = (
        run_sum.get("solver_backend")
        or run_sum.get("backend")
        or solver_backend
    )

    # Resolve output paths from agent response
    run_out = agent_output.get("output_dir", "")
    summary_png = (
        agent_output.get("summary_figure_path")
        or run_sum.get("summary_figure_path")
        or agent_output.get("png_path", "")
    ) or ""
    csv_path = (
        agent_output.get("csv_path")
        or run_sum.get("csv_path", "")
    ) or ""
    if not summary_png and run_out:
        candidate = Path(run_out) / "summary_figures" / "modal_run_summary.png"
        if candidate.exists():
            summary_png = str(candidate)
    if not csv_path and run_out:
        candidate = Path(run_out) / "modal_comprehensive_report.csv"
        if candidate.exists():
            csv_path = str(candidate)
    mesh_vtu = ""
    if run_out:
        candidate = Path(run_out) / "mesh" / "volume_mesh.vtu"
        if candidate.exists():
            mesh_vtu = str(candidate)

    return {
        "stl_path": str(stl),
        "topology": topology,
        "num_modes_computed": len(freqs_hz),
        "eigenfrequencies_hz": freqs_hz,
        "eigenfrequencies_khz": freqs_khz,
        "modes_in_range_hz": modes_in_range_hz,
        "modes_in_range_khz": modes_in_range_khz,
        "target_range_hz": [target_min_hz, target_max_hz],
        "target_range_khz": [target_min_hz / 1000.0, target_max_hz / 1000.0],
        "target_range_pass": len(modes_in_range_hz) > 0,
        "solver_backend": actual_backend,
        "output_dir": run_out,
        "summary_png": summary_png,
        "csv_path": csv_path,
        "mesh_vtu": mesh_vtu,
        "material": material,
        "run_success": agent_output.get("success", True),
    }


def main():
    parser = argparse.ArgumentParser(
        description="3D tetrahedral FEM modal analysis via jax_modal_analysis."
    )
    parser.add_argument("--stl", required=True, help="Path to binary STL (mm units)")
    parser.add_argument(
        "--material",
        required=True,
        help='JSON material properties, e.g. \'{"E_Pa":3e9,"nu":0.35,"rho_kg_m3":1500}\'',
    )
    parser.add_argument("--num-modes", type=int, default=12, help="Number of modes")
    parser.add_argument(
        "--solver-backend",
        default="jax-iterative",
        choices=["arpack", "jax-iterative", "jax-xla"],
        help="Eigensolver backend",
    )
    parser.add_argument(
        "--stl-length-scale",
        type=float,
        default=1e-3,
        help="Scale factor: STL units → metres (default 1e-3 for mm→m)",
    )
    parser.add_argument("--output-dir", default=None, help="Directory for output files")
    parser.add_argument(
        "--target-freq-min", type=float, default=2000.0, help="Target band lower bound (Hz)"
    )
    parser.add_argument(
        "--target-freq-max", type=float, default=8000.0, help="Target band upper bound (Hz)"
    )
    args = parser.parse_args()

    stl = Path(args.stl)
    if not stl.exists():
        print(json.dumps({"error": f"STL not found: {stl}"}))
        sys.exit(1)

    try:
        material = json.loads(args.material)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid --material JSON: {e}"}))
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else Path("/tmp/jax_modal") / stl.stem

    try:
        agent_output = run_modal_agent(
            stl=stl,
            material=material,
            num_modes=args.num_modes,
            solver_backend=args.solver_backend,
            stl_length_scale=args.stl_length_scale,
            output_dir=output_dir,
        )
    except Exception as e:
        print(json.dumps({"error": str(e), "stl_path": str(stl)}))
        sys.exit(1)

    artifact = build_artifact(
        agent_output=agent_output,
        stl=stl,
        material=material,
        num_modes=args.num_modes,
        solver_backend=args.solver_backend,
        target_min_hz=args.target_freq_min,
        target_max_hz=args.target_freq_max,
    )

    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    main()
