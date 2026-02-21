---
name: nistwebbook
description: Look up chemical data from NIST Chemistry WebBook (thermochemistry, spectra, properties)
metadata:
---

# NIST Chemistry WebBook

Query the [NIST Chemistry WebBook](https://webbook.nist.gov/chemistry/) for thermochemical, spectral, and property data. Data are from NIST Standard Reference Database 69.

## Overview

- Search by compound name, chemical formula, CAS Registry Number, or InChI/InChIKey
- Retrieve thermochemistry, IR/MS/UV-Vis spectra, gas chromatography, and basic properties
- Optional: install `nistchempy` for full programmatic search; otherwise script prints WebBook URLs for manual lookup

## Usage

### Search by name (requires nistchempy)
```bash
python3 {baseDir}/scripts/nistwebbook_search.py --query "water"
```

### Look up by CAS number (requires nistchempy)
```bash
python3 {baseDir}/scripts/nistwebbook_search.py --cas "7732-18-5"
```

### Get WebBook URL only (no nistchempy needed)
```bash
python3 {baseDir}/scripts/nistwebbook_search.py --query "methane" --url-only
```

### Limit results
```bash
python3 {baseDir}/scripts/nistwebbook_search.py --query "ethanol" --max-results 3
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Compound name or formula | - |
| `--cas` | CAS Registry Number (e.g. 7732-18-5) | - |
| `--max-results` | Max compounds to return | 5 |
| `--url-only` | Only print NIST WebBook search URL (no nistchempy) | false |
| `--format` | summary or json | summary |

## Output

- **Summary:** Name, formula, CAS RN, molecular weight; links to thermochemistry/spectra on WebBook
- **JSON:** Structured data when using nistchempy
- Without nistchempy: script prints the WebBook search URL so users can open it in a browser

## Notes

- Install for full search: `pip install nistchempy` (also needs requests, bs4, pandas)
- NIST does not provide an official API; nistchempy is an unofficial wrapper
- Reference: [NIST Chemistry WebBook](https://webbook.nist.gov/chemistry/)
