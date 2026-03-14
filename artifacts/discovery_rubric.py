#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from artifacts.artifact import Artifact
except Exception:  # pragma: no cover
    Artifact = None  # type: ignore


@dataclass(frozen=True)
class DiscoveryCheck:
    check_id: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class DiscoveryEvaluation:
    score: int  # 0-100
    tier: str   # survey|analysis|experiment|discovery
    checks: List[DiscoveryCheck]
    metrics: Dict[str, Any]

    def one_line_summary(self) -> str:
        parts = [f"tier={self.tier}", f"score={self.score}/100"]
        for c in self.checks:
            if not c.passed:
                parts.append(f"missing={c.check_id}")
        return ", ".join(parts)

    def to_markdown(self) -> str:
        lines = [
            "## Discovery Rubric",
            f"**Tier:** `{self.tier}`  ·  **DiscoveryScore:** `{self.score}/100`",
            "",
        ]
        for c in self.checks:
            mark = "✓" if c.passed else "✗"
            lines.append(f"- {mark} **{c.label}** — {c.detail}")
        return "\n".join(lines).strip() + "\n"


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _scan_numeric(obj: Any, *, max_depth: int = 6) -> Tuple[int, int]:
    """
    Return (numeric_count, vector_like_count) for nested structures.
    - numeric_count: number of numeric leaves found
    - vector_like_count: count of lists with >=3 numeric values
    """
    if max_depth <= 0:
        return 0, 0
    if _is_number(obj):
        return 1, 0
    if isinstance(obj, dict):
        n = v = 0
        for val in obj.values():
            dn, dv = _scan_numeric(val, max_depth=max_depth - 1)
            n += dn
            v += dv
        return n, v
    if isinstance(obj, list):
        nums = [x for x in obj if _is_number(x)]
        vector_like = 1 if len(nums) >= 3 else 0
        n = len(nums)
        v = vector_like
        for item in obj[:50]:
            dn, dv = _scan_numeric(item, max_depth=max_depth - 1)
            n += dn
            v += dv
        return n, v
    return 0, 0


def _has_key_like(obj: Any, needles: Tuple[str, ...], *, max_depth: int = 6) -> bool:
    if max_depth <= 0:
        return False
    if isinstance(obj, dict):
        for k, v in obj.items():
            k_str = str(k).lower()
            if any(n in k_str for n in needles):
                return True
            if _has_key_like(v, needles, max_depth=max_depth - 1):
                return True
    elif isinstance(obj, list):
        for item in obj[:80]:
            if _has_key_like(item, needles, max_depth=max_depth - 1):
                return True
    return False


def evaluate_discovery(
    *,
    inv_results: Optional[Dict[str, Any]] = None,
    artifacts: Optional[List["Artifact"]] = None,
) -> DiscoveryEvaluation:
    """
    Soft rubric (never gates posting).

    Heuristics are intentionally simple: demos/case studies can surface explicit
    fields (e.g., *_delta_*, *_baseline_*, *_ci_*), while generic investigations
    fall back to artifact-type signals.
    """
    inv_results = inv_results or {}
    artifacts = artifacts or []

    numeric_count, vector_like = _scan_numeric(inv_results)
    inv_metricish = _has_key_like(
        inv_results,
        (
            "metric",
            "score",
            "loss",
            "accuracy",
            "rmse",
            "auc",
            "pll",
            "energy",
            "force",
            "logp",
            "tpsa",
            "mw",
            "descriptor",
        ),
    )
    inv_has_quant = vector_like >= 1 or numeric_count >= 8 or (inv_metricish and numeric_count >= 3)

    # Baseline/control heuristics: explicit "wt_", "baseline", "control", "random"
    inv_has_baseline = _has_key_like(inv_results, ("wt_", "baseline", "control", "random"))

    # Delta/improvement heuristics: explicit "delta", "improv", "gain", "auc_delta", etc.
    inv_has_delta = _has_key_like(inv_results, ("delta", "improv", "gain", "lift"))

    # Uncertainty: explicit CI/SE/posterior/replicates
    inv_has_uncertainty = _has_key_like(inv_results, ("ci", "stderr", "std_err", "posterior", "bootstrap", "replicate", "seed"))

    # Artifact-based quantitative proxy: certain artifact types tend to include computed outputs.
    artifact_types = [getattr(a, "artifact_type", "") for a in artifacts]
    has_artifacts = len(artifacts) > 0
    has_lineage = any(getattr(a, "parent_artifact_ids", []) for a in artifacts)
    has_compute_artifact = any(
        t in {
            "sequence_design",
            "rdkit_properties",
            "admet_prediction",
            "ml_prediction",
            "simulation_data",
            "materials_data",
            "polymer_properties",
        }
        for t in artifact_types
    )

    provenance_ok = has_artifacts and (has_lineage or len(set(artifact_types)) >= 2)
    quantitative_ok = inv_has_quant or has_compute_artifact
    baseline_ok = inv_has_baseline
    uncertainty_ok = inv_has_uncertainty
    delta_ok = inv_has_delta

    # Score weights (soft rubric).
    score = 0
    score += 15 if provenance_ok else 0
    score += 25 if quantitative_ok else 0
    score += 20 if baseline_ok else 0
    score += 20 if uncertainty_ok else 0
    score += 20 if delta_ok else 0

    if not quantitative_ok:
        tier = "survey"
    elif quantitative_ok and not baseline_ok:
        tier = "analysis"
    elif quantitative_ok and baseline_ok and not (uncertainty_ok and delta_ok):
        tier = "experiment"
    else:
        tier = "discovery"

    checks = [
        DiscoveryCheck(
            "provenance",
            "Provenance & lineage",
            provenance_ok,
            "Artifacts present with cross-skill variety/lineage." if provenance_ok else "Missing artifact lineage or too few diverse artifacts.",
        ),
        DiscoveryCheck(
            "quantitative",
            "Quantitative computation",
            quantitative_ok,
            f"Numeric signals found (n≈{numeric_count})." if inv_has_quant else ("Compute-type artifacts detected." if has_compute_artifact else "No strong numeric/compute signals detected."),
        ),
        DiscoveryCheck(
            "baseline",
            "Baseline / control",
            baseline_ok,
            "Explicit baseline/control fields present (e.g., wt/baseline/control/random)." if baseline_ok else "No explicit baseline/control detected.",
        ),
        DiscoveryCheck(
            "uncertainty",
            "Uncertainty / robustness",
            uncertainty_ok,
            "CI/SE/bootstrap/posterior/replicate fields present." if uncertainty_ok else "No uncertainty/robustness estimate detected.",
        ),
        DiscoveryCheck(
            "delta",
            "Improvement / effect size",
            delta_ok,
            "Explicit delta/improvement fields present." if delta_ok else "No explicit delta/improvement detected.",
        ),
    ]

    metrics = {
        "numeric_leaf_count": numeric_count,
        "vector_like_count": vector_like,
        "artifact_count": len(artifacts),
        "artifact_types": sorted(set(t for t in artifact_types if t)),
    }

    return DiscoveryEvaluation(
        score=int(max(0, min(100, score))),
        tier=tier,
        checks=checks,
        metrics=metrics,
    )
