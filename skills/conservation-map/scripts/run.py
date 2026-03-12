#!/usr/bin/env python3
import argparse
import json
import math
import re
from typing import List, Dict

try:
    from Bio.Align import PairwiseAligner
except Exception:  # pragma: no cover
    PairwiseAligner = None

def _parse_aligned(query: str, aligned_json: str) -> List[str]:
    if aligned_json:
        try:
            arr = json.loads(aligned_json)
            if isinstance(arr, list):
                return [str(x).strip().upper() for x in arr if str(x).strip()]
        except Exception:
            pass
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
    parts = re.split(r"[;\n]+", q)
    return [p.strip().upper() for p in parts if p.strip()]


def _is_raw_sequence(s: str) -> bool:
    s = (s or "").strip().upper()
    return bool(s) and bool(re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY]+", s))


def _align_pair(ref: str, seq: str) -> tuple[str, str]:
    if PairwiseAligner is None:
        raise RuntimeError("Biopython PairwiseAligner unavailable")
    aligner = PairwiseAligner()
    aligner.mode = "global"
    aligner.open_gap_score = -10
    aligner.extend_gap_score = -1
    aln = aligner.align(ref, seq)[0]
    ref_g, seq_g = [], []
    ref_i, seq_i = 0, 0
    for (r0, r1), (s0, s1) in zip(aln.aligned[0], aln.aligned[1]):
        while ref_i < r0:
            ref_g.append(ref[ref_i]); seq_g.append("-"); ref_i += 1
        while seq_i < s0:
            ref_g.append("-"); seq_g.append(seq[seq_i]); seq_i += 1
        ref_g.append(ref[r0:r1]); seq_g.append(seq[s0:s1])
        ref_i, seq_i = r1, s1
    while ref_i < len(ref):
        ref_g.append(ref[ref_i]); seq_g.append("-"); ref_i += 1
    while seq_i < len(seq):
        ref_g.append("-"); seq_g.append(seq[seq_i]); seq_i += 1
    return "".join(ref_g), "".join(seq_g)


def _merge_into_master(master_ref: str, master_aligned: List[str], ref_aligned: str, seq_aligned: str) -> tuple[str, List[str], str]:
    i_m = 0
    i_r = 0
    new_master_ref: List[str] = []
    rebuilt_existing = [[] for _ in master_aligned]
    new_seq: List[str] = []
    while i_m < len(master_ref) or i_r < len(ref_aligned):
        c_m = master_ref[i_m] if i_m < len(master_ref) else None
        c_r = ref_aligned[i_r] if i_r < len(ref_aligned) else None
        if c_m == c_r:
            if c_m is None:
                break
            new_master_ref.append(c_m)
            for idx, s in enumerate(master_aligned):
                rebuilt_existing[idx].append(s[i_m])
            new_seq.append(seq_aligned[i_r])
            i_m += 1; i_r += 1
            continue
        if c_r == "-" and c_m is not None:
            new_master_ref.append(c_m)
            for idx, s in enumerate(master_aligned):
                rebuilt_existing[idx].append(s[i_m])
            new_seq.append("-")
            i_m += 1; i_r += 1
            continue
        if c_m == "-" and c_r is not None:
            new_master_ref.append("-")
            for idx, s in enumerate(master_aligned):
                rebuilt_existing[idx].append(s[i_m])
            new_seq.append("-" if c_r != "-" else seq_aligned[i_r])
            i_m += 1
            if c_r == "-":
                i_r += 1
            continue
        if c_r is not None:
            new_master_ref.append("-")
            for idx in range(len(master_aligned)):
                rebuilt_existing[idx].append("-")
            new_seq.append(seq_aligned[i_r])
            i_r += 1
            continue
        break
    merged_ref = "".join(new_master_ref)
    merged_existing = ["".join(chunks) for chunks in rebuilt_existing]
    merged_new_seq = "".join(new_seq)
    return merged_ref, merged_existing, merged_new_seq


def _msa_from_raw(seqs: List[str]) -> List[str]:
    seqs = [s.strip().upper() for s in seqs if _is_raw_sequence(s)]
    if len(seqs) < 2:
        return seqs
    ref = seqs[0]
    master_ref = ref
    aligned = [ref]
    for s in seqs[1:]:
        ref_al, s_al = _align_pair(ref, s)
        master_ref, aligned, s_to_master = _merge_into_master(master_ref, aligned, ref_al, s_al)
        aligned.append(s_to_master)
    L = max(len(a) for a in aligned)
    return [a.ljust(L, "-") for a in aligned]


def conservation_map(aligned_sequences: List[str]) -> dict:
    if not aligned_sequences:
        return {"error": "No aligned_sequences provided", "aligned_sequences": [], "count": 0}

    # Accept raw (unaligned) sequences and align them on the fly.
    if any("-" not in s for s in aligned_sequences) and any(_is_raw_sequence(s) for s in aligned_sequences):
        aligned_sequences = _msa_from_raw(aligned_sequences)

    L = max(len(s) for s in aligned_sequences)
    aligned_sequences = [s.ljust(L, "-") for s in aligned_sequences]

    positions = []
    for j in range(L):
        col = [s[j] for s in aligned_sequences]
        counts: Dict[str, int] = {}
        for c in col:
            if c == "-":
                continue
            counts[c] = counts.get(c, 0) + 1
        n = sum(counts.values())
        if n == 0:
            positions.append({"col": j + 1, "conservation": 0.0, "entropy": 0.0, "top": "-", "n": 0})
            continue
        freqs = {k: v / n for k, v in counts.items()}
        top = sorted(freqs.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        entropy = -sum(p * math.log(p + 1e-12, 2) for p in freqs.values())
        conservation = max(freqs.values())
        positions.append({
            "col": j + 1,
            "conservation": round(conservation, 4),
            "entropy": round(entropy, 4),
            "top": top,
            "n": n,
        })

    conserved = [p["col"] for p in positions if p["conservation"] >= 0.8 and p["top"] != "-"]
    variable = [p["col"] for p in positions if p["conservation"] <= 0.4 and p["n"] > 0]

    # Convenience keys for downstream mutation generator
    protected_positions = conserved[: min(8, len(conserved))]
    return {
        "count": len(aligned_sequences),
        "alignment_length": L,
        "aligned_sequences": aligned_sequences,
        "positions": positions,
        "conserved_columns": conserved,
        "variable_columns": variable,
        "protected_positions": protected_positions,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Compute conservation map from aligned peptide sequences")
    p.add_argument("--query", "-q", default="", help="JSON/semicolon list of aligned (or raw) sequences")
    p.add_argument("--aligned-json", default="", help="JSON list of aligned sequences (avoids '-' argv parsing issues)")
    p.add_argument("--format", "-f", choices=["json", "summary"], default="json")
    p.add_argument("--describe-schema", action="store_true")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps({"input_json_fields": []}))
        return

    aligned = _parse_aligned(args.query, args.aligned_json)
    payload = conservation_map(aligned)
    if args.format == "summary":
        if payload.get("error"):
            print(payload["error"])
            return
        print(f"Conservation map: L={payload['alignment_length']}, n={payload['count']}")
        print(f"Conserved cols (≥0.8): {payload['conserved_columns'][:12]}")
        print(f"Variable cols (≤0.4): {payload['variable_columns'][:12]}")
        return
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
