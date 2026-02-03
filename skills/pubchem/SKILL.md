---
name: pubchem
description: Search PubChem for chemical compounds, properties, and identifiers
metadata:
  openclaw:
    emoji: "🧪"
    requires:
      bins:
        - python3
---

# PubChem Compound Lookup

Query the PubChem database for chemical compounds, molecular properties, SMILES, InChI, and related data. PubChem is NCBI's open chemistry database.

## Overview

- Search compounds by name or identifier
- Retrieve molecular formula, weight, SMILES, InChI, InChIKey
- Find related compounds and synonyms
- No API key required (rate limit: 5 requests/second)

## Usage

### Search by compound name:
```bash
python3 {baseDir}/scripts/pubchem_search.py --query "aspirin"
```

### Get compound by CID:
```bash
python3 {baseDir}/scripts/pubchem_search.py --cid 2244
```

### Get detailed properties:
```bash
python3 {baseDir}/scripts/pubchem_search.py --cid 2244 --format detailed
```

### Search with max results:
```bash
python3 {baseDir}/scripts/pubchem_search.py --query "caffeine" --max-results 5
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Compound name or search term | - |
| `--cid` | PubChem Compound ID | - |
| `--max-results` | Max results for search | 10 |
| `--format` | Output: summary, detailed, json | summary |

## Output

- **Summary:** CID, name, molecular formula, molecular weight, SMILES
- **Detailed:** Adds InChI, InChIKey, synonyms, related CIDs
- **JSON:** Full API response

## Notes

- Rate limit: 5 requests per second (no API key)
- Use --cid for exact compound when you know the ID
- Use --query for name or text search
