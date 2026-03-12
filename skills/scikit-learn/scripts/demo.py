#!/usr/bin/env python3
"""
scikit-learn — Lightweight ML Regression Demo (ScienceClaw)

Purpose
  - Provide a stable CLI entrypoint for the `scikit-learn` skill so agents can
    invoke it in online investigations without accidentally running non-CLI
    example modules in this directory.

Behavior
  - Accepts --query <topic>
  - Optionally accepts --input-json with upstream numeric rows
  - Fits a simple log-log linear regression and returns JSON with R² and an
    interpretable scaling exponent (alpha)

Usage:
  python demo.py --query "SSTR2 binding potency scaling" --format json
"""

import argparse
import hashlib
import json
import sys
from typing import Optional, Tuple, List

import numpy as np

try:
    from sklearn.linear_model import LinearRegression
except ImportError:
    print(json.dumps({"error": "scikit-learn not installed"}))
    sys.exit(1)


INPUT_SCHEMA = {
    "input_json_fields": ["rows"],
    "rows_schema": {"x": "number", "y": "number"},
    "optional_fields": ["x_label", "y_label"],
    "description": "Linear regression on (x, y) rows (log-log compatible).",
    "fallback": "synthetic (x, y) rows derived from --query topic",
}


def _seed(query: str) -> int:
    return int(hashlib.md5(query.encode("utf-8")).hexdigest(), 16) % (2**32)


def _load_upstream_rows(input_json: str) -> List[dict]:
    if not input_json:
        return []
    try:
        data = json.loads(input_json)
        rows = data.get("rows", [])
        if isinstance(rows, list) and len(rows) >= 3 and isinstance(rows[0], dict):
            if "x" in rows[0] and "y" in rows[0]:
                return rows
    except Exception:
        pass
    return []


def _make_synthetic_rows(query: str, n: int = 40) -> Tuple[List[dict], str, str]:
    rng = np.random.default_rng(_seed(query))
    q = query.lower()

    # Default: power-law style log-log linear relationship.
    x_label = "log10(parameters)"
    y_label = "log10(outcome)"
    alpha_true = 0.08 + float(rng.normal(0, 0.01))

    if any(k in q for k in ("ic50", "ec50", "kd", "ki", "binding", "dose", "concentration")):
        x_label = "log10(concentration)"
        y_label = "log10(response)"
        alpha_true = 1.4 + float(rng.normal(0, 0.15))

    x = rng.uniform(6.0, 11.0, n)  # already log-scale
    y = -alpha_true * x + (3.5 + float(rng.normal(0, 0.1))) + rng.normal(0, 0.05, n)
    rows = [{"x": float(xi), "y": float(yi), "x_label": x_label, "y_label": y_label} for xi, yi in zip(x, y)]
    return rows, x_label, y_label


def run_regression(query: str, rows: Optional[List[dict]] = None) -> dict:
    if rows:
        x_label = rows[0].get("x_label", "x")
        y_label = rows[0].get("y_label", "y")
        x = np.array([float(r["x"]) for r in rows], dtype=float).reshape(-1, 1)
        y = np.array([float(r["y"]) for r in rows], dtype=float)
        data_source = "upstream"
    else:
        rows, x_label, y_label = _make_synthetic_rows(query)
        x = np.array([float(r["x"]) for r in rows], dtype=float).reshape(-1, 1)
        y = np.array([float(r["y"]) for r in rows], dtype=float)
        data_source = "synthetic"

    model = LinearRegression()
    model.fit(x, y)
    r2 = float(model.score(x, y))
    slope = float(model.coef_[0])
    intercept = float(model.intercept_)

    # For log-log style power-law fits: y = log(A) - alpha * x  -> alpha = -slope
    alpha = -slope

    return {
        "topic": query,
        "model": "LinearRegression",
        "data_source": data_source,
        "n_observations": int(len(y)),
        "x_label": x_label,
        "y_label": y_label,
        "coefficients": {"intercept": round(intercept, 6), "slope": round(slope, 6)},
        "r2": round(r2, 6),
        "r_squared": round(r2, 6),
        "alpha": round(alpha, 6),
        "scaling_exponent": round(alpha, 6),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="scikit-learn regression demo (ScienceClaw)")
    p.add_argument("--describe-schema", action="store_true", help="Print expected --input-json schema as JSON and exit")
    p.add_argument("--query", "-q", default="general trend", help="Topic to analyse")
    p.add_argument("--format", "-f", default="summary", choices=["summary", "json"])
    p.add_argument("--input-json", default="", help="JSON with upstream data: {rows: [{x, y}], x_label?, y_label?}")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps(INPUT_SCHEMA))
        return

    rows = _load_upstream_rows(args.input_json)
    out = run_regression(args.query, rows=rows if rows else None)

    if args.format == "json":
        print(json.dumps(out, indent=2))
    else:
        print("=" * 60)
        print("scikit-learn LinearRegression")
        print("=" * 60)
        print(f"Topic: {out['topic']}")
        print(f"N: {out['n_observations']}")
        print(f"R²: {out['r2']}")
        print(f"alpha: {out['alpha']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
