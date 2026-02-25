---
name: chembl
description: "Small-molecule drug lookup by exact drug name or ChEMBL ID. Query MUST be a single drug name or ID — 1 to 3 words maximum. Valid examples: 'sotorasib', 'imatinib', 'ibrutinib', 'CHEMBL25', 'AMG 510'. If the topic is 'sotorasib KRAS G12C', the correct query is 'sotorasib'. If the topic is 'BTK inhibitors in CLL', search PubMed first to get a specific drug name, then query ChEMBL with that name. Strip protein names, mutation labels, and mechanism words — pass only the compound name."
metadata:
---

# ChEMBL Drug and Compound Lookup

Query the ChEMBL database for drug-like molecules, drug targets, and bioactivity data. ChEMBL is EBI's open database of drug discovery and medicinal chemistry.

## IMPORTANT: Query must be a specific drug or compound name

ChEMBL searches by molecule name. **Always use a specific drug name or compound identifier** (e.g. `sotorasib`, `ibrutinib`, `CHEMBL1873475`). Do NOT pass topic phrases like "kinase inhibitor resistance" — these will return garbage results. If the topic mentions multiple drugs, pick the most specific one.

## When NOT to Use This Skill

Do NOT use ChEMBL when the query is any of the following — it will return large biologics, cell therapy entries, or protein records with `MW=?`, `logP=?`, `phase=-1`:

- **Biological therapies**: cell therapies, stem cells, antibodies, CAR-T, biologics (e.g. "allogeneic mesenchymal stem cells", "anti-PD1 antibody")
- **Mechanism or concept phrases**: "proximity-induced degradation", "PROTAC linker", "covalent warhead", "undruggable target"
- **Disease names without a specific drug**: "Alzheimer's disease", "pancreatic cancer", "KRAS oncogenesis"
- **Pathway or process terms**: "mTOR signaling", "ubiquitin-proteasome pathway", "kinase cascade"

**Correct workflow for mechanism-based topics (e.g. PROTAC, degrader, proximity):**
1. Search PubMed first with the mechanism query
2. Extract specific small-molecule compound names from the papers (e.g. "ARV-110", "dBET6", "MZ1")
3. Then query ChEMBL with those specific names

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
