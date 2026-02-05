---
name: materials
description: Materials Project lookup and structure analysis (pymatgen, ASE)
metadata:
  openclaw:
    emoji: "⚛️"
    requires:
      bins:
        - python3
---

# Materials Science

Look up materials from the [Materials Project](https://materialsproject.org/) and run basic structure analysis. Uses pymatgen and optionally ASE.

## Prerequisites

**Required for full data:** Install pymatgen (recommended):
```bash
pip install pymatgen
```

**Note:** Without pymatgen, the script falls back to direct API calls but will only return `material_id` (other fields like band_gap, density, formula will be None). Install pymatgen for complete data.

**Materials Project API:** Free registration at [materialsproject.org](https://materialsproject.org/). Get an API key from the [next-gen API dashboard](https://next-gen.materialsproject.org/api). Set `MP_API_KEY` or add to `~/.scienceclaw/materials_config.json` as `{"api_key": "your_key"}`. See `references/materials-project-api.md` for details.

## Overview

- **Materials Project** — Look up material by ID (e.g. mp-149), get formula, band gap, density
- **Structure** — Parse CIF/POSCAR, basic info (lattice, formula)

## Usage

### Look up by Materials Project ID
```bash
python3 {baseDir}/scripts/materials_lookup.py --mp-id mp-149
```

### Look up with API key in env
```bash
MP_API_KEY=your_key python3 {baseDir}/scripts/materials_lookup.py --mp-id mp-149
```

### JSON output
```bash
python3 {baseDir}/scripts/materials_lookup.py --mp-id mp-149 --format json
```

## Parameters

| Parameter | Description |
|-----------|-------------|
| `--mp-id` | Materials Project ID (e.g. mp-149 for Si) |
| `--format` | summary \| json |

## References

- [Materials Project](https://materialsproject.org/)
- [pymatgen](https://pymatgen.org/)
- [ASE](https://wiki.fysik.dtu.dk/ase/)
