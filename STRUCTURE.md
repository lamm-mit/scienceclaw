# ScienceClaw Project Structure

Clean, organized structure for autonomous science agents.

## Directory Layout

```
scienceclaw/
├── setup.py                    # Main setup script (simplified)
├── setup/                      # Setup components (NEW)
│   ├── __init__.py
│   ├── soul_generator.py       # Generates SOUL.md for OpenClaw
│   ├── agent_creator.py        # Agent profile creation (TODO)
│   └── platform_registration.py # Platform registration (TODO)
│
├── autonomous/                 # Autonomous operation (REORGANIZED)
│   ├── __init__.py
│   ├── heartbeat_daemon.py     # Main 6-hour heartbeat loop (MOVED)
│   ├── loop_controller.py      # Investigation cycle orchestrator
│   ├── start_daemon.sh         # Start daemon (MOVED)
│   └── stop_daemon.sh          # Stop daemon (MOVED)
│
├── memory/                     # Phase 1: Memory system
│   ├── __init__.py
│   ├── journal.py              # Agent journal (JSONL log)
│   ├── investigation_tracker.py # Investigation tracking
│   └── knowledge_graph.py      # Knowledge graph
│
├── reasoning/                  # Phase 2: Scientific reasoning
│   ├── __init__.py
│   ├── scientific_engine.py    # Main orchestrator
│   ├── gap_detector.py         # Gap detection
│   ├── hypothesis_generator.py # Hypothesis generation
│   ├── experiment_designer.py  # Experiment design
│   ├── executor.py             # Experiment execution
│   └── analyzer.py             # Result analysis
│
├── coordination/               # Phase 5: Multi-agent coordination
│   ├── __init__.py
│   └── session_manager.py      # Collaborative sessions
│
├── utils/                      # Utilities
│   ├── __init__.py
│   ├── post_parser.py          # Parse scientific posts
│   └── tool_selector.py        # Tool recommendation
│
├── skills/                     # 18 scientific tools
│   ├── blast/, pubmed/, uniprot/, pdb/, sequence/, arxiv/
│   ├── pubchem/, chembl/, tdc/, cas/, nistwebbook/, rdkit/
│   ├── materials/, datavis/, websearch/
│   └── infinite/, sciencemolt/ # Platform clients
│
└── tests/                      # Test suites
    ├── test_reasoning_phase2.py
    ├── test_phase3.py
    ├── test_phase5.py
    └── test_integration.py
```

## Key Changes

### 1. Setup Modularization

**Before:**
- Single 1005-line `setup.py` file
- All logic mixed together

**After:**
- Clean 200-line `setup.py` entry point
- Modular `setup/` package:
  - `soul_generator.py` - SOUL.md generation (cleanly separated)
  - `agent_creator.py` - Profile creation (TODO: extract from setup.py.backup)
  - `platform_registration.py` - Registration logic (TODO: extract)

**Benefits:**
- Easier to understand and maintain
- SOUL.md generation can be tested independently
- Reusable components

### 2. Autonomous Directory

**Before:**
- `heartbeat_daemon.py` in root
- `start_daemon.sh`, `stop_daemon.sh` in root
- `loop_controller.py` in `autonomous/`

**After:**
- All autonomous components in `autonomous/`:
  - `heartbeat_daemon.py` - Main daemon (moved)
  - `loop_controller.py` - Investigation orchestrator
  - `start_daemon.sh` - Start script (moved, updated paths)
  - `stop_daemon.sh` - Stop script (moved)

**Benefits:**
- Logical grouping of related functionality
- Cleaner root directory
- Easier to find daemon-related files

### 3. SOUL.md Generation

**Before:**
- Embedded in 400-line function in setup.py
- Hard to test or reuse

**After:**
- Standalone `setup/soul_generator.py` module
- Clean `generate_soul_md(profile)` function
- Can be imported and tested independently
- Includes test function

**Benefits:**
- More maintainable
- Testable
- Reusable (can regenerate SOUL.md anytime)

## Usage

### Setup a new agent

```bash
# Quick setup (randomized)
python3 setup.py --quick

# Quick setup with specific preset
python3 setup.py --quick --profile biology --name "BioBot-7"

# Interactive setup
python3 setup.py
```

### Run autonomous heartbeat

```bash
# One cycle
./autonomous/start_daemon.sh once

# Background process
./autonomous/start_daemon.sh background

# Systemd service (auto-start on boot)
./autonomous/start_daemon.sh service

# Stop
./autonomous/stop_daemon.sh
```

### Regenerate SOUL.md

```python
from setup.soul_generator import save_soul_md
import json

# Load profile
with open("~/.scienceclaw/agent_profile.json") as f:
    profile = json.load(f)

# Regenerate SOUL.md
save_soul_md(profile)
```

## Migration Notes

### For existing agents

If you have an agent already set up:

1. **No changes needed** - your profile and config files are unchanged
2. **Daemon scripts moved** - use `./autonomous/start_daemon.sh` instead of `./start_daemon.sh`
3. **setup.py works the same** - simplified but compatible

### Old files preserved

- `setup.py.backup` - Original 1005-line setup.py (kept for reference)

## Future Improvements

### TODO: Complete modularization

Extract remaining setup.py logic into modules:

1. **agent_creator.py**
   - Interactive profile creation
   - Profile validation
   - Display functions

2. **platform_registration.py**
   - Moltbook registration
   - Infinite registration
   - Submolt creation
   - Subscription management

3. **setup_cli.py**
   - Argparse configuration
   - Main CLI logic
   - Help text

### Benefits after full modularization

- Each module <300 lines
- Comprehensive unit tests
- Easy to extend with new platforms
- Reusable components for other tools

## Testing

```bash
# Test SOUL.md generation
python3 setup/soul_generator.py

# Test integration (all phases)
python3 test_integration.py

# Test specific phase
python3 tests/test_phase3.py
python3 tests/test_phase5.py
```

## Summary

The reorganization makes ScienceClaw more maintainable and professional:

✅ **Modular** - Components separated by function  
✅ **Organized** - Related files grouped logically  
✅ **Clean** - Root directory uncluttered  
✅ **Testable** - Each component can be tested independently  
✅ **Maintainable** - Smaller files, clearer responsibilities  

**Status**: Partially complete. Core reorganization done, full modularization in progress.
