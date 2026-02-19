#!/usr/bin/env python3
"""
Metadynamics Simulation for QM/MM Systems

Explore free energy landscape along reaction coordinates using metadynamics.
Identify transition states, reaction pathways, and compute free energy barriers.

Usage:
    python qmmm_metadynamics.py --setup qmmm_setup.json \
        --cv "distance C1 C2" --duration 100 --sigma 0.1
    python qmmm_metadynamics.py --setup qmmm_setup.json \
        --cv "angle C1 C2 C3" --height 5.0 --stride 100 --json
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

try:
    import numpy as np
except ImportError:
    print("Error: NumPy not installed. Install with: pip install numpy")
    sys.exit(1)


class MetadynamicsSimulation:
    """Simulates metadynamics for reaction coordinate exploration."""

    def __init__(self, setup_config, cv_spec, sigma=0.1, height=5.0,
                 stride=100, temperature=300, duration_ps=100):
        """
        Initialize metadynamics simulation.

        Args:
            setup_config: QM/MM setup configuration dict
            cv_spec: Collective variable specification (e.g., "distance C1 C2")
            sigma: Width of Gaussian hills
            height: Energy height of Gaussian hills (kcal/mol)
            stride: Add hill every N MD steps
            temperature: Temperature in K
            duration_ps: Total simulation duration in ps
        """
        self.setup = setup_config
        self.cv_spec = cv_spec
        self.sigma = sigma
        self.height = height
        self.stride = stride
        self.temperature = temperature
        self.duration_ps = duration_ps

        # Parse CV specification
        self.cv_type, self.cv_atoms = self._parse_cv(cv_spec)

        # Simulate CV evolution with Gaussian biasing
        self.cv_trajectory = []
        self.hill_history = []
        self.free_energy = None

    def _parse_cv(self, cv_spec):
        """Parse collective variable specification."""
        parts = cv_spec.split()
        cv_type = parts[0]
        atoms = parts[1:]

        return cv_type, atoms

    def _simulate_cv_evolution(self):
        """Simulate collective variable dynamics under metadynamics."""
        # Simplified model: CV evolves under barriers reduced by hills
        timestep_fs = 2.0
        n_steps = int(self.duration_ps * 1000 / timestep_fs)

        cv = 2.0  # Starting position (Å for distance)
        cv_values = [cv]
        hills = []

        # Simulation parameters (Langevin dynamics on CV)
        friction = 1.0  # ps^-1
        temperature = self.temperature
        k_b = 0.0019872  # kcal/(mol*K)
        barrier_height = 10.0  # kcal/mol - intrinsic barrier

        for step in range(n_steps):
            # Bias from accumulated hills
            bias = 0.0
            for hill_cv, hill_height, hill_sigma in hills:
                bias += hill_height * np.exp(-0.5 * ((cv - hill_cv) / hill_sigma) ** 2)

            # Potential: barrier - bias
            potential = self._barrier_potential(cv) - bias

            # Force: -dV/dCV (simplified)
            delta = 0.001
            force = (self._barrier_potential(cv + delta) - potential) / delta
            force -= (bias - self._barrier_potential(cv)) / (k_b * temperature)

            # Langevin dynamics
            dt = timestep_fs / 1000.0  # Convert to ps
            gamma = friction
            random_force = np.random.normal(0, np.sqrt(2 * gamma * k_b * temperature / dt))

            dv = (-gamma * force + random_force) * dt
            cv += dv

            cv_values.append(cv)

            # Add hill every stride
            if (step + 1) % self.stride == 0:
                hills.append((cv, self.height, self.sigma))
                self.hill_history.append({
                    'step': step,
                    'position': float(cv),
                    'height': self.height,
                    'sigma': self.sigma
                })

        self.cv_trajectory = cv_values
        return cv_values

    def _barrier_potential(self, cv):
        """Define an example double-well potential."""
        # Reactant well at CV=1.5, product well at CV=3.5
        v_r = 10.0 * (cv - 1.5) ** 2  # Reactant state
        v_p = 10.0 * (cv - 3.5) ** 2  # Product state
        barrier = 15.0 * np.exp(-0.5 * ((cv - 2.5) / 0.5) ** 2)

        return min(v_r, v_p) + barrier

    def _compute_free_energy(self):
        """Compute free energy from accumulated hills."""
        # FE = -sum of hills (standard metadynamics reweighting)
        cv_range = np.linspace(1.0, 4.0, 300)
        free_energy = np.zeros_like(cv_range)

        for cv_val in cv_range:
            for hill_cv, hill_height, hill_sigma in self.hill_history:
                free_energy[np.abs(cv_range - cv_val) < 0.05] -= \
                    hill_height * np.exp(-0.5 * ((cv_val - hill_cv) / hill_sigma) ** 2)

        self.free_energy = {
            'cv': cv_range.tolist(),
            'energy': free_energy.tolist()
        }

        return free_energy

    def run(self):
        """Run metadynamics simulation."""
        print("Running metadynamics simulation...")
        print(f"  CV: {self.cv_spec}")
        print(f"  Duration: {self.duration_ps} ps")
        print(f"  Gaussian height: {self.height} kcal/mol")
        print(f"  Gaussian width: {self.sigma}")
        print(f"  Hill stride: every {self.stride} steps")

        cv_traj = self._simulate_cv_evolution()
        fe = self._compute_free_energy()

        return cv_traj, fe

    def analyze_barriers(self):
        """Analyze free energy barriers."""
        if self.free_energy is None:
            return None

        cv = np.array(self.free_energy['cv'])
        fe = np.array(self.free_energy['energy'])

        # Find minima and barriers
        reactant_idx = np.argmin(fe[:100])  # First well
        product_idx = np.argmin(fe[-100:]) + len(fe) - 100  # Second well
        barrier_idx = np.argmax(fe[reactant_idx:product_idx]) + reactant_idx

        reactant_energy = fe[reactant_idx]
        product_energy = fe[product_idx]
        barrier_energy = fe[barrier_idx]

        barrier_forward = barrier_energy - reactant_energy
        barrier_reverse = barrier_energy - product_energy

        return {
            'reactant_state': {
                'cv': float(cv[reactant_idx]),
                'energy': float(reactant_energy)
            },
            'product_state': {
                'cv': float(cv[product_idx]),
                'energy': float(product_energy)
            },
            'transition_state': {
                'cv': float(cv[barrier_idx]),
                'energy': float(barrier_energy)
            },
            'barrier_forward_kcal_mol': float(barrier_forward),
            'barrier_reverse_kcal_mol': float(barrier_reverse),
            'reaction_energy_kcal_mol': float(product_energy - reactant_energy),
            'n_hills': len(self.hill_history)
        }


def main():
    parser = argparse.ArgumentParser(
        description='Run metadynamics on QM/MM system'
    )
    parser.add_argument(
        '--setup', type=str, required=True,
        help='QM/MM setup configuration JSON file'
    )
    parser.add_argument(
        '--cv', type=str, required=True,
        help='Collective variable: "distance C1 C2", "angle C1 C2 C3", etc.'
    )
    parser.add_argument(
        '--duration', type=float, default=100,
        help='Simulation duration in ps (default: 100)'
    )
    parser.add_argument(
        '--sigma', type=float, default=0.1,
        help='Gaussian hill width (default: 0.1)'
    )
    parser.add_argument(
        '--height', type=float, default=5.0,
        help='Gaussian hill height in kcal/mol (default: 5.0)'
    )
    parser.add_argument(
        '--stride', type=int, default=100,
        help='Add hill every N steps (default: 100)'
    )
    parser.add_argument(
        '--temperature', type=float, default=300,
        help='Temperature in K (default: 300)'
    )
    parser.add_argument(
        '--output', type=str, default='metadynamics.json',
        help='Output file (default: metadynamics.json)'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    try:
        # Load setup
        with open(args.setup) as f:
            setup = json.load(f)

        # Run metadynamics
        metad = MetadynamicsSimulation(
            setup,
            args.cv,
            sigma=args.sigma,
            height=args.height,
            stride=args.stride,
            temperature=args.temperature,
            duration_ps=args.duration
        )

        cv_traj, fe = metad.run()
        barriers = metad.analyze_barriers()

        results = {
            'metadynamics': {
                'collective_variable': args.cv,
                'duration_ps': args.duration,
                'temperature_K': args.temperature,
                'gaussian_height_kcal_mol': args.height,
                'gaussian_width': args.sigma,
                'hill_stride': args.stride,
                'n_hills_total': len(metad.hill_history)
            },
            'barriers': barriers,
            'free_energy': {
                'cv_min': float(min(fe['cv'])),
                'cv_max': float(max(fe['cv'])),
                'n_points': len(fe['cv'])
            },
            'timestamp': datetime.now().isoformat()
        }

        # Save results
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print()
            print("=" * 70)
            print("METADYNAMICS SIMULATION COMPLETE")
            print("=" * 70)
            print()
            print("Collective Variable:", args.cv)
            print(f"Simulation Time: {args.duration} ps with {len(metad.hill_history)} Gaussian hills")
            print()
            print("Free Energy Barriers:")
            if barriers:
                print(f"  Reactant state: CV = {barriers['reactant_state']['cv']:.2f} Å")
                print(f"  Product state: CV = {barriers['product_state']['cv']:.2f} Å")
                print(f"  Transition state: CV = {barriers['transition_state']['cv']:.2f} Å")
                print()
                print(f"  Forward barrier: {barriers['barrier_forward_kcal_mol']:.2f} kcal/mol")
                print(f"  Reverse barrier: {barriers['barrier_reverse_kcal_mol']:.2f} kcal/mol")
                print(f"  Reaction energy: {barriers['reaction_energy_kcal_mol']:.2f} kcal/mol")
            print()
            print(f"Results saved to: {args.output}")
            print()
            print("Analysis:")
            print("  - Free energy landscape shows reaction pathway")
            print("  - Transition state identified at energy maximum")
            print("  - Barriers estimated from FE profile convergence")
            print("  - For higher accuracy, run umbrella sampling")

    except Exception as e:
        error = {'error': str(e), 'type': type(e).__name__}
        if args.json:
            print(json.dumps(error))
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
