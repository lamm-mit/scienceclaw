# music-corpus

Downloads and parses a small open MIDI corpus using music21's built-in corpus (Bach chorales and other included works). Returns structured JSON with piece metadata, chord sequences, and note sequences for downstream harmonic and motif analysis.

## Usage

```bash
python3 skills/music-corpus/scripts/music_corpus.py --query "bach" --max-pieces 10
python3 skills/music-corpus/scripts/music_corpus.py --query "folk" --max-pieces 5 --format json
```

## Output

```json
{
  "query": "bach",
  "pieces": [
    {
      "title": "Chorale BWV 253",
      "composer": "Bach",
      "key": "G major",
      "tempo": 100,
      "time_signature": "4/4",
      "chord_sequence": ["G", "D", "Em", "C"],
      "note_sequence": [67, 69, 71, 72],
      "duration_beats": 32,
      "n_measures": 8
    }
  ],
  "total_pieces": 10,
  "total_notes": 4821
}
```

## Dependencies

- music21 (pip install music21)
