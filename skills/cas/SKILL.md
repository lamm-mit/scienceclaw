---
name: cas
description: Look up chemicals in CAS Common Chemistry (name, CAS RN, SMILES, InChI; ~500k compounds)
metadata:
  openclaw:
    emoji: "⚗️"
    requires:
      bins:
        - python3
---

# CAS Common Chemistry

Query [CAS Common Chemistry](https://commonchemistry.cas.org/) for compound names, CAS Registry Numbers®, molecular formula, mass, SMILES, InChI, and experimental properties. Covers nearly 500,000 compounds (CC BY-NC 4.0).

**API access:** Request a free API key at [https://www.cas.org/services/commonchemistry-api](https://www.cas.org/services/commonchemistry-api). The script works without a key for public endpoints; if CAS requires a key, set `CAS_API_KEY` or use `~/.scienceclaw/cas_config.json`.

## Overview

- Search by compound name (supports trailing wildcard, e.g. `aspirin*`), CAS RN, SMILES, or InChI/InChIKey
- Get detail: name, formula, mass, InChI, SMILES, experimental properties (e.g. melting point, density)
- Reference: `references/cas-common-chemistry-api.md`

## Usage

### Search by name
```bash
python3 {baseDir}/scripts/cas_search.py --query "aspirin"
```

### Get detail by CAS Registry Number
```bash
python3 {baseDir}/scripts/cas_search.py --cas "50-78-2"
```

### Search with wildcard
```bash
python3 {baseDir}/scripts/cas_search.py --query "atrazin*"
```

### JSON output
```bash
python3 {baseDir}/scripts/cas_search.py --query "caffeine" --format json
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Name, SMILES, or InChI (name supports trailing *) | - |
| `--cas` | CAS Registry Number (e.g. 50-78-2) | - |
| `--max-results` | Max search results | 10 |
| `--format` | summary, detailed, json | summary |

## Output

- **Summary:** CAS RN, name, formula, molecular mass, SMILES
- **Detailed:** Adds InChI, InChIKey, experimental properties, synonyms
- **JSON:** Full API response

## Notes

- Request API access: [CAS Common Chemistry API](https://www.cas.org/services/commonchemistry-api)
- Optional: set `CAS_API_KEY` or config file if CAS requires authentication
