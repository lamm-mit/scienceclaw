#!/usr/bin/env python3
"""
ASE Properties Calculator

Calculate physical properties of optimized structures.

Usage:
    python ase_properties.py --structure optimized.xyz
    python ase_properties.py --structure crystal.cif --method PM6
    python ase_properties.py --structure molecule.xyz --json
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from ase import Atoms
    from ase.io import read as ase_read
    from ase.calculators.mopac import MOPAC
except ImportError:
    print("Error: ASE not installed. Install with: pip install ase")
    sys.exit(1)


def calculate_properties(atoms, method='PM6'):
    """Calculate molecular/material properties."""
    atoms.calc = MOPAC(method=method)

    properties = {
        'structure': {
            'n_atoms': len(atoms),
            'symbols': atoms.get_chemical_symbols(),
            'formula': atoms.get_chemical_formula(),
        },
        'geometry': {
            'cell': atoms.get_cell().tolist(),
            'pbc': atoms.get_pbc().tolist(),
            'volume': float(atoms.get_volume())
        },
        'energy': {
            'total_energy': float(atoms.get_potential_energy()),
            'units': 'eV'
        }
    }

    # Calculate forces (indicates stability if all near zero)
    forces = atoms.get_forces()
    properties['forces'] = {
        'max_force': float((forces ** 2).sum(axis=1) ** 0.5).max(),
        'rms_force': float(((forces ** 2).sum(axis=1) ** 0.5).mean()),
        'units': 'eV/Angstrom'
    }

    # Distance matrix
    from ase.geometry import get_distances
    D, D_len = get_distances(atoms, mic=False)
    properties['distances'] = {
        'min_distance': float(D_len[D_len > 0].min()),
        'max_distance': float(D_len.max()),
        'units': 'Angstrom'
    }

    return properties


def main():
    parser = argparse.ArgumentParser(
        description='Calculate properties of atomic structures'
    )
    parser.add_argument(
        '--structure', type=str, required=True,
        help='Input structure file (XYZ, CIF, etc.)'
    )
    parser.add_argument(
        '--method', type=str, default='PM6',
        help='Quantum method: PM6, PM7, PM6-D3H4X (default: PM6)'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    try:
        atoms = ase_read(args.structure)
        properties = calculate_properties(atoms, method=args.method)

        if args.json:
            print(json.dumps(properties, indent=2))
        else:
            print(f"Structure: {properties['structure']['formula']}")
            print(f"  Atoms: {properties['structure']['n_atoms']}")
            print(f"  Volume: {properties['geometry']['volume']:.3f} Å³")
            print(f"Energy: {properties['energy']['total_energy']:.6f} eV")
            print(f"Forces: max={properties['forces']['max_force']:.6f}, rms={properties['forces']['rms_force']:.6f} eV/Å")
            print(f"Distances: {properties['distances']['min_distance']:.3f}-{properties['distances']['max_distance']:.3f} Å")

    except Exception as e:
        error = {'error': str(e), 'type': type(e).__name__}
        if args.json:
            print(json.dumps(error))
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
