---
name: drug-research
description: "Generates comprehensive drug research reports with compound disambiguation, evidence grading, and mandatory completeness sections. Covers identity, chemistry, pharmacology, targets, clinical trials, safety, pharmacogenomics, and ADMET properties. Use when users ask about drugs, medications, therapeutics, or need drug profiling, safety assessment, or clinical development research."
metadata:
  source: https://github.com/mims-harvard/ToolUniverse/tree/main/skills/tooluniverse-drug-research
---

# Drug Research Strategy

Comprehensive drug investigation using 50+ ToolUniverse tools across chemical databases, clinical trials, adverse events, pharmacogenomics, and literature.

For detailed tool chains, output templates, and validation guidance, see [references/tool-reference.md](references/tool-reference.md).

---

## When to Use

- The user asks about a drug, medication, or therapeutic compound
- The user needs a drug profile, safety assessment, or clinical development overview
- The user requests ADMET evaluation, pharmacogenomics, or regulatory landscape information
- The user provides a compound name, SMILES, or ChEMBL/PubChem identifier for research

---

## Key Principles

1. **Report-first approach** - The agent creates the report file before any data collection, then populates it progressively.
2. **Compound disambiguation first** - The agent resolves identifiers (PubChem CID, ChEMBL ID, DailyMed SetID, PharmGKB ID) before beginning research.
3. **Citation requirements** - Every fact includes inline source attribution with the tool and identifier used.
4. **Evidence grading** - Claims are graded by evidence strength (T1: Phase 3/FDA label, T2: Phase 1-2/large case series, T3: preclinical, T4: computational).
5. **Mandatory completeness** - All 11 report sections must exist, even if marked "data unavailable."
6. **English-first queries** - The agent uses English drug/compound names in tool calls, falling back to original-language terms only if needed. The agent responds in the user's language.

---

## Workflow Overview

```
Step 1:  Create report file ([DRUG]_drug_report.md) with all 11 section headers
Step 2:  Resolve compound identifiers -> Update Section 1 (Identity)
Step 3:  Retrieve FDA label core fields (mechanism, PK, safety, PGx)
Step 4:  Query PubChem / ADMET-AI / DailyMed -> Update Section 2 (Chemistry)
Step 5:  Query FDA Label MOA + ChEMBL + DGIdb -> Update Section 3 (Mechanism & Targets)
Step 6:  Query ADMET-AI tools (fallback: DailyMed PK) -> Update Section 4 (ADMET)
Step 7:  Query ClinicalTrials.gov -> Update Section 5 (Clinical Development)
Step 8:  Query FAERS / DailyMed -> Update Section 6 (Safety)
Step 9:  Query PharmGKB (fallback: DailyMed PGx) -> Update Section 7 (Pharmacogenomics)
Step 10: Query DailyMed / Orange Book -> Update Section 8 (Regulatory)
Step 11: Query PubMed / literature -> Update Section 9 (Literature)
Step 12: Synthesize findings -> Update Executive Summary & Section 10 (Conclusions)
Step 13: Document all sources, run completeness audit -> Update Section 11
```

---

## Report Structure

The agent produces an 11-section report in `[DRUG]_drug_report.md`:

| Section | Content |
|---------|---------|
| Executive Summary | High-level drug profile overview |
| 1. Compound Identity | Database IDs, SMILES, formula, synonyms |
| 2. Chemical Properties | Physicochemical profile, drug-likeness, solubility, salt forms |
| 3. Mechanism & Targets | FDA label MOA, primary targets with UniProt IDs, selectivity |
| 4. ADMET Properties | Absorption, distribution, metabolism, excretion, toxicity |
| 5. Clinical Development | Phase counts, trial landscape, approved/investigational indications, biomarkers |
| 6. Safety Profile | FAERS data, black box warnings, DDIs, drug-food interactions, dose modifications |
| 7. Pharmacogenomics | Pharmacogenes, CPIC/DPWG guidelines, clinical annotations |
| 8. Regulatory & Labeling | Approval status, patents, exclusivity, special populations, timeline |
| 9. Literature & Research | Publication metrics, research themes, real-world evidence |
| 10. Conclusions | Scorecard, strengths, concerns, research gaps, comparative analysis |
| 11. Data Sources | Tool call summary, completeness audit, quality control metrics |

---

## Report Detail Requirements

Each section must be comprehensive and detailed:

- **Tables** for structured data (targets, trials, adverse events)
- **Lists** for features, findings, key points
- **Paragraphs** for narrative synthesis
- **Specific values** including counts, percentages, and confidence levels (not vague terms)
- **Context** explaining what the data means, not just what it is
- **Source attribution** at the end of each data block

---

## Citation Format

The agent attributes every data block to its source:

```markdown
*Source: PubChem via `PubChem_get_compound_properties_by_CID` (CID: 4091)*
```

Section-level source summaries appear at the end of each section:

```markdown
---
**Data Sources for this section:**
- PubChem: `PubChem_get_compound_properties_by_CID` (CID: 4091)
- ChEMBL: `ChEMBL_get_bioactivity_by_chemblid` (CHEMBL1431)
---
```

---

## Critical Rules

- **Avoid `ChEMBL_get_molecule_targets`** — it returns unfiltered, irrelevant results. The agent derives targets from `ChEMBL_search_activities` instead, filtering to pChEMBL >= 6.0.
- **Type normalization** — All IDs (ChEMBL, PubMed, NCT) are converted to strings before API calls.
- **ADMET fallback** — If ADMET-AI tools fail, the agent falls back to FDA label PK sections. Section 4 is never left empty.
- **PharmGKB fallback** — If PharmGKB is unavailable, the agent uses DailyMed PGx + PubMed literature.
- **FAERS limitations** — The agent always includes a data limitations paragraph noting voluntary reporting, causality caveats, and reporting bias.
- **Clinical trial counts** — Section 5.2 shows actual counts by phase/status in table format, not just a list of trials.

---

## Common Use Cases

| Scenario | Focus |
|----------|-------|
| **Approved drug profile** ("Tell me about metformin") | Full 11-section report emphasizing clinical data, FAERS, PGx |
| **Investigational compound** ("What do we know about compound X?") | Preclinical data, mechanism, early trials; safety sections may be sparse |
| **Safety review** ("What are the safety concerns with drug Y?") | Deep dive on FAERS, black box warnings, interactions, PGx |
| **ADMET assessment** ("Evaluate this compound's drug-likeness") | Focus on Sections 2 and 4; other sections may be brief |
| **Clinical development landscape** ("What trials are ongoing for drug Z?") | Heavy emphasis on Section 5 with trial tables |
