# Artifacts System

This module implements versioned, addressable artifacts that ground scientific findings in concrete, integrity-checked records.

## Overview

Every skill invocation produces an `Artifact` — a JSON-based record containing:
- **artifact_id**: Globally unique UUID
- **artifact_type**: Classification (e.g., `pubmed_results`, `protein_data`, `admet_prediction`)
- **producer_agent**: Authenticated agent name
- **skill_used**: The tool invoked (e.g., `pubmed`, `tdc`, `blast`)
- **payload**: Unchanged skill JSON output
- **investigation_id**: Links to InvestigationTracker topic
- **timestamp**: ISO 8601 UTC
- **content_hash**: SHA256 integrity check

## Storage

Artifacts are appended to `~/.scienceclaw/artifacts/{agent_name}/store.jsonl` (JSONL format, one JSON object per line).

## Key Files

- **artifact.py** - Core `Artifact` dataclass and `ArtifactStore` API
- **mutator.py** - Mutation operators for artifact modification
- **reactor.py** - Orchestrates multi-step artifact transformations
- **needs.py** - Dependency/requirement tracking
- **discovery_rubric.py** - Evaluation criteria for artifact quality

## Address Scheme

Artifacts are addressed as: `artifact://{agent_name}/{artifact_id}`

## Domain Gating

Agent domains (derived from `preferred_tools`) restrict which artifact types can be posted to collaborative sessions. Maps skills to allowed artifact types via `SKILL_DOMAIN_MAP`.

## API Quick Reference

```python
from artifacts.artifact import ArtifactStore

store = ArtifactStore("CrazyChem")
artifact = store.create(artifact_type="pubmed_results", payload={...})
artifacts = store.list(artifact_type="pubmed_results", limit=10)
```

See `artifact.py` for full API.
