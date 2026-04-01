#!/usr/bin/env python3
"""
uma_screen.py — Relax a set of crystal structures with UMA at multiple pressures.

Reads CIF files from --structures-dir (default: ~/.scienceclaw/enumerated_structures),
relaxes each at each pressure using UMA, computes formation energies, and checks
0 GPa stability against the Materials Project convex hull.

No hardcoded prototypes — structures come from the structure-enumeration skill
or any other source that produces CIF files.

ScienceClaw skill contract: argparse, --format json, JSON on stdout.
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

GPA_TO_EV_PER_A3 = 1.0 / 160.21766208
DEFAULT_STRUCTURES_DIR = Path.home() / ".scienceclaw" / "enumerated_structures"


def log(msg: str) -> None:
    print(f"[uma_screen] {msg}", file=sys.stderr, flush=True)


def find_cif_files(structures_dir: Path) -> list[Path]:
    """Find all CIF files in the given directory."""
    if not structures_dir.exists():
        return []
    return sorted(structures_dir.glob("*.cif"))


def read_structure(cif_path: Path):
    """Read a CIF file into ASE Atoms."""
    from ase.io import read as ase_read
    return ase_read(str(cif_path))


def identify_metal(atoms) -> str | None:
    """Identify the metal element (heaviest non-H element) in a structure."""
    from ase.data import atomic_numbers
    symbols = set(atoms.get_chemical_symbols())
    non_h = [s for s in symbols if s != "H"]
    if not non_h:
        return None
    return max(non_h, key=lambda s: atomic_numbers.get(s, 0))


def build_element_reference(symbol: str):
    """Build elemental bulk reference. Uses ASE's built-in structures."""
    from ase.build import bulk
    # Known ground-state structures with experimental lattice constants
    refs = {
        "La": ("fcc", {"a": 5.31}),
        "Y":  ("hcp", {"a": 3.65, "c": 5.73}),
        "Ca": ("fcc", {"a": 5.58}),
        "Ce": ("fcc", {"a": 5.16}),
        "Sc": ("hcp", {"a": 3.31, "c": 5.27}),
        "Th": ("fcc", {"a": 5.08}),
        "Lu": ("hcp", {"a": 3.50, "c": 5.55}),
        "Ba": ("bcc", {"a": 5.02}),
        "Sr": ("fcc", {"a": 6.08}),
        "Mg": ("hcp", {"a": 3.21, "c": 5.21}),
        "Li": ("bcc", {"a": 3.49}),
        "Na": ("bcc", {"a": 4.23}),
        "K":  ("bcc", {"a": 5.23}),
    }
    if symbol in refs:
        crystal, params = refs[symbol]
        return bulk(symbol, crystal, **params)
    # Fallback: let ASE guess
    return bulk(symbol)


def build_h2_reference():
    """Build an H2 molecule in a 10 A box."""
    from ase import Atoms
    h2 = Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.74]], pbc=True)
    h2.set_cell([10.0, 10.0, 10.0])
    h2.center()
    return h2


def relax_atoms(atoms, predictor, pressure_gpa, fmax, steps):
    """Relax ASE Atoms with UMA at given pressure."""
    from ase.optimize import FIRE
    from ase.filters import FrechetCellFilter
    from fairchem.core import FAIRChemCalculator
    import numpy as np

    calc = FAIRChemCalculator(predictor, task_name="omat")
    atoms.calc = calc
    filtered = FrechetCellFilter(atoms, scalar_pressure=pressure_gpa * GPA_TO_EV_PER_A3)
    opt = FIRE(filtered, logfile=None)

    t0 = time.time()
    converged = opt.run(fmax=fmax, steps=steps)
    elapsed = time.time() - t0

    energy = atoms.get_potential_energy()
    forces = atoms.get_forces()
    fmax_val = float(np.max(np.linalg.norm(forces, axis=1)))

    return {
        "energy_eV": float(energy),
        "energy_per_atom_eV": float(energy / len(atoms)),
        "converged": bool(converged),
        "steps_taken": opt.nsteps,
        "fmax_achieved": round(fmax_val, 6),
        "volume_A3": float(atoms.get_volume()),
        "n_atoms": len(atoms),
        "elapsed_s": round(elapsed, 2),
    }


def get_e_above_hull(metal, formula, total_energy_eV):
    """Query MP convex hull at 0 GPa."""
    try:
        from mp_api.client import MPRester
        from pymatgen.analysis.phase_diagram import PhaseDiagram, PDEntry
        from pymatgen.core import Composition

        api_key = os.environ.get("MP_API_KEY")
        if not api_key:
            return None

        chemsys = "-".join(sorted([metal, "H"]))
        log(f"  Fetching MP hull for {chemsys}...")
        with MPRester(api_key) as mpr:
            entries = mpr.get_entries_in_chemsys(chemsys)

        my_entry = PDEntry(Composition(formula), total_energy_eV, name=f"UMA-{formula}")
        pd = PhaseDiagram(list(entries) + [my_entry])
        return float(pd.get_e_above_hull(my_entry))
    except Exception as e:
        log(f"  Hull failed for {formula}: {e}")
        return None


def run_pipeline(args):
    """Run the screening pipeline on CIF files from structures_dir."""
    from fairchem.core import pretrained_mlip
    from ase.io import write as ase_write

    structures_dir = Path(args.structures_dir)
    cif_files = find_cif_files(structures_dir)

    if not cif_files:
        return {"status": "ERROR", "error": f"No CIF files found in {structures_dir}"}

    pressures = [float(p) for p in args.pressures.split(",")]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    log(f"Found {len(cif_files)} structures in {structures_dir}")
    log(f"Pressures: {pressures} GPa")

    # Load UMA
    log(f"Loading UMA model '{args.model}' on {args.device}...")
    predictor = pretrained_mlip.get_predict_unit(args.model, device=args.device)
    log("Model loaded.")

    # Identify unique metals and compute elemental references
    log("Scanning structures for metals...")
    metals_found = set()
    structure_info = []
    for cif in cif_files:
        atoms = read_structure(cif)
        metal = identify_metal(atoms)
        formula = atoms.get_chemical_formula(mode="metal")
        n_h = sum(1 for s in atoms.get_chemical_symbols() if s == "H")
        n_metal = len(atoms) - n_h
        metals_found.add(metal)
        structure_info.append({
            "cif_path": cif,
            "atoms": atoms,
            "metal": metal,
            "formula": formula,
            "n_metal": n_metal,
            "n_h": n_h,
            "label": cif.stem,
        })

    log(f"Metals found: {metals_found}")

    # Elemental references (at 0 GPa)
    log("Computing elemental references...")
    metal_ref = {}
    for metal in metals_found:
        if metal is None:
            continue
        log(f"  Relaxing {metal} bulk...")
        ref_atoms = build_element_reference(metal)
        r = relax_atoms(ref_atoms, predictor, 0.0, args.fmax, args.steps)
        metal_ref[metal] = r["energy_per_atom_eV"]
        log(f"    {metal}: {r['energy_per_atom_eV']:.4f} eV/atom")

    log("  Relaxing H2...")
    h2 = build_h2_reference()
    h2_result = relax_atoms(h2, predictor, 0.0, args.fmax, args.steps)
    e_h2_total = h2_result["energy_eV"]
    log(f"    H2: {e_h2_total:.4f} eV")

    # Relax each structure at each pressure
    results = []
    total = len(structure_info) * len(pressures)
    count = 0

    for info in structure_info:
        pressure_data = {}
        for pressure in pressures:
            count += 1
            label = f"{info['label']}_{pressure:.0f}GPa"
            log(f"  [{count}/{total}] {label}...")

            atoms = info["atoms"].copy()
            try:
                r = relax_atoms(atoms, predictor, pressure, args.fmax, args.steps)
            except Exception as e:
                log(f"    ERROR: {e}")
                pressure_data[pressure] = {"status": "FAILED", "error": str(e)}
                continue

            # Save relaxed CIF
            cif_out = output_dir / f"{label}.cif"
            try:
                ase_write(str(cif_out), atoms, format="cif")
                r["cif_path"] = str(cif_out)
            except Exception:
                pass

            # Formation energy
            metal = info["metal"]
            if metal and metal in metal_ref:
                n_total = info["n_metal"] + info["n_h"]
                e_total = r["energy_per_atom_eV"] * n_total
                e_f = (e_total - info["n_metal"] * metal_ref[metal]
                       - (info["n_h"] / 2.0) * e_h2_total) / n_total
                r["formation_energy_eV_per_atom"] = round(e_f, 6)
            else:
                r["formation_energy_eV_per_atom"] = None

            # Hull at 0 GPa
            if pressure == 0.0 and metal:
                r["e_above_hull_eV"] = get_e_above_hull(
                    metal, info["formula"], r["energy_eV"])

            r["pressure_GPa"] = pressure
            r["status"] = "COMPLETED"
            pressure_data[pressure] = r

            ef_str = f"{r.get('formation_energy_eV_per_atom', 'N/A')}"
            log(f"    E/atom={r['energy_per_atom_eV']:.4f} Ef={ef_str} "
                f"{'converged' if r['converged'] else 'NOT converged'}")

        results.append({
            "label": info["label"],
            "formula": info["formula"],
            "metal": info["metal"],
            "n_atoms": info["n_metal"] + info["n_h"],
            "pressures": {f"{p:.0f}": pressure_data.get(p, {}) for p in pressures},
        })

    # Rank by formation energy at highest pressure
    max_p = f"{max(pressures):.0f}"

    def sort_key(r):
        pd = r.get("pressures", {}).get(max_p, {})
        ef = pd.get("formation_energy_eV_per_atom")
        return ef if ef is not None else 999.0

    results.sort(key=sort_key)

    ranking = []
    for rank, r in enumerate(results, 1):
        pd = r.get("pressures", {}).get(max_p, {})
        entry = {"rank": rank, "formula": r["formula"], "label": r["label"]}
        ef = pd.get("formation_energy_eV_per_atom")
        if ef is not None:
            entry["formation_energy_eV_per_atom"] = ef
            entry["converged"] = pd.get("converged", False)
        hull = r.get("pressures", {}).get("0", {}).get("e_above_hull_eV")
        if hull is not None:
            entry["e_above_hull_eV_0GPa"] = round(hull, 6)
        ranking.append(entry)

    return {
        "status": "COMPLETED",
        "model": args.model,
        "structures_dir": str(structures_dir),
        "n_structures": len(structure_info),
        "pressures_GPa": pressures,
        "output_dir": str(output_dir),
        "ranking": ranking,
        "candidates": results,
        "reference_energies": {
            "metals_eV_per_atom": metal_ref,
            "H2_eV": e_h2_total,
        },
    }


def _submit_to_slurm(args):
    """No GPU locally — submit this script to SLURM."""
    import subprocess
    from datetime import datetime, timezone

    script_path = Path(__file__).resolve()
    venv = os.environ.get("VIRTUAL_ENV", "")
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    slurm_script = f"""#!/bin/bash
#SBATCH --job-name=uma-screen
#SBATCH --partition=venkvis-h100
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --output={out_dir}/slurm-%j.out
#SBATCH --error={out_dir}/slurm-%j.err

source {venv}/bin/activate
export MP_API_KEY="{os.environ.get('MP_API_KEY', '')}"
export HF_TOKEN="{os.environ.get('HF_TOKEN', '')}"

{sys.executable} {script_path} \\
  --structures-dir {args.structures_dir} \\
  --pressures {args.pressures} \\
  --model {args.model} \\
  --device cuda \\
  --fmax {args.fmax} \\
  --steps {args.steps} \\
  --output-dir {out_dir} \\
  --format json
"""
    submit_path = out_dir / "submit.sh"
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
        "structures_dir": str(args.structures_dir),
        "after_job": args.after_job,
        "note": f"Check: squeue -j {job_id}. Results: cat {out_dir}/slurm-{job_id}.out",
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Relax structures with UMA at multiple pressures")
    parser.add_argument("--structures-dir", default=str(DEFAULT_STRUCTURES_DIR),
                        help=f"Directory of CIF files to relax "
                             f"(default: {DEFAULT_STRUCTURES_DIR})")
    parser.add_argument("--pressures", default="0,150",
                        help="Comma-separated pressures in GPa (default: 0,150)")
    parser.add_argument("--model", default="uma-m-1p1",
                        choices=["uma-s-1p1", "uma-s-1p2", "uma-m-1p1"])
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--fmax", type=float, default=0.05)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--output-dir", default="./uma_screen_output")
    parser.add_argument("--after-job", default=None,
                        help="SLURM job ID to wait for before starting "
                             "(adds --dependency=afterok:<id>)")
    parser.add_argument("--format", default="json", choices=["json", "summary"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Auto-detect GPU; submit to SLURM if unavailable
    if args.device == "cuda" and not args.dry_run:
        try:
            import torch
            if not torch.cuda.is_available():
                _submit_to_slurm(args)
                return
        except ImportError:
            _submit_to_slurm(args)
            return

    structures_dir = Path(args.structures_dir)

    if args.dry_run:
        cifs = find_cif_files(structures_dir)
        pressures = [float(p) for p in args.pressures.split(",")]
        plan = {
            "status": "DRY_RUN",
            "structures_dir": str(structures_dir),
            "n_structures": len(cifs),
            "structures": [f.stem for f in cifs],
            "pressures_GPa": pressures,
            "total_relaxations": len(cifs) * len(pressures),
            "model": args.model,
        }
        print(json.dumps(plan, indent=2))
        return

    try:
        output = run_pipeline(args)
    except Exception as e:
        print(json.dumps({"status": "FAILED", "error": str(e),
                          "traceback": traceback.format_exc()}, indent=2))
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(output, indent=2))
    else:
        print(f"\n=== UMA Screening Results ===")
        print(f"Structures: {output['n_structures']} from {output['structures_dir']}")
        print(f"Pressures: {output['pressures_GPa']} GPa")
        print()
        for entry in output["ranking"]:
            ef = entry.get("formation_energy_eV_per_atom", "N/A")
            hull = entry.get("e_above_hull_eV_0GPa", "N/A")
            ef_s = f"{ef:+.4f}" if isinstance(ef, float) else ef
            hull_s = f"{hull:.4f}" if isinstance(hull, float) else hull
            print(f"  #{entry['rank']:2d}  {entry['label']:<30s}  "
                  f"Ef={ef_s:>8s}  Ehull={hull_s:>8s}")


if __name__ == "__main__":
    main()
