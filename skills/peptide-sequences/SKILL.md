---
name: peptide-sequences
description: Generate a curated peptide sequence set for a target (e.g., somatostatin analogs) to seed MSA, conservation, and design branches.
metadata:
  skill-author: ScienceClaw demo
---

# Peptide Sequences

Seed a peptide-sequence artifact with a small, curated set of therapeutically relevant peptide scaffolds.

Designed for protein/peptide design demos where you want an explicit upstream `peptide_sequences` artifact that downstream skills can branch from:

- `peptide-msa` → `sequence_alignment`
- `conservation-map` → `conservation_map`
- `mutation-generator` → `mutation_space`
- `peptide-stability` → `stability_scores`
- `candidate-ranking` → `ranked_candidates`

## CLI

```bash
python3 scripts/run.py --query "SSTR2"
python3 scripts/run.py --query "Somatostatin receptor 2" --format json
```

