#!/usr/bin/env python3
import argparse
import json
import re
from typing import List, Dict


AA_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$", re.I)


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


def _parse_ints(vals: List[str]) -> List[int]:
    out = []
    for v in vals or []:
        try:
            out.append(int(v))
        except Exception:
            pass
    return out


KD = {
    "A": 1.8, "C": 2.5, "D": -3.5, "E": -3.5, "F": 2.8, "G": -0.4, "H": -3.2,
    "I": 4.5, "K": -3.9, "L": 3.8, "M": 1.9, "N": -3.5, "P": -1.6, "Q": -3.5,
    "R": -4.5, "S": -0.8, "T": -0.7, "V": 4.2, "W": -0.9, "Y": -1.3,
}


def _net_charge(seq: str) -> int:
    pos = sum(seq.count(x) for x in "KRH")
    neg = sum(seq.count(x) for x in "DE")
    return int(pos - neg)


def _gravy(seq: str) -> float:
    aa = [c for c in seq if c in KD]
    if not aa:
        return 0.0
    return sum(KD[c] for c in aa) / len(aa)


def _stability_score(seq: str) -> float:
    charge = _net_charge(seq)
    gravy = _gravy(seq)
    cysteines = seq.count("C")
    score = 1.0
    score -= min(0.8, abs(charge) * 0.08)
    score -= min(0.8, max(0.0, gravy - 1.5) * 0.25)
    score -= 0.15 if cysteines >= 3 else 0.0
    return max(0.0, score)


def _edit_distance(a: str, b: str) -> int:
    if not a or not b:
        return 0
    if len(a) != len(b):
        m = max(len(a), len(b))
        a2 = a.ljust(m, "-")
        b2 = b.ljust(m, "-")
        return sum(1 for i in range(m) if a2[i] != b2[i])
    return sum(1 for i in range(len(a)) if a[i] != b[i])


def rank(reference: str, sequences: List[str], hotspot_positions: List[int]) -> dict:
    ref = (reference or "").strip().upper()
    if ref and not AA_RE.fullmatch(ref):
        ref = ""
    hs = set(int(x) for x in hotspot_positions or [] if isinstance(x, int) and x > 0)

    rows = []
    for s in sequences:
        seq = (s or "").strip().upper()
        if not seq or not AA_RE.fullmatch(seq):
            continue
        stab = _stability_score(seq)
        dist = _edit_distance(ref, seq) if ref else 0
        hotspot_mut = 0
        if ref and hs:
            for pos in hs:
                if 1 <= pos <= min(len(ref), len(seq)) and ref[pos - 1] != seq[pos - 1]:
                    hotspot_mut += 1
        score = stab - 0.08 * dist - 0.25 * hotspot_mut
        rows.append({
            "sequence": seq,
            "stability_score": round(stab, 4),
            "edit_distance": dist,
            "hotspot_mutations": hotspot_mut,
            "combined_score": round(score, 4),
        })

    rows.sort(key=lambda r: (-r["combined_score"], r["edit_distance"], r["sequence"]))
    top = rows[:10]
    return {
        "reference_sequence": ref,
        "hotspot_positions": sorted(hs),
        "ranked_candidates": top,
        "top_candidates": [r["sequence"] for r in top[:5]],
        "count": len(rows),
        "sequences": [r["sequence"] for r in top],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Rank peptide candidates using stability heuristics and hotspot protection")
    p.add_argument("--query", "-q", default="", help="Semicolon/JSON list of sequences (if --sequences not provided)")
    p.add_argument("--sequences", nargs="*", default=[], help="Candidate sequences")
    p.add_argument("--reference", default="", help="Reference sequence for edit-distance and hotspot penalties")
    p.add_argument("--reference-sequence", dest="reference_sequence", default="", help="Alias for --reference (reactor-friendly)")
    p.add_argument("--hotspot-positions", nargs="*", default=[], help="1-based hotspot positions (protect these)")
    p.add_argument("--protected-positions", nargs="*", default=[], help="Alias for hotspot positions (reactor-friendly)")
    p.add_argument("--format", "-f", choices=["json", "summary"], default="json")
    p.add_argument("--describe-schema", action="store_true")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps({"input_json_fields": []}))
        return

    seqs = _parse_sequences(args.query, args.sequences)
    hs = _parse_ints(args.hotspot_positions) + _parse_ints(args.protected_positions)
    ref = args.reference_sequence or args.reference
    payload = rank(reference=ref, sequences=seqs, hotspot_positions=hs)
    if args.format == "summary":
        print(f"Ranked {payload.get('count',0)} candidates; top={payload.get('top_candidates',[])[:3]}")
        for r in payload.get("ranked_candidates", [])[:5]:
            print(f"  - {r['sequence']}: score={r['combined_score']} stab={r['stability_score']} d={r['edit_distance']} hot={r['hotspot_mutations']}")
        return
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
