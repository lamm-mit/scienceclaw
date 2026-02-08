# ScienceClaw Memory System

Persistent memory infrastructure for autonomous science agents.

## Overview

The memory system provides three core components:

1. **AgentJournal** - Append-only JSONL log of observations, hypotheses, experiments, and conclusions
2. **InvestigationTracker** - Multi-step investigation management across heartbeat cycles
3. **KnowledgeGraph** - Graph database of scientific concepts and relationships

## Directory Structure

```
memory/
├── __init__.py              # Package exports
├── journal.py               # AgentJournal implementation
├── investigation_tracker.py # InvestigationTracker implementation
├── knowledge_graph.py       # KnowledgeGraph implementation
├── README.md                # This file
│
├── tools/                   # CLI and utilities
│   ├── __init__.py
│   └── cli.py               # Memory inspection CLI
│
└── examples/                # Usage examples
    ├── __init__.py
    ├── usage_examples.py    # Basic usage patterns
    └── integration_example.py # Heartbeat integration
```

## Quick Start

### Basic Usage

```python
from memory import AgentJournal, InvestigationTracker, KnowledgeGraph

# Initialize for an agent
journal = AgentJournal("BioAgent-7")
tracker = InvestigationTracker("BioAgent-7")
kg = KnowledgeGraph("BioAgent-7")

# Log an observation
journal.log_observation(
    content="Interesting post about CRISPR delivery",
    observation="LNP formulation shows 3x improvement",
    source="post_123"
)

# Start an investigation
inv_id = tracker.create_investigation(
    hypothesis="DLin-MC3-DMA improves muscle delivery",
    goal="Test LNP formulation hypothesis",
    priority="high"
)

# Add knowledge
kg.add_concept("DLin-MC3-DMA", type="compound")
kg.add_relationship("DLin-MC3-DMA", "improves", "CRISPR delivery")
```

### Using the CLI

Inspect agent memory from the command line:

```bash
# View recent journal entries
./memory_cli journal --agent BioAgent-7 --recent 10

# Show active investigations
./memory_cli investigations --agent BioAgent-7 --active

# Search knowledge graph
./memory_cli graph --agent BioAgent-7 --search "CRISPR"

# Get memory statistics
./memory_cli stats --agent BioAgent-7

# Export all memory
./memory_cli export --agent BioAgent-7 --format json
```

Or use Python module syntax:
```bash
python3 -m memory.tools.cli journal --agent BioAgent-7 --recent 10
```

### Examples

Run example code to see memory system in action:

```bash
# Basic usage patterns
python3 memory/examples/usage_examples.py

# Heartbeat integration pattern
python3 memory/examples/integration_example.py
```

## Storage

Memory is stored in `~/.scienceclaw/`:

```
~/.scienceclaw/
├── journals/
│   └── {agent_name}/
│       └── journal.jsonl        # Append-only log
│
├── investigations/
│   └── {agent_name}/
│       └── tracker.json         # Active/completed investigations
│
└── knowledge/
    └── {agent_name}/
        └── graph.json           # Concepts and relationships
```

## Components

### AgentJournal

Append-only log of all agent activities:

```python
journal = AgentJournal("BioAgent-7")

# Log different entry types
journal.log_observation(content="...", observation="...", source="...")
journal.log_hypothesis(content="...", hypothesis="...", testable=True)
journal.log_experiment(content="...", tool="blast", parameters={}, results={})
journal.log_conclusion(content="...", conclusion="...", confidence=0.8)

# Query journal
recent = journal.get_recent_entries(limit=10)
by_type = journal.get_entries_by_type("hypothesis")
searched = journal.search_entries("CRISPR")
```

### InvestigationTracker

Multi-step investigation management:

```python
tracker = InvestigationTracker("BioAgent-7")

# Create investigation
inv_id = tracker.create_investigation(
    hypothesis="Aspirin crosses BBB",
    goal="Test BBB prediction",
    priority="medium"
)

# Add experiments
tracker.add_experiment(inv_id, {
    "tool": "pubchem",
    "parameters": {"query": "aspirin"},
    "results_summary": "SMILES: CC(=O)OC1=..."
})

# Mark complete
tracker.mark_complete(inv_id, conclusion="Hypothesis supported")

# Check for duplicates
is_dup = tracker.is_duplicate_investigation("Aspirin crosses BBB")
```

### KnowledgeGraph

Graph database of scientific knowledge:

```python
kg = KnowledgeGraph("BioAgent-7")

# Add concepts
kg.add_concept("aspirin", type="compound")
kg.add_concept("BBB", type="biological_barrier")

# Add relationships
kg.add_relationship("aspirin", "crosses", "BBB", confidence=0.87)

# Query
concepts = kg.get_related_concepts("aspirin")
neighbors = kg.get_neighbors("aspirin")
shortest = kg.find_shortest_path("aspirin", "brain")
```

## Integration with Autonomous Loop

The autonomous heartbeat daemon uses memory to:

1. **Check for duplicates** - Avoid re-investigating topics
2. **Track progress** - Resume multi-step investigations
3. **Learn from history** - Build on past findings
4. **Maintain context** - Remember conversations and interactions

Example integration:

```python
from memory import AgentJournal, InvestigationTracker, KnowledgeGraph
from autonomous import AutonomousLoopController

# Initialize
journal = AgentJournal(agent_name)
tracker = InvestigationTracker(agent_name)
kg = KnowledgeGraph(agent_name)

controller = AutonomousLoopController(agent_profile)

# Run heartbeat with memory
controller.run_heartbeat_cycle()
# → Automatically uses memory for deduplication and context
```

## Testing

```bash
# Run memory system tests
python3 tests/test_memory.py

# Or use pytest
pytest tests/test_memory.py -v
```

## Performance

- **Journal**: O(1) append, O(n) search
- **Investigations**: O(1) lookup by ID
- **Knowledge Graph**: O(edges) for traversal

For typical agent workloads (<10K entries), performance is excellent.

## File Formats

### Journal (JSONL)
```json
{"timestamp": "2026-02-08T12:00:00", "type": "observation", "content": "..."}
{"timestamp": "2026-02-08T12:05:00", "type": "hypothesis", "hypothesis": "..."}
```

### Investigations (JSON)
```json
{
  "investigations": {
    "inv_123": {
      "hypothesis": "...",
      "status": "active",
      "experiments": [...]
    }
  }
}
```

### Knowledge Graph (JSON)
```json
{
  "concepts": {
    "aspirin": {"type": "compound", "added": "2026-02-08T12:00:00"}
  },
  "relationships": [
    {"from": "aspirin", "to": "BBB", "type": "crosses", "confidence": 0.87}
  ]
}
```

## Best Practices

1. **Use descriptive content** - Make journal entries searchable
2. **Set priorities** - Mark important investigations as "high"
3. **Add metadata** - Include source URLs, timestamps, agent info
4. **Regular cleanup** - Archive old investigations periodically
5. **Backup storage** - Memory files are precious

## Troubleshooting

**"Permission denied"**
- Check `~/.scienceclaw/` directory permissions
- Run: `chmod 700 ~/.scienceclaw`

**"File not found"**
- Memory is created on first use
- Run setup: `python3 setup.py --quick`

**Large file sizes**
- Archive old journal entries: `journal.archive_old_entries(days=90)`
- Compact knowledge graph: `kg.prune_low_confidence_edges(threshold=0.3)`

## API Reference

See docstrings in:
- `memory/journal.py` - AgentJournal API
- `memory/investigation_tracker.py` - InvestigationTracker API
- `memory/knowledge_graph.py` - KnowledgeGraph API

## Contributing

When adding features to the memory system:

1. Add to appropriate module (journal, tracker, or graph)
2. Update examples in `memory/examples/`
3. Add tests to `tests/test_memory.py`
4. Update this README

---

**Status**: Production-ready, actively used by Phase 3 autonomous loop.
