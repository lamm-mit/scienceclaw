# BGPT Paper Search

BioGPT-powered scientific paper search returning 25+ structured fields per paper including extracted methods, results, sample sizes, and quality scores. Superior to basic PubMed search for structured data extraction.

## Setup

Configure as a remote MCP server. BGPT provides a hosted MCP endpoint.

```json
// MCP server configuration
{
  "mcpServers": {
    "bgpt": {
      "url": "https://mcp.bgpt.ai/v1",
      "headers": {
        "Authorization": "Bearer YOUR_BGPT_API_KEY"
      }
    }
  }
}
```

**Pricing:**
- Free tier: 50 searches/network (shared quota)
- Paid: $0.01/result with API key
- Get key at: https://bgpt.ai

## Available Tools

Once connected as MCP server, BGPT exposes:

| Tool | Description |
|------|-------------|
| `search_papers` | Full-text search with structured extraction |
| `get_paper` | Retrieve single paper by DOI/PMID |
| `search_by_entity` | Find papers mentioning specific genes/proteins/drugs |
| `get_citations` | Forward/backward citation graph |
| `summarize_evidence` | Synthesize findings across papers |

## 25+ Fields Returned Per Paper

```json
{
  "pmid": "37123456",
  "doi": "10.1038/s41586-024-xxxxx",
  "title": "...",
  "abstract": "...",
  "full_text_available": true,

  // Extracted structured data
  "study_type": "randomized_controlled_trial",
  "sample_size": 1247,
  "sample_size_confidence": 0.95,
  "population": "adults with type 2 diabetes",
  "intervention": "semaglutide 2.4mg weekly",
  "comparator": "placebo",
  "primary_outcome": "HbA1c reduction at 26 weeks",
  "effect_size": "-1.2% HbA1c (95% CI: -1.4 to -1.0)",
  "p_value": 0.001,
  "statistical_method": "mixed-effects model",

  // Quality scores
  "quality_score": 0.87,
  "bias_risk": "low",
  "evidence_level": "1b",
  "jadad_score": 4,

  // Methods
  "methods_summary": "...",
  "tools_used": ["flow cytometry", "western blot", "ELISA"],
  "cell_lines": ["HEK293", "HeLa"],
  "model_organisms": ["C57BL/6 mice"],
  "key_reagents": ["anti-CD3 antibody (clone OKT3)"],

  // Results
  "key_findings": ["...", "..."],
  "numerical_results": [{"metric": "IC50", "value": 45.2, "unit": "nM"}],
  "figures_count": 6,
  "tables_count": 3,
  "supplementary_available": true,

  // Metadata
  "journal": "Nature",
  "impact_factor": 69.5,
  "year": 2024,
  "authors": ["Smith J", "Doe A"],
  "institution": "Harvard Medical School",
  "funding": ["NIH R01 CA123456"],
  "conflicts_of_interest": "none declared"
}
```

## Search Examples

```python
# Via MCP tool call (when integrated)
result = mcp_client.call_tool("bgpt", "search_papers", {
    "query": "CRISPR base editing off-target effects",
    "filters": {
        "year_min": 2022,
        "study_types": ["clinical_trial", "cohort"],
        "min_quality_score": 0.7
    },
    "max_results": 20,
    "fields": ["title", "sample_size", "key_findings", "quality_score"]
})

# Search by entity
result = mcp_client.call_tool("bgpt", "search_by_entity", {
    "entity_type": "protein",
    "entity_id": "P00533",  # UniProt EGFR
    "context": "inhibitor binding",
    "include_drug_interactions": True
})

# Summarize evidence across papers
summary = mcp_client.call_tool("bgpt", "summarize_evidence", {
    "query": "PD-1 inhibitor efficacy in non-small cell lung cancer",
    "synthesis_type": "meta_analysis_style",
    "max_papers": 50
})
```

## vs. PubMed Search

| Feature | PubMed | BGPT |
|---------|--------|------|
| Fields returned | ~10 | 25+ |
| Sample size extraction | Manual | Automatic |
| Effect size extraction | No | Yes |
| Quality scoring | No | Yes (0-1 scale) |
| Methods extraction | No | Yes |
| Full-text search | Limited | Yes |
| Cost | Free | Free tier/paid |

## Best For

- Systematic reviews and meta-analyses (structured data extraction)
- Finding papers with specific sample sizes or effect sizes
- Identifying studies using particular experimental methods or cell lines
- Evidence synthesis across large paper sets
- Quality-filtered literature review
