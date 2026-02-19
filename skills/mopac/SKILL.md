---
name: mopac
description: Semi-empirical quantum chemistry with MOPAC. Fast QM calculations for geometry optimization, properties, activation barriers, reaction pathways. Methods PM6, PM7, PM6-D3H4X for 1000x faster than DFT. For full DFT accuracy, use ase. For classical MD, use openmm.
license: LGPL
metadata:
    skill-author: K-Dense Inc.
    domain: computational-chemistry, quantum-chemistry
---

# MOPAC Semi-Empirical Quantum Chemistry

## Overview

MOPAC provides semi-empirical quantum chemistry calculations that are ~1000x faster than DFT while maintaining reasonable accuracy for many applications. This skill enables rapid computational investigation of reaction mechanisms, transition states, activation barriers, and molecular properties. MOPAC is ideal for high-throughput screening and rapid hypothesis testing in drug discovery and materials chemistry.

## Core Capabilities

### 1. Geometry Optimization

**Molecular Structures:**

Optimize small molecules and drug-like compounds:

```python
# PM6 method (balanced speed/accuracy)
# PM7 method (improved accuracy, slightly slower)
# PM6-D3H4X (includes dispersion corrections for D3 interactions)

mopac_optimized = optimize_structure(
    smiles="CCO",
    method="PM6",
    convergence="tight"
)

# Get optimized geometry and energy
energy = mopac_optimized.get_energy()
structure = mopac_optimized.get_structure()
```

**Key Features:**
- Fast convergence (seconds to minutes)
- Suitable for molecules up to ~100 atoms efficiently
- Can handle aromatic, heterocyclic, organometallic systems
- Includes hydrogen bonding, van der Waals interactions

### 2. Transition State Finding

**Activation Barriers:**

Locate and characterize transition states:

```python
# Min-TS-Min pathway
# 1. Optimize reactant
# 2. Find transition state (TS keyword in MOPAC)
# 3. Optimize product

ts_structure = find_transition_state(
    reactant="reactant.smi",
    product="product.smi",
    method="PM6"
)

activation_barrier = ts_structure.get_energy() - reactant.get_energy()
```

**Applications:**
- Drug metabolism prediction (phase I/II mechanisms)
- Chemical reactivity assessment
- Reaction selectivity prediction
- Mechanistic hypothesis validation

### 3. Molecular Properties

**Calculate from Quantum Wavefunction:**

```python
- Dipole moment
- Polarizability
- Electronegativity
- Electrostatic potential (ESP)
- Partial charges (Mulliken, Löwdin)
- Orbital energies (HOMO, LUMO, gap)
- Hardness, softness (chemical potential)
- Reactivity indices (Fukui functions)
```

**For Drug Design:**
- Predict pKa (using COSMO solvation)
- Estimate metabolic susceptibility
- Assess chemical stability
- Identify reactive hot spots

### 4. Solvation Effects

**COSMO Implicit Solvent Model:**

Calculate properties in aqueous/organic media:

```python
# COSMO (Conductor-like Screening Model)
# Implicit solvent descriptions for:
# - Water
# - DMSO, DMF
# - Chloroform, dichloromethane
# - Alcohols

aqueous_energy = calculate_solvation(
    structure="molecule.xyz",
    solvent="water",
    method="PM6"
)

# pKa prediction from desolvation energy
```

### 5. Vibrational Analysis

**Frequencies and Thermochemistry:**

Compute IR-active vibrational modes:

```python
- Vibrational frequencies
- Infrared intensities
- Raman scattering
- Zero-point energy (ZPE)
- Enthalpy corrections
- Entropy corrections
- Gibbs free energy at any temperature
```

## MOPAC Methods

### PM6 (Parametrized Model 6)
- **Accuracy:** Good for organics, heteroatoms, hydrogen bonding
- **Speed:** Very fast (~seconds)
- **Use:** General purpose, drug discovery, screening

### PM7
- **Accuracy:** Improved over PM6 (metallorganic, transition metals)
- **Speed:** Slightly slower than PM6 (~10-30 seconds)
- **Use:** More accurate properties, metal-containing systems

### PM6-D3H4X
- **Accuracy:** Best for weak interactions (dispersion, H-bonding)
- **Speed:** ~2x PM6
- **Use:** Noncovalent interactions, supramolecular chemistry, protein-ligand docking

## Use Cases

**Drug Discovery:**
- ADMET property prediction
- Metabolite structure elucidation
- pKa/logP calculations
- Off-target toxicity prediction (reactivity-based)

**Reaction Mechanism:**
- Identify rate-limiting step
- Predict regioselectivity
- Understand stereoselectivity
- Design synthetic routes

**Materials Chemistry:**
- Conjugation in organic semiconductors
- Band gap prediction for dyes
- Hydrogen storage materials
- Supramolecular assembly design

**Chemical Stability:**
- Hydrolysis rates
- Oxidative degradation pathways
- Shelf-life prediction
- Storage condition optimization

## Integration with Other Skills

**Input:**
- SMILES from `pubchem` (convert to structures)
- Protein residues from `uniprot` (study interaction mechanisms)
- Known ligands from `chembl` (understand binding mechanisms)

**Output:**
- Transition states for mechanistic understanding
- Properties for ML model training
- Reactivity predictions for chemical screening
- Activation barriers for kinetic modeling

## Accuracy vs. DFT

| Property | MOPAC (PM6) | DFT | Error | Time (MOPAC) | Time (DFT) |
|----------|-----------|-----|-------|-------------|----------|
| Geometry | 0.02 Å | 0.01 Å | ±0.01 Å | 5 sec | 5 min |
| Energy | ±1-2 eV | ±0.1 eV | ±1 eV | 5 sec | 5 min |
| Barriers | ±2-4 kcal | ±0.5 kcal | ±2 kcal | 30 sec | 2-4 hrs |
| pKa | ±0.5 units | ±0.3 units | ±0.5 | 20 sec | 30 min |

**When to use MOPAC:**
- ✅ Fast screening (drug discovery)
- ✅ Reaction mechanism validation
- ✅ Property prediction (pKa, dipole)
- ✅ Large molecule ensembles

**When to use DFT:**
- ✅ High accuracy needed
- ✅ Weak interactions (dispersion)
- ✅ Excited state chemistry
- ✅ Periodic systems (crystals)

## Limitations

- Parameterized for specific atom types (main group + some transition metals)
- Less accurate for charged species or transition metals
- Cannot predict NMR shifts or electron density maps
- No excited states (use DFT)
- Parameterization based on training set (may have extrapolation errors)

## Example Workflow

```bash
# 1. Optimize structure
python mopac_optimize.py --smiles "CC(C)CC(N)C(=O)O" --method PM6

# 2. Calculate properties
python mopac_properties.py --structure optimized.xyz --include-frequencies

# 3. Find transition state
python mopac_transition_state.py --reactant reactant.xyz --product product.xyz

# 4. Predict pKa
python mopac_pka.py --structure molecule.xyz --solvent water

# 5. Analyze reactivity
python mopac_reactivity.py --structure molecule.xyz --method PM6-D3H4X
```

## References

- MOPAC Manual: http://openmopac.net/
- MOPAC2016 Tutorial: http://openmopac.net/MOPAC2016_Tutorial.pdf
- PM6 Paper: Stewart, J.J.P. (2007) JMC
- PM7 Paper: Stewart, J.J.P. (2013) JMC
