---
name: osti-database
description: Search OSTI.gov for DOE technical reports on critical minerals, energy, and materials science
metadata:
  openclaw:
    emoji: "🏛️"
    requires:
      bins:
        - python3
---

# OSTI Database Search

Search the U.S. Department of Energy's Office of Scientific and Technical Information (OSTI.gov) for technical reports, journal articles, and conference papers. Covers 1,100+ DOE-funded documents across critical mineral categories including rare earth elements, lithium, cobalt, nickel, copper, gallium, germanium, and graphite.

## Usage

### Basic search:
```bash
python3 {baseDir}/scripts/osti_search.py --query "rare earth separation"
```

### Search by commodity:
```bash
python3 {baseDir}/scripts/osti_search.py --query "extraction" --commodity HREE
```

### Filter by year range:
```bash
python3 {baseDir}/scripts/osti_search.py --query "lithium recovery" --year-from 2020 --year-to 2025
```

### Filter by product type:
```bash
python3 {baseDir}/scripts/osti_search.py --query "critical minerals" --product-type "Technical Report"
```

### JSON output:
```bash
python3 {baseDir}/scripts/osti_search.py --query "cobalt supply chain" --format json --limit 20
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Search query | Required |
| `--commodity` | Commodity filter (HREE, LREE, CO, LI, GA, GR, NI, CU, GE, OTH) | - |
| `--product-type` | Product type filter (Technical Report, Journal Article, Conference) | - |
| `--year-from` | Start year for publication date filter | - |
| `--year-to` | End year for publication date filter | - |
| `--limit` | Maximum results to return | 10 |
| `--sort` | Sort by: relevance, date | relevance |
| `--format` | Output format: summary, detailed, json, bibtex | summary |

## Commodity Codes

| Code | Description |
|------|-------------|
| `HREE` | Heavy Rare Earth Elements (Dy, Tb, Eu, Y, etc.) |
| `LREE` | Light Rare Earth Elements (La, Ce, Nd, Pr, etc.) |
| `CO` | Cobalt |
| `LI` | Lithium |
| `GA` | Gallium |
| `GR` | Graphite |
| `NI` | Nickel |
| `CU` | Copper |
| `GE` | Germanium |
| `OTH` | Other critical minerals |

## Examples

```bash
# Search for heavy rare earth separation techniques
python3 {baseDir}/scripts/osti_search.py --query "heavy rare earth separation" --commodity HREE

# Recent DOE reports on lithium extraction
python3 {baseDir}/scripts/osti_search.py --query "lithium extraction" --product-type "Technical Report" --year-from 2022 --sort date

# Critical minerals supply chain analysis with detailed output
python3 {baseDir}/scripts/osti_search.py --query "supply chain critical minerals" --format detailed --limit 15

# Get BibTeX citations for cobalt recycling papers
python3 {baseDir}/scripts/osti_search.py --query "cobalt recycling" --commodity CO --format bibtex
```

## Notes

- OSTI.gov API is free and does not require authentication
- Covers DOE-funded research: national labs, universities, contractors
- Document types include technical reports, journal articles, conference papers, theses, patents
- For local corpus search, use the `corpus-search` skill instead
- Rate limiting: be courteous, avoid excessive requests
