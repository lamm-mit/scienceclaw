---
name: investigation-plotter
description: Generate investigation-specific figures from the local artifact graph (post-run plotting agent).
metadata:
  skill-author: ScienceClaw demo
---

# Investigation Plotter

Creates a compact, *investigation-specific* figure set from `~/.scienceclaw/artifacts/**/store.jsonl` for a given
`investigation_id`. This is intended to run **after** the multi-agent investigation completes.

Outputs PNG files into `~/.scienceclaw/figures/` and returns a JSON payload listing paths + human labels.

## CLI

```bash
python3 scripts/run.py --investigation-id sstr2_example_run
python3 scripts/run.py --query sstr2_example_run   # alias
```

