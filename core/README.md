# Core Infrastructure

This module provides the foundational systems for skill execution, registry, and LLM integration.

## Overview

Core implements:
- **Skill registry** — metadata, dependencies, and domain mapping for 270+ scientific tools
- **Skill execution** — Python subprocess runners with JSON output parsing
- **LLM client** — Claude API integration for reasoning, skill selection, and synthesis
- **Skill selection** — LLM-powered tool choice from the full registry, based on topic and agent profile
- **Topic analysis** — LLM-driven investigation strategy determination
- **DAG execution** — dependency-aware skill chain planning

## Key Files

- **llm_client.py** — Claude API wrapper with caching and rate-limit handling
- **skill_registry.py** — Registry of 270+ skills organised into domain families: literature retrieval (`pubmed`, `arxiv`, `biorxiv-database`), protein analysis (`blast`, `uniprot`, `esm`, `alphafold-database`), small-molecule chemistry (`pubchem`, `chembl`, `rdkit`, `pytdc`), materials science (`materials`, `pymatgen`), single-cell / genomics (`scanpy`, `scvi-tools`, `clinvar-database`, `gwas-database`), and cross-domain utilities
- **skill_executor.py** — Subprocess execution with JSON output capture, error handling, and artifact creation
- **skill_selector.py** — LLM-powered skill selection: given a topic and agent profile, returns an ordered skill chain with parameters. No hardcoded routing — selection emerges from reasoning.
- **skill_dag.py** — Dependency graphs and execution planning for multi-step chains
- **topic_analyzer.py** — Determines investigation strategy from topic via LLM
- **skill_tree_searcher.py** — Hierarchical skill search and discovery across domain families

## Skill Execution Flow

```
topic → topic_analyzer (LLM) → investigation strategy
      → skill_selector (LLM)  → [skill₁, skill₂, skill₃, ...]
      → skill_executor (subprocess) → JSON output → Artifact
```

Each skill exposes a standard CLI and returns typed JSON, enabling chainable composition without string parsing.

## Registry API

```python
from core.skill_registry import SkillRegistry

registry = SkillRegistry()
skills = registry.find_by_domain("protein_characterization")
metadata = registry.get_skill_metadata("pubmed")
```

## LLM Client

```python
from core.llm_client import LLMClient

client = LLMClient()
response = client.analyze_topic("CRISPR delivery mechanisms")
insights = client.generate_insights(findings=[...])
```

## 270+ Skills

Skills are organized into nine domain families (radial map in paper Figure 1). Machine learning and genomics infrastructure form the largest categories. All skills return typed JSON — any chain is possible; which sequence an agent activates emerges from how it reasons about the scientific question.
