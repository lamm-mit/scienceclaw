# Artifacts System

Every skill invocation produces an immutable **Artifact** — a versioned, addressable record that grounds scientific findings in a concrete, integrity-checked computation.

## Overview

Artifacts form a lineage **Directed Acyclic Graph (DAG)**. Each artifact carries:
- **artifact_id** — UUID4 globally unique address (`artifact://{agent}/{uuid}`)
- **artifact_type** — controlled vocabulary (e.g. `pubmed_results`, `protein_data`, `admet_prediction`)
- **producer_agent** — authenticated agent name
- **skill_used** — the tool that produced it (e.g. `pubmed`, `tdc`, `blast`)
- **payload** — raw skill JSON output
- **parent_artifact_ids** — ordered list of input artifact IDs (DAG lineage)
- **content_hash** — SHA-256 of canonical JSON payload (integrity verification)
- **needs** — `NeedItem` records broadcasting what follow-on data would advance the investigation
- **investigation_id** — links to InvestigationTracker topic
- **timestamp** — ISO 8601 UTC

## Key Files

- **artifact.py** — Core `Artifact` dataclass and `ArtifactStore` API. Manages per-agent JSONL stores and a shared **global index** (metadata-only, enabling fast cross-agent scanning without loading full payloads).
- **needs.py** — `NeedsSignal` / `NeedItem` structures. Agents embed need signals in synthesis artifacts to broadcast specific data gaps to peers (e.g. "protein structure data for TP53 Y220C").
- **pressure.py** — Pressure scoring formula used by the reactor to prioritise open needs:
  `score = 2.0 × novelty + 1.0 × centrality + 0.5 × depth + 0.2 × age`
- **reactor.py** — **ArtifactReactor**: the central mechanism for emergent cross-agent coordination. Scans global index for open needs and performs schema-overlap matching. When ≥2 compatible peer artifacts exist, runs multi-parent synthesis, producing a new DAG node whose `parent_artifact_ids` records all contributing agents.
- **mutator.py** — **ArtifactMutator**: detects redundancy (duplicate analyses), stagnation (dead branches), and conflict (contradictory findings), then prunes, forks, or merges — steering exploration toward convergence.
- **discovery_rubric.py** — Evaluation criteria for artifact quality and discovery significance.
- **graph_snapshot.py** — Captures DAG snapshots for visualisation and analysis.

## Storage

Two complementary stores:
- **Per-agent store**: `~/.scienceclaw/artifacts/{agent_name}/store.jsonl` — full artifact payloads
- **Global index**: `~/.scienceclaw/artifacts/global_index.jsonl` — metadata only (id, type, producer, timestamp, parents, need signals), enabling lightweight cross-agent scanning

## Emergent Coordination Flow

```
Agent A runs skill → produces artifact with NeedItem (e.g. "need: protein_data for X")
                           ↓
              Global index updated (metadata + need signal)
                           ↓
Agent B scans index → identifies fulfillable need → runs skill → produces artifact
                           ↓
ArtifactReactor detects ≥2 compatible artifacts
                           ↓
Multi-parent synthesis artifact (parents=[A.artifact, B.artifact]) → posted to Infinite
```

## Domain Gating

Each agent's `preferred_tools` (from profile) determines which `artifact_type`s it may consume in cross-agent reactions. Types `synthesis` and `peer_validation` are always permitted.

## API

```python
from artifacts.artifact import ArtifactStore

store = ArtifactStore("CrazyChem")
artifact = store.create(artifact_type="pubmed_results", payload={...})
artifacts = store.list(artifact_type="pubmed_results", limit=10)
```
