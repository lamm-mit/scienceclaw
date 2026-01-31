---
name: pubmed
description: Search PubMed for scientific literature and retrieve abstracts
metadata:
  {
    "openclaw": {
      "emoji": "📚",
      "requires": {
        "bins": ["python3"]
      }
    }
  }
---

# PubMed Search

Search the PubMed database for scientific literature, retrieve abstracts, and format citations.

## Overview

PubMed is a free database of biomedical literature from MEDLINE, life science journals, and online books. This skill uses NCBI's E-utilities API to search and fetch articles.

## Usage

### Basic search:
```bash
python3 {baseDir}/scripts/pubmed_search.py --query "CRISPR gene editing"
```

### Search with filters:
```bash
python3 {baseDir}/scripts/pubmed_search.py --query "cancer immunotherapy" --year 2024 --max-results 20
```

### Get full abstracts:
```bash
python3 {baseDir}/scripts/pubmed_search.py --query "machine learning drug discovery" --format detailed
```

### Export citations:
```bash
python3 {baseDir}/scripts/pubmed_search.py --query "protein folding" --format bibtex
```

### Fetch specific article by PMID:
```bash
python3 {baseDir}/scripts/pubmed_search.py --pmid 35648464
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Search query (supports PubMed syntax) | Required* |
| `--pmid` | Specific PubMed ID to fetch | - |
| `--max-results` | Maximum number of results | 10 |
| `--year` | Filter by publication year | - |
| `--year-start` | Start year for date range | - |
| `--year-end` | End year for date range | - |
| `--author` | Filter by author name | - |
| `--journal` | Filter by journal name | - |
| `--format` | Output format: summary, detailed, bibtex, json | summary |
| `--sort` | Sort by: relevance, date, first_author | relevance |

*Required unless `--pmid` is provided

## Search Syntax

PubMed supports advanced search operators:

- **AND/OR/NOT**: Combine terms (`cancer AND therapy`)
- **Phrases**: Use quotes (`"breast cancer"`)
- **Field tags**: `[Title]`, `[Author]`, `[Journal]`, `[MeSH]`
- **Wildcards**: `*` for truncation (`immun*`)

### Examples:
```
cancer[Title] AND therapy[Title]
"machine learning"[Title/Abstract]
Smith J[Author] AND 2024[Date - Publication]
Nature[Journal]
CRISPR[MeSH Terms]
```

## Examples

### Search recent papers on a topic:
```bash
python3 {baseDir}/scripts/pubmed_search.py --query "AlphaFold protein structure" --year 2024 --max-results 15
```

### Search by author:
```bash
python3 {baseDir}/scripts/pubmed_search.py --query "CRISPR" --author "Doudna JA"
```

### Get BibTeX for citations:
```bash
python3 {baseDir}/scripts/pubmed_search.py --query "deep learning genomics" --format bibtex --max-results 5
```

### Combine multiple filters:
```bash
python3 {baseDir}/scripts/pubmed_search.py --query "COVID-19 vaccine" --year-start 2023 --year-end 2024 --sort date
```

## Output Formats

### Summary
Compact list with title, authors, journal, and year.

### Detailed
Full abstract, author affiliations, MeSH terms, and DOI.

### BibTeX
Citation format for LaTeX documents.

### JSON
Machine-readable format with all metadata.

## Notes

- NCBI E-utilities have rate limits; heavy usage should use an API key
- Set `NCBI_EMAIL` environment variable for better rate limits
- Set `NCBI_API_KEY` for up to 10 requests/second (vs 3/second without)
- Results are returned by relevance by default
