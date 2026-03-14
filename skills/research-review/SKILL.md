# Claude Code Research Review Guide

This document outlines a comprehensive peer review workflow for ML research implementations, with three key phases:

## Core Review Process

**Initial Validation**: The workflow first checks prerequisites—ensuring `ml_res.md` exists (from implementation phase) alongside planning and survey documents. If missing, it halts with a clear directive: "需要先运行 /research-implement 完成代码实现" (complete implementation first).

**Atomic Concept Verification**: Rather than general code inspection, the review extracts "atomic academic concepts" from survey documents—individual formulas, loss functions, normalization layers. Each concept gets mapped to expected code locations, then verified line-by-line. A checklist table documents whether each concept is correctly implemented (✓), missing (✗), or oversimplified.

## Performance Assessment (New Standard)

The workflow now treats performance validation as mandatory, not optional. After 2-epoch validation, it calculates loss reduction percentage and compares metrics against random baselines. If loss decreases less than 5% or accuracy stays within ±10% of random chance, it flags "性能异常" (performance anomaly).

This triggers **Step 5b—Algorithm Reflection**: adjusting hyperparameters (learning rate, batch size, normalization) up to 2 iterations, with quantified before/after comparisons. Changes are restricted to training configuration; core algorithm logic remains protected.

## Safeguards

- **Anti-Drift Check**: Each iteration rereads original survey and plan documents to ensure modifications align with intended research design
- **Execution Verification**: Confirms training actually ran by checking elapsed time against dataset size and model parameters
- **Dataset Authenticity**: Requires real data loaded (not synthetic tensors), verified by executing data pipelines
- **Three Verdicts**: `PASS` (all checks + reasonable performance), `NEEDS_REVISION` (code bugs), `BLOCKED` (unfixable issues after attempts)
