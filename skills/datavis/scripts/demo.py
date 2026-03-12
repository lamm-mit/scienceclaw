#!/usr/bin/env python3
"""
datavis — CLI entrypoint (ScienceClaw)

The main `plot_data.py` script is a subcommand-style CLI, which doesn't work
well with the generic SkillExecutor parameter passing (it assumes `--query`).

This `demo.py` provides a stable single-command interface:
  - Accepts --query <topic>
  - Optionally accepts --input-json with {data: [..]} numeric series
  - Generates a small PNG figure (saved under ~/.scienceclaw/figures/)
  - Returns JSON including the saved file path
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


INPUT_SCHEMA = {
    "input_json_fields": ["data"],
    "data_schema": {"data": "list[number]"},
    "description": "Quick histogram/line figure from numeric data.",
    "fallback": "synthetic data from --query topic",
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
    p = argparse.ArgumentParser(description="datavis demo CLI (ScienceClaw)")
    p.add_argument("--describe-schema", action="store_true", help="Print expected --input-json schema as JSON and exit")
    p.add_argument("--query", "-q", default="data", help="Topic label for synthetic fallback")
    p.add_argument("--format", "-f", default="summary", choices=["summary", "json"])
    p.add_argument("--input-json", default="", help="Optional JSON with upstream data: {data: [number, ...]}")
    p.add_argument("--output", default="", help="Optional output path. Defaults to ~/.scienceclaw/figures/")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps(INPUT_SCHEMA))
        return

    upstream = _load_upstream_data(args.input_json)
    data_source = "upstream" if upstream is not None else "synthetic"
    rng = np.random.default_rng(_seed(args.query))
    data = upstream if upstream is not None else rng.normal(0, 1, 200).tolist()

    out_dir = Path.home() / ".scienceclaw" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.output:
        out_path = Path(args.output)
        if out_path.is_dir():
            out_path = out_path / "datavis_plot.png"
    else:
        out_path = out_dir / f"datavis_{abs(_seed(args.query))}.png"

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.plot(data[:120], color="#0ea5e9", lw=1.7)
    ax.set_title(f"datavis snapshot — {args.query[:50]}")
    ax.set_xlabel("index")
    ax.set_ylabel("value")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    result = {
        "topic": args.query,
        "data_source": data_source,
        "n": len(data),
        "figure_path": str(out_path),
    }

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("=" * 60)
        print("datavis demo")
        print("=" * 60)
        print(f"Topic: {result['topic']}")
        print(f"Saved: {Path(result['figure_path']).name}")
        print("=" * 60)


if __name__ == "__main__":
    main()

