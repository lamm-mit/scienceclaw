---
name: candidate-ranking
description: Rank peptide variants using stability heuristics and hotspot protection; emit top candidates.
metadata:
  skill-author: ScienceClaw demo
---

# Candidate Ranking

Ranks candidates based on a simple weighted score:
- stability_score (heuristic)
- penalty for hotspot mutations if hotspot positions provided
- penalty for edit distance vs reference sequence if provided

## CLI
```bash
python3 scripts/run.py --reference AGCKNFFWKTFTSC --sequences AGCKNFFWKTFTSC AGCKNFFLKTFTSC
```

