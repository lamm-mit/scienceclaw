# Idea Generation Skill Summary

This workflow generates **5 research ideas grounded in literature**, following this process:

## Key Steps

1. **Check Workspace** – Audit existing papers in `$W/papers/`
2. **Plan Strategy** – Decide whether to use current collection or search for more papers
3. **Acquire Resources** – Either delegate to `/research-collect` (100+ papers) or run quick searches
4. **Analyze Literature** – Extract contributions, methods, limitations, and gaps from papers
5. **Generate Ideas** – Create 5 distinct concepts using different strategies (combination, simplification, generalization, constraint relaxation, architecture innovation)
6. **Score & Enhance** – Rate ideas by novelty/feasibility/impact; detail the top candidate with math and implementation roadmap
7. **Code Mapping** – Link concepts to reference implementations
8. **Summarize** – Document all findings and next steps

## Core Principle

"Ideas MUST be grounded in actual papers, not generated from model knowledge." Each idea requires citations (≥2 papers by arXiv ID).

## Output Location

Results save to `$W/ideas/` as individual markdown files, plus consolidated summary.

## Integration

Works with `/research-collect` (upstream) and `/research-pipeline` (downstream for implementation).
