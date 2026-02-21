---
name: minerals-data
description: Query and analyze structured CSV datasets on critical minerals production, trade, and supply chains
metadata:
  openclaw:
    emoji: "📊"
    requires:
      bins:
        - python3
---

# Minerals Data — Structured CSV Querying

Query and analyze structured CSV datasets from the critical minerals corpus. Supports listing available datasets, describing schemas, filtering, grouping, and aggregation via pandas.

## Usage

### List available datasets:
```bash
python3 {baseDir}/scripts/query_data.py --list
```

### Describe a dataset:
```bash
python3 {baseDir}/scripts/query_data.py --dataset usgs/production.csv --describe
```

### Query with DSL:
```bash
python3 {baseDir}/scripts/query_data.py --dataset usgs/production.csv --query "groupby:commodity|agg:value:sum|sort:value:desc|head:10"
```

### Filter with pandas expression:
```bash
python3 {baseDir}/scripts/query_data.py --dataset usgs/production.csv --filter "year >= 2022"
```

### Combine filter and query:
```bash
python3 {baseDir}/scripts/query_data.py --dataset usgs/trade.csv --filter "commodity == 'lithium'" --query "groupby:country|agg:value:sum|sort:value:desc|head:5"
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--list` | List all available CSV datasets | - |
| `--dataset` | Path to CSV file (relative to corpus dir) | - |
| `--describe` | Show schema, dtypes, sample rows, statistics | - |
| `--query` | Pipe-delimited DSL for pandas operations | - |
| `--filter` | Pandas query expression for filtering | - |
| `--corpus-dir` | Directory containing data files | ~/critical-minerals-data/ |
| `--format` | Output format: table, json, csv | table |

## Query DSL

Pipe-delimited operations that map to pandas:

| Operation | Syntax | Example |
|-----------|--------|---------|
| Group by | `groupby:col` | `groupby:commodity` |
| Aggregate | `agg:col:func` | `agg:value:sum` |
| Sort | `sort:col:dir` | `sort:value:desc` |
| Head | `head:n` | `head:10` |
| Select columns | `select:col1,col2` | `select:commodity,value` |

Functions: `sum`, `mean`, `count`, `min`, `max`, `median`, `std`

## Examples

```bash
# Top producing countries for lithium
python3 {baseDir}/scripts/query_data.py --dataset usgs/production.csv \
  --filter "commodity == 'lithium'" \
  --query "groupby:country|agg:value:sum|sort:value:desc|head:10"

# Year-over-year trade data
python3 {baseDir}/scripts/query_data.py --dataset comtrade/exports.csv \
  --query "groupby:year|agg:value:sum|sort:year:asc"

# Dataset overview
python3 {baseDir}/scripts/query_data.py --dataset worldbank/indicators.csv --describe
```

## Notes

- Requires `pandas>=2.0.0` (already in ScienceClaw requirements)
- CSV catalog is cached at `~/critical-minerals-data/.csv_catalog.json`
- Handles encoding fallbacks: UTF-8, Latin-1, CP1252
- Filter expressions are sanitized to prevent code injection
