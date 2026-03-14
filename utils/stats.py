#!/usr/bin/env python3
from __future__ import annotations

import random
from typing import Iterable, Tuple, List, Optional


def bootstrap_mean_ci(
    values: Iterable[float],
    *,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> Optional[Tuple[float, float, float]]:
    """
    Nonparametric bootstrap CI for the mean.

    Returns (mean, ci_low, ci_high) or None if insufficient data.
    Deterministic given `seed`.
    """
    vals: List[float] = [float(v) for v in values]
    if len(vals) < 2:
        return None
    rng = random.Random(seed)
    n = len(vals)
    boot_means = []
    for _ in range(int(n_boot)):
        sample = [vals[rng.randrange(n)] for _ in range(n)]
        boot_means.append(sum(sample) / n)
    boot_means.sort()

    lo_idx = int((alpha / 2) * len(boot_means))
    hi_idx = int((1 - alpha / 2) * len(boot_means)) - 1
    lo_idx = max(0, min(lo_idx, len(boot_means) - 1))
    hi_idx = max(0, min(hi_idx, len(boot_means) - 1))

    mean = sum(vals) / n
    return mean, boot_means[lo_idx], boot_means[hi_idx]

