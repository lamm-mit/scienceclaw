#!/usr/bin/env python3
"""
STL Renderer — three publication-quality views of any binary STL file.

Produces:
  - isometric.png     3-D perspective view
  - top.png           XY top-down projection
  - crosssection.png  XZ slice at Y = midpoint

All geometry derived from the STL bounding box — no hardcoded dimensions.

Usage:
  python3 stl_renderer.py --stl /path/to/mesh.stl
  python3 stl_renderer.py --stl /path/to/mesh.stl --out-dir /tmp/render --upload-imgur
  python3 stl_renderer.py --stl /path/to/mesh.stl --views isometric top  # subset
  python3 stl_renderer.py --stl /path/to/mesh.stl --dpi 300 --max-tris 4000

Output JSON:
  {
    "stl_path": "...",
    "num_triangles": 7556,
    "bounding_box_mm": {"x": 20.0, "y": 60.0, "z": 1.2},
    "views": {
      "isometric":    {"path": "...", "url": "..."},
      "top":          {"path": "...", "url": "..."},
      "crosssection": {"path": "...", "url": "..."}
    }
  }
"""

import argparse
import json
import struct
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.patches import Polygon as MPoly
from matplotlib.collections import PatchCollection


# ---------------------------------------------------------------------------
# STL parsing
# ---------------------------------------------------------------------------

def _read_stl(path: Path) -> Tuple[np.ndarray, Dict]:
    """
    Parse binary STL → (tris, bbox).
    tris shape: (N, 3, 3)  — N triangles, 3 vertices, xyz
    bbox: {"x_min","x_max","y_min","y_max","z_min","z_max","x","y","z"}
    """
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"STL too small: {len(data)} bytes")
    n_tri = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + n_tri * 50
    if len(data) < expected:
        raise ValueError(f"STL truncated: expected {expected} bytes, got {len(data)}")

    tris = np.zeros((n_tri, 3, 3), dtype=np.float32)
    offset = 84
    for i in range(n_tri):
        offset += 12  # skip normal
        for v in range(3):
            tris[i, v] = struct.unpack_from("<fff", data, offset)
            offset += 12
        offset += 2   # attribute

    xs = tris[:, :, 0].ravel()
    ys = tris[:, :, 1].ravel()
    zs = tris[:, :, 2].ravel()
    bbox = {
        "x_min": float(xs.min()), "x_max": float(xs.max()),
        "y_min": float(ys.min()), "y_max": float(ys.max()),
        "z_min": float(zs.min()), "z_max": float(zs.max()),
        "x": round(float(xs.max() - xs.min()), 3),
        "y": round(float(ys.max() - ys.min()), 3),
        "z": round(float(zs.max() - zs.min()), 3),
    }
    return tris, bbox


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

FILL_COLOR = "#0ea5e9"
EDGE_COLOR = "#0369a1"


def _subsample(tris: np.ndarray, max_tris: int) -> np.ndarray:
    step = max(1, len(tris) // max_tris)
    return tris[::step]


def render_isometric(tris: np.ndarray, bbox: Dict, out_path: Path,
                     dpi: int = 180, max_tris: int = 3000) -> Path:
    """3-D perspective view of the STL."""
    sub = _subsample(tris, max_tris)
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")

    pc = Poly3DCollection(sub, alpha=0.65, linewidth=0,
                          facecolor=FILL_COLOR, edgecolor="none")
    ax.add_collection3d(pc)

    ax.set_xlim(bbox["x_min"], bbox["x_max"])
    ax.set_ylim(bbox["y_min"], bbox["y_max"])
    ax.set_zlim(bbox["z_min"], bbox["z_max"] + bbox["z"] * 0.1)
    ax.set_xlabel("x (mm)", fontsize=9)
    ax.set_ylabel("y (mm)", fontsize=9)
    ax.set_zlabel("z (mm)", fontsize=9)
    ax.set_title(
        f"Isometric view\n"
        f"{bbox['x']:.1f}×{bbox['y']:.1f}×{bbox['z']:.2f} mm  ·  {len(tris):,} triangles",
        fontsize=10, fontweight="bold",
    )
    ax.view_init(elev=28, azim=-55)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_path), dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return out_path


def render_top(tris: np.ndarray, bbox: Dict, out_path: Path,
               dpi: int = 180, max_tris: int = 4000) -> Path:
    """Top-down XY projection."""
    sub = _subsample(tris, max_tris)
    aspect = bbox["y"] / max(bbox["x"], 1e-6)
    fig, ax = plt.subplots(figsize=(6, min(6 * aspect, 14)))

    patches = [MPoly(tri[:, :2], closed=True) for tri in sub]
    pc = PatchCollection(patches, facecolor=FILL_COLOR, edgecolor="none", alpha=0.5)
    ax.add_collection(pc)
    ax.set_xlim(bbox["x_min"], bbox["x_max"])
    ax.set_ylim(bbox["y_min"], bbox["y_max"])
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)", fontsize=10)
    ax.set_ylabel("y (mm)", fontsize=10)
    ax.set_title(
        f"Top view (XY)  —  {bbox['x']:.1f}×{bbox['y']:.1f} mm",
        fontsize=10, fontweight="bold",
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_path), dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return out_path


def render_crosssection(tris: np.ndarray, bbox: Dict, out_path: Path,
                        dpi: int = 180, slice_axis: str = "y") -> Path:
    """
    Cross-section at the midpoint of slice_axis.
    Default: XZ slice at Y = mid  →  shows rib profile.
    """
    if slice_axis == "y":
        mid   = (bbox["y_min"] + bbox["y_max"]) / 2.0
        tol   = (bbox["y_max"] - bbox["y_min"]) * 0.05
        hspan = (bbox["x_min"], bbox["x_max"])
        vspan = (bbox["z_min"] - bbox["z"] * 0.05,
                 bbox["z_max"] + bbox["z"] * 0.15)
        xi, zi = 0, 2
        xlabel, ylabel = "x (mm)", "z (mm)"
        title = f"Cross-section (XZ at Y={mid:.1f} mm)"
        ref_lines = [
            (bbox["z_min"] + (bbox["z_max"] - bbox["z_min"]) * 0.33,
             "#d97706", f"~base: {bbox['z_min'] + (bbox['z_max']-bbox['z_min'])*0.33:.2f} mm"),
            (bbox["z_max"],
             "#dc2626", f"rib top: {bbox['z_max']:.2f} mm"),
        ]
    else:  # x-axis slice
        mid   = (bbox["x_min"] + bbox["x_max"]) / 2.0
        tol   = (bbox["x_max"] - bbox["x_min"]) * 0.05
        hspan = (bbox["y_min"], bbox["y_max"])
        vspan = (bbox["z_min"] - bbox["z"] * 0.05,
                 bbox["z_max"] + bbox["z"] * 0.15)
        xi, zi = 1, 2
        xlabel, ylabel = "y (mm)", "z (mm)"
        title = f"Cross-section (YZ at X={mid:.1f} mm)"
        ref_lines = [
            (bbox["z_max"], "#dc2626", f"top: {bbox['z_max']:.2f} mm"),
        ]

    near = [tri for tri in tris
            if any(abs(v[1 if slice_axis == "y" else 0] - mid) < tol for v in tri)]

    fig_w = min(12, max(6, bbox["x"] / 5))
    fig, ax = plt.subplots(figsize=(fig_w, 4))

    for tri in near:
        xs = [v[xi] for v in tri] + [tri[0][xi]]
        zs = [v[zi] for v in tri] + [tri[0][zi]]
        ax.fill(xs, zs, alpha=0.3, color=FILL_COLOR, linewidth=0)
        ax.plot(xs, zs, color=EDGE_COLOR, linewidth=0.6, alpha=0.8)

    for z_val, col, label in ref_lines:
        ax.axhline(z_val, color=col, linestyle="--", linewidth=1.5, label=label)

    ax.set_xlim(*hspan)
    ax.set_ylim(*vspan)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title + "\nrib profile", fontsize=10, fontweight="bold")
    if ref_lines:
        ax.legend(fontsize=8, loc="upper right")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_path), dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Optional imgur upload
# ---------------------------------------------------------------------------

def _try_upload(path: Path) -> str:
    try:
        _ROOT = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(_ROOT))
        from utils.imgur import upload_figure
        url = upload_figure(path)
        return url or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

VALID_VIEWS = ("isometric", "top", "crosssection")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render isometric / top / cross-section views of a binary STL"
    )
    parser.add_argument("--stl",          required=True, help="Path to binary STL file")
    parser.add_argument("--out-dir",      default="",
                        help="Output directory (default: same dir as STL)")
    parser.add_argument("--views",        nargs="+", default=list(VALID_VIEWS),
                        choices=VALID_VIEWS,
                        help="Which views to render (default: all three)")
    parser.add_argument("--dpi",          type=int, default=180,
                        help="PNG resolution (default 180)")
    parser.add_argument("--max-tris",     type=int, default=3000,
                        help="Subsample cap for 3-D/top views (default 3000)")
    parser.add_argument("--upload-imgur", action="store_true",
                        help="Upload each PNG to imgur and include URL in output")
    parser.add_argument("--slice-axis",   default="y", choices=["x", "y"],
                        help="Axis for cross-section slice (default: y → XZ plane)")
    args = parser.parse_args()

    stl_path = Path(args.stl)
    if not stl_path.exists():
        print(json.dumps({"error": f"STL not found: {args.stl}"}))
        sys.exit(1)

    try:
        tris, bbox = _read_stl(stl_path)
    except Exception as e:
        print(json.dumps({"error": f"STL parse failed: {e}"}))
        sys.exit(1)

    out_dir = Path(args.out_dir) if args.out_dir else stl_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = stl_path.stem
    views_result: Dict[str, Dict] = {}

    render_map = {
        "isometric":    lambda p: render_isometric(tris, bbox, p, args.dpi, args.max_tris),
        "top":          lambda p: render_top(tris, bbox, p, args.dpi, args.max_tris),
        "crosssection": lambda p: render_crosssection(tris, bbox, p, args.dpi,
                                                       args.slice_axis),
    }

    for view in args.views:
        out_path = out_dir / f"{stem}_{view}.png"
        render_map[view](out_path)
        entry: Dict = {"path": str(out_path.resolve())}
        if args.upload_imgur:
            entry["url"] = _try_upload(out_path)
        views_result[view] = entry

    result = {
        "stl_path":      str(stl_path.resolve()),
        "num_triangles": int(len(tris)),
        "bounding_box_mm": {
            "x": bbox["x"], "y": bbox["y"], "z": bbox["z"],
        },
        "views": views_result,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
