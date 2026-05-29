"""Helpers for formal enrichment of existing CategoryScienceClaw runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from categoryscienceclaw.example_runs import run_example


def enrich_7t10_formal_extension(out_dir: str | Path, *, cycles: int = 30, use_scienceclaw: bool = True) -> dict[str, Any]:
    """Create the 7T10 formal descriptor extension without mutating the baseline export."""

    return run_example(
        "7t10-formal-extension",
        out_dir,
        cycles=cycles,
        complexity="high",
        use_scienceclaw=use_scienceclaw,
    )
