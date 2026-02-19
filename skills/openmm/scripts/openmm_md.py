#!/usr/bin/env python3
"""
OpenMM Molecular Dynamics Simulation

Run MD simulations for proteins, ligands, and complexes.

Usage:
    python openmm_md.py --structure protein.pdb --temperature 300 --duration 10
    python openmm_md.py --pdb complex.pdb --ensemble npt --steps 50000 --json
"""

import argparse
import json
import sys

try:
    from openmm import *
    from openmm.app import *
    from openmm.unit import *
except ImportError:
    print("Error: OpenMM not installed. Install with: conda install -c conda-forge openmm")
    sys.exit(1)


def run_simulation(pdb_file, temperature=300, ensemble='nvt', duration_ns=10,
                   force_field='amber14', output_prefix='trajectory'):
    """
    Run MD simulation.

    Args:
        pdb_file: Input PDB file
        temperature: Temperature in K
        ensemble: NVE, NVT (Langevin), or NPT
        duration_ns: Simulation duration in nanoseconds
        force_field: Force field name (amber14, charmm36, opls)
        output_prefix: Prefix for output files

    Returns:
        dict with simulation results
    """
    # Load structure
    pdb = PDBFile(pdb_file)

    # Load force field
    if 'amber' in force_field.lower():
        ff_files = ['amber14-all.xml', 'amber14/tip3p.xml']
    elif 'charmm' in force_field.lower():
        ff_files = ['charmm36.xml', 'charmm36/water.xml']
    elif 'opls' in force_field.lower():
        ff_files = ['oplsaa.xml', 'spce.xml']
    else:
        ff_files = ['amber14-all.xml', 'amber14/tip3p.xml']

    forcefield = ForceField(*ff_files)

    # Create system
    system = forcefield.createSystem(
        pdb.topology,
        nonbondedMethod=PME,
        nonbondedCutoff=1.0*nanometer,
        constraints=HBonds,
        rigidWater=True
    )

    # Choose integrator and ensemble
    if ensemble.lower() == 'npt':
        integrator = LangevinMiddleIntegrator(temperature*kelvin, 1/picosecond, 2*femtoseconds)
        system.addForce(MonteCarloBarostat(1*bar, temperature*kelvin))
    else:  # NVT (Langevin)
        integrator = LangevinIntegrator(temperature*kelvin, 1/picosecond, 2*femtoseconds)

    # Create simulation
    platform = Platform.getPlatformByName('CUDA' if 'CUDA' in [p.getName() for p in Platform.getPlatforms()] else 'CPU')
    simulation = Simulation(pdb.topology, system, integrator, platform)
    simulation.context.setPositions(pdb.positions)

    # Energy minimization
    print("Minimizing energy...")
    simulation.minimizeEnergy(maxIterations=1000)

    # Equilibration (short NVT)
    print("Equilibrating...")
    simulation.context.setVelocitiesToTemperature(temperature*kelvin)
    simulation.step(5000)  # 10 ps

    # Production run
    print(f"Running {duration_ns} ns MD in {ensemble.upper()} ensemble...")

    # Add reporters
    timestep_fs = 2  # femtoseconds
    steps_per_ns = int(1000 / timestep_fs)
    total_steps = int(duration_ns * steps_per_ns)

    simulation.reporters.append(
        DCDReporter(f'{output_prefix}.dcd', 5000)  # Every 10 ps
    )
    simulation.reporters.append(
        StateDataReporter(f'{output_prefix}.log', 5000, temperature=True,
                         density=True, potentialEnergy=True,
                         kineticEnergy=True, totalEnergy=True, speed=True)
    )

    # Run MD
    simulation.step(total_steps)

    # Extract final properties
    state = simulation.context.getState(getEnergy=True, getPositions=True, getVelocities=True)

    results = {
        'simulation': {
            'duration_ns': duration_ns,
            'ensemble': ensemble.upper(),
            'temperature_K': temperature,
            'force_field': force_field,
            'total_steps': total_steps,
            'timestep_fs': timestep_fs
        },
        'final_state': {
            'potential_energy_kJ_mol': float(state.getPotentialEnergy() / kilojoules_per_mole),
            'kinetic_energy_kJ_mol': float(state.getKineticEnergy() / kilojoules_per_mole),
            'total_energy_kJ_mol': float((state.getPotentialEnergy() + state.getKineticEnergy()) / kilojoules_per_mole)
        },
        'output_files': {
            'trajectory': f'{output_prefix}.dcd',
            'log': f'{output_prefix}.log'
        }
    }

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Run molecular dynamics simulation with OpenMM'
    )
    parser.add_argument(
        '--structure', '--pdb', type=str, required=True,
        help='Input PDB file'
    )
    parser.add_argument(
        '--temperature', type=float, default=300,
        help='Temperature in Kelvin (default: 300)'
    )
    parser.add_argument(
        '--ensemble', type=str, default='nvt',
        help='Ensemble: NVE, NVT, NPT (default: NVT)'
    )
    parser.add_argument(
        '--duration', type=float, default=10,
        help='Simulation duration in nanoseconds (default: 10)'
    )
    parser.add_argument(
        '--force-field', type=str, default='amber14',
        help='Force field: amber14, charmm36, opls (default: amber14)'
    )
    parser.add_argument(
        '--output', type=str, default='trajectory',
        help='Output file prefix (default: trajectory)'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    try:
        results = run_simulation(
            args.structure,
            temperature=args.temperature,
            ensemble=args.ensemble,
            duration_ns=args.duration,
            force_field=args.force_field,
            output_prefix=args.output
        )

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("✓ Simulation completed")
            print(f"  Duration: {results['simulation']['duration_ns']} ns")
            print(f"  Ensemble: {results['simulation']['ensemble']}")
            print(f"  Final potential energy: {results['final_state']['potential_energy_kJ_mol']:.2f} kJ/mol")
            print(f"  Trajectory saved to: {results['output_files']['trajectory']}")

    except Exception as e:
        error = {'error': str(e), 'type': type(e).__name__}
        if args.json:
            print(json.dumps(error))
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
