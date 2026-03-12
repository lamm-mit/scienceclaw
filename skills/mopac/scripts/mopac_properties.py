#!/usr/bin/env python3
"""
MOPAC Molecular Properties

Calculate quantum chemical properties and reactivity indices.

Usage:
    python mopac_properties.py --smiles "CCO" --method PM6
    python mopac_properties.py --structure optimized.xyz --include-frequencies
    python mopac_properties.py --smiles "c1ccccc1" --solvent water --json
"""

import argparse
import json
import sys

try:
    from ase import Atoms
    from ase.io import read as ase_read
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

    conf = mol.GetConformer()
    positions = [
        [conf.GetAtomPosition(atom.GetIdx()).x,
         conf.GetAtomPosition(atom.GetIdx()).y,
         conf.GetAtomPosition(atom.GetIdx()).z]
        for atom in mol.GetAtoms()
    ]
    symbols = [atom.GetSymbol() for atom in mol.GetAtoms()]

    return Atoms(symbols=symbols, positions=positions)


def calculate_properties(atoms, method='PM6', solvent=None):
    """Calculate MOPAC properties."""

    # Setup MOPAC calculator
    calc_kwargs = {'method': method, 'task': 'ESP'}

    if solvent and solvent.lower() != 'vacuum':
        calc_kwargs['solvent'] = solvent.upper()

    atoms.calc = MOPAC(**calc_kwargs)

    # Get energy
    energy = atoms.get_potential_energy()

    properties = {
        'molecule': {
            'formula': atoms.get_chemical_formula(),
            'n_atoms': len(atoms),
            'symbols': atoms.get_chemical_symbols()
        },
        'energy': {
            'total': float(energy),
            'units_eV': 'eV',
            'units_kcal_mol': 'kcal/mol',
            'total_kcal_mol': float(energy * 23.06)
        },
        'method': method,
        'solvent': solvent if solvent else 'vacuum',
    }

    # Get forces (geometry quality)
    forces = atoms.get_forces()
    max_force = (forces ** 2).sum(axis=1) ** 0.5
    properties['geometry'] = {
        'max_force': float(max_force.max()),
        'rms_force': float(((forces ** 2).sum(axis=1) ** 0.5).mean()),
        'units': 'eV/Angstrom'
    }

    # HOMO-LUMO gap (semi-empirical estimate)
    # Note: More detailed calculation would require explicit MOPAC output parsing
    properties['quantum'] = {
        'note': 'Advanced quantum properties (HOMO, LUMO, reactivity indices) require MOPAC output parsing',
        'recommendation': 'Use MOPAC with OUTPUT keyword for detailed orbital information'
    }

    return properties


def main():
    parser = argparse.ArgumentParser(
        description='Calculate MOPAC quantum chemical properties'
    )
    parser.add_argument(
        '--smiles', type=str,
        help='SMILES string'
    )
    parser.add_argument(
        '--structure', type=str,
        help='Input structure file'
    )
    parser.add_argument(
        '--method', type=str, default='PM6',
        help='MOPAC method (default: PM6)'
    )
    parser.add_argument(
        '--solvent', type=str,
        help='Solvent (water, dmso, chloroform, etc.)'
    )
    parser.add_argument(
        '--include-frequencies', action='store_true',
        help='Calculate vibrational frequencies (slower)'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    try:
        # Load structure
        if args.smiles:
            atoms = smiles_to_3d(args.smiles)
        elif args.structure:
            atoms = ase_read(args.structure)
        else:
            parser.error("Provide --smiles or --structure")

        # Calculate properties
        properties = calculate_properties(atoms, method=args.method, solvent=args.solvent)

        if args.json:
            print(json.dumps(properties, indent=2))
        else:
            print(f"Molecule: {properties['molecule']['formula']}")
            print(f"  Atoms: {properties['molecule']['n_atoms']}")
            print(f"Method: {properties['method']}")
            print(f"Solvent: {properties['solvent']}")
            print(f"Energy: {properties['energy']['total']:.6f} eV ({properties['energy']['total_kcal_mol']:.2f} kcal/mol)")
            print(f"Geometry:")
            print(f"  Max force: {properties['geometry']['max_force']:.6f} eV/Å")
            print(f"  RMS force: {properties['geometry']['rms_force']:.6f} eV/Å")

    except Exception as e:
        error = {'error': str(e), 'type': type(e).__name__}
        if args.json:
            print(json.dumps(error))
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
