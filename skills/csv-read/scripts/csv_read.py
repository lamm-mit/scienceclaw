"""
csv_read — load a CSV or XLSX file and return a JSON preview.
"""

import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Read a CSV or XLSX file and return JSON preview.")
    parser.add_argument("--path", required=True, help="Absolute path to the CSV or XLSX file.")
    parser.add_argument("--max-rows", type=int, default=100, help="Maximum rows to return (default 100).")
    args = parser.parse_args()

    try:
        import pandas as pd
        if args.path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(args.path)
        else:
            df = pd.read_csv(args.path)
        sample = df.head(args.max_rows)
        print(json.dumps({
            "columns": list(df.columns),
            "shape": list(df.shape),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "data": sample.values.tolist(),
        }))
    except Exception as e:
        print(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    main()
