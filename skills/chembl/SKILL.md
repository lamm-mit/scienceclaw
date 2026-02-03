---
name: chembl
description: Search ChEMBL for drug-like molecules, targets, and bioactivity data
metadata:
  openclaw:
    emoji: "💊"
    requires:
      bins:
        - python3
---

# ChEMBL Drug and Compound Lookup

Query the ChEMBL database for drug-like molecules, drug targets, and bioactivity data. ChEMBL is EBI's open database of drug discovery and medicinal chemistry.

## Overview

- Search molecules by name or ChEMBL ID
- Retrieve molecular properties, SMILES, drug indications
- Find targets and bioactivity (IC50, Ki, etc.)
- No API key required

## Usage

### Search by compound or drug name
```bash
python3 {baseDir}/scripts/chembl_search.py --query "aspirin"
```

### Get molecule by ChEMBL ID
```bash
python3 {baseDir}/scripts/chembl_search.py --chembl-id CHEMBL25
```

### Detailed output
```bash
python3 {baseDir}/scripts/chembl_search.py --query "imatinib" --format detailed
```

### Limit search results
```bash
python3 {baseDir}/scripts/chembl_search.py --query "kinase inhibitor" --max-results 5
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Compound or drug name or search term | - |
| `--chembl-id` | ChEMBL molecule ID (e.g. CHEMBL25) | - |
| `--max-results` | Max results for search | 10 |
| `--format` | Output: summary, detailed, json | summary |

## Output

- **Summary:** ChEMBL ID, pref_name, molecular formula, MW, SMILES, max_phase
- **Detailed:** Adds drug type, first approval, indications, targets
- **JSON:** Full API response

## Notes

- ChEMBL IDs look like CHEMBL25, CHEMBL1234567
- Use --query for name or text search
- Use --chembl-id when you know the exact molecule ID
