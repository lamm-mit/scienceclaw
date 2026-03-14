# Scientific Reasoning Engine

This module implements the autonomous scientific method: gap detection, hypothesis generation, experiment design, execution, and result analysis.

## Overview

The reasoning engine transforms observations into structured investigations:

1. **Gap Detection** - Identifies unanswered questions from posts and memory
2. **Hypothesis Generation** - Creates testable predictions with mechanistic reasoning
3. **Experiment Design** - Selects tools and parameters to test hypotheses
4. **Execution** - Runs designed experiments via skill executor
5. **Analysis** - Draws conclusions and updates knowledge graph

## Key Files

- **scientific_engine.py** - Main orchestrator implementing the reasoning loop
- **gap_detector.py** - Analyzes community posts for knowledge gaps
- **hypothesis_generator.py** - Generates testable scientific hypotheses
- **hypothesis_validator.py** - Evaluates hypothesis quality and testability
- **experiment_designer.py** - Designs multi-step tool chains for hypothesis testing
- **executor.py** - Executes experiment designs, collects results
- **analyzer.py** - Synthesizes results, draws conclusions, updates memory

## Reasoning Loop

```
Observe (posts, memory)
    ↓
Gap Detection (what's unknown?)
    ↓
Hypothesis Generation (testable predictions)
    ↓
Hypothesis Scoring (novelty, feasibility, impact, testability)
    ↓
Experiment Design (select tools, plan execution)
    ↓
Execute (run tool chains)
    ↓
Analyze (synthesize findings, update knowledge graph)
    ↓
Conclude (mechanistic insights, forward-looking questions)
```

## API Quick Reference

```python
from reasoning.scientific_engine import ScientificReasoningEngine

engine = ScientificReasoningEngine(agent_name="BioAgent-7")

# Detect gaps in memory and recent posts
gaps = engine.detect_gaps()

# Generate hypotheses from gaps
hypotheses = engine.generate_hypotheses(gap=gaps[0])

# Design and execute experiments
result = engine.conduct_investigation(hypothesis=hypotheses[0])
```

## Integration

Integrates with:
- **memory/** - Logs investigations and conclusions
- **core/** - Skill selection and execution
- **autonomous/** - Investigation orchestration

## Scoring

Hypotheses scored on: novelty (not explored), feasibility (testable), impact (meaningful findings), testability (has verifiable predictions).
