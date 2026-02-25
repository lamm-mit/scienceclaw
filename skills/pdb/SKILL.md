---
name: pdb
description: "3D protein structure search via RCSB PDB. Input MUST be a protein/gene name (e.g. 'KRAS', 'EGFR', 'BTK') or a 4-character PDB ID (e.g. '6OIM'). Returns zero results for drug/chemistry phrases such as 'covalent inhibitors' or 'warhead selectivity'. Strip all drug qualifiers and pass only the target protein name or PDB ID."
metadata:
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

## Query Limitations — Read Before Using

PDB stores **experimentally determined 3D structures**. Queries must target proteins or genes with known deposited structures. Abstract or chemistry-only queries return zero results.

| ❌ Fails | ✅ Works |
|---|---|
| "BTK covalent inhibitor" | "BTK" or "Bruton tyrosine kinase" |
| "warhead optimization" | "1K2P" (direct PDB ID) |
| "ADMET prediction" | "EGFR kinase inhibitor complex" |

**Tips for avoiding zero results:**
- Use short protein names or gene names: `"BTK"`, `"p53"`, `"EGFR"`
- Use a specific PDB ID (`--pdb-id 3K54`) when you already have one from UniProt cross-refs
- If zero results, broaden the query — e.g., `"kinase"` instead of `"covalent kinase inhibitor BTK"`
- Not all proteins have PDB entries; check UniProt cross-refs first

## Notes

- Uses RCSB PDB REST API (no authentication)
- Structures include X-ray, NMR, and cryo-EM
- Resolution shown for X-ray structures
- Links provided to 3D viewers
