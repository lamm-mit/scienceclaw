---
name: conservation-map
description: Compute per-position conservation/entropy for an aligned peptide MSA (aligned sequences).
metadata:
  skill-author: ScienceClaw demo
---

# Conservation Map

Compute conservation for each alignment column from an MSA.

Accepts either:
- `--aligned-json` (preferred): a JSON list of aligned sequences (safe even if sequences contain `-`)
- `--query`: JSON list or `;`-separated raw/aligned sequences (raw sequences will be aligned internally)

## CLI
```bash
python3 scripts/run.py --aligned-json '["AGC--K","AGCFFK"]'
python3 scripts/run.py --query "AGCKNFFWKTFTSC;FCFWKTCT"
```
