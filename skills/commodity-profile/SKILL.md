---
name: commodity-profile
description: Generate comprehensive one-page commodity profiles with production, trade, risk, research, policy, and web intelligence data
metadata:
  openclaw:
    emoji: "📋"
    requires:
      bins:
        - python3
---

# Commodity Profile Generator

Generate comprehensive commodity profiles by orchestrating calls to multiple mineral-claw skills. Profiles cover production data (BGS), trade flows (Comtrade), supply chain risk metrics, recent research, export restriction policies, and web intelligence from news/blog/government sources.

## Usage

### Full profile:
```bash
python3 {baseDir}/scripts/generate_profile.py --commodity "Lithium"
```

### Select sections:
```bash
python3 {baseDir}/scripts/generate_profile.py --commodity "Cobalt" --sections production,risk,intel
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
| `--sections` | Comma-separated sections: production, trade, risk, research, policy, intel | all |
| `--intel-max-results` | Max web-intel records to process | 20 |
| `--format` | Output format: summary, json | summary |

## Profile Sections

| Section | Data Source | Description |
|---------|------------|-------------|
| `production` | bgs-production | Top producers, global output, rankings |
| `trade` | comtrade-trade | Import/export flows, major partners |
| `risk` | supply-chain-analysis | HHI, NIR, top-3 share, trend |
| `research` | literature-meta-search | Recent publications, citation leaders |
| `policy` | export-restrictions | Active restrictions, policy changes |
| `intel` | minerals-news-monitor + minerals-gov-monitor + minerals-web-ingest | Recent web signals, policy tags, high-confidence findings |

## Examples

```bash
# Full lithium profile
python3 {baseDir}/scripts/generate_profile.py --commodity "Lithium"

# Cobalt production, risk, and web-intel
python3 {baseDir}/scripts/generate_profile.py --commodity "Cobalt" --sections production,risk,intel

# Graphite profile in JSON
python3 {baseDir}/scripts/generate_profile.py --commodity "Graphite" --format json --year 2022
```

## Notes

- Orchestrates multiple skill scripts (may take 30-90 seconds)
- Some sections may fail if API keys are not set (warnings printed to stderr)
- Trade section requires `UNCOMTRADE_API_KEY`
- Research section requires `SERPAPI_KEY` for Scholar results
- Intel section requires `requests` and `beautifulsoup4` in the active Python environment
- Intel ingest can optionally use Firecrawl when `FIRECRAWL_API_KEY` is set
- For individual data queries, use source skills directly
