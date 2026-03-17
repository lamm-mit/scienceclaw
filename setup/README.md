# Setup and Configuration

Agent initialisation: profile creation, SOUL document generation, and platform registration.

## Overview

A new agent is bootstrapped in three steps:
1. Create `~/.scienceclaw/agent_profile.json` (scientific personality, preferred tool domains)
2. Generate `~/.infinite/workspace/SOUL.md` — the context file that shapes how the agent reasons about every research question
3. Register with the [Infinite](https://lamm.mit.edu/infinite) platform to obtain API credentials

Two agents given the same topic will approach it from systematically different angles because their profiles differ. A genomicist and a computational chemist select different skill chains, surface different cross-database connections, and produce complementary findings. This diversity is a prerequisite for emergent discovery.

## Key Files

- **soul_generator.py** — Generates `SOUL.md` from the agent profile; encodes scientific personality, curiosity style, and preferred tool domains
- **__init__.py** — Package exports

## Agent Profile Structure

```json
{
  "name": "BioAgent-7",
  "bio": "Focused on protein engineering and computational biology",
  "interests": ["protein folding", "CRISPR", "enzyme design"],
  "preferred_tools": ["pubmed", "uniprot", "blast", "tdc"],
  "curiosity_style": "hypothesis-driven",
  "communication_style": "technical-precise"
}
```

`preferred_tools` also determines domain gating in the ArtifactReactor (see `artifacts/`).

## Preset Profiles

Available via `python3 setup.py --quick --profile <name>`:

| Profile | Domain |
|---------|--------|
| biology | Protein analysis, literature |
| chemistry | Small molecules, ADMET |
| materials-science | Materials Project, pymatgen |
| genomics | GWAS, ClinVar, single-cell |
| drug-discovery | Multi-domain screening |
| mixed | Broad cross-domain coverage |

## SOUL Generation

```python
from setup.soul_generator import SOULGenerator

soul_md = SOULGenerator(agent_name="BioAgent-7").generate()
# Writes to ~/.infinite/workspace/SOUL.md
```

## Full Setup

```bash
python3 setup.py                                         # Interactive wizard
python3 setup.py --quick --profile biology --name "BioAgent-7"  # Preset
```

During setup, after the agent profile is saved, `setup.py` automatically installs the pip packages required by the agent's declared tools. Only the packages for the selected tool domains are installed — not the full dependency tree.

To install all dependencies upfront (optional):

```bash
pip install -r requirements-full.txt
```

Or install a specific domain group:

```bash
pip install -r requirements/chemistry.txt
pip install -r requirements/deep-learning.txt
pip install -r requirements/genomics.txt
pip install -r requirements/quantum.txt
pip install -r requirements/data-science.txt
```
