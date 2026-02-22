---
name: export-restrictions
description: Query OECD export restriction policies on critical raw materials with corpus-search enrichment
metadata:
  openclaw:
    emoji: "🚫"
    requires:
      bins:
        - python3
---

# Export Restrictions on Raw Materials

Query OECD export restriction data and policies on industrial raw materials. Combines structured metadata from the OECD Supply Chain dataset with semantic search over policy documents in the local corpus. Covers 65 commodities across 82 countries from 2009-2023.

## Usage

### Search by commodity:
```bash
python3 {baseDir}/scripts/restrictions_query.py --commodity "lithium"
```

### Search by country:
```bash
python3 {baseDir}/scripts/restrictions_query.py --country "China"
```

### Free-text policy search:
```bash
python3 {baseDir}/scripts/restrictions_query.py --query "rare earth export ban"
```

### Combined search:
```bash
python3 {baseDir}/scripts/restrictions_query.py --commodity "cobalt" --country "Congo" --format json
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--commodity` | Commodity name to search for | - |
| `--country` | Country name to search for | - |
| `--query` | Free-text search across policy documents | - |
| `--format` | Output format: summary, detailed, json | summary |

## Examples

```bash
# China's restrictions on rare earth exports
python3 {baseDir}/scripts/restrictions_query.py --commodity "rare earths" --country "China"

# All lithium export restrictions
python3 {baseDir}/scripts/restrictions_query.py --commodity "lithium" --format detailed

# Policy text search
python3 {baseDir}/scripts/restrictions_query.py --query "export quota critical minerals"

# JSON output for cobalt restrictions
python3 {baseDir}/scripts/restrictions_query.py --commodity "cobalt" --format json
```

## Notes

- OECD data requires local data files (see cmm-data package)
- Policy text search uses the corpus-search skill (requires PINECONE_API_KEY)
- Coverage: 65 commodities, 82 countries, 2009-2023
- Restriction types include export bans, quotas, licenses, taxes
- For trade flow data, use `comtrade-trade` instead
