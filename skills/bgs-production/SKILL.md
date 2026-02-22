---
name: bgs-production
description: Query BGS World Mineral Statistics for production, imports, and exports by commodity, country, and year
metadata:
  openclaw:
    emoji: "🌍"
    requires:
      bins:
        - python3
---

# BGS World Mineral Statistics

Query the British Geological Survey's World Mineral Statistics database for mineral production, imports, and exports by commodity, country, and year. Covers global mineral data with country-level breakdowns.

## Usage

### Basic search:
```bash
python3 {baseDir}/scripts/bgs_query.py --query "lithium"
```

### Production by country:
```bash
python3 {baseDir}/scripts/bgs_query.py --query "Cobalt" --country "Congo"
```

### Filter by year range:
```bash
python3 {baseDir}/scripts/bgs_query.py --query "Copper" --year-from 2018 --year-to 2022
```

### Get country ranking:
```bash
python3 {baseDir}/scripts/bgs_query.py --query "Graphite" --ranking --top-n 10
```

### Filter by statistic type:
```bash
python3 {baseDir}/scripts/bgs_query.py --query "Nickel" --statistic-type "Exports"
```

### JSON output:
```bash
python3 {baseDir}/scripts/bgs_query.py --query "Rare earths" --format json --limit 20
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Commodity name to search for | Required |
| `--country` | Filter by country name | - |
| `--year-from` | Start year for date filter | - |
| `--year-to` | End year for date filter | - |
| `--statistic-type` | Statistic type: Production, Imports, Exports | Production |
| `--ranking` | Show country ranking by production | false |
| `--top-n` | Number of top countries in ranking | 15 |
| `--limit` | Maximum records to return | 50 |
| `--format` | Output format: summary, detailed, json | summary |

## Examples

```bash
# Top lithium producers
python3 {baseDir}/scripts/bgs_query.py --query "Lithium" --ranking --top-n 10

# Cobalt production in Congo over time
python3 {baseDir}/scripts/bgs_query.py --query "Cobalt" --country "Congo" --year-from 2015 --format detailed

# Rare earth exports globally
python3 {baseDir}/scripts/bgs_query.py --query "Rare earths" --statistic-type "Exports" --format json

# Graphite production ranking for 2021
python3 {baseDir}/scripts/bgs_query.py --query "Graphite" --ranking --year-from 2021 --year-to 2021
```

## Notes

- Data from the BGS OGC API (free, no authentication required)
- Covers global mineral production, imports, and exports statistics
- Country names use BGS conventions (e.g., "Congo (Democratic Republic)" not "DRC")
- Year filtering is applied client-side after fetching records
- Rate limiting: be courteous, avoid excessive requests
