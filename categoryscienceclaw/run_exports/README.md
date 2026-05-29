# CategoryScienceClaw Run Exports

This directory contains formalized CategoryScienceClaw run outputs.

## Current Export

`structure_contact_7T10_formalized_20260528/` is a post-run formalization of the ScienceClaw 7T10 structure-contact/mechanics trace.

Audit status: **PASS**

| Metric | Count |
| --- | ---: |
| Objects | 20 |
| Morphisms | 17 |
| Artifacts | 32 |
| Certificates | 31 |
| Events | 63 |
| Open downstream needs | 6 |

## Main Files

| File | Purpose |
| --- | --- |
| `schema.json` | Typed object and morphism schema for the formalized run. |
| `artifacts.jsonl` | Typed artifacts with original ScienceClaw IDs, parent links, metadata, and source hashes. |
| `needs.index.jsonl` | Open downstream needs for future decentralized agents. |
| `events.jsonl` | Append-only post-run import, certificate, and need-advertisement events. |
| `agents.json` | Agents inferred from artifact producers and their morphisms. |
| `certificates/` | Post-run proof certificates for typed provenance, validation, and publication edges. |

## Visuals

- `structure_contact_7T10_summary.md`: human-readable run summary.
- `structure_contact_7T10_graph.mmd`: Mermaid graph of the formalized categorical trace.
