---
name: mutation-generator
description: Generate conservative vs aggressive peptide mutation variants given a reference sequence and optional protected/hotspot positions.
metadata:
  skill-author: ScienceClaw demo
---

# Mutation Generator

Creates a small mutation space for a peptide scaffold.

- Conservative: substitutions within broad physicochemical groups
- Aggressive: larger substitutions, multiple mutations

## CLI
```bash
python3 scripts/run.py --sequence AGCKNFFWKTFTSC --strategy conservative --n-variants 8
python3 scripts/run.py --sequence AGCKNFFWKTFTSC --strategy aggressive --max-mutations 3 --n-variants 12
```

