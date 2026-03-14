# Research Pipeline Skill Overview

This is an **orchestrator skill** that manages a complete ML research workflow without performing the actual research tasks itself.

## Core Identity

The orchestrator is a **scheduler and validator**, not a researcher. It:
- Checks for output files
- Reads summaries from prior phases
- Dispatches work to sub-agents via `sessions_spawn`
- Validates deliverables

As stated: "你**不**分析论文...你**不**写代码" (does not analyze papers, does not write code).

## Key Execution Rule

**Sequential, single-dispatch constraint:** Each response can call `sessions_spawn` at most once. No parallel task launching. The orchestrator must wait for sub-agent completion before advancing to the next phase.

## Six-Phase Pipeline

1. **Literature Survey** → `papers/_meta/` directory with JSON files
2. **Deep Survey** → `survey_res.md` with method comparisons
3. **Implementation Plan** → `plan_res.md` with 4 sections (Dataset/Model/Training/Testing)
4. **Implementation** → `project/run.py` and `ml_res.md` with results
5. **Review** → `judge_v*.md` with PASS/BLOCKED verdict (up to 3 iterations)
6. **Full Experiment** → `experiment_res.md` with ablation studies

## Task Dispatch Format

`sessions_spawn` requires:
- `task`: Starts with `/skill-name`, includes workspace path, context summary (2–5 lines), and expected output
- `label`: Phase identifier
- `runTimeoutSeconds`: Recommended 1800

The tool is called **after** reading prior outputs to bridge context between independent sub-agent sessions.
