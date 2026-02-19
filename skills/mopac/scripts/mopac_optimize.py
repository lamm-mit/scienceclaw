#!/usr/bin/env python3
"""
MOPAC Structure Optimization

Optimize molecular structures using semi-empirical quantum chemistry.
Fast QM calculations for drug discovery and reaction mechanism studies.

Usage:
    python mopac_optimize.py --smiles "CCO" --method PM6
    python mopac_optimize.py --structure molecule.xyz --method PM7
    python mopac_optimize.py --smiles "c1ccccc1" --json
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from ase import Atoms
    from ase.io import read as ase_read, write as ase_write
    from ase.optimize import BFGS
    from ase.calculators.mopac import MOPAC
except ImportError:
    print("Error: ASE not installed. Install with: pip install ase")
    sys.exit(1)

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
except ImportError:
    Chem = None


def smiles_to_3d(smiles):
    """Convert SMILES to 3D structure."""
    if Chem is None:
        raise ImportError("RDKit required. Install: conda install -c conda-forge rdkit")

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, randomSeed=42)
    AllChem.MMFFOptimizeMolecule(mol)

    # Convert to ASE
    conf = mol.GetConformer()
    positions = []
    symbols = []

    for atom in mol.GetAtoms():
        pos = conf.GetAtomPosition(atom.GetIdx())
        positions.append([pos.x, pos.y, pos.z])
        symbols.append(atom.GetSymbol())

    return Atoms(symbols=symbols, positions=positions)


def optimize_with_mopac(atoms, method='PM6', convergence='default', fmax=0.01, steps=1000):
    """
    Optimize structure using MOPAC.

    Args:
        atoms: ASE Atoms object
        method: PM6, PM7, PM6-D3H4X
        convergence: default or tight
        fmax: Force criterion (eV/Å)
        steps: Max steps

    Returns:
        dict with results
    """
    # Create MOPAC calculator
    calc_kwargs = {'method': method}

    if convergence == 'tight':
        calc_kwargs['scf'] = 'GNORM=0.01'
    else:
        calc_kwargs['scf'] = 'GNORM=0.1'

    atoms.calc = MOPAC(**calc_kwargs)

    # Optimize
    optimizer = BFGS(atoms, trajectory='optimization.traj')
    converged = optimizer.run(fmax=fmax, steps=steps)

    # Extract results
    energy = atoms.get_potential_energy()
    forces = atoms.get_forces()
    max_force = (forces ** 2).sum(axis=1) ** 0.5

    results = {
        'converged': bool(converged),
        'energy': float(energy),
        'energy_units': 'eV',
        'energy_kcal_mol': float(energy * 23.06),
        'max_force': float(max_force.max()),
        'max_force_units': 'eV/Angstrom',
        'rms_force': float(((forces ** 2).sum(axis=1) ** 0.5).mean()),
        'n_atoms': len(atoms),
        'method': method,
        'convergence': convergence,
        'steps_taken': int(optimizer.nsteps),
        'structure': {
            'formula': atoms.get_chemical_formula(),
            'symbols': atoms.get_chemical_symbols(),
            'positions': atoms.get_positions().tolist()
        }
    }

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Optimize molecular structures using MOPAC'
    )
    parser.add_argument(
        '--smiles', type=str,
        help='SMILES string to optimize'
    )
    parser.add_argument(
        '--structure', type=str,
        help='Input structure file (XYZ, PDB, etc.)'
    )
    parser.add_argument(
        '--method', type=str, default='PM6',
        help='MOPAC method: PM6, PM7, PM6-D3H4X (default: PM6)'
    )
    parser.add_argument(
        '--convergence', type=str, default='default',
        help='Convergence: default or tight (default: default)'
    )
    parser.add_argument(
        '--fmax', type=float, default=0.01,
        help='Force criterion in eV/Å (default: 0.01)'
    )
    parser.add_argument(
        '--steps', type=int, default=1000,
        help='Maximum optimization steps (default: 1000)'
    )
    parser.add_argument(
        '--output', type=str, default='optimized.xyz',
        help='Output structure file (default: optimized.xyz)'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    try:
        # Load or create structure
        if args.smiles:
            atoms = smiles_to_3d(args.smiles)
        elif args.structure:
            atoms = ase_read(args.structure)
        else:
            parser.error("Provide either --smiles or --structure")

        # Optimize
        results = optimize_with_mopac(
            atoms,
            method=args.method,
            convergence=args.convergence,
            fmax=args.fmax,
            steps=args.steps
        )

        # Save structure
        ase_write(args.output, atoms)
        results['output_file'] = args.output

        # Output
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            status = "✓" if results['converged'] else "⚠"
            print(f"{status} Optimization {'converged' if results['converged'] else 'did not converge'}")
            print(f"  Method: {results['method']}")
            print(f"  Formula: {results['structure']['formula']}")
            print(f"  Energy: {results['energy']:.6f} eV ({results['energy_kcal_mol']:.2f} kcal/mol)")
            print(f"  Max force: {results['max_force']:.6f} eV/Å")
            print(f"  RMS force: {results['rms_force']:.6f} eV/Å")
            print(f"  Steps: {results['steps_taken']}/{args.steps}")
            print(f"  Saved to: {args.output}")

    except Exception as e:
        error = {'error': str(e), 'type': type(e).__name__}
        if args.json:
            print(json.dumps(error))
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
