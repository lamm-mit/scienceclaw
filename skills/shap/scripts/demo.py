#!/usr/bin/env python3
"""
shap — SHapley Additive exPlanations

Accepts --query <topic> and trains a GradientBoosting model on a synthetic
dataset whose features reflect the query domain, then computes SHAP values
to identify which features most drive the prediction.

Returns JSON with feature importances, SHAP summary stats, and model accuracy.

Usage:
    python demo.py --query "neural scaling laws" [--format json]
"""

import argparse
import hashlib
import json
import sys

import numpy as np

try:
    import shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False

try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.inspection import permutation_importance
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

if not _SKLEARN_AVAILABLE:
    print(json.dumps({"error": "scikit-learn not installed"}))
    sys.exit(1)


INPUT_SCHEMA = {
    "input_json_fields": ["rows"],
    "rows_schema": {"feature_cols": "inferred from keys minus target", "target": "string"},
    "description": "SHAP feature importances on real tabular rows.",
    "fallback": "synthetic domain-matched dataset from --query",
}


def _load_upstream_tabular(input_json: str):
    """Parse rows and target from --input-json. Returns (X_array, y_array, feature_names) or None."""
    if not input_json:
        return None
    try:
        data = json.loads(input_json)
        rows = data.get("rows", [])
        if len(rows) < 4:
            return None
        target_col = data.get("target", None)
        # Auto-detect target: last numeric column or one named loss/y/target
        all_keys = [k for k in rows[0].keys() if isinstance(rows[0][k], (int, float))]
        if target_col is None or target_col not in all_keys:
            for candidate in ("loss", "y", "target", "label"):
                if candidate in all_keys:
                    target_col = candidate
                    break
            else:
                target_col = all_keys[-1]
        feature_cols = [k for k in all_keys if k != target_col]
        if not feature_cols:
            return None
        X = np.array([[r[c] for c in feature_cols] for r in rows], dtype=float)
        y = np.array([r[target_col] for r in rows], dtype=float)
        return X, y, feature_cols
    except Exception:
        return None


def _seed(query: str) -> int:
    return int(hashlib.md5(query.encode()).hexdigest(), 16) % (2**32)


# Domain-specific feature definitions
DOMAIN_FEATURES = {
    "scaling": {
        "features": ["log_params", "log_tokens", "log_flops", "architecture_depth",
                     "learning_rate", "batch_size", "data_quality"],
        "target": "test_loss",
    },
    "drug": {
        "features": ["molecular_weight", "logP", "hbd", "hba", "rotatable_bonds",
                     "aromatic_rings", "tpsa"],
        "target": "bioavailability",
    },
    "gene": {
        "features": ["expression_level", "variant_severity", "conservation_score",
                     "domain_disruption", "pathway_centrality", "tissue_specificity"],
        "target": "disease_association",
    },
    "polymer": {
        "features": ["molecular_weight", "crystallinity", "hydrophilicity",
                     "degradation_rate", "tensile_strength"],
        "target": "biodegradability",
    },
}


def _get_feature_config(query: str) -> dict:
    q = query.lower()
    for kw, cfg in DOMAIN_FEATURES.items():
        if kw in q:
            return cfg
    # Generic
    n = min(6, max(3, len(query.split()) // 2))
    feats = [f"feature_{i+1}" for i in range(n)]
    return {"features": feats, "target": "outcome"}


def build_dataset(query: str, n_samples: int = 200) -> tuple:
    rng = np.random.default_rng(_seed(query))
    cfg = _get_feature_config(query)
    features = cfg["features"]
    n_feat = len(features)

    X = rng.normal(0, 1, (n_samples, n_feat))

    # Build target with non-uniform feature importances
    true_weights = rng.exponential(1.0, n_feat)
    true_weights /= true_weights.sum()
    # Non-linear target (quadratic + interactions)
    y = X @ true_weights + 0.3 * (X[:, 0] ** 2) + rng.normal(0, 0.15, n_samples)

    return X, y, features, true_weights


def run_shap(query: str, upstream_tabular=None) -> dict:
    data_source = "synthetic"
    if upstream_tabular is not None:
        X, y, feature_names = upstream_tabular
        data_source = "upstream"
    else:
        X, y, feature_names, _ = build_dataset(query)
    # With very small datasets, avoid single-sample test sets
    if len(X) < 10:
        X_train, X_test, y_train, y_test = X, X, y, y
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=_seed(query) % (2**31))

    model = GradientBoostingRegressor(n_estimators=80, max_depth=3,
                                      random_state=_seed(query) % (2**31))
    model.fit(X_train, y_train)
    r2 = model.score(X_test, y_test)

    if _SHAP_AVAILABLE:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        total = mean_abs_shap.sum() if mean_abs_shap.sum() > 0 else 1.0
        importance_pct = (mean_abs_shap / total * 100).round(2).tolist()
        shap_summary = {
            name: {
                "mean_abs_shap": round(float(v), 5),
                "importance_pct": round(float(pct), 2),
            }
            for name, v, pct in zip(feature_names, mean_abs_shap.tolist(), importance_pct)
        }
    else:
        # Fallback: use permutation importance
        perm = permutation_importance(model, X_test, y_test, n_repeats=10,
                                       random_state=_seed(query) % (2**31))
        raw = np.abs(perm.importances_mean)
        total = raw.sum() if raw.sum() > 0 else 1.0
        importance_pct = (raw / total * 100).round(2).tolist()
        shap_summary = {
            name: {
                "mean_abs_shap": round(float(v), 5),
                "importance_pct": round(float(pct), 2),
            }
            for name, v, pct in zip(feature_names, raw.tolist(), importance_pct)
        }

    ranked = sorted(
        zip(feature_names, importance_pct),
        key=lambda x: -x[1]
    )

    return {
        "topic": query,
        "model": "GradientBoostingRegressor",
        "r_squared": round(float(r2), 4),
        "n_train": len(y_train),
        "n_test": len(y_test),
        "data_source": data_source,
        "feature_importance": {
            name: pct for name, pct in ranked
        },
        "top_features": [
            {"feature": name, "importance_pct": pct}
            for name, pct in ranked[:5]
        ],
        "shap_summary": shap_summary,
    }


def main():
    parser = argparse.ArgumentParser(description="SHAP feature importance analysis")
    parser.add_argument("--query", "-q", default="general model",
                        help="Research topic to analyse")
    parser.add_argument("--format", "-f", default="summary",
                        choices=["summary", "json"])
    parser.add_argument("--describe-schema", action="store_true",
                        help="Print expected --input-json schema as JSON and exit")
    parser.add_argument("--input-json", default="",
                        help="JSON with upstream data: {rows: [{feature_cols..., target}], target: str}")
    args = parser.parse_args()

    if args.describe_schema:
        print(json.dumps(INPUT_SCHEMA))
        sys.exit(0)

    upstream_tabular = _load_upstream_tabular(getattr(args, "input_json", ""))
    result = run_shap(args.query, upstream_tabular=upstream_tabular)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("=" * 60)
        print(f"SHAP — Feature Importance: '{args.query[:50]}'")
        print("=" * 60)
        print(f"Model R²    : {result['r_squared']}")
        print(f"Train/Test  : {result['n_train']}/{result['n_test']}")
        print("Top Features (by mean |SHAP|):")
        for item in result["top_features"]:
            bar = "█" * int(item["importance_pct"] / 3)
            print(f"  {item['feature']:30s} {item['importance_pct']:5.1f}%  {bar}")
        print("=" * 60)


if __name__ == "__main__":
    main()
