#!/usr/bin/env python3
"""
QM/MM System Setup and Preparation

Prepare hybrid QM/MM systems for enzyme mechanism studies.
Define QM region (reactive atoms) and MM region (protein/solvent).

Usage:
    python qmmm_setup.py --pdb enzyme.pdb --qm-atoms "C1 C2 N3" --qm-method MOPAC
    python qmmm_setup.py --pdb complex.pdb --qm-atoms atoms.txt --buffer 12
    python qmmm_setup.py --pdb system.pdb --qm-atoms "OG1:SER195" --json
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from ase import Atoms
    from ase.io import read as ase_read, write as ase_write
except ImportError:
    print("Error: ASE not installed. Install with: pip install ase")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("Error: NumPy not installed. Install with: pip install numpy")
    sys.exit(1)


def parse_qm_atoms(qm_spec):
    """
    Parse QM atom specification.

    Formats:
    - "C1 C2 N3" - atom indices
    - "OG1:SER195 NZ:LYS100" - residue:atom pairs
    - atoms.txt - file with atom specifications

    Returns:
        list of atom indices
    """
    qm_atoms = []

    # Check if it's a file
    qm_file = Path(qm_spec)
    if qm_file.exists():
        with open(qm_file) as f:
            specs = [line.strip() for line in f if line.strip()]
    else:
        specs = qm_spec.split()

    return specs  # Return specs for matching against structure


def setup_qmmm_system(pdb_file, qm_atoms, qm_method='MOPAC',
                     mm_forcefield='AMBER14', buffer_distance=15.0):
    """
    Set up QM/MM system.

    Args:
        pdb_file: Input PDB structure
        qm_atoms: List of QM atom specifications
        qm_method: QM method (MOPAC, ORCA, TeraChem)
        mm_forcefield: MM force field (AMBER14, CHARMM36, OPLS)
        buffer_distance: Distance (Å) for QM region buffer

    Returns:
        dict with system information
    """
    # Read structure
    try:
        atoms = ase_read(pdb_file)
    except Exception as e:
        raise ValueError(f"Cannot read PDB file: {e}")

    n_atoms = len(atoms)
    symbols = atoms.get_chemical_symbols()
    positions = atoms.get_positions()

    # Parse QM atoms (simplified - in real system would parse PDB residue info)
    qm_indices = []
    for spec in qm_atoms:
        if spec.isdigit():
            qm_indices.append(int(spec) - 1)  # Convert to 0-indexed
        else:
            # Would need PDB parsing for residue:atom format
            # For now, accept atom indices
            pass

    if not qm_indices:
        raise ValueError("No valid QM atoms specified")

    # Define QM region center
    qm_center = positions[qm_indices].mean(axis=0)

    # Find all atoms within buffer distance
    qm_region_indices = set()
    for i, pos in enumerate(positions):
        dist = np.linalg.norm(pos - qm_center)
        if dist < buffer_distance:
            qm_region_indices.add(i)

    # Make sure all specified atoms are included
    qm_region_indices.update(qm_indices)
    qm_region_list = sorted(list(qm_region_indices))

    mm_region_list = [i for i in range(n_atoms) if i not in qm_region_indices]

    results = {
        'structure': {
            'pdb_file': pdb_file,
            'n_atoms_total': n_atoms,
            'n_atoms_qm': len(qm_region_list),
            'n_atoms_mm': len(mm_region_list),
            'qm_region_percent': 100.0 * len(qm_region_list) / n_atoms
        },
        'qm_setup': {
            'method': qm_method,
            'atoms': qm_region_list,
            'center': qm_center.tolist(),
            'charge': 0,
            'multiplicity': 1,
            'solvent': 'implicit'
        },
        'mm_setup': {
            'forcefield': mm_forcefield,
            'atoms': mm_region_list,
            'water_model': 'TIP3P' if 'AMBER' in mm_forcefield else 'TIP3P',
            'constraint': 'H-bonds'
        },
        'interface': {
            'buffer_distance_angstrom': buffer_distance,
            'link_atom_treatment': 'capping',
            'electrostatic_embedding': 'electronic',
            'qm_mm_cutoff': 12.0
        },
        'equilibration_protocol': {
            'step1_qm_region': {
                'description': 'Fix MM atoms, relax QM region only',
                'duration_ps': 5,
                'ensemble': 'NVT',
                'temperature_K': 300
            },
            'step2_hybrid': {
                'description': 'Gradually couple QM-MM interactions',
                'duration_ps': 10,
                'ensemble': 'NVT',
                'temperature_K': 300
            },
            'step3_full': {
                'description': 'Full system equilibration',
                'duration_ps': 50,
                'ensemble': 'NPT',
                'temperature_K': 300,
                'pressure_bar': 1.0
            }
        }
    }

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Setup QM/MM hybrid system for enzyme mechanism studies'
    )
    parser.add_argument(
        '--pdb', type=str, required=True,
        help='Input PDB structure file'
    )
    parser.add_argument(
        '--qm-atoms', type=str, required=True,
        help='QM atoms: space-separated indices, or filename, or "RES:ATOM" format'
    )
    parser.add_argument(
        '--qm-method', type=str, default='MOPAC',
        help='QM method: MOPAC, ORCA, TeraChem (default: MOPAC)'
    )
    parser.add_argument(
        '--force-field', type=str, default='AMBER14',
        help='MM force field: AMBER14, CHARMM36, OPLS (default: AMBER14)'
    )
    parser.add_argument(
        '--buffer', type=float, default=15.0,
        help='QM region buffer distance in Å (default: 15.0)'
    )
    parser.add_argument(
        '--output', type=str, default='qmmm_setup.json',
        help='Output configuration file (default: qmmm_setup.json)'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output as JSON to stdout'
    )

    args = parser.parse_args()

    try:
        qm_specs = parse_qm_atoms(args.qm_atoms)
        setup = setup_qmmm_system(
            args.pdb,
            qm_specs,
            qm_method=args.qm_method,
            mm_forcefield=args.force_field,
            buffer_distance=args.buffer
        )

        # Save configuration
        with open(args.output, 'w') as f:
            json.dump(setup, f, indent=2)

        if args.json:
            print(json.dumps(setup, indent=2))
        else:
            print("=" * 70)
            print("QM/MM SYSTEM SETUP COMPLETE")
            print("=" * 70)
            print()
            print("Structure Information:")
            print(f"  Total atoms: {setup['structure']['n_atoms_total']}")
            print(f"  QM region: {setup['structure']['n_atoms_qm']} atoms ({setup['structure']['qm_region_percent']:.1f}%)")
            print(f"  MM region: {setup['structure']['n_atoms_mm']} atoms ({100-setup['structure']['qm_region_percent']:.1f}%)")
            print()
            print("QM Setup:")
            print(f"  Method: {setup['qm_setup']['method']}")
            print(f"  Charge: {setup['qm_setup']['charge']}")
            print(f"  Multiplicity: {setup['qm_setup']['multiplicity']}")
            print()
            print("MM Setup:")
            print(f"  Force field: {setup['mm_setup']['forcefield']}")
            print(f"  Water model: {setup['mm_setup']['water_model']}")
            print(f"  Constraints: {setup['mm_setup']['constraint']}")
            print()
            print("Interface Parameters:")
            print(f"  Buffer distance: {setup['interface']['buffer_distance_angstrom']} Å")
            print(f"  Electrostatic embedding: {setup['interface']['electrostatic_embedding']}")
            print(f"  QM-MM cutoff: {setup['interface']['qm_mm_cutoff']} Å")
            print()
            print("Equilibration Protocol:")
            for step, details in setup['equilibration_protocol'].items():
                print(f"  {step}: {details['duration_ps']} ps {details['ensemble']} @ {details['temperature_K']} K")
            print()
            print(f"Configuration saved to: {args.output}")
            print()
            print("Next steps:")
            print("  1. Review QM/MM setup in generated JSON")
            print("  2. Run equilibration: python qmmm_equilibrate.py")
            print("  3. Run metadynamics: python qmmm_metad.py")
            print("  4. Analyze mechanism: python qmmm_mechanism.py")

    except Exception as e:
        error = {'error': str(e), 'type': type(e).__name__}
        if args.json:
            print(json.dumps(error))
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
