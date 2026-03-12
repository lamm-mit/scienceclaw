---
name: geometry-generator
description: Generate parametric bioinspired ribbed membrane STL geometry via LLM-guided design. Takes a spec JSON (from StructureAnalyst/PropertyPredictor upstream artifacts), calls the LLM with a structured CAD prompt to produce design parameters, then builds a triangulated STL mesh in Python. Returns artifact JSON with stl_path, mesh stats, and the prompt used.
metadata:
  category: materials-design
  requires: numpy, scipy, core/llm_client
---

# Geometry Generator

Generates parametric bioinspired hierarchical ribbed membrane STL geometry.

All design parameters flow from upstream artifacts (StructureAnalyst motifs +
PropertyPredictor targets) — no hardcoded values.

## Usage

```bash
# From upstream artifact spec file
python3 {baseDir}/scripts/stl_generator.py \
  --spec '{"rib_spacing_mm":2.5,"thickness_mm":0.4,"aspect_ratio":3.0,"num_scales":2}' \
  --output /tmp/membrane.stl

# From upstream artifact file
python3 {baseDir}/scripts/stl_generator.py \
  --spec-file /path/to/structural_motifs.json \
  --output /tmp/membrane.stl
```

## Output JSON

```json
{
  "stl_path": "/path/to/membrane.stl",
  "num_vertices": 1234,
  "num_faces": 2468,
  "bounding_box_mm": {"x": 20.0, "y": 20.0, "z": 1.2},
  "primary_rib_count": 8,
  "secondary_rib_count": 16,
  "prompt_used": "...",
  "design_params": {...}
}
```

## STL Prompt

The LLM is called with the canonical bioinspired ribbed membrane prompt
(see PROMPT.md). It returns structured design parameters as JSON.
Python then constructs the mesh from those parameters.
