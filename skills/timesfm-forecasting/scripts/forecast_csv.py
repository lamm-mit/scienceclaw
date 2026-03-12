#!/usr/bin/env python3
"""
TimesFM End-to-End CSV Forecasting

Loads TimesFM 2.5 from Hugging Face, forecasts numeric columns in a CSV,
and outputs point forecasts + 80%/90% prediction intervals.

Usage:
    python3 forecast_csv.py --input data.csv --horizon 30
    python3 forecast_csv.py --input data.csv --horizon 14 --value-col expression --date-col time
    python3 forecast_csv.py --input data.csv --horizon 7 --output forecast.csv
    python3 forecast_csv.py --input data.csv --horizon 30 --format json

Output (CSV default):
    step,point_forecast,pi80_lower,pi80_upper,pi90_lower,pi90_upper

Output (JSON):
    {"horizon": 30, "forecasts": [{"step": 1, "point": 1.23, ...}]}
"""

import argparse
import json
import sys
import subprocess


def run_preflight(model_version: str = "v2.5") -> bool:
    """Run system check; return True if OK."""
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    check_script = os.path.join(script_dir, "check_system.py")
    result = subprocess.run(
        [sys.executable, check_script, "--model", model_version, "--json"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        try:
            report = json.loads(result.stdout)
            print(f"System check failed: {report.get('critical_failures')}",
                  file=sys.stderr)
        except Exception:
            print(f"System check failed:\n{result.stdout}", file=sys.stderr)
        return False
    return True


def load_csv(input_path: str, date_col: str = None, value_col: str = None):
    """Load CSV and return (dates, values, column_name) tuple."""
    import pandas as pd
    import numpy as np

    df = pd.read_csv(input_path)

    # Auto-detect date column
    if date_col is None:
        for col in df.columns:
            if any(k in col.lower() for k in ["date", "time", "timestamp", "t", "index"]):
                date_col = col
                break

    # Auto-detect value column (first numeric column that isn't the date)
    if value_col is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if date_col and date_col in numeric_cols:
            numeric_cols = [c for c in numeric_cols if c != date_col]
        if not numeric_cols:
            raise ValueError("No numeric columns found in CSV")
        value_col = numeric_cols[0]
        print(f"Auto-detected value column: '{value_col}'", file=sys.stderr)

    values = df[value_col].dropna().values.astype(float)
    dates = df[date_col].values if date_col and date_col in df.columns else None

    return dates, values, value_col


def run_forecast(values, horizon: int, batch_size: int = 32,
                 backend: str = "cpu") -> dict:
    """
    Load TimesFM and run forecast. Returns forecast dict.

    Downloads model from HuggingFace on first run (~800MB for v2.5).
    """
    import numpy as np

    # Detect best available backend
    if backend == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                backend = "gpu"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                backend = "cpu"  # MPS backend in timesfm uses "cpu" param
            else:
                backend = "cpu"
        except ImportError:
            backend = "cpu"

    print(f"Loading TimesFM 2.5 (backend={backend})...", file=sys.stderr)
    print("First run downloads ~2GB from Hugging Face.", file=sys.stderr)

    import timesfm

    tfm = timesfm.TimesFm(
        hparams=timesfm.TimesFmHparams(
            backend=backend,
            per_core_batch_size=batch_size,
            horizon_len=horizon,
        ),
        checkpoint=timesfm.TimesFmCheckpoint(
            huggingface_repo_id="google/timesfm-2.5-500m-pytorch"
        ),
    )
    tfm.load_from_checkpoint(repo_id="google/timesfm-2.5-500m-pytorch")

    # Determine frequency based on series length
    # Heuristic: long series = high-freq
    freq = 0 if len(values) > 200 else 1

    print(f"Running forecast: horizon={horizon}, context_len={len(values)}, freq={freq}",
          file=sys.stderr)

    point_forecast, quantile_forecast = tfm.forecast(
        inputs=[values],
        freq=[freq],
    )

    # quantile_forecast shape: (batch, horizon, num_quantiles)
    # TimesFM 2.5 default quantile levels: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    # Indices:                               0    1    2    3    4    5    6    7    8
    pf = point_forecast[0]   # (horizon,)
    qf = quantile_forecast[0]  # (horizon, 9)

    return {
        "point": pf.tolist(),
        "pi80_lower": qf[:, 1].tolist(),   # 20th percentile
        "pi80_upper": qf[:, 7].tolist(),   # 80th percentile
        "pi90_lower": qf[:, 0].tolist(),   # 10th percentile
        "pi90_upper": qf[:, 8].tolist(),   # 90th percentile
    }


def output_csv(forecast: dict, output_path: str = None):
    """Write forecast to CSV."""
    import csv
    import io

    horizon = len(forecast["point"])
    rows = []
    for i in range(horizon):
        rows.append({
            "step": i + 1,
            "point_forecast": round(forecast["point"][i], 6),
            "pi80_lower": round(forecast["pi80_lower"][i], 6),
            "pi80_upper": round(forecast["pi80_upper"][i], 6),
            "pi90_lower": round(forecast["pi90_lower"][i], 6),
            "pi90_upper": round(forecast["pi90_upper"][i], 6),
        })

    fields = ["step", "point_forecast", "pi80_lower", "pi80_upper",
              "pi90_lower", "pi90_upper"]

    if output_path:
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Forecast written to {output_path}", file=sys.stderr)
    else:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        print(buf.getvalue())


def output_json(forecast: dict, output_path: str = None, value_col: str = "value"):
    """Write forecast to JSON."""
    horizon = len(forecast["point"])
    result = {
        "column": value_col,
        "horizon": horizon,
        "forecasts": [
            {
                "step": i + 1,
                "point_forecast": round(forecast["point"][i], 6),
                "pi80_lower": round(forecast["pi80_lower"][i], 6),
                "pi80_upper": round(forecast["pi80_upper"][i], 6),
                "pi90_lower": round(forecast["pi90_lower"][i], 6),
                "pi90_upper": round(forecast["pi90_upper"][i], 6),
            }
            for i in range(horizon)
        ]
    }

    out = json.dumps(result, indent=2)
    if output_path:
        with open(output_path, "w") as f:
            f.write(out)
        print(f"Forecast written to {output_path}", file=sys.stderr)
    else:
        print(out)


def main():
    parser = argparse.ArgumentParser(
        description="Forecast time series in a CSV file using TimesFM 2.5"
    )
    parser.add_argument("--input", required=True, help="Input CSV file path")
    parser.add_argument("--horizon", type=int, required=True,
                        help="Number of steps to forecast")
    parser.add_argument("--date-col", default=None,
                        help="Name of date/time column (auto-detected if not provided)")
    parser.add_argument("--value-col", default=None,
                        help="Name of value column to forecast (auto-detected if not provided)")
    parser.add_argument("--output", default=None,
                        help="Output file path (default: print to stdout)")
    parser.add_argument("--format", choices=["csv", "json"], default="csv",
                        help="Output format (default: csv)")
    parser.add_argument("--batch-size", type=int, default=32,
                        help="Batch size for model inference (default: 32)")
    parser.add_argument("--backend", choices=["cpu", "gpu", "auto"], default="auto",
                        help="Compute backend (default: auto-detect)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip system requirements check")

    args = parser.parse_args()

    # Preflight
    if not args.skip_preflight:
        if not run_preflight("v2.5"):
            print("Run with --skip-preflight to bypass (may fail or be slow).",
                  file=sys.stderr)
            sys.exit(1)

    try:
        # Load data
        dates, values, value_col = load_csv(args.input, args.date_col, args.value_col)
        print(f"Loaded {len(values)} data points from '{value_col}'", file=sys.stderr)

        if len(values) < 5:
            print(f"Error: Need at least 5 data points, got {len(values)}", file=sys.stderr)
            sys.exit(1)

        # Run forecast
        forecast = run_forecast(values, args.horizon, args.batch_size, args.backend)

        # Output
        if args.format == "json":
            output_json(forecast, args.output, value_col)
        else:
            output_csv(forecast, args.output)

    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e), "type": type(e).__name__}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
