#!/usr/bin/env python3
"""Compute phonon properties and assess dynamic stability using phonopy + UMA.

Uses the finite-displacement method: create displaced supercells, compute forces
with an ML potential (UMA), build force constants, and check for imaginary modes.

Reference: adapted from https://github.com/hyllios/utils/tree/main/benchmark_ph
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np


def find_structures(args):
    """Collect CIF file paths from --structure or --structures-dir."""
    paths = []
    if args.structure:
        p = Path(args.structure)
        if p.exists():
            paths.append(p)
        else:
            print(f"Error: file not found: {p}", file=sys.stderr)
            sys.exit(1)
    if args.structures_dir:
        d = Path(args.structures_dir)
        if d.exists():
            paths.extend(sorted(d.glob("*.cif")))
    if not paths:
        print("Error: no structures found. Provide --structure or --structures-dir",
              file=sys.stderr)
        sys.exit(1)
    return paths


def auto_supercell(n_atoms):
    """Choose supercell dimensions based on unit cell size."""
    if n_atoms <= 4:
        return [3, 3, 3]
    elif n_atoms <= 16:
        return [2, 2, 2]
    elif n_atoms <= 48:
        return [2, 2, 1]
    else:
        return [1, 1, 1]


def compute_phonons(atoms, predictor, task, supercell_dims, displacement):
    """Compute phonon properties for an ASE Atoms object.

    Returns dict with frequencies, stability flag, thermal properties.
    """
    import phonopy
    from phonopy.structure.atoms import PhonopyAtoms
    from fairchem.core import FAIRChemCalculator

    # Convert ASE Atoms to PhonopyAtoms
    ph_atoms = PhonopyAtoms(
        symbols=atoms.get_chemical_symbols(),
        cell=atoms.get_cell(),
        scaled_positions=atoms.get_scaled_positions(),
    )

    # Create phonopy object
    ph = phonopy.Phonopy(
        ph_atoms,
        supercell_matrix=np.diag(supercell_dims),
        primitive_matrix="auto",
    )

    # Generate displaced supercells
    ph.generate_displacements(distance=displacement, is_diagonal=False)
    supercells = ph.supercells_with_displacements

    print(f"    {len(supercells)} displaced supercells "
          f"({supercell_dims[0]}x{supercell_dims[1]}x{supercell_dims[2]}, "
          f"{len(supercells[0])} atoms each)", file=sys.stderr)

    # Compute forces using UMA
    calc = FAIRChemCalculator(predictor, task_name=task)
    force_sets = []
    for j, scell in enumerate(supercells):
        # Convert PhonopyAtoms supercell to ASE Atoms
        from ase import Atoms as ASEAtoms
        ase_scell = ASEAtoms(
            symbols=scell.symbols,
            positions=scell.positions,
            cell=scell.cell,
            pbc=True,
        )
        ase_scell.calc = calc
        forces = ase_scell.get_forces()

        # Acoustic sum rule correction: subtract drift force
        drift = forces.mean(axis=0)
        forces -= drift

        force_sets.append(forces)

    # Set forces and compute force constants
    ph.forces = force_sets
    ph.produce_force_constants()
    ph.symmetrize_force_constants()

    # Get phonon frequencies at commensurate q-points
    ph.run_mesh([8, 8, 8])
    mesh_dict = ph.get_mesh_dict()
    frequencies = mesh_dict["frequencies"]  # shape: (n_qpoints, n_bands)
    qpoints = mesh_dict["qpoints"]

    # Find gamma point (q = [0,0,0])
    gamma_idx = None
    for idx, q in enumerate(qpoints):
        if np.allclose(q, [0, 0, 0], atol=1e-6):
            gamma_idx = idx
            break

    all_freqs = frequencies.flatten()
    min_freq = float(np.min(all_freqs))
    max_freq = float(np.max(all_freqs))
    n_imaginary = int(np.sum(all_freqs < -0.5))  # THz threshold

    # Stability check
    # At Gamma: acoustic modes (first 3) may have small negatives — ignore if > -0.5 THz
    # All other modes must be positive
    stable = True
    if gamma_idx is not None:
        gamma_freqs = frequencies[gamma_idx]
        n_bands = len(gamma_freqs)
        # Acoustic modes (first 3): allow down to threshold
        # Optical modes: must be >= 0
        if n_bands > 3:
            if np.any(gamma_freqs[3:] < 0):
                stable = False
        if np.any(gamma_freqs[:3] < -0.5):
            stable = False
    # Non-gamma points: all must be >= 0
    non_gamma_mask = np.ones(len(qpoints), dtype=bool)
    if gamma_idx is not None:
        non_gamma_mask[gamma_idx] = False
    non_gamma_freqs = frequencies[non_gamma_mask]
    if np.any(non_gamma_freqs < 0):
        stable = False

    # Thermal properties
    thermal = {}
    try:
        ph.run_thermal_properties(t_min=0, t_max=600, t_step=75)
        tp = ph.get_thermal_properties_dict()
        for temp, fe, entropy, cv in zip(
            tp["temperatures"], tp["free_energy"], tp["entropy"], tp["heat_capacity"]
        ):
            if temp in (0, 75, 150, 300, 600):
                thermal[f"{int(temp)}K"] = {
                    "free_energy_kJ_per_mol": round(float(fe), 3),
                    "entropy_J_per_mol_K": round(float(entropy), 3),
                    "heat_capacity_J_per_mol_K": round(float(cv), 3),
                }
    except Exception as e:
        print(f"    Warning: thermal properties failed: {e}", file=sys.stderr)

    return {
        "dynamically_stable": stable,
        "min_frequency_THz": round(min_freq, 4),
        "max_frequency_THz": round(max_freq, 4),
        "n_imaginary_modes": n_imaginary,
        "n_modes": int(frequencies.shape[1]),
        "n_qpoints": int(frequencies.shape[0]),
        "thermal_properties": thermal,
    }


def _submit_to_slurm(args):
    """No GPU locally — submit this script to SLURM."""
    import subprocess
    from datetime import datetime, timezone

    script_path = Path(__file__).resolve()
    venv = os.environ.get("VIRTUAL_ENV", "")
    out_dir = Path(args.output_dir or "./phonon_output").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd_parts = [sys.executable, str(script_path)]
    if args.structure:
        cmd_parts.extend(["--structure", args.structure])
    if args.structures_dir:
        cmd_parts.extend(["--structures-dir", args.structures_dir])
    cmd_parts.extend([
        "--model", args.model,
        "--task", args.task,
        "--device", "cuda",
        "--displacement", str(args.displacement),
        "--format", "json",
    ])
    if args.supercell:
        cmd_parts.extend(["--supercell", args.supercell])
    if args.output_dir:
        cmd_parts.extend(["--output-dir", args.output_dir])

    slurm_script = f"""#!/bin/bash
#SBATCH --job-name=phonon-screen
#SBATCH --partition=venkvis-h100
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1
#SBATCH --output={out_dir}/slurm-%j.out
#SBATCH --error={out_dir}/slurm-%j.err

source {venv}/bin/activate
export MP_API_KEY="{os.environ.get('MP_API_KEY', '')}"
export HF_TOKEN="{os.environ.get('HF_TOKEN', '')}"

{' '.join(cmd_parts)}
"""
    submit_path = out_dir / "submit_phonon.sh"
    submit_path.write_text(slurm_script)
    submit_path.chmod(0o755)

    sbatch_cmd = ["sbatch"]
    if args.after_job:
        sbatch_cmd.extend(["--dependency", f"afterok:{args.after_job}"])
    sbatch_cmd.append(str(submit_path))

    result = subprocess.run(sbatch_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": result.stderr.strip()}))
        sys.exit(1)

    job_id = None
    for word in result.stdout.strip().split():
        if word.isdigit():
            job_id = word

    print(json.dumps({
        "status": "SUBMITTED_TO_SLURM",
        "job_id": job_id,
        "output_dir": str(out_dir),
        "after_job": args.after_job,
        "note": f"Check: squeue -j {job_id}. Results: cat {out_dir}/slurm-{job_id}.out",
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Compute phonon properties and assess dynamic stability")
    parser.add_argument("--structure", help="Single CIF/POSCAR file")
    parser.add_argument("--structures-dir",
                        help="Directory of CIF files to analyze")
    parser.add_argument("--supercell", default=None,
                        help="Supercell dims e.g. 2,2,2 (default: auto)")
    parser.add_argument("--displacement", type=float, default=0.01,
                        help="Displacement distance in Angstrom (default: 0.01)")
    parser.add_argument("--model", default="uma-m-1p1",
                        choices=["uma-s-1p1", "uma-s-1p2", "uma-m-1p1"])
    parser.add_argument("--task", default="omat")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--imaginary-threshold", type=float, default=-0.5,
                        help="Threshold in THz for imaginary mode (default: -0.5)")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--after-job", default=None,
                        help="SLURM job ID to wait for before starting "
                             "(adds --dependency=afterok:<id>)")
    parser.add_argument("--format", default="json", choices=["summary", "json"])
    args = parser.parse_args()

    # Auto-detect GPU; submit to SLURM if unavailable
    if args.device == "cuda":
        try:
            import torch
            if not torch.cuda.is_available():
                _submit_to_slurm(args)
                return
        except ImportError:
            _submit_to_slurm(args)
            return

    cif_paths = find_structures(args)
    print(f"[phonon] {len(cif_paths)} structures to analyze", file=sys.stderr)

    # Load UMA model once
    from fairchem.core import pretrained_mlip
    from ase.io import read as ase_read

    print(f"[phonon] Loading UMA model '{args.model}'...", file=sys.stderr)
    predictor = pretrained_mlip.get_predict_unit(args.model, device=args.device)

    supercell_dims = None
    if args.supercell:
        supercell_dims = [int(x) for x in args.supercell.split(",")]

    results = []
    for idx, cif_path in enumerate(cif_paths, 1):
        label = cif_path.stem
        print(f"[phonon] [{idx}/{len(cif_paths)}] {label}...", file=sys.stderr)

        try:
            atoms = ase_read(str(cif_path))
            dims = supercell_dims or auto_supercell(len(atoms))

            t0 = time.time()
            phonon_result = compute_phonons(
                atoms, predictor, args.task, dims, args.displacement
            )
            elapsed = time.time() - t0

            entry = {
                "label": label,
                "formula": atoms.get_chemical_formula(mode="metal"),
                "n_atoms": len(atoms),
                "supercell": dims,
                "elapsed_s": round(elapsed, 1),
                **phonon_result,
            }
            results.append(entry)

            status = "STABLE" if entry["dynamically_stable"] else "UNSTABLE"
            print(f"    {status}: min_freq={entry['min_frequency_THz']:.2f} THz, "
                  f"n_imaginary={entry['n_imaginary_modes']}, "
                  f"{elapsed:.1f}s", file=sys.stderr)

        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)
            results.append({
                "label": label,
                "status": "FAILED",
                "error": str(e),
            })

    # Save results
    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "phonon_results.json").write_text(json.dumps(results, indent=2))

    stable_count = sum(1 for r in results if r.get("dynamically_stable"))
    output = {
        "status": "COMPLETED",
        "total": len(results),
        "dynamically_stable": stable_count,
        "dynamically_unstable": len(results) - stable_count,
        "results": results,
    }

    if args.format == "json":
        print(json.dumps(output, indent=2))
    else:
        print(f"\n=== Phonon Stability Analysis ===")
        print(f"Structures: {len(results)}")
        print(f"Stable: {stable_count} / {len(results)}")
        print()
        for r in results:
            if "dynamically_stable" in r:
                s = "STABLE" if r["dynamically_stable"] else "UNSTABLE"
                print(f"  {r['label']:<30s} {s:<10s} "
                      f"min_freq={r['min_frequency_THz']:>7.2f} THz  "
                      f"n_imag={r['n_imaginary_modes']}")
            else:
                print(f"  {r['label']:<30s} FAILED: {r.get('error', '?')}")


if __name__ == "__main__":
    main()
