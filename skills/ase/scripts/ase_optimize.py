#!/usr/bin/env python3
"""
ASE Geometry Optimization

Optimize molecular or periodic structures to minimum energy configurations.
Supports SMILES input (converted to 3D geometry) or XYZ/CIF files.

Usage:
    python ase_optimize.py --smiles "CCO" --method PM6
    python ase_optimize.py --structure molecule.xyz --steps 500
    python ase_optimize.py --structure crystal.cif --fmax 0.05
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from ase import Atoms
    from ase.io import read as ase_read, write as ase_write
    from ase.optimize import BFGS, LBFGS
except ImportError:
    print("Error: ASE not installed. Install with: pip install ase")
    sys.exit(1)

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
except ImportError:
    Chem = None


def smiles_to_3d(smiles):
    """Convert SMILES to 3D structure using RDKit."""
    if Chem is None:
        raise ImportError("RDKit required for SMILES conversion. Install with: conda install -c conda-forge rdkit")

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, randomSeed=42)
    AllChem.MMFFOptimizeMolecule(mol)

    # Convert to ASE Atoms
    conf = mol.GetConformer()
    positions = []
    symbols = []

    for atom in mol.GetAtoms():
        pos = conf.GetAtomPosition(atom.GetIdx())
        positions.append([pos.x, pos.y, pos.z])
        symbols.append(atom.GetSymbol())

    return Atoms(symbols=symbols, positions=positions)


def optimize_structure(atoms, method='LBFGS', fmax=0.01, steps=1000, optimizer_type='LBFGS'):
    """
    Optimize atomic structure.

    Args:
        atoms: ASE Atoms object
        method: Calculator method (PM6, PM7, etc.)
        fmax: Force convergence criterion (eV/Å)
        steps: Maximum optimization steps
        optimizer_type: BFGS or LBFGS

    Returns:
        dict with optimization results
    """
    try:
        from ase.calculators.mopac import MOPAC
        calc = MOPAC(method=method)
    except ImportError:
        try:
            from ase.calculators.emt import EMT
            calc = EMT()
            method = "EMT"
        except ImportError:
            raise ImportError("No calculator available. Install MOPAC or use EMT.")

    atoms.calc = calc

    # Choose optimizer
    if optimizer_type.upper() == 'BFGS':
        optimizer = BFGS(atoms, trajectory='optimization.traj')
    else:
        optimizer = LBFGS(atoms, trajectory='optimization.traj')

    # Run optimization
    converged = optimizer.run(fmax=fmax, steps=steps)

    # Extract results
    energy = atoms.get_potential_energy()
    forces = atoms.get_forces()
    max_force = (forces ** 2).sum(axis=1) ** 0.5

    results = {
        'converged': converged,
        'energy': float(energy),
        'energy_units': 'eV',
        'max_force': float(max_force.max()),
        'max_force_units': 'eV/Angstrom',
        'n_atoms': len(atoms),
        'method': method,
        'fmax': fmax,
        'steps_taken': optimizer.nsteps,
        'structure': {
            'symbols': atoms.get_chemical_symbols(),
            'positions': atoms.get_positions().tolist(),
            'cell': atoms.get_cell().tolist(),
            'pbc': atoms.get_pbc().tolist()
        }
    }

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Optimize molecular or periodic structures using ASE'
    )
    parser.add_argument(
        '--smiles', type=str,
        help='SMILES string to optimize (requires RDKit)'
    )
    parser.add_argument(
        '--structure', type=str,
        help='Input structure file (XYZ, CIF, etc.)'
    )
    parser.add_argument(
        '--method', type=str, default='PM6',
        help='Quantum method: PM6, PM7, PM6-D3H4X (default: PM6)'
    )
    parser.add_argument(
        '--fmax', type=float, default=0.01,
        help='Force convergence criterion in eV/Å (default: 0.01)'
    )
    parser.add_argument(
        '--steps', type=int, default=1000,
        help='Maximum optimization steps (default: 1000)'
    )
    parser.add_argument(
        '--optimizer', type=str, default='LBFGS',
        help='Optimizer type: BFGS or LBFGS (default: LBFGS)'
    )
    parser.add_argument(
        '--output', type=str, default='optimized.xyz',
        help='Output structure file (default: optimized.xyz)'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output results as JSON to stdout'
    )

    args = parser.parse_args()

    # Load or create structure
    if args.smiles:
        atoms = smiles_to_3d(args.smiles)
    elif args.structure:
        atoms = ase_read(args.structure)
    else:
        parser.error("Provide either --smiles or --structure")

    # Optimize
    try:
        results = optimize_structure(
            atoms,
            method=args.method,
            fmax=args.fmax,
            steps=args.steps,
            optimizer_type=args.optimizer
        )

        # Save optimized structure
        ase_write(args.output, atoms)
        results['output_file'] = args.output

        # Output
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"✓ Optimization {'converged' if results['converged'] else 'did not converge'}")
            print(f"  Energy: {results['energy']:.6f} eV")
            print(f"  Max force: {results['max_force']:.6f} eV/Å")
            print(f"  Steps: {results['steps_taken']}/{args.steps}")
            print(f"  Structure saved to: {args.output}")

    except Exception as e:
        error_result = {
            'error': str(e),
            'type': type(e).__name__
        }
        if args.json:
            print(json.dumps(error_result, indent=2))
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
