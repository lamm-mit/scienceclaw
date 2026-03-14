# Continuous Knowledge Metabolism - Summary

This workflow automates a **daily research paper ingestion and synthesis cycle**. Here's the operational flow:

## Core Process

**Setup Check:** Requires initialized `metabolism/config.json` with `currentDay >= 1`.

**Five-stage cycle:**

1. **Search** — 5-day sliding window queries via arXiv and OpenAlex, deduplicating against `processed_ids`
2. **Read** — Extract methodology, conclusions, and knowledge connections from new papers
3. **Update** — Integrate findings into `metabolism/knowledge/` files (max 200 lines per topic, with compression of older content when needed)
4. **Hypothesize** — Generate new research hypotheses only when patterns genuinely emerge; skip if no insights warrant it
5. **Log** — Record daily metrics and increment `currentDay`

## Key Constraints

- "不捏造论文中未出现的事实性声明" (don't fabricate claims absent from source papers)
- Preserve citations and evidence trails during knowledge compression
- Never force hypothesis generation
- Always read current file state before modifications

The system emphasizes **incremental, honest knowledge building** over raw output volume.
