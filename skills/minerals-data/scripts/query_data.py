#!/usr/bin/env python3
"""
Structured CSV Query Tool for Critical Minerals Data

Lists, describes, and queries CSV datasets from the critical minerals
corpus using pandas. Supports a simple pipe-delimited DSL for groupby,
aggregation, sorting, and filtering.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is required. Install with: pip install pandas>=2.0.0", file=sys.stderr)
    sys.exit(1)


DEFAULT_CORPUS_DIR = os.path.expanduser("~/critical-minerals-data")
CATALOG_FILE = ".csv_catalog.json"

# Source organization detection (same pattern as corpus-search)
SOURCE_ORG_MAP = {
    "usgs": "USGS",
    "comtrade": "UN Comtrade",
    "worldbank": "World Bank",
    "world_bank": "World Bank",
    "sec": "SEC",
    "wto": "WTO",
    "mindat": "Mindat",
    "mincan": "MinCan",
    "doe": "DOE",
    "eia": "EIA",
    "iea": "IEA",
}

# Commodity detection keywords
COMMODITY_KEYWORDS = {
    "rare_earth": ["rare earth", "ree", "lanthanide", "neodymium", "dysprosium"],
    "lithium": ["lithium"],
    "cobalt": ["cobalt"],
    "nickel": ["nickel"],
    "copper": ["copper"],
    "gallium": ["gallium"],
    "graphite": ["graphite"],
    "germanium": ["germanium"],
    "manganese": ["manganese"],
    "platinum_group": ["platinum", "palladium", "pgm"],
    "tungsten": ["tungsten"],
}

# Dangerous patterns to reject in filter expressions
UNSAFE_PATTERNS = [
    r"\bimport\b", r"\bexec\b", r"\beval\b", r"\bos\.", r"\bsys\.",
    r"\b__\w+__\b", r"\bopen\b", r"\bfile\b", r"\bsubprocess\b",
    r"\bcompile\b", r"\bglobals\b", r"\blocals\b", r"\bgetattr\b",
    r"\bsetattr\b", r"\bdelattr\b", r"\bbreakpoint\b",
]


def sanitize_filter(expr: str) -> str:
    """
    Sanitize a pandas query expression to prevent code injection.

    Raises ValueError if dangerous patterns are detected.
    """
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, expr, re.IGNORECASE):
            raise ValueError(f"Unsafe filter expression: contains forbidden pattern matching '{pattern}'")
    return expr


def read_csv_safe(filepath: str) -> pd.DataFrame:
    """Read CSV with encoding fallbacks."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            return pd.read_csv(filepath, encoding=encoding)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Error reading {filepath}: {e}", file=sys.stderr)
            return pd.DataFrame()
    print(f"Error: Could not read {filepath} with any encoding", file=sys.stderr)
    return pd.DataFrame()


def detect_source_org(filepath: str, corpus_dir: str) -> str:
    """Auto-detect source organization from directory name."""
    rel = os.path.relpath(filepath, corpus_dir)
    parts = Path(rel).parts
    for part in parts:
        key = part.lower().replace("-", "_").replace(" ", "_")
        if key in SOURCE_ORG_MAP:
            return SOURCE_ORG_MAP[key]
    return "unknown"


def detect_commodity(columns: List[str], filepath: str) -> str:
    """Detect commodity from column names and file path."""
    searchable = " ".join(columns).lower() + " " + filepath.lower()
    for commodity, keywords in COMMODITY_KEYWORDS.items():
        for kw in keywords:
            if kw in searchable:
                return commodity
    return "general"


def build_catalog(corpus_dir: str) -> List[Dict[str, Any]]:
    """Scan corpus directory for CSVs and build catalog."""
    catalog = []
    for root, dirs, files in os.walk(corpus_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in sorted(files):
            if not filename.lower().endswith(".csv"):
                continue

            filepath = os.path.join(root, filename)
            rel = os.path.relpath(filepath, corpus_dir)

            try:
                df = read_csv_safe(filepath)
                if df.empty:
                    continue

                source_org = detect_source_org(filepath, corpus_dir)
                commodity = detect_commodity(list(df.columns), filepath)

                catalog.append({
                    "path": rel,
                    "rows": len(df),
                    "columns": list(df.columns),
                    "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                    "source_org": source_org,
                    "commodity": commodity,
                    "size_bytes": os.path.getsize(filepath),
                })
            except Exception as e:
                print(f"  Warning: Could not catalog {rel}: {e}", file=sys.stderr)

    return catalog


def load_catalog(corpus_dir: str) -> List[Dict[str, Any]]:
    """Load or build CSV catalog."""
    catalog_path = os.path.join(corpus_dir, CATALOG_FILE)
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # Build fresh catalog
    print("Building CSV catalog...", file=sys.stderr)
    catalog = build_catalog(corpus_dir)
    save_catalog(corpus_dir, catalog)
    return catalog


def save_catalog(corpus_dir: str, catalog: List[Dict[str, Any]]):
    """Save CSV catalog to disk."""
    catalog_path = os.path.join(corpus_dir, CATALOG_FILE)
    os.makedirs(os.path.dirname(catalog_path) or ".", exist_ok=True)
    with open(catalog_path, "w") as f:
        json.dump(catalog, f, indent=2)


def list_datasets(corpus_dir: str, output_format: str = "table"):
    """List all available CSV datasets."""
    catalog = load_catalog(corpus_dir)

    if not catalog:
        print("No CSV datasets found.", file=sys.stderr)
        return

    if output_format == "json":
        print(json.dumps(catalog, indent=2))
        return

    # Table format
    print(f"\nAvailable CSV datasets ({len(catalog)} files):\n")
    print(f"{'Path':<50} {'Rows':>8} {'Cols':>6} {'Source':<15} {'Commodity':<15}")
    print("-" * 100)
    for entry in catalog:
        print(f"{entry['path']:<50} {entry['rows']:>8} {len(entry['columns']):>6} {entry['source_org']:<15} {entry['commodity']:<15}")
    print()


def describe_dataset(filepath: str, corpus_dir: str, output_format: str = "table"):
    """Show schema, dtypes, sample rows, and statistics for a dataset."""
    full_path = os.path.join(corpus_dir, filepath)
    if not os.path.exists(full_path):
        print(f"Error: Dataset not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    df = read_csv_safe(full_path)
    if df.empty:
        print("Error: Could not read dataset or dataset is empty.", file=sys.stderr)
        sys.exit(1)

    source_org = detect_source_org(full_path, corpus_dir)
    commodity = detect_commodity(list(df.columns), full_path)

    if output_format == "json":
        info = {
            "path": filepath,
            "rows": len(df),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "source_org": source_org,
            "commodity": commodity,
            "sample": df.head(5).to_dict(orient="records"),
            "statistics": df.describe(include="all").to_dict(),
        }
        print(json.dumps(info, indent=2, default=str))
        return

    # Table format
    print(f"\nDataset: {filepath}")
    print(f"Source: {source_org} | Commodity: {commodity}")
    print(f"Rows: {len(df):,} | Columns: {len(df.columns)}")
    print()

    print("Schema:")
    print(f"  {'Column':<30} {'Type':<15} {'Non-null':>10} {'Unique':>10}")
    print("  " + "-" * 70)
    for col in df.columns:
        non_null = df[col].notna().sum()
        unique = df[col].nunique()
        print(f"  {col:<30} {str(df[col].dtype):<15} {non_null:>10} {unique:>10}")
    print()

    print("Sample (first 5 rows):")
    print(df.head(5).to_string(index=False))
    print()

    # Numeric statistics
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        print("Statistics (numeric columns):")
        print(df[numeric_cols].describe().to_string())
        print()


def parse_dsl(dsl: str) -> List[Tuple[str, List[str]]]:
    """
    Parse pipe-delimited DSL into operations.

    Format: "groupby:col|agg:col:func|sort:col:dir|head:n|select:col1,col2"
    """
    operations = []
    for part in dsl.split("|"):
        part = part.strip()
        if not part:
            continue
        tokens = part.split(":")
        op = tokens[0].lower()
        args = tokens[1:]
        operations.append((op, args))
    return operations


def execute_query(df: pd.DataFrame, dsl: str) -> pd.DataFrame:
    """Execute DSL query against a DataFrame."""
    operations = parse_dsl(dsl)

    grouped = None
    for op, args in operations:
        if op == "groupby" and args:
            col = args[0]
            if col not in df.columns:
                print(f"Error: Column '{col}' not found. Available: {list(df.columns)}", file=sys.stderr)
                sys.exit(1)
            grouped = df.groupby(col)

        elif op == "agg" and len(args) >= 2:
            col, func = args[0], args[1]
            valid_funcs = {"sum", "mean", "count", "min", "max", "median", "std"}
            if func not in valid_funcs:
                print(f"Error: Unknown aggregation '{func}'. Valid: {valid_funcs}", file=sys.stderr)
                sys.exit(1)
            if grouped is not None:
                if col not in df.columns:
                    print(f"Error: Column '{col}' not found.", file=sys.stderr)
                    sys.exit(1)
                df = grouped[col].agg(func).reset_index()
            else:
                if col not in df.columns:
                    print(f"Error: Column '{col}' not found.", file=sys.stderr)
                    sys.exit(1)
                df = pd.DataFrame({col: [getattr(df[col], func)()]})
            grouped = None

        elif op == "sort" and args:
            col = args[0]
            ascending = True
            if len(args) > 1 and args[1].lower() == "desc":
                ascending = False
            if col not in df.columns:
                print(f"Error: Column '{col}' not found.", file=sys.stderr)
                sys.exit(1)
            df = df.sort_values(col, ascending=ascending)

        elif op == "head" and args:
            try:
                n = int(args[0])
                df = df.head(n)
            except ValueError:
                print(f"Error: Invalid head value '{args[0]}'", file=sys.stderr)

        elif op == "select" and args:
            cols = args[0].split(",")
            missing = [c for c in cols if c not in df.columns]
            if missing:
                print(f"Error: Columns not found: {missing}", file=sys.stderr)
                sys.exit(1)
            df = df[cols]

        else:
            print(f"Warning: Unknown operation '{op}', skipping", file=sys.stderr)

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Query and analyze critical minerals CSV datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Query DSL operations (pipe-delimited):
  groupby:col          Group by column
  agg:col:func         Aggregate (sum, mean, count, min, max, median, std)
  sort:col:dir         Sort (asc or desc)
  head:n               Take first n rows
  select:col1,col2     Select columns

Examples:
  %(prog)s --list
  %(prog)s --dataset usgs/production.csv --describe
  %(prog)s --dataset usgs/production.csv --query "groupby:commodity|agg:value:sum|sort:value:desc|head:10"
  %(prog)s --dataset usgs/trade.csv --filter "year >= 2022" --query "groupby:country|agg:value:sum"
        """,
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available CSV datasets",
    )
    parser.add_argument(
        "--dataset", "-d",
        help="Path to CSV file (relative to corpus dir)",
    )
    parser.add_argument(
        "--describe",
        action="store_true",
        help="Show schema, dtypes, sample rows, statistics",
    )
    parser.add_argument(
        "--query", "-q",
        help="Pipe-delimited DSL for pandas operations",
    )
    parser.add_argument(
        "--filter", "-f",
        help="Pandas query expression for filtering rows",
    )
    parser.add_argument(
        "--corpus-dir",
        default=DEFAULT_CORPUS_DIR,
        help=f"Directory containing data files (default: {DEFAULT_CORPUS_DIR})",
    )
    parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json", "csv"],
        help="Output format (default: table)",
    )

    args = parser.parse_args()

    # Validate corpus directory
    if not os.path.isdir(args.corpus_dir):
        print(f"Error: Corpus directory not found: {args.corpus_dir}", file=sys.stderr)
        print("Create the directory and add CSV files.", file=sys.stderr)
        sys.exit(1)

    # List mode
    if args.list:
        list_datasets(args.corpus_dir, args.format)
        return

    # Describe mode
    if args.dataset and args.describe:
        describe_dataset(args.dataset, args.corpus_dir, args.format)
        return

    # Query mode
    if args.dataset and (args.query or args.filter):
        full_path = os.path.join(args.corpus_dir, args.dataset)
        if not os.path.exists(full_path):
            print(f"Error: Dataset not found: {args.dataset}", file=sys.stderr)
            sys.exit(1)

        df = read_csv_safe(full_path)
        if df.empty:
            print("Error: Could not read dataset or dataset is empty.", file=sys.stderr)
            sys.exit(1)

        # Apply filter
        if args.filter:
            try:
                safe_filter = sanitize_filter(args.filter)
                df = df.query(safe_filter)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"Error applying filter: {e}", file=sys.stderr)
                sys.exit(1)

        # Apply DSL query
        if args.query:
            df = execute_query(df, args.query)

        # Output
        if args.format == "json":
            print(df.to_json(orient="records", indent=2, default_handler=str))
        elif args.format == "csv":
            print(df.to_csv(index=False))
        else:
            print(df.to_string(index=False))
        return

    # No valid action specified
    if args.dataset:
        print("Error: Specify --describe, --query, or --filter with --dataset", file=sys.stderr)
    else:
        print("Error: Specify --list, or --dataset with an action", file=sys.stderr)
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
