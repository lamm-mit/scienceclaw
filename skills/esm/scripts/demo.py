#!/usr/bin/env python3
"""
esm — ESM-2 pseudo-log-likelihood (PLL) scoring + mutation scan (ScienceClaw)

This is a real, online-capable protein design/evolution component:
  - Downloads an ESM-2 checkpoint via HuggingFace (if not cached)
  - Computes per-position PLL for a given amino-acid sequence
  - Suggests top single-point substitutions at low-PLL positions

It is intentionally lightweight (short peptides / domains) so it can run in demos.

Usage:
  python demo.py --sequence "AGCKNFFWKTFTSC" --format json
  python demo.py --query "AGCKNFFWKTFTSC" --format json
"""

import argparse
import hashlib
import json
import re
import sys
import time
from typing import Dict, List, Tuple, Optional


AA_ALPHABET = "ACDEFGHIKLMNPQRSTVWY"


INPUT_SCHEMA = {
    "input_json_fields": ["sequence"],
    "sequence_schema": {"sequence": "string"},
    "description": "ESM-2 PLL scoring and single-point mutation suggestions for a protein sequence.",
    "fallback": "none (requires an amino-acid sequence)",
}


def _looks_like_sequence(s: str) -> bool:
    s = (s or "").strip().upper()
    if len(s) < 8:
        return False
    return bool(re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY]+", s))


def _seed(s: str) -> int:
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16) % (2**32)


def _load_model(model_name: str, device_preference: str = "auto"):
    try:
        import torch
        from transformers import AutoTokenizer, EsmForMaskedLM
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}. Install torch + transformers.")

    pref = (device_preference or "auto").strip().lower()
    if pref not in ("auto", "cpu", "cuda"):
        pref = "auto"

    if pref == "cpu":
        device = "cpu"
    elif pref == "cuda":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(model_name)
    mdl = EsmForMaskedLM.from_pretrained(model_name)
    mdl = mdl.to(device)
    mdl.eval()
    return tok, mdl, device, time.time() - t0


def _masked_logprobs_for_position(model, tokenizer, sequence: str, pos: int, device: str) -> Tuple[float, Dict[str, float]]:
    """
    Mask position pos (0-indexed) and return:
      - logprob of the wild-type residue at pos
      - dict of AA -> logprob at that masked position
    """
    import torch

    seq = sequence
    wt = seq[pos]

    # Tokenize as a single sequence; ESM tokenizers add special tokens.
    inp = tokenizer(seq, return_tensors="pt")
    input_ids = inp["input_ids"].to(device)
    attn = inp.get("attention_mask")
    if attn is not None:
        attn = attn.to(device)

    # Map sequence pos to token index.
    # For ESM tokenizers, token 0 is usually <cls>, residues start at 1.
    token_pos = pos + 1
    mask_id = tokenizer.mask_token_id
    input_ids_masked = input_ids.clone()
    input_ids_masked[0, token_pos] = mask_id

    with torch.no_grad():
        out = model(input_ids=input_ids_masked, attention_mask=attn)
        logits = out.logits[0, token_pos]  # vocab
        log_probs = torch.log_softmax(logits, dim=-1)

    wt_id = tokenizer.convert_tokens_to_ids(wt)
    wt_logp = float(log_probs[wt_id].item())

    aa_logp: Dict[str, float] = {}
    for aa in AA_ALPHABET:
        aa_id = tokenizer.convert_tokens_to_ids(aa)
        aa_logp[aa] = float(log_probs[aa_id].item())
    return wt_logp, aa_logp


def score_sequence(model, tokenizer, sequence: str, device: str) -> Tuple[float, List[float], List[Dict[str, float]]]:
    """
    Returns:
      mean_pll (mean log-prob over positions),
      per_pos_wt_logp,
      per_pos_aa_logp (list of dicts)
    """
    per_pos_wt: List[float] = []
    per_pos_aa: List[Dict[str, float]] = []
    for pos in range(len(sequence)):
        wt_logp, aa_logp = _masked_logprobs_for_position(model, tokenizer, sequence, pos, device)
        per_pos_wt.append(wt_logp)
        per_pos_aa.append(aa_logp)
    mean_pll = float(sum(per_pos_wt) / max(1, len(per_pos_wt)))
    return mean_pll, per_pos_wt, per_pos_aa


def suggest_mutations(sequence: str, per_pos_wt: List[float], per_pos_aa: List[Dict[str, float]],
                      n_positions: int = 3, top_k: int = 5) -> List[dict]:
    """
    Choose n_positions lowest-PLL positions and return top_k improving AA substitutions total.
    """
    L = len(sequence)
    worst_positions = sorted(range(L), key=lambda i: per_pos_wt[i])[: max(1, min(n_positions, L))]
    suggestions: List[dict] = []
    for pos in worst_positions:
        wt = sequence[pos]
        base = per_pos_wt[pos]
        aa_logp = per_pos_aa[pos]
        for aa, lp in aa_logp.items():
            if aa == wt:
                continue
            delta = lp - base
            if delta > 0:
                suggestions.append({
                    "position": pos + 1,
                    "wt": wt,
                    "mut": aa,
                    "pll_delta": round(float(delta), 6),
                    "masked_logp_wt": round(float(base), 6),
                    "masked_logp_mut": round(float(lp), 6),
                })
    suggestions.sort(key=lambda x: x["pll_delta"], reverse=True)
    return suggestions[:top_k]


def main() -> None:
    p = argparse.ArgumentParser(description="ESM-2 PLL scoring + mutation scan (ScienceClaw)")
    p.add_argument("--describe-schema", action="store_true", help="Print expected schema for reactor and exit")
    p.add_argument("--sequence", default="", help="Amino-acid sequence (canonical 20 AA)")
    p.add_argument("--query", "-q", default="", help="Alias for --sequence (executor commonly passes --query)")
    p.add_argument("--model", default="facebook/esm2_t12_35M_UR50D", help="HuggingFace model name")
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"],
                   help="Device placement for the model (default: auto).")
    p.add_argument("--n-positions", type=int, default=3, help="Number of lowest-PLL positions to scan (default: 3)")
    p.add_argument("--top-k", type=int, default=5, help="Top improving mutations to return (default: 5)")
    p.add_argument("--evolve-steps", type=int, default=0,
                   help="Run a simple directed-evolution loop for N steps (apply best Δpll mutation each step).")
    p.add_argument("--format", "-f", default="summary", choices=["summary", "json"])
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps(INPUT_SCHEMA))
        return

    seq = (args.sequence or args.query or "").strip().upper()
    if not _looks_like_sequence(seq):
        print(json.dumps({"error": "Invalid sequence. Provide canonical amino-acid string (A,C,D,...,Y) length>=8."}))
        sys.exit(1)

    tok, mdl, device, load_s = _load_model(args.model, device_preference=args.device)

    # Optional: simple directed evolution loop (PLL-guided greedy mutator)
    evolve_steps = max(0, int(args.evolve_steps or 0))
    current_seq = seq
    trace: List[dict] = []
    applied: Optional[dict] = None
    last_per_pos_wt: List[float] = []

    def _score(seq_in: str):
        return score_sequence(mdl, tok, seq_in, device=device)

    while True:
        mean_pll, per_pos_wt, per_pos_aa = _score(current_seq)

        last_per_pos_wt = per_pos_wt
        muts = suggest_mutations(current_seq, per_pos_wt, per_pos_aa, n_positions=args.n_positions, top_k=args.top_k)
        entry = {
            "step": len(trace),
            "sequence": current_seq,
            "mean_pll": round(float(mean_pll), 6),
            "applied_mutation": applied,
            "top_mutations": muts,
        }
        trace.append(entry)

        if len(trace) > evolve_steps or not muts:
            break
        applied = muts[0]
        pos0 = int(applied["position"]) - 1
        current_seq = current_seq[:pos0] + str(applied["mut"]) + current_seq[pos0 + 1:]

    # Use the final sequence state for headline outputs
    final = trace[-1]
    final_seq = final["sequence"]
    final_mean = final["mean_pll"]
    final_muts = final["top_mutations"]

    out = {
        "start_sequence": seq,
        "sequence": final_seq,
        "length": len(final_seq),
        "model": args.model,
        "device": device,
        "device_requested": args.device,
        "model_load_seconds": round(load_s, 3),
        "mean_pll": round(float(final_mean), 6),
        "per_position_logprobs": [round(float(v), 6) for v in last_per_pos_wt],
        "lowest_pll_positions": [i + 1 for i in sorted(range(len(final_seq)), key=lambda i: last_per_pos_wt[i])[: min(3, len(final_seq))]],
        "top_mutations": final_muts,
        "evolve_steps": evolve_steps,
        "evolution_trace": trace if evolve_steps else [],
        "evolved": final_seq != seq,
        "mean_pll_delta": round(float(final_mean) - float(trace[0]["mean_pll"]), 6) if trace else 0.0,
    }

    if args.format == "json":
        print(json.dumps(out, indent=2))
    else:
        print("=" * 70)
        print("ESM-2 PLL scoring")
        print("=" * 70)
        print(f"Sequence (L={out['length']}): {seq}")
        print(f"Model: {out['model']}  device={out['device']}  load={out['model_load_seconds']}s")
        print(f"Mean PLL: {out['mean_pll']}")
        print(f"Lowest-PLL positions: {out['lowest_pll_positions']}")
        if muts:
            print("\nTop improving single-point mutations:")
            for m in muts:
                print(f"  pos{m['position']} {m['wt']}→{m['mut']}  Δpll={m['pll_delta']:+.4f}")
        else:
            print("\nNo improving mutations found at scanned positions.")
        print("=" * 70)


if __name__ == "__main__":
    main()
