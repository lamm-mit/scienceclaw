# Agent Memory System

The memory system allows agents to track investigations, maintain a journal, and build a knowledge graph across multiple heartbeat cycles.

---

## Quick Start

```python
from memory import AgentJournal, InvestigationTracker, KnowledgeGraph

# Initialize memory
journal = AgentJournal("MyAgent")
tracker = InvestigationTracker("MyAgent")
kg = KnowledgeGraph("MyAgent")

# Log an observation
journal.log_observation(
    content="Found CRISPR paper on LNP delivery",
    source="pmid:12345678",
    tags=["CRISPR", "delivery"]
)

# Form hypothesis
journal.log_hypothesis(
    hypothesis="LNP composition affects delivery efficiency",
    motivation="Multiple papers show variable results"
)

# Create investigation
inv_id = tracker.create_investigation(
    hypothesis="LNP composition affects delivery",
    goal="Identify optimal lipid ratios",
    planned_experiments=["pubmed_search", "chembl_search"]
)
```

---

## CLI Interface

```bash
# Check agent stats
python3 memory_cli.py --agent MyAgent stats

# View recent journal entries
python3 memory_cli.py --agent MyAgent journal --recent 10

# Check active investigations
python3 memory_cli.py --agent MyAgent investigations --active

# Search knowledge graph
python3 memory_cli.py --agent MyAgent graph --search "CRISPR"
```

---

## Storage

Memory is stored as plain-text JSON files in your home directory:

```
~/.scienceclaw/
├── journals/MyAgent/journal.jsonl       # All observations and hypotheses
├── investigations/MyAgent/tracker.json   # Investigation tracking
└── knowledge/MyAgent/graph.json         # Knowledge graph
```

You can inspect these files directly!

---

## Common Patterns

### Pattern 1: Multi-Cycle Investigation

```python
# Heartbeat 1: Start investigation
inv_id = tracker.create_investigation(
    hypothesis="...",
    planned_experiments=["pubmed", "chembl", "tdc"]
)

# Heartbeat 2: Continue (fetch active investigations)
active = tracker.get_active_investigations()
inv = active[0]
tracker.add_experiment(inv['id'], experiment_data)

# Heartbeat 3: Complete
tracker.mark_complete(
    inv_id,
    conclusion="Found optimal concentration is 50mol%",
    confidence="high"
)
```

### Pattern 2: Knowledge Accumulation

```python
# After each discovery
kg.add_finding(
    finding="DLin-MC3-DMA at 50mol% optimal for muscle delivery",
    related_concepts=[
        {"name": "DLin-MC3-DMA", "type": "compound"},
        {"name": "muscle tissue", "type": "organism"}
    ]
)

# Detect contradictions
contradictions = kg.find_contradictions()
```

---

## Components

| Component | Purpose | File |
|-----------|---------|------|
| **AgentJournal** | Record observations, hypotheses, results | `journal.py` |
| **InvestigationTracker** | Track multi-cycle investigations | `investigation_tracker.py` |
| **KnowledgeGraph** | Build semantic knowledge network | `knowledge_graph.py` |
| **CLI** | Command-line inspection interface | `tools/cli.py` |

---

## Testing

```bash
# Run test suite
python3 tests/test_memory.py

# Check integration with heartbeat
python3 memory/examples/integration_example.py
```

---

## See Also

- [README.md](../README.md) - Main ScienceClaw documentation
- [Full docstrings](journal.py) - For detailed API reference
