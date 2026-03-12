#!/usr/bin/env python3
"""
TDC Property & Activity Prediction for ScienceClaw

Uses tdc.Oracle (no DeepPurpose / DGL required) to compute real drug-likeness
and target-activity scores for one or more SMILES strings.

Oracles available without heavy dependencies:
  qed        — Quantitative Estimate of Drug-likeness (0-1)
  logp       — Wildman-Crippen logP
  sa         — Synthetic Accessibility score (1=easy, 10=hard)
  drd2       — DRD2 (dopamine receptor D2) activity probability
  gsk3b      — GSK3β inhibition probability
  jnk3       — JNK3 inhibition probability

Usage:
  python3 tdc_predict.py --smiles "CCO"
  python3 tdc_predict.py --smiles "CCO" --oracles qed logp sa drd2
  python3 tdc_predict.py --smiles-file mols.smi --format json
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from tdc import Oracle
    _TDC_AVAILABLE = True
except ImportError:
    _TDC_AVAILABLE = False

# Oracles that work without DeepPurpose / DGL
AVAILABLE_ORACLES = ["qed", "logp", "sa", "drd2", "gsk3b", "jnk3"]
DEFAULT_ORACLES   = ["qed", "logp", "sa", "drd2", "gsk3b", "jnk3"]

ORACLE_DESC = {
    "qed":   "Drug-likeness (0-1, higher=better)",
    "logp":  "Lipophilicity (Wildman-Crippen logP)",
    "sa":    "Synthetic accessibility (1=easy, 10=hard)",
    "drd2":  "DRD2 activity probability (0-1)",
    "gsk3b": "GSK3β inhibition probability (0-1)",
    "jnk3":  "JNK3 inhibition probability (0-1)",
}

_oracle_cache: dict = {}


def _get_oracle(name: str):
    if name not in _oracle_cache:
        _oracle_cache[name] = Oracle(name)
    return _oracle_cache[name]


def predict(smiles_list: list, oracle_names: list, output_format: str = "summary") -> list:
    if not _TDC_AVAILABLE:
        print("Error: PyTDC not installed. Run: pip install PyTDC")
        sys.exit(1)

    results = []
    for smi in smiles_list:
        row = {"smiles": smi, "scores": {}}
        for name in oracle_names:
            try:
                val = _get_oracle(name)(smi)
                row["scores"][name] = round(float(val), 4)
            except Exception as e:
                row["scores"][name] = f"error: {e}"
        # Convenience top-level keys for downstream consumers
        row["qed"]   = row["scores"].get("qed")
        row["logp"]  = row["scores"].get("logp")
        row["sa"]    = row["scores"].get("sa")
        row["drd2"]  = row["scores"].get("drd2")
        row["gsk3b"] = row["scores"].get("gsk3b")
        row["jnk3"]  = row["scores"].get("jnk3")
        results.append(row)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Predict drug-likeness and target-activity scores using TDC Oracles."
    )
    parser.add_argument("--smiles", "-s", help="Single SMILES string")
    parser.add_argument("--smiles-file", "-f", help="File with one SMILES per line")
    parser.add_argument(
        "--oracles", nargs="+", default=DEFAULT_ORACLES,
        choices=AVAILABLE_ORACLES,
        help=f"Oracles to run (default: all). Choices: {AVAILABLE_ORACLES}",
    )
    # Legacy --model arg: silently accepted for backwards compatibility
    parser.add_argument("--model", "-m", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--list-models", action="store_true",
                        help="List available oracles and exit")
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    args = parser.parse_args()

    if args.list_models:
        print("TDC Oracles (no DeepPurpose required):")
        for name in AVAILABLE_ORACLES:
            print(f"  {name:<10}  {ORACLE_DESC[name]}")
        return

    smiles_list = []
    if args.smiles:
        smiles_list.append(args.smiles.strip())
    if args.smiles_file:
        path = Path(args.smiles_file)
        if not path.exists():
            print(f"Error: file not found: {path}")
            sys.exit(1)
        for line in path.read_text().splitlines():
            line = line.strip().split("#")[0].strip()
            if line:
                smiles_list.append(line)
    if not smiles_list:
        print("Error: provide --smiles or --smiles-file")
        parser.print_help()
        sys.exit(1)

    results = predict(smiles_list, args.oracles, args.format)

    if args.format == "json":
        print(json.dumps(results, indent=2))
        return

    # Human-readable summary
    for r in results:
        print(f"SMILES: {r['smiles'][:60]}")
        for name, val in r["scores"].items():
            desc = ORACLE_DESC.get(name, "")
            print(f"  {name:<8} {val:>8}   ({desc})")
        print()


if __name__ == "__main__":
    main()
