---
name: datavis
description: Create scientific plots and visualizations using matplotlib and seaborn
metadata:
  {
    "openclaw": {
      "emoji": "📊",
      "requires": {
        "bins": ["python3"]
      }
    }
  }
---

# Scientific Data Visualization

Create publication-quality scientific plots and visualizations using matplotlib and seaborn.

## Overview

This skill provides data visualization capabilities for scientific data:
- Line plots, scatter plots, bar charts
- Heatmaps and clustermaps
- Box plots and violin plots
- Histograms and density plots
- Sequence logos (for bioinformatics)
- Multiple subplot layouts

## Usage

### Create a line plot from CSV:
```bash
python3 {baseDir}/scripts/plot_data.py line --data data.csv --x time --y value --output plot.png
```

### Create a scatter plot:
```bash
python3 {baseDir}/scripts/plot_data.py scatter --data data.csv --x x_col --y y_col --hue group
```

### Create a heatmap:
```bash
python3 {baseDir}/scripts/plot_data.py heatmap --data matrix.csv --output heatmap.png
```

### Create a bar chart:
```bash
python3 {baseDir}/scripts/plot_data.py bar --data data.csv --x category --y value
```

### Plot from JSON data:
```bash
python3 {baseDir}/scripts/plot_data.py line --json '{"x": [1,2,3], "y": [4,5,6]}'
```

## Plot Types

### line
Line plot for continuous data.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--data` | CSV file path | - |
| `--json` | JSON data string | - |
| `--x` | X-axis column | Required |
| `--y` | Y-axis column(s), comma-separated | Required |
| `--hue` | Color grouping column | - |
| `--style` | Line style column | - |
| `--markers` | Add markers | False |

### scatter
Scatter plot for showing relationships.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--data` | CSV file path | - |
| `--x` | X-axis column | Required |
| `--y` | Y-axis column | Required |
| `--hue` | Color grouping column | - |
| `--size` | Size column | - |
| `--alpha` | Point transparency | 0.7 |

### bar
Bar chart for categorical data.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--data` | CSV file path | - |
| `--x` | Category column | Required |
| `--y` | Value column | Required |
| `--hue` | Color grouping column | - |
| `--horizontal` | Horizontal bars | False |
| `--error` | Error bar column | - |

### heatmap
Heatmap for matrix data.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--data` | CSV file path | Required |
| `--cmap` | Color map | viridis |
| `--annotate` | Show values | False |
| `--cluster` | Cluster rows/columns | False |

### box
Box plot for distributions.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--data` | CSV file path | - |
| `--x` | Grouping column | - |
| `--y` | Value column | Required |
| `--hue` | Color grouping column | - |

### violin
Violin plot for distributions.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--data` | CSV file path | - |
| `--x` | Grouping column | - |
| `--y` | Value column | Required |
| `--hue` | Color grouping column | - |
| `--split` | Split violins by hue | False |

### histogram
Histogram for distributions.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--data` | CSV file path | - |
| `--x` | Value column | Required |
| `--bins` | Number of bins | auto |
| `--kde` | Add KDE line | False |
| `--hue` | Color grouping column | - |

## Common Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output` | Output file path | plot.png |
| `--format` | Output format: png, svg, pdf | png |
| `--title` | Plot title | - |
| `--xlabel` | X-axis label | column name |
| `--ylabel` | Y-axis label | column name |
| `--figsize` | Figure size (width,height) | 10,6 |
| `--style` | Seaborn style | whitegrid |
| `--palette` | Color palette | deep |
| `--dpi` | Output resolution | 150 |
| `--legend` | Legend position | auto |
| `--logx` | Log scale X-axis | False |
| `--logy` | Log scale Y-axis | False |

## Examples

### Multi-line plot with legend:
```bash
python3 {baseDir}/scripts/plot_data.py line --data timeseries.csv --x date --y "temp,humidity" --title "Weather Data" --output weather.png
```

### Scatter plot with regression line:
```bash
python3 {baseDir}/scripts/plot_data.py scatter --data experiment.csv --x dose --y response --hue treatment --title "Dose Response" --output dose_response.png
```

### Clustered heatmap:
```bash
python3 {baseDir}/scripts/plot_data.py heatmap --data expression.csv --cluster --cmap RdBu_r --title "Gene Expression" --output heatmap.svg --format svg
```

### Box plot with multiple groups:
```bash
python3 {baseDir}/scripts/plot_data.py box --data measurements.csv --x condition --y value --hue treatment --title "Treatment Effects"
```

### Histogram with KDE:
```bash
python3 {baseDir}/scripts/plot_data.py histogram --data samples.csv --x measurement --bins 30 --kde --title "Distribution"
```

### Publication-quality figure:
```bash
python3 {baseDir}/scripts/plot_data.py scatter --data results.csv --x x --y y --figsize 8,6 --dpi 300 --format svg --style white --output figure1.svg
```

## Color Palettes

- **deep**: Default seaborn palette
- **muted**: Muted colors
- **bright**: Bright colors
- **pastel**: Pastel colors
- **dark**: Dark colors
- **colorblind**: Colorblind-friendly
- **viridis**: Perceptually uniform
- **plasma**: Perceptually uniform
- **RdBu**: Red-Blue diverging
- **coolwarm**: Cool-Warm diverging

## Notes

- Data can be provided as CSV files or JSON strings
- SVG output is recommended for publications
- Use `--dpi 300` for high-resolution figures
- Column names with spaces should be quoted
