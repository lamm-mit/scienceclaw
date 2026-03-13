---
name: pointcloud-generator
description: Generate a colour-coded 3D point cloud (.xyz + .pcd) for bioinspired hierarchical ribbed membrane lattices — Cricket wing harp layer, Cicada tymbal corrugation layer, and multi-scale hierarchical lattice layer. Each structural element is analytically sampled (pure numpy, no LLM, no OpenSCAD) and assigned a distinct RGB colour. Produces ASCII XYZ, PCL v0.7 ASCII PCD, and a 4-panel PNG (isometric, top-XY, side-XZ, side-YZ). Chainable downstream of pointcloud-generator or upstream of fem-analysis.
metadata:
  category: materials-design
  requires: numpy, matplotlib, mpl_toolkits
---

# Point Cloud Generator

Generates a 3D point cloud for a **Hierarchical Ribbed Membrane Lattice** inspired by
*Gryllus bimaculatus* (cricket wing harp) and cicada tymbal geometry.

Three structurally distinct Z-layers are sampled analytically:

| Layer | Z offset | Structural feature | Colour |
|---|---|---|---|
| Cricket harp | 0 mm | Base membrane + diagonal file ridge + parallel harp veins | grey / red / orange |
| Cicada tymbal | +1.5 mm | Cosine-graded corrugation ribs (tall centre, zero at edges) | blue |
| Hierarchical lattice | +3.0 mm | Primary / secondary / tertiary rib scales (3 densities) | dark / mid / light green |

## Usage

```bash
# From inline JSON spec
python3 {baseDir}/scripts/pointcloud_generator.py \
  --spec '{"biological_inspiration":"Cricket wing harp + Cicada tymbal",
           "rib_spacing_mm":2.5,"thickness_mm":0.4,"aspect_ratio":2.5,"num_scales":3}' \
  --output-dir /tmp/pointcloud_out

# From spec file
python3 {baseDir}/scripts/pointcloud_generator.py \
  --spec-file /path/to/spec.json \
  --output-dir /tmp/pointcloud_out
```

## Output JSON (stdout)

```json
{
  "xyz_path":  "/tmp/pointcloud_out/membrane_lattice.xyz",
  "pcd_path":  "/tmp/pointcloud_out/membrane_lattice.pcd",
  "png_path":  "/tmp/pointcloud_out/pointcloud_views.png",
  "total_points": 18348,
  "bounding_box_mm": {"x_min":0,"x_max":50,"y_min":0,"y_max":120,"z_min":-0.07,"z_max":3.80},
  "layers": {
    "cricket_harp":       {"points": 11496, "z_mm": 0.0},
    "cicada_tymbal":      {"points": 3000,  "z_mm": 1.5},
    "hierarchical_lattice":{"points": 3852, "z_mm": 3.0}
  }
}
```

## Output Files

| File | Format | Description |
|---|---|---|
| `membrane_lattice.xyz` | ASCII `x y z r g b` | Standard XYZ+RGB, one point per line |
| `membrane_lattice.pcd` | PCL v0.7 ASCII | Compatible with PCL, CloudCompare, Open3D |
| `pointcloud_views.png` | PNG | 4-panel matplotlib figure, dark background |

## Geometry Parameters (from spec)

| Field | Default | Effect |
|---|---|---|
| `rib_spacing_mm` | 2.5 | Primary rib pitch; secondary = ÷3, tertiary = ÷6 |
| `thickness_mm` | 0.4 | Base membrane thickness; controls Z roughness |
| `aspect_ratio` | 2.5 | H = W × aspect_ratio (W fixed at 50 mm) |
| `num_scales` | 3 | Number of rib hierarchy levels (2 or 3) |

## Chaining

```bash
# Generate point cloud then run FEM on same spec
PCD=$(python3 skills/pointcloud-generator/scripts/pointcloud_generator.py \
        --spec '{"rib_spacing_mm":2.5,"thickness_mm":0.4}' \
        --output-dir /tmp/out | jq -r '.pcd_path')

python3 skills/fem-analysis/scripts/mechanism_analysis.py \
  --stl /tmp/out/membrane_lattice.xyz \   # FEM reads bounding box from any 3D file
  --topology cricket_harp \
  --rib-spacing-mm 2.5 --rib-height-mm 0.8
```

## Colour Legend

```
■ grey   (180,180,180)  Base membrane
■ red    (220, 50, 50)  Diagonal file ridge (cricket harp)
■ orange (220,140, 50)  Harp veins (X-parallel)
■ blue   ( 50,100,220)  Cicada tymbal corrugation ribs (graded height)
■ dark ■ (20,120,50)    Primary ribs — level 1 (coarse, 2.5 mm pitch)
■ mid  ■ (80,180,80)    Secondary ribs — level 2 (medium, 0.83 mm pitch)
■ light■ (160,220,160)  Tertiary ribs — level 3 (fine, 0.42 mm pitch)
```
