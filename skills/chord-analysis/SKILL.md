# chord-analysis

Performs harmonic analysis on a music corpus using music21. Takes corpus JSON (from music-corpus skill) or a query string, runs Roman numeral analysis, and returns chord progression frequencies and transition matrices.

## Usage

```bash
python3 skills/chord-analysis/scripts/chord_analysis.py --query "bach"
python3 skills/chord-analysis/scripts/chord_analysis.py --query "bach" --input-json /path/to/corpus.json
```

## Output

```json
{
  "query": "bach",
  "n_pieces_analysed": 10,
  "chord_progressions": [
    {"chord": "I", "roman": "I", "count": 142, "frequency": 0.18},
    {"chord": "V", "roman": "V", "count": 98, "frequency": 0.12}
  ],
  "top_bigrams": [["I", "V"], ["V", "I"], ["I", "IV"]],
  "transition_matrix": {"I": {"V": 0.34, "IV": 0.21}},
  "total_chords": 782
}
```

## Dependencies

- music21
