#!/usr/bin/env python3
"""Relax a crystal structure using Meta's UMA model via fairchem.

UMA (Universal Materials Accelerator) is a machine-learned interatomic potential
that provides near-DFT accuracy at a fraction of the computational cost.

Requires:
  - fairchem-core (pip install fairchem-core)
  - HF_TOKEN environment variable or huggingface-cli login (gated model)
"""

import argparse
import json
import os
import sys
import tempfile
from io import StringIO
from pathlib import Path


def check_dependencies():
    """Verify required packages are installed."""
    missing = []
    try:
        import fairchem.core  # noqa: F401
    except ImportError:
        missing.append("fairchem-core")
    try:
        import ase  # noqa: F401
    except ImportError:
        missing.append("ase")
    if missing:
        print(f"Error: missing dependencies: {', '.join(missing)}\n"
              f"Install with: pip install {' '.join(missing)}", file=sys.stderr)
        sys.exit(1)


def resolve_structure(args):
    """Load an ASE Atoms object from file path or Materials Project ID."""
    from ase.io import read as ase_read

    if args.structure:
        path = Path(args.structure)
        if not path.exists():
            print(f"Error: structure file not found: {path}", file=sys.stderr)
            sys.exit(1)
        try:
            atoms = ase_read(str(path))
        except Exception as e:
            print(f"Error reading structure file: {e}", file=sys.stderr)
            sys.exit(1)
        return atoms, str(path)

    if args.mp_id:
        mp_id = args.mp_id
        mp_api_key = os.environ.get("MP_API_KEY")
        if not mp_api_key:
            print("Error: MP_API_KEY environment variable required for --mp-id",
                  file=sys.stderr)
            sys.exit(1)
        try:
            from mp_api.client import MPRester
            from pymatgen.io.ase import AseAtomsAdaptor
            with MPRester(mp_api_key) as mpr:
                structure = mpr.get_structure_by_material_id(mp_id)
            atoms = AseAtomsAdaptor.get_atoms(structure)
        except ImportError:
            print("Error: mp-api and pymatgen required for --mp-id\n"
                  "Install with: pip install mp-api pymatgen", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error fetching structure for {mp_id}: {e}", file=sys.stderr)
            sys.exit(1)
        return atoms, mp_id

    print("Error: provide --structure or --mp-id", file=sys.stderr)
    sys.exit(1)


def atoms_to_cif_string(atoms):
    """Convert ASE Atoms to CIF string."""
    from ase.io import write as ase_write
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".cif", delete=False)
    tmp.close()
    try:
        ase_write(tmp.name, atoms, format="cif")
        return Path(tmp.name).read_text()
    finally:
        os.unlink(tmp.name)


def run_relaxation(atoms, model_name, task_name, device, relax_cell,
                   fmax, max_steps, optimizer_name, output_traj,
                   pressure_gpa=0.0):
    """Run structure relaxation and return results dict."""
    from fairchem.core import pretrained_mlip, FAIRChemCalculator

    predictor = pretrained_mlip.get_predict_unit(model_name, device=device)
    calc = FAIRChemCalculator(predictor, task_name=task_name)
    atoms.calc = calc

    initial_energy = atoms.get_potential_energy()
    formula = atoms.get_chemical_formula()

    if optimizer_name == "FIRE":
        from ase.optimize import FIRE as Optimizer
    else:
        from ase.optimize import LBFGS as Optimizer

    if pressure_gpa != 0.0:
        relax_cell = True  # pressure requires cell relaxation

    if relax_cell:
        from ase.filters import FrechetCellFilter
        pressure_ev_per_A3 = pressure_gpa / 160.21766208
        opt_atoms = FrechetCellFilter(atoms, scalar_pressure=pressure_ev_per_A3)
    else:
        opt_atoms = atoms

    traj_writer = None
    if output_traj:
        from ase.io import Trajectory
        traj_writer = Trajectory(output_traj, "w", atoms)

    opt = Optimizer(opt_atoms, logfile=sys.stderr)
    if traj_writer:
        opt.attach(traj_writer.write, interval=1)

    converged = opt.run(fmax=fmax, steps=max_steps)
    steps_taken = opt.nsteps

    if traj_writer:
        traj_writer.close()

    final_energy = atoms.get_potential_energy()
    forces = atoms.get_forces()
    import numpy as np
    fmax_achieved = float(np.max(np.linalg.norm(forces, axis=1)))

    cell = atoms.get_cell()
    lengths = cell.lengths()
    volume = atoms.get_volume()

    relaxed_cif = atoms_to_cif_string(atoms)

    return {
        "status": "COMPLETED",
        "model": model_name,
        "task": task_name,
        "formula": formula,
        "n_atoms": len(atoms),
        "initial_energy_eV": round(float(initial_energy), 6),
        "final_energy_eV": round(float(final_energy), 6),
        "energy_per_atom_eV": round(float(final_energy) / len(atoms), 6),
        "converged": bool(converged),
        "steps_taken": steps_taken,
        "fmax_achieved": round(fmax_achieved, 6),
        "pressure_GPa": pressure_gpa,
        "cell_relaxed": relax_cell,
        "lattice_a": round(float(lengths[0]), 4),
        "lattice_b": round(float(lengths[1]), 4),
        "lattice_c": round(float(lengths[2]), 4),
        "volume_A3": round(float(volume), 4),
        "relaxed_structure_cif": relaxed_cif,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Relax a crystal structure using Meta's UMA model")
    parser.add_argument("--structure", "-s",
                        help="Path to CIF, POSCAR, or XYZ structure file")
    parser.add_argument("--mp-id",
                        help="Materials Project ID (e.g. mp-149); "
                             "fetches structure automatically")
    parser.add_argument("--model", "-m", default="uma-m-1p1",
                        choices=["uma-s-1p1", "uma-s-1p2", "uma-m-1p1"],
                        help="UMA checkpoint (default: uma-m-1p1)")
    parser.add_argument("--task", "-t", default="omat",
                        choices=["omat", "omol", "omc", "oc20", "odac"],
                        help="Task / DFT level of theory (default: omat)")
    parser.add_argument("--device", default="cuda",
                        choices=["cuda", "cpu"],
                        help="Compute device (default: cuda)")
    parser.add_argument("--relax-cell", action="store_true",
                        help="Enable full cell relaxation "
                             "(shape + volume + positions)")
    parser.add_argument("--pressure", type=float, default=0.0,
                        help="External pressure in GPa (default: 0). "
                             "Implies --relax-cell.")
    parser.add_argument("--fmax", type=float, default=0.05,
                        help="Force convergence threshold in eV/A "
                             "(default: 0.05)")
    parser.add_argument("--steps", type=int, default=200,
                        help="Max optimizer steps (default: 200)")
    parser.add_argument("--optimizer", default="FIRE",
                        choices=["FIRE", "LBFGS"],
                        help="ASE optimizer (default: FIRE)")
    parser.add_argument("--output-traj",
                        help="Path to save ASE trajectory file")
    parser.add_argument("--output-cif",
                        help="Path to save relaxed structure as CIF")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate inputs without running relaxation")
    parser.add_argument("--format", default="summary",
                        choices=["summary", "json"])
    args = parser.parse_args()

    # Auto-detect GPU availability
    if args.device == "cuda":
        try:
            import torch
            if not torch.cuda.is_available():
                print("No GPU detected, falling back to CPU", file=sys.stderr)
                args.device = "cpu"
        except ImportError:
            args.device = "cpu"

    check_dependencies()

    atoms, source = resolve_structure(args)
    formula = atoms.get_chemical_formula()

    if args.dry_run:
        info = {
            "dry_run": True,
            "source": source,
            "formula": formula,
            "n_atoms": len(atoms),
            "model": args.model,
            "task": args.task,
            "device": args.device,
            "relax_cell": args.relax_cell,
            "fmax": args.fmax,
            "steps": args.steps,
            "optimizer": args.optimizer,
        }
        if args.format == "json":
            print(json.dumps(info, indent=2))
        else:
            print("=== DRY RUN ===")
            for k, v in info.items():
                print(f"  {k}: {v}")
        return

    result = run_relaxation(
        atoms=atoms,
        model_name=args.model,
        task_name=args.task,
        device=args.device,
        relax_cell=args.relax_cell,
        fmax=args.fmax,
        max_steps=args.steps,
        optimizer_name=args.optimizer,
        output_traj=args.output_traj,
        pressure_gpa=args.pressure,
    )

    if args.output_cif:
        cif_path = Path(args.output_cif)
        cif_path.write_text(result["relaxed_structure_cif"])
        result["output_cif_path"] = str(cif_path)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"  status:          {result['status']}")
        print(f"  formula:         {result['formula']}")
        print(f"  model:           {result['model']}")
        print(f"  task:            {result['task']}")
        print(f"  initial energy:  {result['initial_energy_eV']:.4f} eV")
        print(f"  final energy:    {result['final_energy_eV']:.4f} eV")
        print(f"  energy/atom:     {result['energy_per_atom_eV']:.4f} eV")
        print(f"  converged:       {result['converged']}")
        print(f"  steps:           {result['steps_taken']}")
        print(f"  fmax achieved:   {result['fmax_achieved']:.4f} eV/A")
        print(f"  cell relaxed:    {result['cell_relaxed']}")
        print(f"  lattice:         {result['lattice_a']:.3f} x "
              f"{result['lattice_b']:.3f} x {result['lattice_c']:.3f} A")
        print(f"  volume:          {result['volume_A3']:.2f} A^3")
        if args.output_cif:
            print(f"  saved CIF:       {args.output_cif}")


if __name__ == "__main__":
    main()
