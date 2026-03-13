---
name: jax-modal-analysis
description: 3D tetrahedral FEM modal analysis of a membrane STL. Takes a binary STL (mm units) + material properties JSON, repairs surface mesh, generates tetrahedral volume mesh via TetGen, assembles 3D stiffness/mass matrices with jax-fem, solves the generalised eigenvalue problem, and reports eigenfrequencies + mode shapes. Returns artifact JSON with eigenfrequencies_hz, eigenfrequencies_khz, modes_in_range, target_range_pass, and paths to summary PNG and CSV.
metadata:
  category: materials-design
  requires: stl_modal_pipeline, tetgen, pyvista, meshio, trimesh, scipy, jax
  conda_env: jax_fem
---

# JAX 3D Modal Analysis

Full 3D tetrahedral FEM eigenvalue solver for ribbed membrane resonators.
Complements `fem-analysis` (2D Kirchhoff plate approximation) by accounting for
3D volumetric effects, frame stiffness, and out-of-plane deformation.

## Usage

```bash
python3 {baseDir}/scripts/jax_modal_analysis.py \
  --stl /path/to/membrane.stl \
  --material '{"E_Pa":3e9,"nu":0.35,"rho_kg_m3":1500}' \
  --num-modes 12 \
  --solver-backend jax-iterative \
  --stl-length-scale 1e-3 \
  --target-freq-min 2000 \
  --target-freq-max 8000 \
  --output-dir /tmp/jax_modal_results
```

## Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--stl` | path | required | Binary STL file (mm units assumed) |
| `--material` | JSON str | required | `{"E_Pa":3e9,"nu":0.35,"rho_kg_m3":1500}` |
| `--num-modes` | int | 12 | Number of modes to compute |
| `--solver-backend` | str | `jax-iterative` | `arpack`, `jax-iterative`, or `jax-xla` |
| `--stl-length-scale` | float | `1e-3` | Scale factor to convert STL units → metres |
| `--target-freq-min` | float | 2000 | Lower bound of target frequency band (Hz) |
| `--target-freq-max` | float | 8000 | Upper bound of target frequency band (Hz) |
| `--output-dir` | path | auto | Directory for all output files |

## Output JSON

```json
{
  "stl_path": "/path/to/membrane.stl",
  "topology": "v1_cricket_fine",
  "num_modes_computed": 12,
  "eigenfrequencies_hz":  [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2153.0, 2388.1, ...],
  "eigenfrequencies_khz": [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 2.153, 2.388, ...],
  "modes_in_range_hz":  [2153.0, 2388.1, 5401.2, 6890.3],
  "modes_in_range_khz": [2.153, 2.388, 5.401, 6.890],
  "target_range_hz": [2000, 8000],
  "target_range_khz": [2.0, 8.0],
  "target_range_pass": true,
  "solver_backend": "arpack",
  "output_dir": "/tmp/jax_modal_results/v1_cricket_fine_...",
  "summary_png": "/tmp/.../summary_figures/modal_run_summary.png",
  "csv_path": "/tmp/.../modal_comprehensive_report.csv",
  "mesh_vtu": "/tmp/.../mesh/volume_mesh.vtu"
}
```

## Chaining with fem-analysis

`fem-analysis` and `jax-modal-analysis` are **complementary**, not alternatives:

| Skill | Model | Speed | Best for |
|-------|-------|-------|----------|
| `fem-analysis` | 2D Kirchhoff plate | ~1 s | Fast screening, flat membranes |
| `jax-modal-analysis` | 3D tetrahedral FEM | 30–120 s | Full 3D validation, ribbed/curved geometries |

Recommended workflow:
1. Run `fem-analysis` to shortlist candidates (fast 2D pass/fail)
2. Run `jax-modal-analysis` on shortlisted STLs for full 3D validation
