---
name: pdb
description: Search and fetch protein structures from the Protein Data Bank (PDB)
metadata:
  openclaw:
    emoji: "🔮"
    requires:
      bins:
        - python3
---

# PDB - Protein Data Bank

Search and fetch protein structures from the RCSB Protein Data Bank.

## Usage

### Search for structures:
```bash
python3 {baseDir}/scripts/pdb_search.py --query "kinase human"
```

### Get structure details:
```bash
python3 {baseDir}/scripts/pdb_search.py --pdb-id 1ATP
```

### Search by sequence:
```bash
python3 {baseDir}/scripts/pdb_search.py --sequence "MTEYKLVVVGAGGVGKSALTIQLIQ" --identity 70
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Text search query | - |
| `--pdb-id` | Specific PDB ID to fetch | - |
| `--sequence` | Sequence for similarity search | - |
| `--identity` | Minimum sequence identity % | 90 |
| `--max-results` | Maximum results | 10 |
| `--format` | Output: summary, detailed, json | summary |

## Examples

```bash
# Search for insulin structures
python3 {baseDir}/scripts/pdb_search.py --query "insulin"

# Get details for a specific structure
python3 {baseDir}/scripts/pdb_search.py --pdb-id 4HHB

# Find structures similar to a sequence
python3 {baseDir}/scripts/pdb_search.py --sequence "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH" --identity 50

# Get JSON output
python3 {baseDir}/scripts/pdb_search.py --query "p53 DNA binding" --format json
```

## Output Fields

- **PDB ID** - 4-character structure identifier
- **Title** - Structure title
- **Resolution** - X-ray resolution in Angstroms
- **Method** - Experimental method (X-RAY, NMR, EM)
- **Release Date** - When structure was released
- **Organism** - Source organism
- **Chains** - Polymer chains in structure

## Notes

- Uses RCSB PDB REST API (no authentication)
- Structures include X-ray, NMR, and cryo-EM
- Resolution shown for X-ray structures
- Links provided to 3D viewers
