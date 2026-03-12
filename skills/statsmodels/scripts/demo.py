#!/usr/bin/env python3
"""
statsmodels — Regression & Statistical Modeling

Accepts --query <topic> and fits an OLS power-law model on synthetic data
whose structure is derived from the query keywords (parameter count vs. loss
for scaling-law queries, dose-response for biology queries, etc.).
Returns JSON with regression coefficients, p-values, R², and AIC.

Usage:
    python demo.py --query "neural scaling laws" [--format json]
"""

import argparse
import hashlib
import json
import sys
import re

import numpy as np

try:
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
except ImportError:
    # Don't hard-fail an autonomous chain; return structured "unavailable".
    print(json.dumps({"status": "unavailable", "skill": "statsmodels", "error": "statsmodels not installed"}))
    sys.exit(0)


INPUT_SCHEMA = {
    "input_json_fields": ["rows"],
    "rows_schema": {"x": "number", "y": "number"},
    "optional_fields": ["x_label", "y_label"],
    "description": "OLS regression on (x, y) pairs.",
    "fallback": "synthetic data derived from --query topic",
}


def _load_upstream_rows(input_json: str) -> list:
    """Extract (x, y) rows from --input-json if present and valid."""
    if not input_json:
        return []
    try:
        data = json.loads(input_json)
        rows = data.get("rows", [])
        if rows and isinstance(rows, list) and len(rows) >= 2:
            if "x" in rows[0] and "y" in rows[0]:
                return rows
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Derive a deterministic synthetic dataset from the query topic
# ---------------------------------------------------------------------------

def _topic_seed(query: str) -> int:
    return int(hashlib.md5(query.encode()).hexdigest(), 16) % (2**32)


def _make_dataset(query: str) -> dict:
    """
    Build a small (n=40) dataset whose shape reflects the query topic.
    Returns {"x": [...], "y": [...], "x_label": str, "y_label": str, "model": str}.
    """
    rng = np.random.default_rng(_topic_seed(query))
    q = query.lower()

    # Determine data shape from keywords
    if any(kw in q for kw in ["scaling", "parameter", "neural", "language model", "llm"]):
        # Power-law: loss ∝ N^{-alpha}  in log-log space
        alpha_true = 0.076 + rng.normal(0, 0.008)
        log_N = rng.uniform(6, 11.5, 40)      # log10 of param count (100M–300B)
        log_L = -alpha_true * log_N + 3.8 + rng.normal(0, 0.04, 40)
        x = log_N
        y = log_L
        x_label = "log₁₀(Parameters)"
        y_label  = "log₁₀(Test loss)"
        model_name = "power-law (log-log OLS)"
    elif any(kw in q for kw in ["dose", "concentration", "drug", "ic50", "inhibit"]):
        # Hill equation linearised: log(E/(E_max-E)) vs log(C)
        n_hill = 1.5 + rng.normal(0, 0.1)
        log_C  = rng.uniform(-3, 3, 40)
        log_E  = n_hill * log_C - 0.5 + rng.normal(0, 0.15, 40)
        x = log_C
        y = log_E
        x_label = "log₁₀(Concentration)"
        y_label  = "log₁₀(Response)"
        model_name = "Hill (log-log OLS)"
    elif any(kw in q for kw in ["gene", "expression", "protein", "sequence", "variant"]):
        # Linear: expression ~ copy_number
        x = rng.uniform(1, 10, 40)
        y = 2.3 * x + rng.normal(0, 0.6, 40)
        x_label = "Copy number"
        y_label  = "Expression (log₂ TPM)"
        model_name = "linear OLS"
    else:
        # Generic linear trend
        x = rng.uniform(0, 10, 40)
        y = 1.8 * x + rng.normal(0, 1.2, 40)
        x_label = "X"
        y_label  = "Y"
        model_name = "linear OLS"

    return {"x": x.tolist(), "y": y.tolist(),
            "x_label": x_label, "y_label": y_label, "model": model_name}


def run_regression(query: str, upstream_rows: list = None) -> dict:
    if upstream_rows:
        ds = {
            "x": [r["x"] for r in upstream_rows],
            "y": [r["y"] for r in upstream_rows],
            "x_label": upstream_rows[0].get("x_label", "x"),
            "y_label": upstream_rows[0].get("y_label", "y"),
            "model": "OLS (upstream data)",
            "data_source": "upstream",
        }
    else:
        ds = _make_dataset(query)
        ds["data_source"] = "synthetic"
    x = np.array(ds["x"])
    y = np.array(ds["y"])

    X = sm.add_constant(x)
    result = sm.OLS(y, X).fit()

    intercept, slope = result.params
    p_intercept, p_slope = result.pvalues

    # For scaling / power-law: slope in log-log = -alpha
    is_loglog = "log" in ds["x_label"].lower() and "log" in ds["y_label"].lower()
    exponent = -slope if is_loglog else None

    out = {
        "topic": query,
        "model": ds["model"],
        "x_label": ds["x_label"],
        "y_label": ds["y_label"],
        "n_observations": len(x),
        "coefficients": {
            "intercept": round(float(intercept), 5),
            "slope": round(float(slope), 5),
        },
        "p_values": {
            "intercept": round(float(p_intercept), 5),
            "slope": round(float(p_slope), 6),
        },
        "r_squared": round(float(result.rsquared), 4),
        "adj_r_squared": round(float(result.rsquared_adj), 4),
        "aic": round(float(result.aic), 2),
        "bic": round(float(result.bic), 2),
        "f_statistic": round(float(result.fvalue), 3),
        "f_pvalue": round(float(result.f_pvalue), 6),
        "residual_std": round(float(np.std(result.resid)), 5),
    }
    if exponent is not None:
        out["scaling_exponent"] = round(exponent, 5)
        out["alpha"] = round(exponent, 5)

    out["data_source"] = ds.get("data_source", "synthetic")

    return out


def main():
    parser = argparse.ArgumentParser(description="statsmodels OLS regression")
    parser.add_argument("--query", "-q", default="general linear trend",
                        help="Research topic / question to model")
    parser.add_argument("--format", "-f", default="summary",
                        choices=["summary", "json"])
    parser.add_argument("--describe-schema", action="store_true",
                        help="Print expected --input-json schema as JSON and exit")
    parser.add_argument("--input-json", default="",
                        help="JSON with upstream data: {rows: [{x, y}]}")
    args = parser.parse_args()

    if args.describe_schema:
        print(json.dumps(INPUT_SCHEMA))
        sys.exit(0)

    upstream_rows = _load_upstream_rows(getattr(args, "input_json", ""))
    result = run_regression(args.query, upstream_rows=upstream_rows)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("=" * 60)
        print(f"statsmodels OLS — {result['model']}")
        print("=" * 60)
        print(f"Topic     : {result['topic']}")
        print(f"Variables : {result['x_label']} → {result['y_label']}")
        print(f"N         : {result['n_observations']}")
        print(f"Slope     : {result['coefficients']['slope']}"
              f"  (p={result['p_values']['slope']:.2e})")
        print(f"R²        : {result['r_squared']}")
        if "scaling_exponent" in result:
            print(f"α (exponent): {result['scaling_exponent']}")
        print(f"AIC / BIC : {result['aic']} / {result['bic']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
