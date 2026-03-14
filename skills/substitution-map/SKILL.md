---
name: substitution-map
description: Map substitute materials for critical minerals with trade-off analysis and supply risk assessment
metadata:
  openclaw:
    emoji: "🔄"
    requires:
      bins:
        - python3
---

# Substitution Map

Map substitute materials for a critical mineral commodity with trade-off analysis (performance, cost, availability) and supply risk assessment. Uses a curated knowledge base of substitution relationships enriched with live data from BGS production statistics and corpus search.

## Usage

### Find substitutes for a commodity:
```bash
python3 {baseDir}/scripts/substitution_lookup.py --commodity lithium
```

### Filter by application:
```bash
python3 {baseDir}/scripts/substitution_lookup.py --commodity cobalt --application batteries
```

### JSON output:
```bash
python3 {baseDir}/scripts/substitution_lookup.py --commodity rare_earth --format json
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--commodity` | Commodity to find substitutes for | Required |
| `--application` | Specific application: batteries, magnets, catalysts, alloys, electronics | all |
| `--format` | Output format: summary, detailed, json | summary |

## Available Commodities

| Commodity | Key Applications |
|-----------|-----------------|
| `lithium` | Batteries, ceramics, lubricants |
| `cobalt` | Batteries, superalloys, catalysts |
| `rare_earth` | Magnets, catalysts, phosphors |
| `nickel` | Batteries, stainless steel, alloys |
| `graphite` | Batteries, refractories, lubricants |
| `manganese` | Steel, batteries, chemicals |
| `gallium` | Semiconductors, LEDs, solar cells |
| `germanium` | Fiber optics, IR optics, solar cells |
| `copper` | Wiring, electronics, motors |

## Examples

```bash
# All lithium substitutes
python3 {baseDir}/scripts/substitution_lookup.py --commodity lithium

# Cobalt substitutes in batteries
python3 {baseDir}/scripts/substitution_lookup.py --commodity cobalt --application batteries

# Rare earth substitutes in magnets (JSON)
python3 {baseDir}/scripts/substitution_lookup.py --commodity rare_earth --application magnets --format json
```

## Notes

- Substitution data from curated knowledge base (USGS, industry literature)
- Trade-off ratings: performance (1-5), cost (relative), availability (1-5)
- Supply risk enrichment from BGS when available
- For production data, use `bgs-production`; for risk metrics, use `supply-chain-analysis`
