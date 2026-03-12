# motif-detection

Extracts repeated melodic and rhythmic motifs from a music corpus using sliding-window interval encoding. Returns motifs with interval sequences, occurrence counts, and piece references.

## Usage

```bash
python3 skills/motif-detection/scripts/motif_detection.py --query "bach" --min-length 4 --min-occurrences 3
```

## Output

```json
{
  "query": "bach",
  "motifs": [
    {
      "motif_id": "m_0001",
      "intervals": [2, -2, 1, -1],
      "interval_str": "+2,-2,+1,-1",
      "occurrences": 14,
      "pieces": ["BWV 253", "BWV 281"],
      "genre": "baroque"
    }
  ],
  "n_motifs": 47,
  "min_length": 4,
  "min_occurrences": 3
}
```

## Dependencies

- music21
