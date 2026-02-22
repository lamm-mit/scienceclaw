---
name: supply-chain-analysis
description: Compute supply chain risk metrics for critical minerals — HHI concentration, net import reliance, top-3 share, and trend analysis
metadata:
  openclaw:
    emoji: "📊"
    requires:
      bins:
        - python3
---

# Supply Chain Risk Analysis

Compute supply chain risk metrics for critical minerals including the Herfindahl-Hirschman Index (HHI) for production concentration, net import reliance (NIR), top-3 country share, and multi-year trend analysis. Combines data from BGS World Mineral Statistics and USGS Mineral Commodity Summaries.

## Usage

### Full risk assessment:
```bash
python3 {baseDir}/scripts/supply_chain_metrics.py --commodity "Lithium"
```

### Specific metrics:
```bash
python3 {baseDir}/scripts/supply_chain_metrics.py --commodity "Cobalt" --metrics hhi,nir,top3share
```

### Historical trend:
```bash
python3 {baseDir}/scripts/supply_chain_metrics.py --commodity "Rare earths" --metrics trend --year-from 2015
```

### JSON output:
```bash
python3 {baseDir}/scripts/supply_chain_metrics.py --commodity "Graphite" --format json
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--commodity` | Commodity name (BGS naming) | Required |
| `--year` | Target year for analysis | latest available |
| `--year-from` | Start year for trend analysis | - |
| `--metrics` | Comma-separated metrics: hhi, nir, top3share, trend, all | all |
| `--format` | Output format: summary, json | summary |

## Metrics Explained

| Metric | Description | Risk Thresholds |
|--------|-------------|-----------------|
| **HHI** | Herfindahl-Hirschman Index (0-10000) | <1500 low, 1500-2500 moderate, >2500 high |
| **NIR** | US Net Import Reliance (%) | <25% low, 25-75% moderate, >75% high |
| **Top-3 Share** | Combined share of top 3 producers | <50% low, 50-75% moderate, >75% high |
| **Trend** | Year-over-year production change | Increasing/stable/declining |

## Examples

```bash
# Comprehensive lithium supply chain risk assessment
python3 {baseDir}/scripts/supply_chain_metrics.py --commodity "Lithium" --format json

# Cobalt concentration analysis
python3 {baseDir}/scripts/supply_chain_metrics.py --commodity "Cobalt" --metrics hhi,top3share

# Rare earth NIR trend
python3 {baseDir}/scripts/supply_chain_metrics.py --commodity "Rare earths" --metrics nir,trend --year-from 2018
```

## Notes

- HHI from BGS country-level production data (free API, no auth)
- NIR from USGS Mineral Commodity Summaries (requires local data files)
- Trend analysis requires multiple years of data
- Some commodities may not have all metrics available
- For raw production data, use `bgs-production` skill
