---
name: literature-meta-search
description: Unified search across OSTI, Google Scholar, ArXiv, and corpus-search with deduplication and reciprocal rank fusion
metadata:
  openclaw:
    emoji: "🔬"
    requires:
      bins:
        - python3
---

# Literature Meta-Search

Unified literature search across multiple sources — OSTI, Google Scholar, ArXiv, and the local PDF corpus — with deduplication and reciprocal rank fusion ranking. Returns a single merged result list with an `in_corpus` flag showing which papers are in the local index.

## Usage

### Search all sources:
```bash
python3 {baseDir}/scripts/meta_search.py --query "lithium extraction brine"
```

### Select specific sources:
```bash
python3 {baseDir}/scripts/meta_search.py --query "rare earth separation" --sources osti,scholar
```

### Filter by year:
```bash
python3 {baseDir}/scripts/meta_search.py --query "cobalt supply chain" --year-from 2020 --year-to 2025
```

### JSON output:
```bash
python3 {baseDir}/scripts/meta_search.py --query "critical minerals policy" --format json --top-n 20
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Search query | Required |
| `--sources` | Comma-separated sources: osti, scholar, arxiv, corpus | osti,scholar,arxiv,corpus |
| `--year-from` | Start year for publication filter | - |
| `--year-to` | End year for publication filter | - |
| `--top-n` | Number of results to return | 15 |
| `--format` | Output format: summary, detailed, json | summary |

## Sources

| Source | Type | Auth Required |
|--------|------|---------------|
| `osti` | DOE technical reports | No |
| `scholar` | Google Scholar papers | SERPAPI_KEY |
| `arxiv` | ArXiv preprints | No |
| `corpus` | Local PDF corpus | PINECONE_API_KEY |

## Examples

```bash
# Multi-source search for battery materials
python3 {baseDir}/scripts/meta_search.py --query "solid state battery electrolyte" --top-n 20

# OSTI + Scholar for policy research
python3 {baseDir}/scripts/meta_search.py --query "critical minerals trade policy" --sources osti,scholar

# Recent arxiv + corpus papers
python3 {baseDir}/scripts/meta_search.py --query "rare earth recycling" --sources arxiv,corpus --year-from 2023
```

## Notes

- Uses reciprocal rank fusion to merge results from multiple sources
- Deduplication by fuzzy title matching (>80% similarity)
- `in_corpus` flag indicates which results are in the local PDF index
- Sources that fail (e.g., missing API key) are skipped with a warning
- For single-source search, use the individual skill directly
