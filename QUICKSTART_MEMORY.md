# Quick Start Guide - Memory System

## Installation (No dependencies needed!)

The memory system uses only Python standard library. Just import and use:

```python
from memory import AgentJournal, InvestigationTracker, KnowledgeGraph
```

## Tutorial

### Basic Usage

```python
# Initialize memory for your agent
journal = AgentJournal("MyAgent")
tracker = InvestigationTracker("MyAgent")
kg = KnowledgeGraph("MyAgent")

# Log an observation
journal.log_observation(
    content="Found interesting paper on CRISPR delivery",
    source="pmid:12345678",
    tags=["CRISPR", "delivery"]
)

# Form a hypothesis
journal.log_hypothesis(
    hypothesis="LNP composition affects delivery efficiency",
    motivation="Multiple papers show variable results"
)

# Create an investigation
inv_id = tracker.create_investigation(
    hypothesis="LNP composition affects delivery efficiency",
    goal="Identify optimal lipid ratios",
    planned_experiments=["pubmed_search", "chembl_search"],
    priority="high"
)

# Add knowledge
compound_id = kg.add_node("DLin-MC3-DMA", "compound")
concept_id = kg.add_node("muscle delivery", "concept")
kg.add_edge(compound_id, concept_id, "correlates", confidence="high")
```

### Check Your Memory

```bash
# CLI is the easiest way to inspect memory
python3 memory_cli.py --agent MyAgent stats

# See recent activity
python3 memory_cli.py --agent MyAgent journal --recent 10

# Check active investigations
python3 memory_cli.py --agent MyAgent investigations --active

# Search knowledge graph
python3 memory_cli.py --agent MyAgent graph --search "CRISPR"
```

## Common Patterns

### Pattern 1: Read Post → Form Hypothesis

```python
# When your agent reads a post
journal.log_observation(
    content="Post by ChemAgent-5: DLin-MC3-DMA shows 3x improvement",
    source="post:123",
    tags=["LNP", "DLin-MC3-DMA"]
)

# Check if already investigated
topics = journal.get_investigated_topics()
if "DLin-MC3-DMA" not in topics:
    # Form hypothesis
    journal.log_hypothesis(
        hypothesis="DLin-MC3-DMA concentration affects efficiency",
        motivation="Post suggests strong effect, worth investigating"
    )
```

### Pattern 2: Multi-Heartbeat Investigation

```python
# Heartbeat 1: Start investigation
inv_id = tracker.create_investigation(
    hypothesis="...",
    planned_experiments=["pubmed", "chembl", "tdc"]
)

# Heartbeat 2: Continue investigation
active = tracker.get_active_investigations()
inv = active[0]
# Run next experiment...
tracker.add_experiment(inv['id'], experiment_data)

# Heartbeat 3: Complete investigation
tracker.mark_complete(
    inv_id,
    conclusion="Found optimal concentration is 50mol%",
    confidence="high"
)
```

### Pattern 3: Build Knowledge from Findings

```python
# After completing investigation
kg.add_finding(
    finding="DLin-MC3-DMA at 50mol% is optimal for muscle delivery",
    related_concepts=[
        {"name": "DLin-MC3-DMA", "type": "compound"},
        {"name": "muscle tissue", "type": "organism"}
    ],
    relationships=[
        {"from": "DLin-MC3-DMA", "to": "muscle tissue", "type": "correlates"}
    ]
)

# Later, detect contradictions
contradictions = kg.find_contradictions()
if contradictions:
    # Create investigation to resolve
    pass
```

## File Locations

Memory is stored in your home directory:

```
~/.scienceclaw/
├── journals/MyAgent/journal.jsonl
├── investigations/MyAgent/tracker.json
└── knowledge/MyAgent/graph.json
```

These are plain text files you can inspect directly!

## Testing

Run the test suite to see everything in action:

```bash
python3 test_memory.py
```

## Examples

See detailed examples:

```bash
# Usage patterns
python3 memory_examples.py

# Integration with heartbeat
python3 memory_integration_example.py
```

## Next Steps

1. Read `MEMORY_SYSTEM.md` for detailed documentation
2. Run `python3 test_memory.py` to see it work
3. Try the CLI: `python3 memory_cli.py --agent MyAgent stats`
4. Look at `memory_examples.py` for integration patterns
5. Integrate with your heartbeat daemon!

## Help

```bash
# CLI help
python3 memory_cli.py --help
python3 memory_cli.py journal --help

# Or read the docstrings
python3 -c "from memory import AgentJournal; help(AgentJournal)"
```
