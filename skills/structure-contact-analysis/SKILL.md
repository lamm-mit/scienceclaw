---
name: structure-contact-analysis
description: Identify peptide–protein contact hotspots from a PDB structure (local file or fetched from RCSB) and emit binding hotspot positions.
metadata:
  skill-author: ScienceClaw demo
---

# Structure Contact Analysis

Given a PDB ID (or a local PDB file), compute residue-level contacts between a short peptide chain and a protein chain.

Outputs include:
- inferred peptide chain + sequence
- contact counts per peptide residue
- top hotspot positions suitable for protecting during mutation generation

## CLI

```bash
python3 scripts/run.py --pdb-id 7T10
python3 scripts/run.py --query "SSTR2 octreotide receptor"
python3 scripts/run.py --pdb-path tests/fixtures/mini_complex.pdb
```

