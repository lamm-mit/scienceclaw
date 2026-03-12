#!/usr/bin/env python3
import argparse
import json
import re
from typing import List, Tuple, Dict

try:
    from Bio.Align import PairwiseAligner
except Exception as exc:  # pragma: no cover
    raise SystemExit("Biopython is required for peptide-msa. Install biopython.") from exc


AA_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$", re.I)


def _parse_sequences(query: str, sequences: List[str]) -> List[str]:
    if sequences:
        return [s.strip().upper() for s in sequences if s and s.strip()]
    q = (query or "").strip()
    if not q:
        return []
    # Accept JSON list or semicolon/newline separated sequences
    if q.startswith("["):
        try:
            arr = json.loads(q)
            if isinstance(arr, list):
                return [str(x).strip().upper() for x in arr if str(x).strip()]
        except Exception:
            pass
    parts = re.split(r"[;\n, ]+", q)
    return [p.strip().upper() for p in parts if p.strip()]


def _is_peptide(seq: str) -> bool:
    s = (seq or "").strip().upper()
    return bool(s) and bool(AA_RE.fullmatch(s)) and 2 <= len(s) <= 200


def _align_pair(ref: str, seq: str) -> Tuple[str, str]:
    aligner = PairwiseAligner()
    aligner.mode = "global"
    # Simple gap penalties tuned for short peptides
    aligner.open_gap_score = -10
    aligner.extend_gap_score = -1
    aln = aligner.align(ref, seq)[0]
    # Reconstruct gapped strings from coordinates.
    ref_g = []
    seq_g = []
    ref_i = 0
    seq_i = 0
    for (r0, r1), (s0, s1) in zip(aln.aligned[0], aln.aligned[1]):
        while ref_i < r0:
            ref_g.append(ref[ref_i])
            seq_g.append("-")
            ref_i += 1
        while seq_i < s0:
            ref_g.append("-")
            seq_g.append(seq[seq_i])
            seq_i += 1
        ref_g.append(ref[r0:r1])
        seq_g.append(seq[s0:s1])
        ref_i = r1
        seq_i = s1
    while ref_i < len(ref):
        ref_g.append(ref[ref_i])
        seq_g.append("-")
        ref_i += 1
    while seq_i < len(seq):
        ref_g.append("-")
        seq_g.append(seq[seq_i])
        seq_i += 1
    return "".join(ref_g), "".join(seq_g)


def _merge_into_master(
    master_ref: str,
    master_aligned: List[str],
    ref_aligned: str,
    seq_aligned: str,
) -> Tuple[str, List[str], str]:
    """
    Merge a new (ref_aligned, seq_aligned) pair into an existing MSA defined by
    (master_ref, master_aligned). Returns updated (master_ref, master_aligned, new_seq_aligned_to_master).
    """
    i_m = 0
    i_r = 0
    new_master_ref = []
    rebuilt_existing = [[] for _ in master_aligned]
    new_seq = []

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
            i_m += 1
            i_r += 1
            continue

        if c_r == "-" and c_m is not None:
            new_master_ref.append(c_m)
            for idx, s in enumerate(master_aligned):
                rebuilt_existing[idx].append(s[i_m])
            new_seq.append("-")
            i_m += 1
            i_r += 1
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


def msa(seqs: List[str]) -> dict:
    seqs = [s.strip().upper() for s in seqs if _is_peptide(s)]
    if len(seqs) < 2:
        return {"error": "Need at least 2 peptide sequences for MSA", "sequences": seqs, "count": len(seqs)}

    ref = seqs[0]
    master_ref = ref
    aligned = [ref]
    for s in seqs[1:]:
        ref_al, s_al = _align_pair(ref, s)
        master_ref, aligned, s_to_master = _merge_into_master(master_ref, aligned, ref_al, s_al)
        aligned.append(s_to_master)

    L = max(len(a) for a in aligned)
    aligned = [a.ljust(L, "-") for a in aligned]

    consensus = []
    for j in range(L):
        col = [a[j] for a in aligned]
        counts: Dict[str, int] = {}
        for c in col:
            if c == "-":
                continue
            counts[c] = counts.get(c, 0) + 1
        if not counts:
            consensus.append("-")
        else:
            consensus.append(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0])

    return {
        "sequences": seqs,
        "count": len(seqs),
        "reference_sequence": ref,
        "alignment_length": L,
        "aligned_sequences": aligned,
        # Convenience: JSON-string form for downstream tools that should not
        # receive a list of strings containing '-' characters via argv.
        "aligned_json": json.dumps(aligned),
        "consensus": "".join(consensus),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Lightweight MSA for short peptide sequences")
    p.add_argument("--query", "-q", default="", help="Semicolon/space/JSON list of sequences")
    p.add_argument("--sequences", nargs="*", default=[], help="Peptide sequences (space-separated)")
    p.add_argument("--format", "-f", choices=["json", "summary"], default="json")
    p.add_argument("--describe-schema", action="store_true", help="Print JSON schema for reactor --input-json (optional)")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps({"input_json_fields": []}))
        return

    seqs = _parse_sequences(args.query, args.sequences)
    payload = msa(seqs)

    if args.format == "summary":
        if payload.get("error"):
            print(payload["error"])
            return
        print(f"Aligned {payload['count']} sequences (L={payload['alignment_length']})")
        for s in payload["aligned_sequences"][:6]:
            print("  " + s)
        print("Consensus: " + payload["consensus"])
        return

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
