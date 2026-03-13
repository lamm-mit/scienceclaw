---
name: lsystem-executor
description: Execute L-system and shape grammars to produce visual derivations, SVG/PNG renders, and optional STL meshes
metadata:
---

# L-System Executor

Execute parametric L-system grammars and render the results as images or meshes.

## Overview

Takes a grammar definition (axiom + rewrite rules) and produces:
- Step-by-step derivation showing the string at each iteration
- 2D turtle-graphics rendering as SVG and PNG
- Optional 3D extrusion to STL (if `--stl` flag is passed)

Useful for investigations that produce symbolic growth grammars (urban evolution,
microstructure growth, biological branching) and need a concrete visual artifact.

## Usage

### From a JSON grammar file:
```bash
python3 {baseDir}/scripts/lsystem_render.py --grammar grammar.json --steps 4 --output output_dir/
```

### Inline grammar:
```bash
python3 {baseDir}/scripts/lsystem_render.py \
  --axiom "A" \
  --rules '{"A": "A[+B]A[-B]A", "B": "BB"}' \
  --angle 25 \
  --steps 4 \
  --output output_dir/
```

### With STL export:
```bash
python3 {baseDir}/scripts/lsystem_render.py \
  --grammar grammar.json \
  --steps 3 \
  --stl \
  --output output_dir/
```

## Grammar JSON Format

```json
{
  "axiom": "A",
  "rules": {
    "A": "A[+B]A[-B]A",
    "B": "BB"
  },
  "angle": 25.0,
  "step_length": 10.0,
  "length_scale": 1.0,
  "title": "Urban-Material Growth Grammar"
}
```

### Symbols

| Symbol | Meaning |
|--------|---------|
| `F` | Move forward, drawing a line |
| `A-Z` (uppercase) | Move forward, drawing a line (also rewritable) |
| `f` | Move forward without drawing |
| `+` | Turn left by angle |
| `-` | Turn right by angle |
| `[` | Push position and heading onto stack |
| `]` | Pop position and heading from stack |
| `!` | Decrease line width |
| `>` | Multiply step length by length_scale |

## Outputs

The script produces in the output directory:
- `derivation.txt` — string at each step
- `render.svg` — vector graphics of the final structure
- `render.png` — rasterized version (300 DPI)
- `render_steps.png` — grid showing each derivation step side by side
- `grammar.json` — the grammar used (for reproducibility)
- `render.stl` — 3D mesh (only if `--stl` flag is used)
