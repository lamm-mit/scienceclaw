---
name: qmmm-adaptive
description: QM/MM hybrid simulations with adaptive sampling for enzyme mechanisms and reaction dynamics. Combines quantum mechanics (reactive center) with molecular mechanics (protein/solvent) for accurate transition state and reaction pathway calculations. Supports metadynamics, umbrella sampling, and accelerated MD for enhanced conformational sampling.
license: LGPL
metadata:
    skill-author: K-Dense Inc.
    domain: computational-chemistry, enzyme-mechanisms, computational-biology
---

# QM/MM Adaptive Dynamics Simulations

## Overview

QM/MM (Quantum Mechanics/Molecular Mechanics) hybrid simulations enable accurate computational investigation of enzyme mechanisms, chemical reactions in biological environments, and reaction pathways. This skill combines quantum mechanical accuracy for reactive regions with classical force fields for the surrounding protein and solvent, enabling study of phenomena inaccessible to pure classical or pure quantum approaches.

Adaptive sampling techniques (metadynamics, umbrella sampling, accelerated MD) overcome energy barriers and efficiently explore reaction coordinates, making QM/MM practical for computational drug discovery and enzyme engineering.

## Core Capabilities

### 1. QM/MM Setup and Equilibration

**Hybrid System Preparation:**

Build QM/MM systems with defined quantum and classical regions:

```python
from qmmm import QMMMSystem

# Define QM region (reaction center)
qm_atoms = ["C1", "C2", "N3", "O4"]  # Reactive atoms
qm_method = "MOPAC"  # or ORCA, TeraChem for higher accuracy

# Define MM region (protein + solvent)
mm_forcefield = "AMBER14"

# Create hybrid system
system = QMMMSystem(
    structure="enzyme_complex.pdb",
    qm_atoms=qm_atoms,
    qm_method=qm_method,
    mm_forcefield=mm_forcefield,
    qm_charge=0,
    qm_multiplicity=1,
    buffer_distance=15  # Å from QM center
)

# Equilibrate in stages
system.equilibrate_qm_region(steps=5000)     # Fix MM atoms
system.equilibrate_hybrid(steps=10000)       # Allow coupling
system.equilibrate_full(steps=50000)         # Full system
```

**Key Parameters:**
- QM region size (3-30 atoms typically)
- Link atom treatment (capping vs. effective)
- Electrostatic embedding (mechanical vs. electronic)
- Boundary handling

### 2. Metadynamics - Explore Reaction Coordinate

**Free Energy Landscape Calculation:**

Map reaction pathways and identify transition states:

```python
# Define collective variable (reaction coordinate)
cv = ReactionCoordinate(
    atoms=["C1", "C2"],
    type="distance"  # or angle, dihedral, custom
)

# Run metadynamics
metad = Metadynamics(
    system=qmmm_system,
    cv=cv,
    sigma=0.1,           # Width of Gaussian hills
    height=5.0,          # Energy height (kcal/mol)
    stride=100,          # Add hill every N steps
    temperature=300,     # K
    timestep=1.0         # fs
)

trajectory = metad.run(steps=100000)  # 100 ps with ~1000 hills

# Get free energy profile
free_energy = trajectory.get_free_energy()
barriers = free_energy.analyze_barriers()
```

**Outputs:**
- Free energy profile along reaction coordinate
- Transition state geometry and energy
- Multiple transition pathways (if present)
- Diffusion coefficient along coordinate

### 3. Umbrella Sampling - Precise Barrier Calculation

**Constrained MD for PMF Calculation:**

Systematically sample reaction coordinate windows:

```python
# Define windows along reaction coordinate
windows = [(1.5 + i*0.1) for i in range(20)]  # 1.5 Å to 3.5 Å

umbrella = UmbrellaSampling(
    system=qmmm_system,
    cv=cv,
    windows=windows,
    force_constant=100.0,  # kcal/mol/Å²
    timestep=1.0,
    temperature=300
)

# Run each window (can be parallelized)
umbrella.run_windows(
    equilibration=5000,   # 5 ps equilibration per window
    production=20000,     # 20 ps production per window
    save_frequency=100,   # Save every 0.1 ps
    n_parallel=4          # Run 4 windows in parallel
)

# Analyze using WHAM
free_energy = umbrella.analyze_wham()
```

**Advantages:**
- Higher resolution along coordinate
- Precise barrier heights (±0.5 kcal/mol)
- Error estimation via bootstrap
- Umbrella integration for rate constants

### 4. Accelerated MD (aMD) - Escape Barriers

**Enhanced Sampling via Potential Energy Boost:**

Accelerate sampling by reducing energy barriers:

```python
amd = AcceleratedMD(
    system=qmmm_system,
    boost_type="dual",        # Boost both dihedral + total energy
    e_threshold=10.0,         # Boost below E+10 kcal/mol
    alpha_dihedral=5.0,       # Dihedral boost strength
    alpha_total=10.0,         # Total energy boost strength
    timestep=2.0,
    temperature=300
)

trajectory = amd.run(steps=200000)  # 400 ps with acceleration

# Reweight trajectory to remove boost
free_energy = trajectory.reweight_by_boost_energy()
```

**Applications:**
- Escape local energy minima
- Sample multiple conformational states
- Identify transient intermediates
- Transition pathway discovery

### 5. Transition State Finding

**Locate and Characterize TS Structures:**

```python
# From metadynamics trajectory
ts_finder = TransitionStateFinder(
    metad_trajectory=metad_traj,
    free_energy_surface=fe_profile
)

# Find TS structure (highest energy on MEP)
ts_structure = ts_finder.find_ts(
    refine=True,
    opt_method="L-BFGS"
)

# Characterize TS
ts_analysis = ts_structure.analyze()
print(f"TS Energy: {ts_analysis['energy']:.2f} kcal/mol")
print(f"Barrier height: {ts_analysis['barrier_forward']:.2f} kcal/mol")
print(f"Barrier height (reverse): {ts_analysis['barrier_reverse']:.2f} kcal/mol")
print(f"TS geometry verified: {ts_analysis['verified']}")
```

### 6. Enzyme Mechanism Studies

**Multi-Step Reaction Mechanisms:**

Study sequential bond breaking/forming:

```python
# Example: Serine protease reaction mechanism
# Step 1: Nucleophilic attack (Ser195 on substrate)
# Step 2: Tetrahedral intermediate formation
# Step 3: Acyl-enzyme formation
# Step 4: Water activation and acyl hydrolysis

steps = [
    {
        "name": "Nucleophilic attack",
        "cv": Distance(["Ser195-OG", "C1-substrate"]),
        "expected_barrier": 12.0  # kcal/mol
    },
    {
        "name": "Proton transfer",
        "cv": Distance(["His57-NE", "Proton"]),
        "expected_barrier": 8.0
    },
    {
        "name": "Acylation",
        "cv": Distance(["Ser195-C", "Peptide-N"]),
        "expected_barrier": 5.0
    },
    {
        "name": "Deacylation",
        "cv": Distance(["Water-O", "Acyl-C"]),
        "expected_barrier": 15.0
    }
]

# Run each step with QM/MM
for step in steps:
    result = qmmm.study_step(step)
    print(f"{step['name']}: {result['barrier']:.1f} kcal/mol")
```

## QM Methods (QM Region)

### Fast (for MD)
- **MOPAC PM6-D3H4X** - Semi-empirical, very fast
- **DFTB+** - Density functional tight binding
- **GFN2-xTB** - Extended tight binding

### Balanced (for TS finding)
- **ORCA B3LYP/6-31G(d)** - DFT, good accuracy
- **TeraChem B3LYP** - GPU-accelerated DFT
- **MOPAC PM7** - Improved semi-empirical

### High Accuracy (for benchmarks)
- **ORCA DLPNO-CCSD(T)** - Wave function theory
- **MOLPRO** - High-level quantum chemistry

## MM Methods (MM Region)

- **AMBER14** - Standard biomolecular FF
- **CHARMM36** - High accuracy for proteins
- **OPLS-AA** - Good for organics

## Sampling Techniques

| Technique | Speed | Accuracy | Use Case |
|-----------|-------|----------|----------|
| **Metadynamics** | Fast | Good | Explore landscape, find TS guess |
| **Umbrella Sampling** | Medium | Excellent | Precise barriers, PMF convergence |
| **aMD** | Very Fast | Medium | Escape local minima, sample states |
| **Targeted MD** | Fast | Good | Pull along specific pathway |
| **Steered MD** | Very Fast | Medium | Non-equilibrium pulling experiments |

## Use Cases

**Enzyme Mechanism Elucidation:**
- Identify transition states
- Calculate barrier heights
- Propose mechanistic models
- Explain selectivity and reactivity

**Drug Metabolism Prediction:**
- Predict metabolic pathways
- Identify reactive metabolites
- Calculate oxidation barriers
- Assess bioactivation risk

**Protein Engineering:**
- Design improved catalysts
- Predict activity mutations
- Optimize substrate selectivity
- Lower activation barriers

**Chemical Reactivity in Proteins:**
- Metal coordination mechanisms (metalloproteases, P450 oxidations)
- Radical chemistry (peroxidases, LOX)
- Photochemistry (retinal isomerization, photolyase)
- Hydrolysis mechanisms (proteases, esterases)

## Integration with Other Skills

**Input:**
- Protein structures from `pdb` skill
- Ligand/substrate SMILES from `pubchem`
- Enzyme sequences from `uniprot`
- Literature mechanistic insights from `pubmed`

**Output:**
- TS structures for further analysis by `ase`
- Barriers for publication/comparison
- Mechanistic models for hypothesis testing
- Reactive intermediates for `openmm` MD validation

## Performance Characteristics

**Computational Cost:**
- QM/MM equilibration: ~1-4 hours (500 atoms, 100 ps)
- Metadynamics (100 ps): ~8-24 hours
- Umbrella sampling (20 windows × 20 ps): ~40-120 hours
- aMD (400 ps): ~4-12 hours

**Hardware:**
- CPU: Excellent for MOPAC/DFTB based QM/MM
- GPU: Required for TeraChem or faster convergence
- Parallelization: Windows/replicas parallelize perfectly

## Limitations

- QM region size limited (~30 atoms for DFT)
- Boundary effects at QM/MM interface
- Charge transfer between QM/MM regions approximated
- Polarization effects sometimes underestimated
- Requires quality starting structure

## Example Workflow

```bash
# 1. Prepare QM/MM system
python qmmm_setup.py --pdb enzyme_complex.pdb \
    --qm-atoms "catalytic_residues.txt" \
    --qm-method MOPAC --force-field AMBER14

# 2. Equilibrate
python qmmm_equilibrate.py --system prepared_qmmm.inp \
    --temperature 300 --steps 50000

# 3. Run metadynamics to explore
python qmmm_metad.py --system equilibrated.inp \
    --cv "distance C1 C2" --duration 100 \
    --output metad_landscape.txt

# 4. Find transition state
python qmmm_ts_finder.py --metad-traj metadynamics.dcd \
    --refine true --output ts_structure.pdb

# 5. Run umbrella sampling for precise barrier
python qmmm_umbrella.py --system equilibrated.inp \
    --cv "distance C1 C2" --windows 20 \
    --window-width 0.1 --output pmf.txt

# 6. Analyze mechanism
python qmmm_mechanism.py --ts-structure ts_structure.pdb \
    --umbrella-pmf pmf.txt --report mechanism.md
```

## References

- QM/MM review: Senn & Thiel (2007) Angew. Chem.
- Metadynamics: Laio & Parrinello (2002) PNAS
- Umbrella sampling: Torrie & Valleau (1977) J. Comp. Phys
- aMD: Hamelberg et al. (2004) J. Chem. Phys
- ORCA: Neese (2012) Wiley Interdiscip. Rev. Comput. Mol. Sci.
- TeraChem: Ufimtsev & Martinez (2008) J. Chem. Phys
