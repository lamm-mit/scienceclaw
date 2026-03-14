---
name: scholar-search
description: Search Google Scholar via SerpAPI for academic papers on critical minerals with citation counts and metadata
metadata:
  openclaw:
    emoji: "🎓"
    requires:
      bins:
        - python3
      env:
        - SERPAPI_KEY
---

# Google Scholar Search

Search Google Scholar via SerpAPI for academic papers, conference proceedings, and theses. Returns titles, authors, venues, citation counts, and links. Useful for finding recent research on critical minerals, supply chains, extraction methods, and materials science.

## Usage

### Basic search:
```bash
python3 {baseDir}/scripts/scholar_search.py --query "lithium extraction brine"
```

### Filter by year range:
```bash
python3 {baseDir}/scripts/scholar_search.py --query "rare earth separation" --year-from 2020 --year-to 2025
```

### Sort by citations:
```bash
python3 {baseDir}/scripts/scholar_search.py --query "cobalt supply chain" --sort-by citations
```

### JSON output:
```bash
python3 {baseDir}/scripts/scholar_search.py --query "critical minerals policy" --format json --num-results 15
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Search query | Required |
| `--year-from` | Start year for publication filter | - |
| `--year-to` | End year for publication filter | - |
| `--num-results` | Number of results to return (max 20) | 10 |
| `--sort-by` | Sort order: relevance, citations | relevance |
| `--format` | Output format: summary, detailed, json | summary |

## Examples

```bash
# Recent papers on lithium recycling
python3 {baseDir}/scripts/scholar_search.py --query "lithium-ion battery recycling" --year-from 2022

# Most cited papers on rare earth processing
python3 {baseDir}/scripts/scholar_search.py --query "rare earth element processing" --sort-by citations --num-results 15

# Critical minerals policy research
python3 {baseDir}/scripts/scholar_search.py --query "critical minerals supply chain policy" --format detailed

# Cobalt extraction techniques in JSON
python3 {baseDir}/scripts/scholar_search.py --query "cobalt extraction hydrometallurgy" --format json
```

## Notes

- Requires `SERPAPI_KEY` environment variable
- Google Scholar results include citation counts for impact assessment
- Maximum 20 results per query (SerpAPI limitation)
- For DOE-specific research, use the `osti-database` skill instead
- For local corpus search, use the `corpus-search` skill
