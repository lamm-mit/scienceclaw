---
name: csv-read
description: Read a CSV or XLSX file and return columns, shape, dtypes, and first N rows as JSON.
---

# csv-read

Load a CSV or Excel file using pandas and return a JSON preview including column names, shape, data types, and the first N rows.

## Usage

```bash
python3 scripts/csv_read.py --path /data/results.csv --max-rows 50
```

## Output

JSON with keys: `columns`, `shape`, `dtypes`, `data` (list of rows).
