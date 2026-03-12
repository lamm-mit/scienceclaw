#!/usr/bin/env python3
import argparse
import json
import re
from typing import List, Dict


def _is_sequence(s: str) -> bool:
    s = (s or "").strip().upper()
    return bool(s) and len(s) <= 200 and bool(re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY]+", s))


def _sstr2_seed_set() -> List[Dict[str, str]]:
    # Canonical AA-only sequences for demo seeding (no non-canonical residues).
    # These are NOT claimed to be exact drug sequences; they are scaffold-like
    # representatives suitable for running purely computational downstream steps.
    return [
        {"id": "somatostatin_14", "sequence": "AGCKNFFWKTFTSC", "notes": "Somatostatin-14 (AA-only)"},
        {"id": "octreotide_core", "sequence": "FCFWKTCT", "notes": "Octreotide-like core (AA-only demo proxy)"},
        {"id": "lanreotide_core", "sequence": "YCWKTCT", "notes": "Lanreotide-like core (AA-only demo proxy)"},
        {"id": "dotatate_core", "sequence": "YCGWKTCT", "notes": "DOTATATE-like core (AA-only demo proxy)"},
    ]


def build_sequences(query: str) -> dict:
    q = (query or "").strip()
    if _is_sequence(q):
        seed = [{"id": "query", "sequence": q, "notes": "User-provided peptide sequence"}]
    else:
        seed = _sstr2_seed_set()
    sequences = [s["sequence"] for s in seed]
    labels = [s["id"] for s in seed]
    return {
        "query": q,
        "peptide_set": seed,
        # Convenience keys for downstream reactor overlap
        "sequences": sequences,
        "labels": labels,
        "reference_sequence": sequences[0] if sequences else "",
        "count": len(sequences),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Seed a curated peptide sequence set for downstream design steps")
    p.add_argument("--query", "-q", required=True, help="Target/topic or peptide sequence")
    p.add_argument("--format", "-f", choices=["json", "summary"], default="json")
    p.add_argument("--describe-schema", action="store_true", help="Print JSON schema for reactor --input-json (optional)")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps({"input_json_fields": []}))
        return

    payload = build_sequences(args.query)
    if args.format == "summary":
        lines = [
            f"Peptide seed set for: {payload.get('query','')}",
            f"Sequences: {payload.get('count', 0)}",
        ]
        for rec in payload.get("peptide_set", [])[:8]:
            lines.append(f"  - {rec.get('id')}: {rec.get('sequence')}")
        print("\n".join(lines))
        return

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

