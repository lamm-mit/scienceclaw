#!/usr/bin/env python3
import argparse
import json
import re
from typing import List, Dict


AA_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY-]+$", re.I)

KD = {
    "A": 1.8, "C": 2.5, "D": -3.5, "E": -3.5, "F": 2.8, "G": -0.4, "H": -3.2,
    "I": 4.5, "K": -3.9, "L": 3.8, "M": 1.9, "N": -3.5, "P": -1.6, "Q": -3.5,
    "R": -4.5, "S": -0.8, "T": -0.7, "V": 4.2, "W": -0.9, "Y": -1.3,
}


def _parse_sequences(query: str, sequences: List[str]) -> List[str]:
    if sequences:
        return [s.strip().upper() for s in sequences if s and s.strip()]
    q = (query or "").strip()
    if not q:
        return []
    if q.startswith("["):
        try:
            arr = json.loads(q)
            if isinstance(arr, list):
                return [str(x).strip().upper() for x in arr if str(x).strip()]
        except Exception:
            pass
    parts = re.split(r"[;\n, ]+", q)
    return [p.strip().upper() for p in parts if p.strip()]


def _net_charge(seq: str) -> int:
    pos = sum(seq.count(x) for x in "KRH")
    neg = sum(seq.count(x) for x in "DE")
    return int(pos - neg)


def _gravy(seq: str) -> float:
    aa = [c for c in seq if c in KD]
    if not aa:
        return 0.0
    return sum(KD[c] for c in aa) / len(aa)


def score_sequence(seq: str) -> dict:
    s = seq.replace("-", "").strip().upper()
    if not s or not AA_RE.fullmatch(seq.upper()):
        return {"sequence": seq, "error": "invalid"}
    charge = _net_charge(s)
    gravy = _gravy(s)
    cysteines = s.count("C")
    stability = 1.0
    stability -= min(0.8, abs(charge) * 0.08)
    stability -= min(0.8, max(0.0, gravy - 1.5) * 0.25)
    stability -= 0.15 if cysteines >= 3 else 0.0
    return {
        "sequence": s,
        "length": len(s),
        "net_charge": charge,
        "gravy": round(gravy, 3),
        "cysteines": cysteines,
        "stability_score": round(max(0.0, stability), 4),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Compute quick stability heuristics for peptide sequences")
    p.add_argument("--query", "-q", default="", help="Semicolon/JSON list of sequences")
    p.add_argument("--sequences", nargs="*", default=[], help="Sequences")
    p.add_argument("--format", "-f", choices=["json", "summary"], default="json")
    p.add_argument("--describe-schema", action="store_true")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps({"input_json_fields": []}))
        return

    seqs = _parse_sequences(args.query, args.sequences)
    rows = [score_sequence(s) for s in seqs]
    ok = [r for r in rows if not r.get("error")]
    payload = {"count": len(ok), "scores": ok, "sequences": [r["sequence"] for r in ok]}

    if args.format == "summary":
        print(f"Scored {payload['count']} peptide(s)")
        for r in payload["scores"][:8]:
            print(f"  - {r['sequence']}: stability={r['stability_score']} charge={r['net_charge']} gravy={r['gravy']}")
        return
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

