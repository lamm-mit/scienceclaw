# midi-generator

Generates MIDI files from motif JSON or cluster centroids using music21. Outputs base64-encoded MIDI bytes plus saves a .mid file to ~/.scienceclaw/midi/.

## Usage

```bash
python3 skills/midi-generator/scripts/midi_generator.py --query '{"intervals":[2,-2,1,-1]}' --tempo 72
python3 skills/midi-generator/scripts/midi_generator.py --query "centroid" --tempo 120 --strategy interpolate
```

## Output

```json
{
  "midi_b64": "TVRoZAAAAAYAAQAB...",
  "motif_count": 4,
  "duration_s": 12.3,
  "tempo": 72,
  "strategy": "centroid",
  "output_path": "/home/user/.scienceclaw/midi/motif_1234567890.mid",
  "n_notes": 24
}
```

## Dependencies

- music21
