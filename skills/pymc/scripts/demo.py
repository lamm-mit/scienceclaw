#!/usr/bin/env python3
"""
pymc — Bayesian Linear Regression Demo (ScienceClaw)

Stable CLI entrypoint for the `pymc` skill.

Fits a simple Bayesian linear model on (x, y) rows (typically log-log scaling
data) and returns posterior summary statistics for the slope and derived
exponent alpha.

Usage:
  python demo.py --query "SSTR2 potency scaling" --format json
  python demo.py --query "SSTR2 potency scaling" --input-json '{"rows":[{"x":1,"y":2},...]}' --format json
"""

import argparse
import hashlib
import json
import sys
from typing import List, Optional, Tuple

import numpy as np

try:
    import pymc as pm
except ImportError:
    print(json.dumps({"error": "pymc not installed"}))
    sys.exit(1)


INPUT_SCHEMA = {
    "input_json_fields": ["rows"],
    "rows_schema": {"x": "number", "y": "number"},
    "optional_fields": ["x_label", "y_label"],
    "description": "Bayesian linear regression on upstream (x, y) rows.",
    "fallback": "synthetic (x, y) derived from --query topic",
}


def _seed(query: str) -> int:
    return int(hashlib.md5(query.encode("utf-8")).hexdigest(), 16) % (2**32)


def _load_upstream_rows(input_json: str) -> List[dict]:
    if not input_json:
        return []
    try:
        data = json.loads(input_json)
        rows = data.get("rows", [])
        if isinstance(rows, list) and len(rows) >= 5 and isinstance(rows[0], dict):
            if "x" in rows[0] and "y" in rows[0]:
                return rows
    except Exception:
        pass
    return []


def _make_synthetic_rows(query: str, n: int = 60) -> Tuple[List[dict], str, str]:
    rng = np.random.default_rng(_seed(query))
    q = query.lower()

    x_label = "log10(parameters)"
    y_label = "log10(outcome)"
    alpha_true = 0.08 + float(rng.normal(0, 0.01))

    if any(k in q for k in ("ic50", "ec50", "kd", "ki", "binding", "dose", "concentration")):
        x_label = "log10(concentration)"
        y_label = "log10(response)"
        alpha_true = 1.2 + float(rng.normal(0, 0.12))

    x = rng.uniform(6.0, 11.0, n)
    y = -alpha_true * x + (3.7 + float(rng.normal(0, 0.08))) + rng.normal(0, 0.06, n)
    rows = [{"x": float(xi), "y": float(yi), "x_label": x_label, "y_label": y_label} for xi, yi in zip(x, y)]
    return rows, x_label, y_label


def run_bayes(query: str, rows: Optional[List[dict]] = None) -> dict:
    if rows:
        x_label = rows[0].get("x_label", "x")
        y_label = rows[0].get("y_label", "y")
        x = np.array([float(r["x"]) for r in rows], dtype=float)
        y = np.array([float(r["y"]) for r in rows], dtype=float)
        data_source = "upstream"
    else:
        rows, x_label, y_label = _make_synthetic_rows(query)
        x = np.array([float(r["x"]) for r in rows], dtype=float)
        y = np.array([float(r["y"]) for r in rows], dtype=float)
        data_source = "synthetic"

    rng = np.random.default_rng(_seed(query))
    pm_rng = int(rng.integers(0, 2**31 - 1))

    with pm.Model() as model:
        intercept = pm.Normal("intercept", mu=0.0, sigma=10.0)
        slope = pm.Normal("slope", mu=0.0, sigma=5.0)
        sigma = pm.HalfNormal("sigma", sigma=2.0)
        mu = intercept + slope * x
        pm.Normal("y", mu=mu, sigma=sigma, observed=y)

        idata = pm.sample(
            draws=350,
            tune=350,
            chains=2,
            cores=1,
            random_seed=pm_rng,
            progressbar=False,
            compute_convergence_checks=False,
            target_accept=0.9,
        )

    slope_samples = idata.posterior["slope"].values.reshape(-1)
    intercept_samples = idata.posterior["intercept"].values.reshape(-1)

    slope_mean = float(np.mean(slope_samples))
    slope_lo = float(np.quantile(slope_samples, 0.025))
    slope_hi = float(np.quantile(slope_samples, 0.975))

    alpha_mean = -slope_mean
    alpha_lo = -slope_hi
    alpha_hi = -slope_lo

    return {
        "topic": query,
        "model": "BayesianLinearRegression",
        "data_source": data_source,
        "n_observations": int(len(y)),
        "x_label": x_label,
        "y_label": y_label,
        "posterior": {
            "slope_mean": round(slope_mean, 6),
            "slope_95ci": [round(slope_lo, 6), round(slope_hi, 6)],
            "intercept_mean": round(float(np.mean(intercept_samples)), 6),
        },
        "alpha": round(alpha_mean, 6),
        "alpha_lower": round(alpha_lo, 6),
        "alpha_upper": round(alpha_hi, 6),
        "credible_interval": [round(alpha_lo, 6), round(alpha_hi, 6)],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="PyMC Bayesian regression demo (ScienceClaw)")
    p.add_argument("--describe-schema", action="store_true", help="Print expected --input-json schema as JSON and exit")
    p.add_argument("--query", "-q", default="general trend", help="Topic to analyse")
    p.add_argument("--format", "-f", default="summary", choices=["summary", "json"])
    p.add_argument("--input-json", default="", help="JSON with upstream data: {rows: [{x, y}]}")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps(INPUT_SCHEMA))
        return

    rows = _load_upstream_rows(args.input_json)
    out = run_bayes(args.query, rows=rows if rows else None)

    if args.format == "json":
        print(json.dumps(out, indent=2))
    else:
        print("=" * 60)
        print("PyMC Bayesian Linear Regression")
        print("=" * 60)
        print(f"Topic: {out['topic']}")
        print(f"N: {out['n_observations']}")
        print(f"alpha: {out['alpha']}  95% CI={out['credible_interval']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
