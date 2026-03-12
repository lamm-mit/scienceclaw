---
name: stl-renderer
description: Render publication-quality PNG views of any binary STL file — isometric (3-D perspective), top-down XY projection, and XZ cross-section at Y midpoint. All dimensions derived from the STL bounding box; nothing hardcoded. Optionally uploads to imgur and returns URLs. Chainable downstream of geometry-generator or any skill that produces an STL.
metadata:
  category: visualisation
  requires: numpy, matplotlib, mpl_toolkits
---

# STL Renderer

Produces three views of any binary STL mesh:

| View | Description |
|---|---|
| `isometric` | 3-D perspective, elev=28° azim=−55° |
| `top` | XY top-down projection |
| `crosssection` | XZ slice at Y=midpoint (shows rib/fin profile) |

## Usage

```bash
# All three views, local PNGs
python3 {baseDir}/scripts/stl_renderer.py --stl /path/to/mesh.stl

# Subset of views
python3 {baseDir}/scripts/stl_renderer.py --stl mesh.stl --views isometric crosssection

# Custom output dir + imgur upload
python3 {baseDir}/scripts/stl_renderer.py \
  --stl mesh.stl \
  --out-dir /tmp/render \
  --upload-imgur

# High-res with YZ cross-section instead
python3 {baseDir}/scripts/stl_renderer.py \
  --stl mesh.stl --dpi 300 --slice-axis x
```

## Output JSON

```json
{
  "stl_path": "/path/to/mesh.stl",
  "num_triangles": 7556,
  "bounding_box_mm": {"x": 20.0, "y": 60.0, "z": 1.2},
  "views": {
    "isometric":    {"path": "/tmp/render/mesh_isometric.png",    "url": "https://i.imgur.com/..."},
    "top":          {"path": "/tmp/render/mesh_top.png",          "url": "https://i.imgur.com/..."},
    "crosssection": {"path": "/tmp/render/mesh_crosssection.png", "url": "https://i.imgur.com/..."}
  }
}
```

## Chaining with geometry-generator

```bash
STL=$(python3 skills/geometry-generator/scripts/stl_generator.py \
        --spec '{"rib_spacing_mm":2.5}' --output /tmp/mem.stl | jq -r '.stl_path')

python3 skills/stl-renderer/scripts/stl_renderer.py \
  --stl "$STL" --upload-imgur
```
