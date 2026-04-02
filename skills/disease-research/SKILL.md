---
name: disease-research
description: "Generate comprehensive disease research reports using 100+ ToolUniverse tools. The agent creates a detailed markdown report file and progressively updates it with findings from 10 research dimensions, with full source citations. Use when users ask about diseases, syndromes, or need systematic disease analysis."
metadata:
  source: https://github.com/mims-harvard/ToolUniverse/tree/main/skills/tooluniverse-disease-research
---

# ToolUniverse Disease Research

The agent generates a comprehensive, citation-backed disease research report by creating a markdown file and progressively updating it across 10 research dimensions.

**IMPORTANT**: The agent should always use English disease names and search terms in tool calls, even if the user writes in another language. Original-language terms should only be tried as a fallback if English returns no results. The agent responds in the user's language.

## When to Use

This skill applies when the user:
- Asks about any disease, syndrome, or medical condition
- Needs comprehensive disease intelligence
- Wants a detailed research report with citations
- Asks "what do we know about [disease]?"

## Core Workflow: Report-First Approach

The agent should **not** show the search process to the user. Instead it follows this pattern:

1. **Create report file** — Initialize `{disease_name}_research_report.md` with the full report template
2. **Research each dimension** — Query all relevant ToolUniverse tools per dimension
3. **Update report progressively** — Write findings to the file after completing each dimension
4. **Include citations** — Every fact must reference the source tool that provided it

### The 10 Research Dimensions

| # | Dimension | Key Focus |
|---|-----------|-----------|
| 1 | Disease Identity & Classification | EFO, ICD-10, UMLS, SNOMED identifiers; synonyms; disease hierarchy |
| 2 | Clinical Presentation | HPO phenotypes; symptoms and signs; diagnostic criteria |
| 3 | Genetic & Molecular Basis | Associated genes; GWAS associations; ClinVar pathogenic variants |
| 4 | Treatment Landscape | Approved drugs; clinical trials; treatment guidelines |
| 5 | Biological Pathways & Mechanisms | Reactome pathways; PPI networks; tissue expression |
| 6 | Epidemiology & Risk Factors | Prevalence; risk factors; GWAS studies |
| 7 | Literature & Research Activity | Publication trends; key papers; research institutions |
| 8 | Similar Diseases & Comorbidities | Disease similarity scores; shared genetic basis |
| 9 | Cancer-Specific Information | CIViC variants; molecular profiles; targeted therapies (if applicable) |
| 10 | Drug Safety & Adverse Events | Drug warnings; trial adverse events; FAERS data |

### Example

```
User: "Research Parkinson's disease"

Agent actions (internal, not shown to user):
1. Create "parkinsons_disease_research_report.md" with template
2. Research DIM 1 → Update Identity section
3. Research DIM 2 → Update Clinical section
4. ... continue for all 10 dimensions
5. Present final report to user
```

## Citation Requirements

Every piece of data in the report must include its source tool. The agent should use source columns in tables, `[Source: tool_name]` annotations in lists, and parenthetical `(Source: tool_name, query: ...)` references in prose. A complete tool usage log belongs in the References section at the end of the report.

## Detailed References

For the full report template, complete tool listings per dimension, implementation examples, citation format guide, and quality checklist, see [references/tool-reference.md](references/tool-reference.md).

## Additional Resources

See [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) for complete tool documentation.
See [EXAMPLES.md](EXAMPLES.md) for sample reports.
