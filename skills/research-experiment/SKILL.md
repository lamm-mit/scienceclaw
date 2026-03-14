# Research Experiment Skill Summary

This skill defines a workflow for conducting comprehensive research experiments in machine learning projects. Here's the concise breakdown:

## Core Purpose
Execute full training runs, ablation studies, and iterative supplementary experiments with systematic analysis at each stage.

## Key Workflow Steps

1. **Full Training**: Run the model with production epoch counts from the research plan, recording all metrics and loss values.

2. **Result Analysis**: Evaluate convergence, overfitting patterns, and training stability from the output logs.

3. **Ablation Studies**: Conduct 2-3 component removal experiments (2 epochs each) to measure individual contribution.

4. **Iterative Analysis & Supplementary Experiments** (2 rounds):
   - Analyze current results and propose targeted follow-up experiments
   - Execute sensitivity analysis, visualizations, robustness tests, or baseline comparisons
   - Re-analyze findings and repeat

5. **Final Report**: Compile comprehensive results across all experiment categories into a structured markdown document.

## Critical Constraints

- Modify **only epoch counts and experiment parameters**, never core algorithm logic
- All reported numbers must come from actual execution output
- Two rounds of supplementary experimentation are mandatory
- Requires validation that prior research review verdict shows "PASS"

## Output Deliverables
- Complete experiment report with full results, ablations, and supplementary findings
- Round-by-round analysis documents tracking the iterative discovery process
