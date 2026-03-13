#!/usr/bin/env python3
"""
Point cloud generator for Hierarchical Ribbed Membrane Lattice.
Inspired by Cricket wing harp + Cicada tymbal geometry.

Outputs:
  membrane_lattice.xyz  - ASCII x y z r g b
  membrane_lattice.pcd  - PCL ASCII format
  pointcloud_views.png  - 4-panel matplotlib figure
  stdout               - JSON artifact
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


# ---------------------------------------------------------------------------
# Geometry generators
# ---------------------------------------------------------------------------

def gen_cricket_harp_layer(W, H, thickness, rng):
    """
    Layer 0 (z ~ 0):
      - Base membrane (8000 pts)  grey  (180,180,180)
      - Diagonal file ridge        red   (220, 50, 50)
      - Harp veins (X-parallel)   orange(220,140, 50)
    """
    pts = []

    # --- Base membrane ---
    n_base = 8000
    x = rng.uniform(0, W, n_base)
    y = rng.uniform(0, H, n_base)
    z = rng.normal(0, thickness * 0.05, n_base)   # slight surface roughness
    rgb = np.tile([180, 180, 180], (n_base, 1))
    pts.append(np.column_stack([x, y, z, rgb]))

    # --- Diagonal file ridge: runs ~45° from (0,0) to (W, W) capped at H ---
    n_ridge = 2000
    t = rng.uniform(0, 1, n_ridge)
    # Ridge centre line: x = t*W, y = t*W (45°), capped
    xr = t * W
    yr = t * W
    mask = yr <= H
    xr, yr = xr[mask], yr[mask]
    # Add transverse noise (ridge width ~2 mm)
    ridge_width = 2.0
    perp_noise = rng.normal(0, ridge_width * 0.3, len(xr))
    xr = xr + perp_noise * np.cos(np.pi * 3 / 4)
    yr = yr + perp_noise * np.sin(np.pi * 3 / 4)
    # Clamp to plate
    xr = np.clip(xr, 0, W)
    yr = np.clip(yr, 0, H)
    # Ridge height profile: Gaussian cross-section
    ridge_h = 0.6 * np.exp(-0.5 * (perp_noise / (ridge_width * 0.3)) ** 2)
    zr = ridge_h
    rgb_r = np.tile([220, 50, 50], (len(xr), 1))
    pts.append(np.column_stack([xr, yr, zr, rgb_r]))

    # --- Harp veins: parallel lines along X at regular Y positions ---
    vein_spacing = H / 8.0   # ~8 veins
    vein_ys = np.arange(vein_spacing / 2, H, vein_spacing)
    n_per_vein = max(1, 1500 // len(vein_ys))
    for vy in vein_ys:
        xv = rng.uniform(0, W, n_per_vein)
        yv = rng.normal(vy, 0.3, n_per_vein)
        zv = 0.25 + rng.normal(0, 0.03, n_per_vein)
        rgb_v = np.tile([220, 140, 50], (n_per_vein, 1))
        pts.append(np.column_stack([xv, yv, zv, rgb_v]))

    return np.vstack(pts)


def gen_cicada_tymbal_layer(W, H, z_offset, rng):
    """
    Layer 1 (z ~ z_offset):
      Graded-height corrugation ribs along X (Y-spaced).
      Cosine envelope: tall at Y=H/2, zero at edges.
      ~3000 pts  blue (50,100,220)
    """
    n_pts = 3000
    rib_spacing = 3.0  # mm between corrugation crests
    rib_ys = np.arange(rib_spacing / 2, H, rib_spacing)

    n_per_rib = max(1, n_pts // len(rib_ys))
    pts = []
    max_rib_h = 1.2   # mm at plate centre

    for ry in rib_ys:
        # Cosine envelope: amplitude proportional to cos(pi * (y - H/2) / H)
        env = max_rib_h * np.cos(np.pi * (ry - H / 2) / H) ** 2
        xv = rng.uniform(0, W, n_per_rib)
        yv = rng.normal(ry, 0.25, n_per_rib)
        # Rib height modulated by envelope
        zv = z_offset + env * (0.5 + 0.5 * np.cos(2 * np.pi * xv / W))
        rgb_v = np.tile([50, 100, 220], (n_per_rib, 1))
        pts.append(np.column_stack([xv, yv, zv, rgb_v]))

    return np.vstack(pts)


def gen_hierarchical_lattice_layer(W, H, z_offset, rib_spacing_mm, rib_heights, rng):
    """
    Layer 2 (z ~ z_offset):
      Three-scale rib lattice:
        Primary   (thick, X-parallel): spacing = rib_spacing_mm,         h = rib_heights[0]  dark green
        Secondary (medium, Y-parallel): spacing = rib_spacing_mm/3,      h = rib_heights[1]  med green
        Tertiary  (fine, X-parallel):  spacing = rib_spacing_mm/6,       h = rib_heights[2]  light green
      Total ~4000 pts
    """
    pts = []

    # --- Primary ribs: X-parallel (constant Y lines), thick ---
    sp_primary = rib_spacing_mm
    rib_ys = np.arange(sp_primary / 2, H, sp_primary)
    n_primary_per = max(1, 1500 // max(1, len(rib_ys)))
    for ry in rib_ys:
        xv = rng.uniform(0, W, n_primary_per)
        yv = rng.normal(ry, 0.15, n_primary_per)
        zv = z_offset + rib_heights[0] * rng.uniform(0.9, 1.0, n_primary_per)
        rgb_v = np.tile([20, 120, 50], (n_primary_per, 1))
        pts.append(np.column_stack([xv, yv, zv, rgb_v]))

    # --- Secondary ribs: Y-parallel (constant X lines), medium ---
    sp_secondary = rib_spacing_mm / 3.0
    rib_xs = np.arange(sp_secondary / 2, W, sp_secondary)
    n_secondary_per = max(1, 1500 // max(1, len(rib_xs)))
    for rx in rib_xs:
        xv = rng.normal(rx, 0.1, n_secondary_per)
        yv = rng.uniform(0, H, n_secondary_per)
        zv = z_offset + rib_heights[1] * rng.uniform(0.85, 1.0, n_secondary_per)
        rgb_v = np.tile([80, 180, 80], (n_secondary_per, 1))
        pts.append(np.column_stack([xv, yv, zv, rgb_v]))

    # --- Tertiary ribs: X-parallel, fine ---
    sp_tertiary = rib_spacing_mm / 6.0
    rib_ys_t = np.arange(sp_tertiary / 2, H, sp_tertiary)
    n_tertiary_per = max(1, 1000 // max(1, len(rib_ys_t)))
    for ry in rib_ys_t:
        xv = rng.uniform(0, W, n_tertiary_per)
        yv = rng.normal(ry, 0.05, n_tertiary_per)
        zv = z_offset + rib_heights[2] * rng.uniform(0.8, 1.0, n_tertiary_per)
        rgb_v = np.tile([160, 220, 160], (n_tertiary_per, 1))
        pts.append(np.column_stack([xv, yv, zv, rgb_v]))

    return np.vstack(pts)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def write_xyz(path, cloud):
    """Write ASCII XYZ+RGB: x y z r g b"""
    with open(path, 'w') as f:
        for row in cloud:
            f.write(f"{row[0]:.6f} {row[1]:.6f} {row[2]:.6f} "
                    f"{int(row[3])} {int(row[4])} {int(row[5])}\n")


def write_pcd(path, cloud):
    """Write PCL ASCII PCD v0.7 with XYZRGB fields."""
    n = len(cloud)
    header = (
        "# .PCD v0.7 - Point Cloud Data file format\n"
        "VERSION 0.7\n"
        "FIELDS x y z rgb\n"
        "SIZE 4 4 4 4\n"
        "TYPE F F F F\n"
        "COUNT 1 1 1 1\n"
        f"WIDTH {n}\n"
        "HEIGHT 1\n"
        "VIEWPOINT 0 0 0 1 0 0 0\n"
        f"POINTS {n}\n"
        "DATA ascii\n"
    )
    with open(path, 'w') as f:
        f.write(header)
        for row in cloud:
            r, g, b = int(row[3]), int(row[4]), int(row[5])
            rgb_packed = float((r << 16) | (g << 8) | b)
            f.write(f"{row[0]:.6f} {row[1]:.6f} {row[2]:.6f} {rgb_packed:.0f}\n")


def write_png(path, cloud, max_pts=5000):
    """4-panel figure: isometric, XY, XZ, YZ."""
    n = len(cloud)
    if n > max_pts:
        idx = np.random.choice(n, max_pts, replace=False)
        c = cloud[idx]
    else:
        c = cloud

    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    colors = c[:, 3:6] / 255.0

    fig = plt.figure(figsize=(14, 11))
    fig.patch.set_facecolor('#1a1a2e')

    titles = ['Isometric View', 'Top-Down (XY)', 'Side XZ', 'Side YZ']
    axes_specs = [
        {'type': '3d'},
        {'type': '2d', 'xlabel': 'X (mm)', 'ylabel': 'Y (mm)', 'data': (x, y)},
        {'type': '2d', 'xlabel': 'X (mm)', 'ylabel': 'Z (mm)', 'data': (x, z)},
        {'type': '2d', 'xlabel': 'Y (mm)', 'ylabel': 'Z (mm)', 'data': (y, z)},
    ]

    for i, (title, spec) in enumerate(zip(titles, axes_specs)):
        if spec['type'] == '3d':
            ax = fig.add_subplot(2, 2, i + 1, projection='3d')
            ax.set_facecolor('#0d0d1a')
            ax.scatter(x, y, z, c=colors, s=0.5, alpha=0.6, linewidths=0)
            ax.set_xlabel('X (mm)', color='white', fontsize=7)
            ax.set_ylabel('Y (mm)', color='white', fontsize=7)
            ax.set_zlabel('Z (mm)', color='white', fontsize=7)
            ax.view_init(elev=25, azim=45)
            ax.tick_params(colors='white', labelsize=6)
        else:
            ax = fig.add_subplot(2, 2, i + 1)
            ax.set_facecolor('#0d0d1a')
            ax.scatter(spec['data'][0], spec['data'][1], c=colors, s=0.5,
                       alpha=0.6, linewidths=0)
            ax.set_xlabel(spec['xlabel'], color='white', fontsize=8)
            ax.set_ylabel(spec['ylabel'], color='white', fontsize=8)
            ax.tick_params(colors='white', labelsize=6)
            for spine in ax.spines.values():
                spine.set_edgecolor('#555')

        ax.set_title(title, color='white', fontsize=10, pad=6)

    fig.suptitle('Hierarchical Ribbed Membrane Lattice – Point Cloud',
                 color='white', fontsize=13, y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate(spec: dict, output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    rng = np.random.default_rng(seed=42)

    # --- Parameters (spec overrides defaults) ---
    W = float(spec.get('plate_w_mm', 50.0))
    H = float(spec.get('plate_h_mm', 120.0))
    thickness = float(spec.get('thickness_mm', 0.4))
    layer_sep = float(spec.get('layer_separation_mm', 1.5))
    rib_spacing = float(spec.get('rib_spacing_mm', 2.5))
    rib_heights = [
        float(spec.get('rib_height_primary_mm', 0.8)),
        float(spec.get('rib_height_secondary_mm', 0.5)),
        float(spec.get('rib_height_tertiary_mm', 0.3)),
    ]

    # --- Generate each layer ---
    z0 = 0.0
    z1 = z0 + layer_sep
    z2 = z1 + layer_sep

    harp = gen_cricket_harp_layer(W, H, thickness, rng)
    tymbal = gen_cicada_tymbal_layer(W, H, z1, rng)
    lattice = gen_hierarchical_lattice_layer(W, H, z2, rib_spacing, rib_heights, rng)

    cloud = np.vstack([harp, tymbal, lattice])

    # --- Bounding box ---
    bb = {
        'x_min': float(cloud[:, 0].min()), 'x_max': float(cloud[:, 0].max()),
        'y_min': float(cloud[:, 1].min()), 'y_max': float(cloud[:, 1].max()),
        'z_min': float(cloud[:, 2].min()), 'z_max': float(cloud[:, 2].max()),
    }

    # --- Write outputs ---
    xyz_path = os.path.join(output_dir, 'membrane_lattice.xyz')
    pcd_path = os.path.join(output_dir, 'membrane_lattice.pcd')
    png_path = os.path.join(output_dir, 'pointcloud_views.png')

    write_xyz(xyz_path, cloud)
    write_pcd(pcd_path, cloud)
    write_png(png_path, cloud)

    # --- Layer point counts ---
    counts = {
        'cricket_harp_layer': len(harp),
        'cicada_tymbal_layer': len(tymbal),
        'hierarchical_lattice_layer': len(lattice),
        'total': len(cloud),
    }

    artifact = {
        'artifact_type': 'pointcloud',
        'name': spec.get('name', 'Hierarchical Ribbed Membrane Lattice'),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'parameters': {
            'plate_w_mm': W,
            'plate_h_mm': H,
            'thickness_mm': thickness,
            'layer_separation_mm': layer_sep,
            'rib_spacing_mm': rib_spacing,
            'rib_heights_mm': rib_heights,
        },
        'point_counts': counts,
        'bounding_box_mm': bb,
        'files': {
            'xyz': os.path.abspath(xyz_path),
            'pcd': os.path.abspath(pcd_path),
            'png': os.path.abspath(png_path),
        },
        'layers': [
            {
                'name': 'cricket_harp',
                'z_offset_mm': z0,
                'elements': ['base_membrane', 'file_ridge', 'harp_veins'],
                'inspiration': 'Gryllus bimaculatus wing harp',
            },
            {
                'name': 'cicada_tymbal',
                'z_offset_mm': z1,
                'elements': ['graded_corrugation_ribs'],
                'inspiration': 'Cicada tymbal cosine-envelope rib grading',
            },
            {
                'name': 'hierarchical_lattice',
                'z_offset_mm': z2,
                'elements': ['primary_ribs', 'secondary_ribs', 'tertiary_ribs'],
                'scales': 3,
            },
        ],
    }
    return artifact


def main():
    parser = argparse.ArgumentParser(
        description='Generate hierarchical ribbed membrane lattice point cloud.'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--spec', type=str, help='JSON spec string')
    group.add_argument('--spec-file', type=str, help='Path to JSON spec file')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    args = parser.parse_args()

    if args.spec:
        spec = json.loads(args.spec)
    else:
        with open(args.spec_file) as f:
            spec = json.load(f)

    artifact = generate(spec, args.output_dir)
    print(json.dumps(artifact, indent=2))


if __name__ == '__main__':
    main()
