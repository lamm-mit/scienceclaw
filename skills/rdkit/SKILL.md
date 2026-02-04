---
name: rdkit
description: Cheminformatics with RDKit — descriptors, SMARTS, substructure, MCS
metadata:
  openclaw:
    emoji: "🧬"
    requires:
      bins:
        - python3
---

# RDKit Cheminformatics

Compute molecular descriptors, run SMARTS matches, substructure search, and maximum common substructure (MCS) using [RDKit](https://www.rdkit.org/).

## Prerequisites

```bash
pip install rdkit
```

Or use a conda env that has RDKit (e.g. `conda install -c conda-forge rdkit`).

## Overview

- **Descriptors** — MolWt, LogP, TPSA, HBD/HBA, ring count, etc.
- **SMARTS** — Match a SMARTS pattern against a SMILES
- **Substructure** — Check if one molecule is a substructure of another
- **MCS** — Maximum common substructure of two molecules

## Usage

### Descriptors (from SMILES)
```bash
python3 {baseDir}/scripts/rdkit_tools.py descriptors --smiles "CC(=O)OC1=CC=CC=C1C(=O)O"
```

### SMARTS match
```bash
python3 {baseDir}/scripts/rdkit_tools.py smarts --smiles "c1ccccc1O" --pattern "c[c,n,o]"
```

### Substructure check
```bash
python3 {baseDir}/scripts/rdkit_tools.py substructure --smiles "CC(=O)Oc1ccccc1C(=O)O" --sub "c1ccccc1"
```

### MCS (two molecules)
```bash
python3 {baseDir}/scripts/rdkit_tools.py mcs --smiles "CC(=O)Oc1ccccc1C(=O)O" "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
```

## Parameters

| Subcommand   | Description |
|-------------|-------------|
| `descriptors` | Compute descriptors for one SMILES |
| `smarts`     | Match SMARTS pattern (--smiles, --pattern) |
| `substructure` | Molecule contains substructure? (--smiles, --sub) |
| `mcs`        | Max common substructure of two SMILES |

Use `--format json` for machine-readable output.
