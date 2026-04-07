#!/usr/bin/env python3
"""
motif-detection skill: Extract repeated melodic motifs from music21 corpus.

Uses sliding window + interval encoding to find recurring patterns.
All data is real/computed from music21 corpus.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def _parse_args():
    p = argparse.ArgumentParser(description="Melodic motif detection using music21")
    p.add_argument("--query", default="bach", help="Composer/genre query")
    p.add_argument("--min-length", type=int, default=4, help="Minimum motif length in notes (default: 4)")
    p.add_argument("--min-occurrences", type=int, default=3, help="Minimum occurrences to count as motif (default: 3)")
    p.add_argument("--max-pieces", type=int, default=20, help="Max pieces to scan")
    p.add_argument("--describe-schema", action="store_true", help="Print output schema and exit")
    return p.parse_args()


SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "motifs": {"type": "array"},
        "n_motifs": {"type": "integer"},
        "min_length": {"type": "integer"},
        "min_occurrences": {"type": "integer"},
    }
}


def _get_note_sequences(query: str, max_pieces: int):
    """Extract note sequences (MIDI pitches) from music21 corpus."""
    try:
        from music21 import corpus, note as m21note
    except ImportError:
        return []

    q = query.lower()
    COMPOSER_MAP = {
        "bach": "bach", "beethoven": "beethoven", "mozart": "mozart",
        "haydn": "haydn", "monteverdi": "monteverdi", "josquin": "josquin",
        "handel": "handel", "schubert": "schubert",
    }
    matched = next((v for k, v in COMPOSER_MAP.items() if k in q), "bach")
    paths = corpus.getComposer(matched)

    sequences = []
    for path in list(paths)[:max_pieces]:
        try:
            score = corpus.parse(path)
            title = str(path).split("/")[-1].replace(".xml", "").replace(".krn", "").replace(".mxl", "")
            midi_notes = []
            for el in score.flat.getElementsByClass(m21note.Note):
                midi_notes.append(el.pitch.midi)
                if len(midi_notes) >= 256:
                    break
            if len(midi_notes) >= 8:
                sequences.append({"title": title, "notes": midi_notes})
        except Exception:
            continue
    return sequences


def _extract_motifs(sequences: list, min_length: int, min_occurrences: int, genre: str) -> list:
    """
    Sliding-window interval encoding motif detection.
    Each motif is represented as an interval tuple (differences between consecutive pitches).
    """
    # Build interval sequences per piece
    interval_seqs = []
    for seq_data in sequences:
        notes = seq_data["notes"]
        intervals = tuple(notes[i+1] - notes[i] for i in range(len(notes)-1))
        interval_seqs.append({"title": seq_data["title"], "intervals": intervals})

    # Count occurrences of each sub-sequence of length min_length
    motif_counter: Counter = Counter()
    motif_pieces: dict = defaultdict(set)

    for seq_data in interval_seqs:
        intervals = seq_data["intervals"]
        title = seq_data["title"]
        seen_in_piece = set()
        for start in range(len(intervals) - min_length + 1):
            subseq = intervals[start:start + min_length]
            motif_counter[subseq] += 1
            if subseq not in seen_in_piece:
                motif_pieces[subseq].add(title)
                seen_in_piece.add(subseq)

    # Filter by min_occurrences
    motifs = []
    for i, (subseq, count) in enumerate(motif_counter.most_common(100)):
        if count < min_occurrences:
            break
        interval_list = list(subseq)
        interval_str = ",".join(f"{'+' if x >= 0 else ''}{x}" for x in interval_list)
        pieces_list = sorted(motif_pieces[subseq])[:8]
        motifs.append({
            "motif_id": f"m_{i+1:04d}",
            "intervals": interval_list,
            "interval_str": interval_str,
            "occurrences": count,
            "pieces": pieces_list,
            "genre": genre,
        })

    return motifs


def _genre_from_query(query: str) -> str:
    q = query.lower()
    if any(x in q for x in ["bach", "handel", "baroque"]):
        return "baroque"
    if any(x in q for x in ["beethoven", "mozart", "haydn", "classical"]):
        return "classical"
    if any(x in q for x in ["folk"]):
        return "folk"
    return "classical"


def run(query: str, min_length: int = 4, min_occurrences: int = 3, max_pieces: int = 20) -> dict:
    genre = _genre_from_query(query)
    sequences = _get_note_sequences(query, max_pieces)

    if not sequences:
        return {
            "error": "music21 not installed or no corpus data available",
            "query": query,
            "motifs": [],
            "n_motifs": 0,
            "min_length": min_length,
            "min_occurrences": min_occurrences,
        }

    motifs = _extract_motifs(sequences, min_length=min_length, min_occurrences=min_occurrences, genre=genre)

    return {
        "query": query,
        "motifs": motifs,
        "n_motifs": len(motifs),
        "min_length": min_length,
        "min_occurrences": min_occurrences,
        "n_pieces_scanned": len(sequences),
        "genre": genre,
    }


def main():
    args = _parse_args()
    if args.describe_schema:
        print(json.dumps(SCHEMA, indent=2))
        return
    result = run(
        query=args.query,
        min_length=args.min_length,
        min_occurrences=args.min_occurrences,
        max_pieces=args.max_pieces,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
