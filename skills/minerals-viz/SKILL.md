---
name: minerals-viz
description: Generate charts (PNG/SVG) for critical minerals data — production, trade, import reliance, and time series
metadata:
  openclaw:
    emoji: "📈"
    requires:
      bins:
        - python3
---

# Minerals Visualization

Generate publication-quality charts for critical minerals data using the cmm_data visualizations module. Supports world production bar charts, production time series, import reliance charts, and multi-commodity comparisons.

## Usage

### World production chart:
```bash
python3 {baseDir}/scripts/generate_chart.py --chart-type production --commodity lithi
```

### Time series:
```bash
python3 {baseDir}/scripts/generate_chart.py --chart-type timeseries --commodity cobal
```

### Import reliance:
```bash
python3 {baseDir}/scripts/generate_chart.py --chart-type import-reliance --commodity raree
```

### Custom output:
```bash
python3 {baseDir}/scripts/generate_chart.py --chart-type production --commodity lithi --output lithium_prod.png --format png
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--chart-type` | Chart type: production, timeseries, import-reliance | Required |
| `--commodity` | USGS commodity code (e.g., lithi, cobal, raree, graph, nicke) | Required |
| `--output` | Output file path | auto-generated |
| `--format` | Image format: png, svg | png |
| `--top-n` | Number of countries in production chart | 10 |

## Chart Types

| Type | Description | Data Source |
|------|-------------|-------------|
| `production` | Horizontal bar chart of top producers | USGS world production |
| `timeseries` | Line chart of production over time | USGS salient statistics |
| `import-reliance` | NIR bar chart with threshold line | USGS salient statistics |

## USGS Commodity Codes

| Code | Commodity | Code | Commodity |
|------|-----------|------|-----------|
| `lithi` | Lithium | `cobal` | Cobalt |
| `raree` | Rare Earths | `graph` | Graphite |
| `nicke` | Nickel | `manga` | Manganese |
| `galli` | Gallium | `germa` | Germanium |
| `coppe` | Copper | `tungs` | Tungsten |

## Examples

```bash
# Lithium top producers
python3 {baseDir}/scripts/generate_chart.py --chart-type production --commodity lithi --top-n 10

# Cobalt production time series
python3 {baseDir}/scripts/generate_chart.py --chart-type timeseries --commodity cobal --output cobalt_trend.png

# Rare earth import reliance (SVG)
python3 {baseDir}/scripts/generate_chart.py --chart-type import-reliance --commodity raree --format svg
```

## Notes

- Requires matplotlib (install with: pip install matplotlib)
- USGS data files must be present in cmm-data data directory
- Output defaults to current directory with auto-generated filename
- SVG format recommended for publications and reports
- For raw data access, use the `minerals-data` skill
