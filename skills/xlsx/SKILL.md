---
name: xlsx
description: Extract and preview data from Excel and CSV spreadsheets for scientific analysis
metadata:
  openclaw:
    emoji: "📊"
    requires:
      bins:
        - python3
---

## Overview

Excel and CSV spreadsheet processing for scientific supplementary data, experimental results, and datasets. Extracts sheet names, data previews, and shape information from .xlsx, .xls, and .csv files using openpyxl and pandas.

Particularly useful for processing supplementary tables from publications, high-throughput screening results, omics datasets, and any tabular data shared as spreadsheets.

## Usage

```bash
# Preview first 20 rows from all sheets of an Excel file
python3 skills/xlsx/scripts/xlsx_extract.py --file /path/to/supplementary.xlsx

# Preview specific sheet
python3 skills/xlsx/scripts/xlsx_extract.py --file /path/to/data.xlsx --sheet "Table S1"

# Limit preview rows
python3 skills/xlsx/scripts/xlsx_extract.py --file /path/to/screening.xlsx --head 50

# Process a CSV file
python3 skills/xlsx/scripts/xlsx_extract.py --file /path/to/results.csv
```

## Output Format

```json
{
  "file": "/path/to/supplementary.xlsx",
  "sheets": ["Table S1", "Table S2", "Raw Data"],
  "data": {
    "Table S1": [
      ["Gene", "Log2FC", "p-value", "FDR"],
      ["BRCA1", "2.4", "0.0001", "0.001"],
      ["TP53", "-1.8", "0.003", "0.02"]
    ]
  },
  "shape": {
    "rows": 1250,
    "cols": 8
  }
}
```

## Dependencies

```bash
pip install openpyxl pandas
```
