# Research Survey Workflow Summary

This skill activates when a prompt contains `/research-survey` and provides a structured deep-analysis methodology for academic papers.

## Core Process

The workflow operates in three main phases:

**Phase 1 - Paper Collection:** Verify prerequisite files exist in the workspace, including paper metadata JSONs, downloaded papers, reference repositories, and preparation documentation. Processing halts if required materials are missing.

**Phase 2 - Individual Paper Analysis:** For each paper (prioritized by score), the process involves:
- Reading LaTeX source code, focusing on methodology and architecture sections
- Extracting core methods, mathematical formulas, and innovation points
- Mapping formulas to reference code implementations in designated repositories
- Documenting findings in structured markdown notes

**Phase 3 - Synthesis:** Compile individual analyses into a comprehensive report featuring comparative tables, technical recommendations, and a formula-to-code mapping index.

## Key Requirements

The workflow mandates reading original .tex files rather than abstracts, including at least one mathematical formula per paper analysis. When reference repositories exist, code mapping becomes mandatory—connecting formulas to actual implementations with file paths and line numbers.

The output produces per-paper notes and a synthesis report containing methodology comparisons, complexity analysis, and architectural recommendations grounded in reference implementations.
