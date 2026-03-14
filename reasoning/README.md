# Scientific Reasoning Engine

This module implements the autonomous scientific method: gap detection, hypothesis generation, experiment design, execution, and result analysis.

## Overview

The reasoning engine transforms observations into structured investigations. It runs between heartbeat cycles to maintain a model of what the agent knows and what to investigate next.

Five components:

1. **GapDetector** — scans the agent's memory journal and the [Infinite](https://lamm.mit.edu/infinite) community feed to identify contradictions, unanswered questions, and topics absent from recent investigations
2. **HypothesisGenerator** — transforms detected gaps into candidate hypotheses using scientific pattern templates (mechanism, comparative, intervention)
3. **ExperimentDesigner** — maps each hypothesis to a skill chain by querying the tool registry with domain and entity constraints
4. **ExperimentExecutor** — runs the designed tool chain, producing artifacts and logging intermediate results
5. **ResultAnalyzer** — synthesises artifact payloads, draws conclusions graded against the original hypothesis, updates the knowledge graph

## Key Files

- **scientific_engine.py** — Main orchestrator implementing the reasoning loop
- **gap_detector.py** — Analyses community posts and memory for knowledge gaps
- **hypothesis_generator.py** — Generates testable scientific hypotheses from gaps
- **hypothesis_validator.py** — Evaluates hypothesis quality: novelty, feasibility, impact, testability
- **experiment_designer.py** — Designs multi-step skill chains for hypothesis testing
- **executor.py** — Executes experiment designs, collects results
- **analyzer.py** — Synthesises results, draws conclusions, updates knowledge graph

## Hypothesis Scoring

Candidates scored on four axes:
- **Novelty** — overlap with prior investigations (lower = higher score)
- **Feasibility** — tool coverage in registry
- **Impact** — relevance to current community activity
- **Testability** — concreteness of prediction

Highest-scoring hypothesis proceeds to experiment design.

## Reasoning Loop

```
Observe (posts, memory journal)
    ↓
Gap Detection
    ↓
Hypothesis Generation → Scoring → Select highest
    ↓
Experiment Design (select skill chain)
    ↓
Execute (run tool chain, produce artifacts)
    ↓
Analyze (synthesise findings, update knowledge graph)
```

## Integration

- **memory/** — logs all investigations and conclusions via AgentJournal and KnowledgeGraph
- **core/** — skill selection and execution
- **autonomous/** — reasoning engine called within the autonomous loop cycle
