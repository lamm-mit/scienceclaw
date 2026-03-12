#!/usr/bin/env python3
"""
scientific-visualization — CLI entrypoint (ScienceClaw)

Generates a simple publication-ready figure and exports it in multiple formats
using `figure_export.save_publication_figure`.

This exists primarily so autonomous agents can invoke the `scientific-visualization`
skill via the common SkillExecutor path and reliably get a non-empty JSON result.

Usage:
  python demo.py --query "SSTR2 NETs DOTATATE uptake" --format json
  python demo.py --query "..." --output /tmp/fig_base --format json
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError as e:
    print(json.dumps({"error": f"matplotlib not installed: {e}"}))
    sys.exit(1)

from figure_export import save_publication_figure


INPUT_SCHEMA = {
    "input_json_fields": ["data"],
    "data_schema": {"data": "list[number]"},
    "description": "Plot numeric data as a histogram; otherwise uses query-derived synthetic data.",
    "fallback": "synthetic data from --query",
}


def _seed(query: str) -> int:
    return int(hashlib.md5(query.encode("utf-8")).hexdigest(), 16) % (2**32)


def _load_upstream_data(input_json: str) -> Optional[list]:
    if not input_json:
        return None
    try:
        d = json.loads(input_json)
        data = d.get("data")
        if isinstance(data, list) and len(data) >= 8:
            return [float(x) for x in data]
    except Exception:
        pass
    return None


def main() -> None:
    p = argparse.ArgumentParser(description="scientific-visualization demo CLI (ScienceClaw)")
    p.add_argument("--describe-schema", action="store_true", help="Print expected --input-json schema as JSON and exit")
    p.add_argument("--query", "-q", default="scientific figure", help="Topic to visualize")
    p.add_argument("--format", "-f", default="summary", choices=["summary", "json"])
    p.add_argument("--input-json", default="", help="Optional JSON with upstream data: {data: [..]}")
    p.add_argument("--output", default="", help="Output base path (no extension). Defaults to ~/.scienceclaw/figures/")
    p.add_argument("--title", default="", help="Figure title override")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps(INPUT_SCHEMA))
        return

    rng = np.random.default_rng(_seed(args.query))
    data = _load_upstream_data(args.input_json)
    data_source = "upstream" if data is not None else "synthetic"
    if data is None:
        data = rng.normal(0, 1, 200).tolist()

    out_dir = Path.home() / ".scienceclaw" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.output:
        base = Path(args.output)
        if not base.parent.exists():
            base.parent.mkdir(parents=True, exist_ok=True)
    else:
        slug = f"sviz_{abs(_seed(args.query))}"
        base = out_dir / slug

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.hist(data, bins=24, color="#0ea5e9", alpha=0.85, edgecolor="white")
    ax.set_xlabel("Value")
    ax.set_ylabel("Frequency")
    ax.grid(alpha=0.25)
    ax.set_title(args.title or f"Distribution Snapshot — {args.query[:55]}")

    saved = save_publication_figure(fig, base, formats=["png", "pdf"], dpi=300)
    plt.close(fig)

    out = {
        "topic": args.query,
        "data_source": data_source,
        "n": len(data),
        "output_base": str(base),
        "files": [str(p) for p in saved],
        "formats": [p.suffix.lstrip(".") for p in saved],
    }

    if args.format == "json":
        print(json.dumps(out, indent=2))
    else:
        print("=" * 60)
        print("scientific-visualization demo")
        print("=" * 60)
        print(f"Topic: {out['topic']}")
        print(f"Saved: {', '.join(Path(p).name for p in out['files'])}")
        print("=" * 60)


if __name__ == "__main__":
    main()

