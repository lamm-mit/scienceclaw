#!/usr/bin/env python3
"""
midi-generator skill: Generate MIDI from motif JSON using music21.

Accepts motif JSON (intervals + optional centroid), builds a melody,
saves a .mid file, and returns base64-encoded MIDI bytes.
"""
import argparse
import base64
import json
import sys
import time
from pathlib import Path


MIDI_DIR = Path.home() / ".scienceclaw" / "midi"


def _parse_args():
    p = argparse.ArgumentParser(description="MIDI generation from motif data using music21")
    p.add_argument("--query", default="{}", help="Motif JSON string or cluster centroid JSON or 'centroid'")
    p.add_argument("--clusters-json", default="", help="JSON string of clustering output (use cluster centroids as motifs)")
    p.add_argument("--tempo", type=int, default=100, help="Tempo in BPM (default: 100)")
    p.add_argument("--strategy", default="centroid", choices=["centroid", "interpolate"],
                   help="Generation strategy (centroid: use motif directly; interpolate: blend motifs)")
    p.add_argument("--output-dir", default="", help="Override output directory for .mid file")
    p.add_argument("--describe-schema", action="store_true", help="Print output schema and exit")
    return p.parse_args()


SCHEMA = {
    "type": "object",
    "properties": {
        "midi_b64": {"type": "string", "description": "Base64-encoded MIDI file bytes"},
        "motif_count": {"type": "integer"},
        "duration_s": {"type": "number"},
        "tempo": {"type": "integer"},
        "strategy": {"type": "string"},
        "output_path": {"type": "string"},
        "n_notes": {"type": "integer"},
    }
}


def _intervals_to_midi_notes(intervals: list, start_pitch: int = 60, repeat: int = 4) -> list:
    """Convert interval list to MIDI pitch sequence, repeated."""
    notes = [start_pitch]
    for iv in intervals:
        notes.append(max(21, min(108, notes[-1] + iv)))
    if repeat > 1:
        pattern = list(notes)
        for _ in range(repeat - 1):
            # Transpose each repetition up/down slightly for variation
            last = notes[-1]
            shift = 0  # stay on same root for centroid strategy
            notes.extend(max(21, min(108, p + shift)) for p in pattern[1:])
    return notes


def _build_melody_from_clusters(query_data: dict, strategy: str, tempo: int) -> list:
    """Build MIDI note list from cluster or motif data."""
    # Try to extract intervals from various input formats
    intervals = []

    if isinstance(query_data, dict):
        intervals = (
            query_data.get("centroid_intervals")
            or query_data.get("intervals")
            or []
        )
        if query_data.get("clusters"):
            clusters = query_data["clusters"]
            if strategy == "interpolate":
                # Chain all cluster centroids
                all_intervals = []
                for cluster in clusters[:4]:
                    all_intervals.extend(cluster.get("centroid_intervals", []))
                intervals = all_intervals
            else:
                # centroid strategy: use the largest cluster's centroid
                best = max(clusters, key=lambda c: c.get("n_members", 0))
                intervals = best.get("centroid_intervals", [])
        elif query_data.get("motifs") and strategy == "centroid":
            top_motif = sorted(
                query_data["motifs"], key=lambda m: -m.get("occurrences", 0)
            )[:1]
            if top_motif:
                intervals = top_motif[0].get("intervals", [])

    if not intervals:
        # Fallback: simple diatonic scale motif
        intervals = [2, 2, -1, 2, 2, 2, -1]

    # Clean intervals (allow up to 2-octave jumps; _intervals_to_midi_notes clamps pitch range)
    intervals = [int(round(x)) for x in intervals[:16] if isinstance(x, (int, float)) and abs(x) <= 24]
    if not intervals:
        intervals = [2, 2, -1, 2, 2, 2, -1]

    repeat = 4 if strategy == "centroid" else 2
    return _intervals_to_midi_notes(intervals, start_pitch=60, repeat=repeat)


def _generate_midi_bytes_raw(midi_notes: list, tempo: int) -> bytes:
    """
    Generate a valid MIDI Type-0 file using only the standard library.
    Uses the MIDI spec directly — no music21 dependency.
    """
    # Convert BPM to microseconds per beat
    us_per_beat = int(60_000_000 / max(1, tempo))

    def var_len(value: int) -> bytes:
        """Encode a variable-length MIDI quantity."""
        result = [value & 0x7F]
        value >>= 7
        while value:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        return bytes(reversed(result))

    def uint32_be(v: int) -> bytes:
        return v.to_bytes(4, "big")

    def uint16_be(v: int) -> bytes:
        return v.to_bytes(2, "big")

    ticks_per_beat = 480
    note_duration_ticks = ticks_per_beat // 2  # eighth note

    track_events = bytearray()

    # Tempo event (delta=0)
    track_events += var_len(0)          # delta time
    track_events += b"\xFF\x51\x03"    # meta: set tempo
    track_events += us_per_beat.to_bytes(3, "big")

    # Note events
    channel = 0x00  # channel 1
    velocity = 80

    for pitch in midi_notes:
        pitch = max(0, min(127, int(pitch)))
        # Note On
        track_events += var_len(0)
        track_events += bytes([0x90 | channel, pitch, velocity])
        # Note Off (after duration)
        track_events += var_len(note_duration_ticks)
        track_events += bytes([0x80 | channel, pitch, 0])

    # End of track
    track_events += var_len(0)
    track_events += b"\xFF\x2F\x00"

    track_bytes = bytes(track_events)

    # Build MIDI file
    header = b"MThd" + uint32_be(6) + uint16_be(0) + uint16_be(1) + uint16_be(ticks_per_beat)
    track  = b"MTrk" + uint32_be(len(track_bytes)) + track_bytes
    return header + track


def _generate_midi_bytes(midi_notes: list, tempo: int) -> bytes:
    """Generate MIDI bytes — tries music21 first, falls back to pure-Python implementation."""
    try:
        from music21 import stream, note as m21note, tempo as m21tempo

        s = stream.Stream()
        s.append(m21tempo.MetronomeMark(number=tempo))

        for midi_num in midi_notes:
            n = m21note.Note()
            n.pitch.midi = int(midi_num)
            n.duration.quarterLength = 0.5
            s.append(n)

        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tf:
            tmp_path = tf.name
        s.write("midi", fp=tmp_path)
        with open(tmp_path, "rb") as f:
            data = f.read()
        os.unlink(tmp_path)
        return data
    except (ImportError, Exception):
        # Pure-Python fallback — works without music21
        return _generate_midi_bytes_raw(midi_notes, tempo)


def run(query_str: str, clusters_json: str = "", tempo: int = 100, strategy: str = "centroid", output_dir: str = "") -> dict:
    # Parse clusters_json first (preferred — real centroid intervals from PatternMapper)
    query_data = {}
    if clusters_json:
        try:
            query_data = json.loads(clusters_json)
        except json.JSONDecodeError:
            pass

    # Fall back to --query JSON
    if not query_data and query_str and query_str.strip() not in ("centroid", "interpolate", ""):
        try:
            query_data = json.loads(query_str)
        except json.JSONDecodeError:
            query_data = {}

    midi_notes = _build_melody_from_clusters(query_data, strategy=strategy, tempo=tempo)
    n_notes = len(midi_notes)

    # Track the actual intervals used (for reporting)
    _used_intervals = []
    if query_data.get("clusters"):
        clusters = query_data["clusters"]
        if strategy == "interpolate":
            for c in clusters[:4]:
                _used_intervals.extend(c.get("centroid_intervals", []))
        else:
            best = max(clusters, key=lambda c: c.get("n_members", 0))
            _used_intervals = best.get("centroid_intervals", [])
    elif query_data.get("motifs"):
        top = sorted(query_data["motifs"], key=lambda m: -m.get("occurrences", 0))[:1]
        if top:
            _used_intervals = top[0].get("intervals", [])
    elif query_data.get("intervals") or query_data.get("centroid_intervals"):
        _used_intervals = query_data.get("centroid_intervals") or query_data.get("intervals", [])

    # Generate MIDI bytes
    midi_bytes = _generate_midi_bytes(midi_notes, tempo=tempo)

    # Duration
    beats_per_note = 0.5
    duration_s = round((n_notes * beats_per_note * 60.0) / tempo, 2)

    # Save to disk
    out_dir = Path(output_dir) if output_dir else MIDI_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    out_path = out_dir / f"motif_{ts}.mid"

    if midi_bytes:
        with open(out_path, "wb") as f:
            f.write(midi_bytes)
        midi_b64 = base64.b64encode(midi_bytes).decode("ascii")
    else:
        midi_b64 = ""

    return {
        "midi_b64": midi_b64[:512] + "..." if len(midi_b64) > 512 else midi_b64,  # truncate for JSON display
        "midi_b64_truncated": len(midi_b64) > 512,
        "motif_count": max(1, n_notes // 8),
        "duration_s": duration_s,
        "tempo": tempo,
        "strategy": strategy,
        "output_path": str(out_path) if midi_bytes else "",
        "n_notes": n_notes,
        "n_intervals": len(_used_intervals),
        "source_intervals": [round(float(x), 2) for x in _used_intervals[:16]],
    }


def main():
    args = _parse_args()
    if args.describe_schema:
        print(json.dumps(SCHEMA, indent=2))
        return
    result = run(
        query_str=args.query,
        clusters_json=args.clusters_json,
        tempo=args.tempo,
        strategy=args.strategy,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
