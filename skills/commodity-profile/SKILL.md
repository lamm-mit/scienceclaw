---
name: commodity-profile
description: Generate comprehensive one-page commodity profiles with production, trade, risk, research, and policy data
metadata:
  openclaw:
    emoji: "📋"
    requires:
      bins:
        - python3
---

# Commodity Profile Generator

Generate comprehensive commodity profiles by orchestrating calls to multiple mineral-claw skills. Profiles cover production data (BGS), trade flows (Comtrade), supply chain risk metrics, recent research, and export restriction policies.

## Usage

### Full profile:
```bash
python3 {baseDir}/scripts/generate_profile.py --commodity "Lithium"
```

### Select sections:
```bash
python3 {baseDir}/scripts/generate_profile.py --commodity "Cobalt" --sections production,risk
```

### JSON output:
```bash
python3 {baseDir}/scripts/generate_profile.py --commodity "Rare earths" --format json
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--commodity` | Commodity name (BGS naming) | Required |
| `--year` | Target year | latest available |
| `--sections` | Comma-separated sections: production, trade, risk, research, policy | all |
| `--format` | Output format: summary, json | summary |

## Profile Sections

| Section | Data Source | Description |
|---------|------------|-------------|
| `production` | bgs-production | Top producers, global output, rankings |
| `trade` | comtrade-trade | Import/export flows, major partners |
| `risk` | supply-chain-analysis | HHI, NIR, top-3 share, trend |
| `research` | literature-meta-search | Recent publications, citation leaders |
| `policy` | export-restrictions | Active restrictions, policy changes |

## Examples

```bash
# Full lithium profile
python3 {baseDir}/scripts/generate_profile.py --commodity "Lithium"

# Cobalt production and risk only
python3 {baseDir}/scripts/generate_profile.py --commodity "Cobalt" --sections production,risk

# Graphite profile in JSON
python3 {baseDir}/scripts/generate_profile.py --commodity "Graphite" --format json --year 2022
```

## Notes

- Orchestrates multiple skill scripts (may take 30-60 seconds)
- Some sections may fail if API keys aren't set (warnings printed to stderr)
- Trade section requires UNCOMTRADE_API_KEY
- Research section requires SERPAPI_KEY for Scholar results
- For individual data queries, use the source skills directly
