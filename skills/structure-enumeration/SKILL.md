---
name: structure-enumeration
description: Generate candidate crystal structures by element substitution in prototype structures
metadata:
---

# Structure Enumeration Skill

Generate candidate crystal structures by substituting elements in a prototype structure. Supports three prototype sources: Materials Project lookup, local CIF files, or building from spacegroup + Wyckoff positions.

## Scripts

### `enumerate_structures.py` — Substitute elements in a prototype

From Materials Project (for ambient-pressure phases):
```bash
python3 {baseDir}/scripts/enumerate_structures.py \
  --prototypes LaH3,CaH2 \
  --metals Y,Ca,Sc,Ce \
  --format json
```

From Wyckoff positions (for high-pressure or hypothetical phases not in MP):
```bash
python3 {baseDir}/scripts/enumerate_structures.py \
  --wyckoff '[{"name":"LaH10","spacegroup":225,"lattice":{"a":5.1},"species":["La","H","H"],"coords":[[0,0,0],[0.25,0.25,0.25],[0.118,0.118,0.118]]}]' \
  --metals Y,Ca,Sc,Ce \
  --format json
```

Multiple prototypes via Wyckoff:
```bash
python3 {baseDir}/scripts/enumerate_structures.py \
  --wyckoff '[{"name":"LaH10","spacegroup":225,"lattice":{"a":5.1},"species":["La","H","H"],"coords":[[0,0,0],[0.25,0.25,0.25],[0.118,0.118,0.118]]},{"name":"CaH6","spacegroup":229,"lattice":{"a":3.54},"species":["Ca","H"],"coords":[[0,0,0],[0.25,0,0.5]]}]' \
  --metals Y,Sc,Ce,Ba \
  --format json
```

## Parameters

| Parameter | Description |
|-----------|-------------|
| `--prototypes` | Comma-separated formulas to fetch from Materials Project (e.g. `LaH3,CaH2`). Only works for phases in MP. |
| `--mp-ids` | Comma-separated Materials Project IDs (e.g. `mp-1234,mp-5678`) |
| `--prototype-files` | Comma-separated paths to local CIF/POSCAR files |
| `--wyckoff` | JSON array of prototype specs for building from spacegroup + Wyckoff positions (see format below). Use this for high-pressure phases not in MP. |
| `--metals` | **Required.** Comma-separated target metals for substitution (e.g. `Y,Ca,Sc,Ce`) |
| `--output-dir` | Directory for output CIF files (default: `~/.scienceclaw/enumerated_structures`) |
| `--format` | `summary` \| `json` |
| `--dry-run` | Show plan without generating structures |

## Wyckoff Spec Format

Each prototype is a JSON object with:
```json
{
  "name": "LaH10",
  "spacegroup": 225,
  "lattice": {"a": 5.1},
  "species": ["La", "H", "H"],
  "coords": [[0,0,0], [0.25,0.25,0.25], [0.118,0.118,0.118]]
}
```

- `name`: label for the prototype
- `spacegroup`: international space group number
- `lattice`: `{"a": ...}` for cubic, `{"a": ..., "c": ...}` for hexagonal
- `species`: element at each Wyckoff site (first non-H element is the metal site for substitution)
- `coords`: fractional coordinates for each Wyckoff site

### Common superhydride prototypes

| Prototype | SG | SG# | Lattice | Species | Coordinates |
|-----------|-----|-----|---------|---------|-------------|
| LaH10 (clathrate) | Fm-3m | 225 | a=5.1 | La, H, H | [0,0,0], [0.25,0.25,0.25], [0.118,0.118,0.118] |
| CaH6 (sodalite) | Im-3m | 229 | a=3.54 | Ca, H | [0,0,0], [0.25,0,0.5] |
| H3S | Im-3m | 229 | a=3.09 | S, H | [0,0,0], [0.5,0,0.5] |
| YH9 | P63/mmc | 194 | a=3.6, c=5.5 | Y, H, H | [0,0,0.25], [0.167,0.333,0.25], [0.167,0.333,0.583] |

## How It Works

1. Loads each prototype structure (from MP, local file, or Wyckoff construction)
2. Identifies the metal site (heaviest non-hydrogen element)
3. For each target metal, substitutes the metal site and writes a new CIF file
4. The original prototype is also saved (with `_prototype` suffix)
5. All CIF files are written to `--output-dir`

## Output (JSON)

```json
{
  "status": "success",
  "output_dir": "/home/user/.scienceclaw/enumerated_structures",
  "prototypes_used": ["LaH10", "CaH6"],
  "metals": ["Y", "Ca", "Sc"],
  "total_generated": 6,
  "structures": [
    {
      "label": "YH10_from_LaH10",
      "formula": "YH10",
      "prototype": "LaH10",
      "metal": "Y",
      "n_atoms": 44,
      "cif_path": "/home/user/.scienceclaw/enumerated_structures/YH10_from_LaH10.cif"
    }
  ]
}
```
