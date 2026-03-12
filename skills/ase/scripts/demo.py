#!/usr/bin/env python3
"""
ase — Atomic Simulation Environment (CLI shim for autonomous loops).

Many ASE workflows require structure files and heavyweight calculators.
Autonomous loops often call skills with a uniform `--query` interface; this
script provides a lightweight, non-fabricating entrypoint that returns a
concrete plan for how ASE *would* be used for the given query.

It deliberately does not run simulations or claim computed results.
"""

import argparse
import json
import sys
from datetime import datetime, timezone


def build_plan(query: str) -> dict:
    q = (query or "").strip()
    return {
        "skill": "ase",
        "status": "ok",
        "topic": q,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "note": "Plan only; no simulations executed and no properties claimed.",
        "suggested_workflow": [
            {
                "step": "Choose a structure representation",
                "details": "Provide an XYZ/CIF/POSCAR file or programmatically build an `ase.Atoms` object.",
            },
            {
                "step": "Select a calculator backend",
                "details": "MOPAC (semi-empirical) for fast geometry/energies, or QE/VASP for DFT if installed.",
            },
            {
                "step": "Run geometry optimization",
                "details": "Use BFGS/FIRE with a force threshold (e.g. fmax=0.01 eV/Å).",
            },
            {
                "step": "Extract properties",
                "details": "Total energy, forces, cell/volume (periodic), optionally vibrational modes/phonons.",
            },
        ],
        "entrypoints": {
            "optimize": "skills/ase/scripts/ase_optimize.py (expects --structure ...)",
            "properties": "skills/ase/scripts/ase_properties.py (expects --structure ...)",
        },
        "query": q,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="ase shim (query → suggested workflow)")
    p.add_argument("--query", "-q", default="", help="Topic/prompt")
    p.add_argument("--format", "-f", default="summary", choices=["summary", "json"])
    args = p.parse_args()

    try:
        result = build_plan(args.query)
    except Exception as e:
        print(json.dumps({"skill": "ase", "status": "error", "error": str(e)}))
        sys.exit(0)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("=" * 70)
        print("ase — suggested workflow (no execution)")
        print("=" * 70)
        if result.get("topic"):
            print(f"Topic: {result['topic']}")
        for step in result["suggested_workflow"]:
            print(f"- {step['step']}: {step['details']}")
        print("=" * 70)


if __name__ == "__main__":
    main()

