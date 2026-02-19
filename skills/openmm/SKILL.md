---
name: openmm
description: OpenMM molecular dynamics engine for protein and ligand simulations. Run NVE/NVT/NPT ensembles, compute free energies, analyze dynamics. Supports AMBER, CHARMM, OPLS force fields and GPU acceleration. For classical MD with periodic systems, use ase. For quick quantum chemistry, use mopac.
license: MIT
metadata:
    skill-author: K-Dense Inc.
    domain: computational-chemistry, biomolecular-simulation
---

# OpenMM Molecular Dynamics Engine

## Overview

OpenMM is a toolkit for molecular simulation, particularly suited for biomolecular systems (proteins, ligands, membranes). This skill provides computational investigation capabilities for protein dynamics, ligand binding exploration, conformational sampling, and free energy calculations. OpenMM supports GPU acceleration for high-performance simulations and multiple force fields (AMBER, CHARMM, OPLS).

## Core Capabilities

### 1. Protein Dynamics Simulation

**Basic MD Run:**

Simulate protein motion in explicit solvent:

```python
from openmm import *
from openmm.app import *
from openmm.unit import *

# Load structure
pdb = PDBFile('protein.pdb')

# Create force field and system
forcefield = ForceField('amber14-all.xml', 'amber14/tip3p.xml')
system = forcefield.createSystem(pdb.topology, nonbondedMethod=PME)

# Create integrator (NVT ensemble)
integrator = LangevinIntegrator(300*kelvin, 1/picosecond, 2*femtoseconds)

# Run simulation
simulation = Simulation(pdb.topology, system, integrator)
simulation.context.setPositions(pdb.positions)
simulation.minimizeEnergy()
simulation.reporters.append(PDBReporter('trajectory.pdb', 1000))
simulation.step(100000)  # 200 ps
```

**Key Ensembles:**
- NVE: Constant volume, constant energy (microcanonical)
- NVT: Constant volume, constant temperature (Langevin/Nose-Hoover)
- NPT: Constant pressure, constant temperature (isothermal-isobaric)

### 2. Ligand Binding Exploration

**Protein-Ligand Complex Dynamics:**

Simulate ligand movement in protein binding pocket:

```python
# Load complex (protein + ligand)
pdb = PDBFile('complex.pdb')

# Create system with AMBER FF
forcefield = ForceField('amber14-all.xml', 'amber14/tip3p.xml')
system = forcefield.createSystem(
    pdb.topology,
    nonbondedMethod=PME,
    constraints=HBonds
)

# Run with restraints on protein (ligand free)
# Can use positional restraints to keep protein stable
```

**Binding Free Energy (Alchemical):**

Calculate free energy of ligand binding:

```python
# Thermodynamic Integration (TI) or
# Free Energy Perturbation (FEP)
# Alchemically transform ligand from bound → unbound state
```

### 3. Conformational Sampling

**Enhanced Sampling Techniques:**

Explore conformational landscape:

```python
# Replica Exchange Molecular Dynamics (REMD)
# Multiple replicas at different temperatures
# Exchanges improve sampling efficiency

# Or: Simulated annealing
# Gradual temperature reduction
```

### 4. Energy Minimization

**Structure Optimization:**

Relax structures before MD:

```python
simulation.minimizeEnergy(maxIterations=1000)
```

Finds local energy minimum without dynamics.

### 5. Analysis

**Extract Properties:**

Compute from trajectories:

```python
- Root-mean-square deviation (RMSD)
- Radius of gyration (Rg)
- Hydrogen bond occupancy
- Dihedral angles (phi/psi for proteins)
- Free energy differences
- Binding free energies (MM-PBSA)
```

## Available Force Fields

### Biomolecules
- **AMBER14**: AMBER force field with TIP3P water
- **CHARMM36**: CHARMM force field
- **OPLS**: OPLS-AA force field

### Water Models
- TIP3P: 3-point, commonly used
- TIP4P, TIP5P: Higher accuracy
- OPC: Optimized charge-on-springy particle water

### Ions
- Standard monovalent ions (Na+, Cl-, K+)
- Divalent ions (Ca2+, Mg2+)
- Implicit solvent models (generalized Born)

## Use Cases

**Computational Drug Discovery:**
- Predict protein-ligand binding modes
- Calculate binding free energies
- Identify transient binding pockets
- Screen multiple ligands

**Protein Engineering:**
- Validate designed proteins
- Predict stability (thermal stability from Tm calculations)
- Explore conformational changes
- Design allosteric mechanisms

**Structural Biology:**
- Simulate protein-protein interactions
- Model conformational ensembles
- Compute flexibility maps
- Validate X-ray/cryo-EM structures

**Membrane Systems:**
- Lipid bilayer simulations
- Protein-membrane interactions
- Ion channel dynamics
- Membrane protein folding

## Integration with Other Skills

**Input:**
- Structures from `pdb` (X-ray structures)
- Structures from `ase` (optimized geometries)
- SMILES from `pubchem` (ligand structures)
- Sequences from `uniprot` (homology modeling)

**Output:**
- Trajectories for analysis
- Binding affinities for comparison with `tdc`
- Conformational ensembles for property prediction
- Dynamics data for publication in `arxiv`

## Performance Characteristics

**Timescales:**
- Energy minimization: seconds
- Short equilibration (10 ns): minutes
- Microsecond-scale sampling: hours (with GPU)
- Millisecond sampling: days-weeks

**GPU Acceleration:**
- 50-100x speedup on NVIDIA GPUs (CUDA)
- AMD GPUs supported (HIP)
- CPU fallback available (slow)

## Limitations

- Requires high-performance hardware (GPU recommended)
- Classical force fields have accuracy limits
- Long timescales need multiple runs/ensemble averaging
- Cannot include quantum effects (proton transfer, bond breaking)
- Protein topology fixed during simulation

## Example Workflow

```bash
# 1. Prepare protein structure
python openmm_setup.py --pdb protein.pdb --force-field amber14

# 2. Run MD simulation
python openmm_md.py --structure prepared.pdb --temperature 300 \
    --ensemble nvt --duration 100  # ns

# 3. Analyze trajectory
python openmm_analysis.py --trajectory trajectory.dcd \
    --reference protein.pdb --metrics rmsd radius-of-gyration
```

## References

- OpenMM documentation: https://openmm.org/
- AMBER force field: http://ambermd.org/
- CHARMM: https://www.charmm.org/
- OpenMM examples: https://github.com/openmm/openmm/tree/master/examples
