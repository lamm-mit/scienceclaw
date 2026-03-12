#!/usr/bin/env python3
import argparse
import json
import random
import re
from typing import List, Dict


AA_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$", re.I)

GROUPS = {
    "hydrophobic": list("AILMV"),
    "aromatic": list("FWY"),
    "polar": list("STNQ"),
    "positive": list("KRH"),
    "negative": list("DE"),
    "special": list("CGP"),
}

ALL_AA = list("ACDEFGHIKLMNPQRSTVWY")


def _parse_int_list(vals: List[str]) -> List[int]:
    out = []
    for v in vals or []:
        try:
            out.append(int(v))
        except Exception:
            pass
    return out


def _is_seq(s: str) -> bool:
    s = (s or "").strip().upper()
    return bool(s) and bool(AA_RE.fullmatch(s))


def _pick_positions(n: int, protected: set, k: int) -> List[int]:
    candidates = [i for i in range(1, n + 1) if i not in protected]
    if not candidates:
        return []
    random.shuffle(candidates)
    return candidates[: max(1, min(k, len(candidates)))]


def _similar_choices(wt: str) -> List[str]:
    for g in GROUPS.values():
        if wt in g:
            return [a for a in g if a != wt]
    return [a for a in ALL_AA if a != wt]


def generate_variants(
    sequence: str,
    strategy: str,
    n_variants: int = 12,
    max_mutations: int = 2,
    protected_positions: List[int] = None,
    seed: int = 7,
) -> dict:
    seq = sequence.strip().upper()
    if not _is_seq(seq):
        return {"error": "Invalid peptide sequence", "sequence": sequence}

    random.seed(seed)
    protected = set(int(x) for x in (protected_positions or []) if isinstance(x, int) and x > 0)

    variants: List[Dict] = []
    seen = {seq}
    attempts = 0
    while len(variants) < n_variants and attempts < n_variants * 60:
        attempts += 1
        n_mut = 1 if strategy == "conservative" else random.randint(1, max(1, max_mutations))
        positions = _pick_positions(len(seq), protected, n_mut)
        if not positions:
            break
        chars = list(seq)
        muts: List[Dict[str, object]] = []
        for pos in positions:
            wt = chars[pos - 1]
            choices = _similar_choices(wt) if strategy == "conservative" else [a for a in ALL_AA if a != wt]
            mut = random.choice(choices)
            chars[pos - 1] = mut
            muts.append({"position": pos, "wt": wt, "mut": mut})
        new_seq = "".join(chars)
        if new_seq in seen:
            continue
        seen.add(new_seq)
        variants.append({"sequence": new_seq, "mutations": muts, "strategy": strategy})

    return {
        "sequence": seq,
        "strategy": strategy,
        "protected_positions": sorted(protected),
        "variant_count": len(variants),
        "variants": variants,
        # convenience keys for downstream reactor overlap
        "sequences": [v["sequence"] for v in variants],
        "reference_sequence": seq,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Generate conservative/aggressive mutation variants for a peptide sequence")
    p.add_argument("--query", "-q", default="", help="Peptide sequence (if --sequence not provided)")
    p.add_argument("--sequence", default="", help="Peptide sequence")
    p.add_argument("--strategy", choices=["conservative", "aggressive"], default="conservative")
    p.add_argument("--n-variants", type=int, default=12)
    p.add_argument("--max-mutations", type=int, default=2)
    p.add_argument("--protected-positions", nargs="*", default=[], help="1-based positions to protect from mutation")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--format", "-f", choices=["json", "summary"], default="json")
    p.add_argument("--describe-schema", action="store_true")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps({"input_json_fields": []}))
        return

    seq = args.sequence or args.query
    prot = _parse_int_list(args.protected_positions)
    payload = generate_variants(
        sequence=seq,
        strategy=args.strategy,
        n_variants=max(1, min(60, int(args.n_variants))),
        max_mutations=max(1, min(6, int(args.max_mutations))),
        protected_positions=prot,
        seed=int(args.seed),
    )

    if args.format == "summary":
        if payload.get("error"):
            print(payload["error"])
            return
        print(f"{payload['strategy']} variants: {payload['variant_count']} (protected={payload['protected_positions']})")
        for v in payload["variants"][:8]:
            muts = ", ".join(f"{m['wt']}{m['position']}{m['mut']}" for m in v.get("mutations", []))
            print(f"  - {v['sequence']}  [{muts}]")
        return
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
