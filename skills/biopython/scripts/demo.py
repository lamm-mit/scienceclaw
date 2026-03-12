#!/usr/bin/env python3
"""
biopython — Protein sequence physicochemical analysis (ScienceClaw)

Computes useful peptide/protein features (pI, instability index, GRAVY, AA fractions)
for design/evolution demos.

Usage:
    python demo.py --sequence "AGCKNFFWKTFTSC" --format json
"""

import argparse
import json
import sys

try:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis
except ImportError:
    print("Error: biopython is required. Install with: pip install biopython")
    sys.exit(1)

import re

AA20_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$")


INPUT_SCHEMA = {
    "input_json_fields": ["sequence"],
    "sequence_schema": {"sequence": "string"},
    "description": "ProteinAnalysis features for an amino-acid sequence.",
    "fallback": "none (requires --sequence)",
}


def analyse_sequence(sequence: str) -> dict:
    seq = (sequence or "").strip().upper()
    if len(seq) < 5 or not AA20_RE.fullmatch(seq):
        return {"error": "Invalid sequence. Use canonical amino-acid letters only."}

    pa = ProteinAnalysis(seq)
    instability = float(pa.instability_index())
    pi = float(pa.isoelectric_point())
    gravy = float(pa.gravy())
    aromaticity = float(pa.aromaticity())
    mw = float(pa.molecular_weight())
    aa_counts = pa.count_amino_acids()
    total = max(1, len(seq))
    aa_freq = {k: round(v / total, 4) for k, v in sorted(aa_counts.items())}

    try:
        helix, turn, sheet = pa.secondary_structure_fraction()
    except Exception:
        helix, turn, sheet = 0.0, 0.0, 0.0

    return {
        "sequence": seq,
        "length": len(seq),
        "molecular_weight": round(mw, 3),
        "isoelectric_point": round(pi, 3),
        "instability_index": round(instability, 3),
        "stable": instability < 40.0,
        "gravy": round(gravy, 4),
        "aromaticity": round(aromaticity, 4),
        "secondary_structure_fraction": {
            "helix": round(float(helix), 4),
            "turn": round(float(turn), 4),
            "sheet": round(float(sheet), 4),
        },
        "aa_frequency": aa_freq,
    }


def main():
    parser = argparse.ArgumentParser(
        description='biopython ProteinAnalysis (ScienceClaw)'
    )
    parser.add_argument(
        '--format', '-f',
        default='summary',
        choices=['summary', 'json'],
        help='Output format (default: summary)'
    )
    parser.add_argument("--describe-schema", action="store_true",
                        help="Print expected --input-json schema as JSON and exit")
    parser.add_argument('--sequence', default='', help='Amino-acid sequence (canonical 20 AA)')
    parser.add_argument('--query', '-q', default='', help='Alias for --sequence')

    args = parser.parse_args()

    try:
        if args.describe_schema:
            print(json.dumps(INPUT_SCHEMA))
            return

        seq = args.sequence or args.query
        result = analyse_sequence(seq)

        if args.format == 'json':
            print(json.dumps(result, indent=2))
        else:
            print("=" * 60)
            if "error" in result:
                print("biopython ProteinAnalysis — ERROR")
                print("=" * 60)
                print(result["error"])
                sys.exit(1)
            print("biopython ProteinAnalysis")
            print("=" * 60)
            print(f"Length    : {result['length']}")
            print(f"MW        : {result['molecular_weight']}")
            print(f"pI        : {result['isoelectric_point']}")
            print(f"InstabIdx : {result['instability_index']}  "
                  f"({'stable' if result['stable'] else 'unstable'})")
            print(f"GRAVY     : {result['gravy']}")
            print("=" * 60)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
