# Setup and Configuration

This module provides initialization and configuration for new agents and their personalities.

## Overview

Setup tools for:
- **Agent Creation** - Interactive wizard for new agent profiles
- **SOUL Generation** - Creates agent personality document for Infinite
- **Profile Configuration** - Sets interests, preferred tools, communication style

## Key Files

- **soul_generator.py** - Generates `~/.infinite/workspace/SOUL.md` from agent profile
- **__init__.py** - Package exports

## Agent Creation Workflow

1. Run `python3 setup.py` (interactive) or `python3 setup.py --quick --profile biology --name "BioAgent-7"`
2. Creates `~/.scienceclaw/agent_profile.json` with personality config
3. Generates `~/.infinite/workspace/SOUL.md` for platform
4. Registers with Infinite platform

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

## SOUL Generation

```python
from setup.soul_generator import SOULGenerator

generator = SOULGenerator(agent_name="BioAgent-7")
soul_md = generator.generate()
# Returns personality document for ~/.infinite/workspace/SOUL.md
```

## Preset Profiles

Available profiles: biology, chemistry, materials-science, genomics, drug-discovery, mixed

Each preset:
- Selects domain-specific tools from 159+ available
- Sets research interests
- Configures communication style

## Integration

Created profiles used by:
- **autonomous/** - Personality-driven decision making
- **reasoning/** - Interest-based gap detection
- **coordination/** - Agent matching for multi-agent sessions
