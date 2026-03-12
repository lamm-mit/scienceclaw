#!/usr/bin/env python3
"""
chord-analysis skill: Perform harmonic analysis on music21 corpus.

Accepts a query string (used to fetch corpus via music-corpus skill logic),
runs Roman numeral analysis, and returns chord progression frequencies and
transition matrices.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def _parse_args():
    p = argparse.ArgumentParser(description="Harmonic chord analysis using music21")
    p.add_argument("--query", default="bach", help="Composer/genre query")
    p.add_argument("--input-json", default="", help="Path to corpus JSON from music-corpus skill")
    p.add_argument("--max-pieces", type=int, default=15, help="Max pieces to analyse")
    p.add_argument("--describe-schema", action="store_true", help="Print output schema and exit")
    return p.parse_args()


SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "n_pieces_analysed": {"type": "integer"},
        "chord_progressions": {"type": "array"},
        "top_bigrams": {"type": "array"},
        "transition_matrix": {"type": "object"},
        "total_chords": {"type": "integer"},
    }
}


def _load_corpus_json(path: str):
    p = Path(path)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return None


def _roman_from_music21(query: str, max_pieces: int):
    """Use music21 to do Roman numeral analysis on corpus pieces."""
    try:
        from music21 import corpus, roman, chord as m21chord, key as m21key
    except ImportError:
        return [], 0

    q = query.lower()
    if "bach" in q:
        paths = corpus.getComposer("bach")
    elif "beethoven" in q:
        paths = corpus.getComposer("beethoven")
    elif "mozart" in q:
        paths = corpus.getComposer("mozart")
    else:
        paths = corpus.getComposer("bach")

    all_romans = []
    n_pieces = 0

    for path in list(paths)[:max_pieces]:
        try:
            score = corpus.parse(path)
            # Get key
            k = score.analyze("key")
            # Chordify
            chordified = score.chordify()
            piece_romans = []
            for el in chordified.flat.getElementsByClass(m21chord.Chord):
                try:
                    rn = roman.romanNumeralFromChord(el, k)
                    piece_romans.append(str(rn.figure))
                except Exception:
                    piece_romans.append("?")
                if len(piece_romans) >= 64:
                    break
            all_romans.extend(piece_romans)
            n_pieces += 1
        except Exception:
            continue

    return all_romans, n_pieces


def run(query: str, input_json: str = "", max_pieces: int = 15) -> dict:
    # Try to get Roman numerals directly from music21
    all_romans, n_pieces = _roman_from_music21(query, max_pieces)

    if not all_romans and input_json:
        # Fall back to parsing chord_sequence from corpus JSON
        data = _load_corpus_json(input_json)
        if data and isinstance(data.get("pieces"), list):
            for p in data["pieces"][:max_pieces]:
                chords = p.get("chord_sequence", [])
                all_romans.extend(chords[:64])
                n_pieces += 1

    if not all_romans:
        return {
            "error": "music21 not installed or no data available",
            "query": query,
            "n_pieces_analysed": 0,
            "chord_progressions": [],
            "top_bigrams": [],
            "transition_matrix": {},
            "total_chords": 0,
        }

    # Count chord frequencies
    counter = Counter(all_romans)
    total = len(all_romans)

    chord_progressions = [
        {
            "chord": ch,
            "roman": ch,
            "count": cnt,
            "frequency": round(cnt / total, 4),
        }
        for ch, cnt in counter.most_common(30)
        if ch and ch != "?"
    ]

    # Bigrams
    bigram_counter = Counter()
    for i in range(len(all_romans) - 1):
        a, b = all_romans[i], all_romans[i + 1]
        if a != "?" and b != "?":
            bigram_counter[(a, b)] += 1
    top_bigrams = [[a, b] for (a, b), _ in bigram_counter.most_common(15)]

    # Transition matrix (row = from, col = to, value = conditional probability)
    row_totals: dict = defaultdict(int)
    pair_counts: dict = defaultdict(lambda: defaultdict(int))
    for i in range(len(all_romans) - 1):
        a, b = all_romans[i], all_romans[i + 1]
        if a != "?" and b != "?":
            pair_counts[a][b] += 1
            row_totals[a] += 1

    transition_matrix = {}
    for src, targets in pair_counts.items():
        row_total = row_totals[src]
        transition_matrix[src] = {
            tgt: round(cnt / row_total, 3)
            for tgt, cnt in sorted(targets.items(), key=lambda x: -x[1])[:8]
        }
    # Keep only top 10 source chords
    top_sources = [ch for ch, _ in counter.most_common(10) if ch in transition_matrix]
    transition_matrix = {src: transition_matrix[src] for src in top_sources}

    return {
        "query": query,
        "n_pieces_analysed": n_pieces,
        "chord_progressions": chord_progressions,
        "top_bigrams": top_bigrams,
        "transition_matrix": transition_matrix,
        "total_chords": total,
    }


def main():
    args = _parse_args()
    if args.describe_schema:
        print(json.dumps(SCHEMA, indent=2))
        return
    result = run(query=args.query, input_json=args.input_json, max_pieces=args.max_pieces)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
