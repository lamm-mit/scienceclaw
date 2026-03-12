---
name: fem-analysis
description: Modal analysis of a membrane STL using Kirchhoff plate FEM (scipy eigensolver). Takes a binary STL + material properties JSON, constructs a 2D rectangular FEM mesh, assembles stiffness and mass matrices, extracts the first N eigenfrequencies, and reports whether any mode falls in a target frequency range. Returns artifact JSON with eigenfrequencies_hz, mode_shapes_png, and target_range_pass.
metadata:
  category: materials-design
  requires: numpy, scipy
---

# FEM Modal Analysis

Kirchhoff thin-plate finite element modal analysis for ribbed membrane resonators.

## Usage

```bash
python3 {baseDir}/scripts/modal_analysis.py \
  --stl /path/to/membrane.stl \
  --material '{"E_Pa":3e9,"nu":0.35,"rho_kg_m3":1500}' \
  --target-freq-min 2000 \
  --target-freq-max 8000 \
  --output /tmp/fem_results.json
```

## Output JSON

```json
{
  "eigenfrequencies_hz": [1234.5, 2345.6, ...],
  "num_modes": 10,
  "target_range_hz": [2000, 8000],
  "target_range_pass": true,
  "modes_in_range": [2345.6, 4567.8],
  "mode_shapes_png": "/tmp/mode_shapes.png",
  "mesh_nx": 40, "mesh_ny": 120,
  "material": {"E_Pa": 3e9, "nu": 0.35, "rho_kg_m3": 1500}
}
```
