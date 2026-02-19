---
name: ase
description: Atomic Simulation Environment (ASE) for computational materials science. Perform DFT calculations, geometry optimization, band structure analysis, molecular property prediction, and periodic structure simulations. Supports VASP, MOPAC, Quantum ESPRESSO backends. For quick semi-empirical quantum chemistry, use mopac. For classical molecular dynamics, use openmm.
license: LGPL-3.0
metadata:
    skill-author: K-Dense Inc.
    domain: computational-chemistry, materials-science
---

# Atomic Simulation Environment (ASE)

## Overview

ASE is a Python library for working with atoms and atomic structures. This skill provides computational design capabilities for materials science, including DFT geometry optimization, electronic structure calculations, phonon analysis, and molecular dynamics with classical force fields. ASE interfaces with multiple computational backends (MOPAC, Quantum ESPRESSO, VASP) and is excellent for designing novel materials and predicting their properties computationally.

## Core Capabilities

### 1. Structure Optimization

**Geometry Optimization:**

Optimize atomic structures to find stable configurations:

```python
from ase import Atoms
from ase.optimize import BFGS
from ase.calculators.mopac import MOPAC

# Create structure
atoms = Atoms('H2O', positions=[[0, 0, 0], [1, 0, 0], [0, 1, 0]])

# Set calculator (semi-empirical quantum chemistry)
atoms.calc = MOPAC(method='PM6')

# Optimize geometry
dyn = BFGS(atoms)
dyn.run(fmax=0.01)

# Get optimized coordinates and energy
energy = atoms.get_potential_energy()
forces = atoms.get_forces()
```

**Key Parameters:**
- `fmax`: Force convergence criterion (eV/Å)
- `steps`: Maximum optimization steps
- `trajectory`: File to save optimization trajectory

### 2. Electronic Structure Calculations

**Band Structure:**

Compute electronic band structures for periodic systems:

```python
from ase.build import bulk
from ase.calculators.mopac import MOPAC

# Create periodic structure (bulk silicon)
atoms = bulk('Si', 'diamond', a=5.4)

# Calculate band structure at high-symmetry k-points
atoms.calc = MOPAC(method='PM6-D3H4X')
```

**Density of States:**

Compute electronic density of states:

```python
# Get DOS at different energy levels
from ase.dft.band_structure import calculate_band_structure
```

### 3. Molecular Properties

**Predict from Structure:**

Calculate molecular properties computationally:

```python
# Geometry-optimized properties
- Dipole moment
- Polarizability
- Band gap (for semiconductors)
- Formation energy (for compounds)
- Cohesive energy (for crystals)
```

### 4. Phonon Analysis

**Vibrational Properties:**

Compute phonon frequencies for material stability:

```python
from ase.phonons import Phonons

# Create phonon object
phonons = Phonons(atoms, MOPAC_calc, supercell=(2, 2, 2))
phonons.run()

# Get phonon frequencies and DOS
phonon_frequencies = phonons.get_frequencies()
```

### 5. Molecular Dynamics with Classical Force Fields

**NVT/NPT Ensemble Simulation:**

Run classical MD with force fields (using EMT or custom potentials):

```python
from ase.md.verlet import VelocityVerlet
from ase.md.langevin import Langevin
from ase import units

# NVT ensemble (constant T)
dyn = Langevin(atoms, timestep=1*units.fs, temperature_K=300, friction=0.02)

# Run for specified timesteps
for i in range(1000):
    dyn.run(1)
```

## Available Calculators

### MOPAC (Semi-empirical QM)
- Fast quantum chemistry calculations
- Methods: PM6, PM7, PM6-D3H4X
- Suitable for quick computational design
- Lower accuracy than DFT, much faster

### Quantum ESPRESSO (DFT)
- Full density functional theory
- Plane wave basis set
- Periodic and cluster structures
- Requires Quantum ESPRESSO installation

### VASP (DFT)
- Industry-standard DFT code
- High accuracy
- Computationally expensive
- Requires VASP license and installation

## Use Cases

**Computational Design:**
- Optimize drug molecule structures
- Predict crystal structures for materials
- Calculate formation energies for compound stability
- Design heterogeneous catalysts

**Property Prediction:**
- Band gaps for semiconductors
- Thermal properties (specific heat, expansion)
- Electron-phonon coupling
- Surface energy and reactivity

**Screening:**
- High-throughput property calculations
- Structure stability validation
- Phonon stability (imaginary frequencies indicate instability)
- Thermodynamic feasibility

## Integration with Other Skills

**Input:**
- Structures from `pdb` skill (extract coordinates)
- SMILES from `pubchem` (generate 3D structures)
- Crystal structures from `materials` skill

**Output:**
- Optimized structures for `mopac` (faster reoptimization)
- Properties for `rdkit` (compare with ML models)
- Band structures for `materials` (cross-validate)

## Performance Notes

- **MOPAC:** Fast (~seconds per structure), suitable for large-scale screening
- **Quantum ESPRESSO:** Slow (~hours per structure), high accuracy
- **VASP:** Very slow (~days per structure), highest accuracy

## Limitations

- Requires computational resources (CPU/GPU)
- MOPAC less accurate than DFT
- Quantum ESPRESSO/VASP need external installations
- Cannot predict experimental solubility, in vitro binding
- Periodic boundary conditions assumptions may not match real systems

## Example Workflow

```bash
# 1. Optimize molecular structure
python ase_optimize.py --smiles "CCO" --method PM6

# 2. Calculate properties
python ase_properties.py --structure optimized.xyz

# 3. Run MD simulation
python ase_md.py --structure optimized.xyz --temperature 300 --timesteps 10000

# 4. Analyze phonons (materials)
python ase_phonons.py --structure crystal.xyz --supercell "2 2 2"
```

## References

- ASE documentation: https://wiki.fysik.dtu.dk/ase/
- MOPAC Manual: http://openmopac.net/
- Quantum ESPRESSO: https://www.quantum-espresso.org/
