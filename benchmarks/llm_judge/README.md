# Artifact Reactor — LLM Judge Benchmark

Results and evaluation pipeline for **Artifact Reactor**, an agent architecture
compared against six baselines on 12 scientific research tasks spanning materials
science, kinase biology, and cheminformatics.

## Contents

| Path | What it is |
|---|---|
| [`paper_tasks/`](paper_tasks/) | Raw per-system run outputs for tasks T1–T12. |
| [`llm_judge_evaluation.ipynb`](llm_judge_evaluation.ipynb) | Notebook that scores every run with an LLM judge and produces the results table/plot. |
| [`llm_judge_results.json`](llm_judge_results.json) | Output of the notebook: one JSON record per (task, system) pair, judge scores included. |
| [`llm_judge_bar_plot.pdf`](llm_judge_bar_plot.pdf) | Rendered bar chart from the notebook. |

### `paper_tasks/T1__* … T12__*/`

Twelve task folders. Each holds 7 result files — one per system, all run on `gpt-5-2`
with `seed42`:

- `single_model_direct` — one-shot prompt, no tools.
- `single_agent_with_tools` — one agent with tool access, no decomposition.
- `non_signaling_multi_agent` — multiple agents, no shared coordination signal.
- `centralized_orchestration` — a central orchestrator dispatching to sub-agents.
- `artifact_reactor_no_provenance` — full system, ablating provenance tracking.
- `artifact_reactor_no_parallel` — full system, ablating parallel execution.
- `artifact_reactor` — the full proposed system.

Tasks cover materials science (crystal band gaps, solar cell candidates, topological
insulators), kinase/pathway biology (EGFR/BRAF/CDK2, TP53 isoforms, PTEN/PIK3CA/AKT1,
VEGFR2 resistance), cheminformatics (Lipinski Ro5, CNS drug-likeness, kinase ADMET,
polypharmacology), and an ML literature-trend task.

### `llm_judge_evaluation.ipynb`

Reads the 12 × 7 = 84 result files, extracts each system's final answer (for
`artifact_reactor*` variants this means isolating the `[analysis_result ...]` synthesis
blocks from the raw tool-call dump), and sends each to a Claude judge that scores
**completeness** and **evidence_grounding** (1–5) against a fixed rubric. Combines
those with the harness's programmatic `product_quality_score`, writes the full table to
`llm_judge_results.json`, and renders the comparison as a grouped bar chart
(`llm_judge_bar_plot.pdf`) plus a text summary table.

Requires an `ANTHROPIC_API_KEY` (loaded via `../api_key.env` relative to this folder)
and `paper_tasks/` present alongside the notebook. Runtime is dominated by the judge
loop (~84 sequential API calls, ~6 minutes).
