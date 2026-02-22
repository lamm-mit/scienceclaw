---
name: claimm-datasets
description: Search and discover NETL EDX CLAIMM datasets with 200+ US-focused critical minerals datasets
metadata:
  openclaw:
    emoji: "🗄️"
    requires:
      bins:
        - python3
      env:
        - EDX_API_KEY
---

# CLAIMM Dataset Search

Search and discover datasets from NETL's Energy Data Exchange (EDX) CLAIMM collection. Provides access to 200+ US-focused critical minerals datasets including geological surveys, geochemical analyses, deposit locations, and resource assessments.

## Usage

### Basic search:
```bash
python3 {baseDir}/scripts/claimm_search.py --query "lithium deposits"
```

### Filter by tags:
```bash
python3 {baseDir}/scripts/claimm_search.py --query "rare earth" --tags "geochemistry,geology"
```

### Get dataset details:
```bash
python3 {baseDir}/scripts/claimm_search.py --dataset-id "some-dataset-uuid"
```

### JSON output:
```bash
python3 {baseDir}/scripts/claimm_search.py --query "cobalt mining" --format json --limit 20
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Search query for dataset discovery | - |
| `--tags` | Comma-separated tags to filter by | - |
| `--dataset-id` | Specific dataset ID to retrieve details | - |
| `--limit` | Maximum datasets to return | 20 |
| `--format` | Output format: summary, detailed, json | summary |

## Examples

```bash
# Search for lithium deposit datasets
python3 {baseDir}/scripts/claimm_search.py --query "lithium deposits"

# Geochemistry datasets for rare earths
python3 {baseDir}/scripts/claimm_search.py --query "rare earth" --tags "geochemistry"

# Get detailed info for a specific dataset
python3 {baseDir}/scripts/claimm_search.py --dataset-id "abc123" --format detailed

# All critical minerals datasets in JSON
python3 {baseDir}/scripts/claimm_search.py --query "critical minerals" --format json --limit 50
```

## Notes

- Requires `EDX_API_KEY` environment variable
- CLAIMM = Critical and Lanthanide Inorganic Mineral Materials
- Hosted by NETL (National Energy Technology Laboratory) on EDX platform
- Datasets include CSVs, shapefiles, and metadata
- US-focused but includes some international deposit data
- For production statistics, use `bgs-production` instead
