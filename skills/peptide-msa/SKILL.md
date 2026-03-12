---
name: peptide-msa
description: Perform a simple multiple-sequence alignment (MSA) for short peptides and return aligned sequences + consensus.
metadata:
  skill-author: ScienceClaw demo
---

# Peptide MSA

Lightweight MSA intended for peptides (≈6–40 aa). Produces:

- `aligned_sequences` (list of gapped strings)
- `aligned_json` (JSON string of `aligned_sequences`, safe to pass via argv)
- `consensus` (gapped consensus string)

## CLI

```bash
python3 scripts/run.py --sequences AGCKNFFWKTFTSC FCFWKTCT
python3 scripts/run.py --query "AGCKNFFWKTFTSC;FCFWKTCT"
```
