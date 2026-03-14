# Core Infrastructure

This module provides the foundational systems for skill execution, registry, and LLM integration.

## Overview

Core implements:
- **Skill execution** - Python subprocess runners for 159+ scientific tools
- **Skill registry** - Metadata, dependencies, and expertise mapping
- **LLM client** - Claude API integration for reasoning and analysis
- **Skill selection** - Intelligent tool choice based on topic/hypothesis
- **Topic analysis** - LLM-driven investigation strategy determination

## Key Files

- **llm_client.py** - Claude API wrapper, caching, rate limits
- **skill_executor.py** - Subprocess execution, JSON output parsing, error handling
- **skill_registry.py** - Skill metadata, expertise domains, discovery API
- **skill_selector.py** - LLM-powered skill selection from registry
- **skill_dag.py** - Dependency graphs and execution planning
- **topic_analyzer.py** - Determines investigation strategy from topic (LLM)
- **skill_tree_searcher.py** - Hierarchical skill search and discovery

## Skill Execution Flow

```
topic → topic_analyzer (LLM) → investigation_strategy
       → skill_selector (LLM) → [skill1, skill2, skill3]
       → skill_executor (subprocess) → JSON results → artifact
```

## Registry API

```python
from core.skill_registry import SkillRegistry

registry = SkillRegistry()
skills = registry.find_by_domain("protein_characterization")
metadata = registry.get_skill_metadata("pubmed")
```

## LLM Integration

```python
from core.llm_client import LLMClient

client = LLMClient(cache_dir="~/.scienceclaw/llm_cache")
response = client.analyze_topic("CRISPR delivery mechanisms")
result = client.generate_insights(findings=[...])
```

## 159+ Available Skills

Organized by domain: sequence-analysis, structure-prediction, compound-properties, literature-mining, data-visualization, and more. Full list in `skill_registry.py`.
