# Research Implement Workflow Summary

The `research-implement` skill is a structured protocol for transforming research plans into executable code. Here are the key aspects:

## Core Purpose
This workflow converts a completed research plan into a "fully runnable project" with real execution results—no fabricated outcomes allowed.

## Required Inputs
- `plan_res.md` from `/research-plan` (mandatory)
- `survey_res.md` from `/research-survey` (optional reference)

## Execution Flow

**Project Structure:** Organizes code into `model/`, `data/`, `training/`, `testing/`, `utils/`, plus `run.py` entry point.

**Implementation Order:** Requirements → data pipeline → model architecture → loss/training → evaluation → main script.

**Environment:** Uses `uv venv` for isolated Python environments (never global pip).

## Critical Verification Requirement

> "All values must come from code execution output. Execution failure gets reported as failure."

The `run.py` script must emit `[RESULT]` lines capturing metrics like `train_loss`, `val_metric`, `elapsed`, and `device`.

## Output Deliverable

`ml_res.md` reports actual results directly cited from execution logs, with `⚠️ UNVERIFIED` tags for any values that couldn't be confirmed.

**Key constraint:** Maximum 3 retries before failure reporting; no data fabrication under any circumstance.
