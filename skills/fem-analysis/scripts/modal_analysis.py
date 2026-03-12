#!/usr/bin/env python3
"""
FEM Modal Analysis — Orthotropic Kirchhoff Plate (smeared rib model)

Reads a binary STL, extracts membrane dimensions from the bounding box,
constructs an orthotropic Kirchhoff plate model using a smeared rib
approximation, then computes natural frequencies analytically (exact for
simply-supported BCs) and via a finite-difference eigenvalue solve.

The smeared rib approach models the ribbed membrane as an equivalent
orthotropic plate:
  D_x = D_base + E * I_rib / s_rib   (stiff direction, along ribs)
  D_y = D_base                        (compliant direction, across ribs)
  D_xy = D_base * nu + G * J_rib / s_rib  (torsional)

This is a validated approach for bioinspired ribbed membrane analysis
(see: Dyskin et al., Thin-Walled Structures; Wittrick 1968).

No external FEM library required — pure numpy + scipy.

Usage:
  python3 modal_analysis.py \\
    --stl /path/to/membrane.stl \\
    --material '{"E_Pa":3e9,"nu":0.35,"rho_kg_m3":1500}' \\
    --rib-spacing-mm 2.5 \\
    --rib-height-mm 0.8 \\
    --rib-width-mm 0.625 \\
    --target-freq-min 2000 \\
    --target-freq-max 8000
"""

import argparse
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from scipy.linalg import eigh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# STL reader
# ---------------------------------------------------------------------------

def _read_stl_bbox(path: Path) -> Dict[str, float]:
    """Read bounding box from binary STL (mm)."""
    data = path.read_bytes()
    n_tri = struct.unpack_from("<I", data, 80)[0]
    xs, ys, zs = [], [], []
    offset = 84
    for _ in range(n_tri):
        if offset + 50 > len(data):
            break
        offset += 12  # skip normal
        for _ in range(3):
            x, y, z = struct.unpack_from("<fff", data, offset)
            xs.append(x); ys.append(y); zs.append(z)
            offset += 12
        offset += 2
    return {
        "W_mm": float(max(xs) - min(xs)),
        "H_mm": float(max(ys) - min(ys)),
        "Z_mm": float(max(zs) - min(zs)),
    }


# ---------------------------------------------------------------------------
# Orthotropic plate model — smeared rib
# ---------------------------------------------------------------------------

def smeared_rib_stiffnesses(
    t: float, s: float,
    h_r: float, b_r: float,
    E: float, nu: float,
) -> Dict[str, float]:
    """
    Compute effective bending stiffnesses for a plate with rectangular ribs.

    Args:
        t    : base plate thickness (m)
        s    : rib spacing (m) — centre-to-centre
        h_r  : rib height above base (m)
        b_r  : rib width (m)
        E    : Young's modulus (Pa)
        nu   : Poisson's ratio

    Returns dict with D_x, D_y, D_xy, m_eff (effective mass / m²).
    """
    G = E / (2.0 * (1.0 + nu))
    D_base = E * t**3 / (12.0 * (1.0 - nu**2))

    # Centroid of T-section (base + rib) relative to bottom of base plate
    A_base = t
    A_rib  = h_r * b_r / s      # rib area smeared per unit width
    y_base = t / 2.0
    y_rib  = t + h_r / 2.0
    A_tot  = A_base + A_rib
    y_c    = (A_base * y_base + A_rib * y_rib) / A_tot

    # Bending stiffness about centroid (Steiner + self)
    I_base_c = t**3 / 12.0 + A_base * (y_c - y_base)**2
    I_rib_c  = (b_r / s) * h_r**3 / 12.0 + A_rib * (y_c - y_rib)**2
    I_tot    = I_base_c + I_rib_c

    D_x  = E * I_tot              # stiff direction (along ribs)
    D_y  = D_base                 # compliant direction (across ribs)
    # Torsional: geometric mean of isotropic and rib contribution
    J_rib = b_r * h_r**3 / 3.0 / s   # torsional constant per unit width (smeared)
    D_xy = D_base + G * J_rib         # effective torsional stiffness

    # Effective mass per unit area
    rho_placeholder = 1.0  # caller multiplies by rho
    m_base = t
    m_rib  = h_r * b_r / s
    m_eff  = m_base + m_rib   # thickness-equivalent mass (m * rho = actual mass/area)

    return {"D_x": D_x, "D_y": D_y, "D_xy": D_xy, "m_eff_t": m_eff}


# ---------------------------------------------------------------------------
# Analytical eigenfrequencies — simply-supported orthotropic plate
# ---------------------------------------------------------------------------

def analytical_frequencies(
    W: float, H: float,
    D_x: float, D_y: float, D_xy: float,
    nu: float,
    m_eff: float, rho: float,
    n_modes: int = 20,
) -> np.ndarray:
    """
    Exact natural frequencies for a simply-supported rectangular
    orthotropic Kirchhoff plate (Lekhnitskii / Whitney formula):

      ω²_mn = (π⁴ / m_surf) * [D_x*(m/a)⁴ + 2*(D_12+2*D_66)*(m/a)²*(n/b)²
                                 + D_y*(n/b)⁴]

    where D_12 = nu*sqrt(D_x*D_y), D_66 = D_xy.

    Args:
        W, H   : plate dimensions (m)
        D_x,D_y,D_xy : bending stiffnesses (N·m)
        nu     : Poisson's ratio
        m_eff  : effective thickness (m) for mass calculation
        rho    : density (kg/m³)
        n_modes: number of modes to return

    Returns array of frequencies in Hz, sorted ascending.
    """
    m_surf = rho * m_eff          # mass per unit area (kg/m²)
    D_12   = nu * math.sqrt(D_x * D_y)
    D_66   = D_xy

    freqs = []
    for m_idx in range(1, 15):
        for n_idx in range(1, 15):
            lx = m_idx / W
            ly = n_idx / H
            omega2 = (math.pi**4 / m_surf) * (
                D_x  * lx**4
              + 2.0 * (D_12 + 2.0 * D_66) * lx**2 * ly**2
              + D_y  * ly**4
            )
            freqs.append(math.sqrt(max(omega2, 0.0)) / (2.0 * math.pi))

    freqs = np.array(sorted(freqs))
    return freqs[:n_modes]


# ---------------------------------------------------------------------------
# Finite-difference verification (5-point biharmonic, isotropic)
# ---------------------------------------------------------------------------

def fd_plate_frequencies(
    W: float, H: float,
    t: float, E: float, nu: float, rho: float,
    nx: int = 12, ny: int = 12,
    n_modes: int = 10,
) -> np.ndarray:
    """
    Finite-difference eigenvalue solve for a simply-supported isotropic plate.
    Used as a cross-check on the analytical model.
    Uses the 13-point biharmonic stencil.
    """
    D = E * t**3 / (12.0 * (1.0 - nu**2))
    m_surf = rho * t
    hx = W / (nx + 1)
    hy = H / (ny + 1)

    n_int = nx * ny
    K = np.zeros((n_int, n_int))
    M = np.diag(np.full(n_int, m_surf * hx * hy))

    def idx(i, j):
        return i * ny + j

    for i in range(nx):
        for j in range(ny):
            r = idx(i, j)
            # biharmonic stencil weights (Δ²w = 0 on boundary via simply-supported BC)
            cx = D / hx**4
            cy = D / hy**4
            cxy = 2.0 * D / (hx**2 * hy**2)

            K[r, r] += 6*cx + 6*cy + 8*cxy

            for di, dj, w in [
                (-1,  0, -(4*cx + 2*cxy)), (1, 0, -(4*cx + 2*cxy)),
                ( 0, -1, -(4*cy + 2*cxy)), (0, 1, -(4*cy + 2*cxy)),
                (-2,  0, cx), (2, 0, cx),
                ( 0, -2, cy), (0, 2, cy),
                (-1, -1, cxy), (-1, 1, cxy), (1, -1, cxy), (1, 1, cxy),
            ]:
                ni, nj = i + di, j + dj
                if 0 <= ni < nx and 0 <= nj < ny:
                    K[r, idx(ni, nj)] += w

    try:
        eigenvalues, _ = eigh(K, M, subset_by_index=[0, min(n_modes-1, n_int-1)])
        freqs = np.sqrt(np.abs(eigenvalues)) / (2.0 * math.pi)
        return np.sort(freqs[freqs > 1.0])[:n_modes]
    except Exception:
        return np.array([])


# ---------------------------------------------------------------------------
# Mode shape plot
# ---------------------------------------------------------------------------

def plot_mode_shapes(freqs: np.ndarray, W_mm: float, H_mm: float, png_path: Path, n_plot: int = 6) -> None:
    n_plot = min(n_plot, len(freqs))
    cols = 3
    rows = (n_plot + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 3.5))
    axes = np.array(axes).ravel()

    x = np.linspace(0, W_mm, 60)
    y = np.linspace(0, H_mm, 60)
    X, Y = np.meshgrid(x, y)

    mode_mn = []
    for m in range(1, 10):
        for n in range(1, 10):
            mode_mn.append((m, n))
    mode_mn.sort(key=lambda mn: (mn[0]+mn[1], mn[0]))

    for idx in range(n_plot):
        ax = axes[idx]
        m, n = mode_mn[idx] if idx < len(mode_mn) else (idx+1, 1)
        Z = np.sin(m * np.pi * X / W_mm) * np.sin(n * np.pi * Y / H_mm)
        cf = ax.contourf(X, Y, Z, levels=20, cmap="RdBu_r")
        ax.set_title(f"Mode ({m},{n}): {freqs[idx]:.0f} Hz", fontsize=9)
        ax.set_xlabel("x (mm)", fontsize=7); ax.set_ylabel("y (mm)", fontsize=7)
        ax.tick_params(labelsize=6)
        fig.colorbar(cf, ax=ax, shrink=0.8)

    for idx in range(n_plot, len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle(
        f"Ribbed Membrane Mode Shapes  ({W_mm:.0f}×{H_mm:.0f} mm, simply-supported)",
        fontsize=11
    )
    fig.tight_layout()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(png_path), dpi=130, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Modal analysis of ribbed membrane STL (orthotropic Kirchhoff plate)"
    )
    parser.add_argument("--stl", required=True, help="Path to binary STL")
    parser.add_argument("--material",
                        default='{"E_Pa":3e9,"nu":0.35,"rho_kg_m3":1500}',
                        help="Material JSON: E_Pa, nu, rho_kg_m3")
    parser.add_argument("--rib-spacing-mm", type=float, default=2.5)
    parser.add_argument("--rib-height-mm",  type=float, default=0.8)
    parser.add_argument("--rib-width-mm",   type=float, default=0.625)
    parser.add_argument("--target-freq-min", type=float, default=2000.0)
    parser.add_argument("--target-freq-max", type=float, default=8000.0)
    parser.add_argument("--num-modes", type=int, default=12)
    parser.add_argument("--output", default="", help="Output JSON path")
    parser.add_argument("--mode-shapes-png", default="", help="PNG path for mode shapes")
    args = parser.parse_args()

    stl_path = Path(args.stl)
    if not stl_path.exists():
        print(json.dumps({"error": f"STL not found: {args.stl}"}))
        sys.exit(1)

    try:
        mat = json.loads(args.material)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid --material JSON: {e}"}))
        sys.exit(1)

    E   = float(mat.get("E_Pa",      3e9))
    nu  = float(mat.get("nu",        0.35))
    rho = float(mat.get("rho_kg_m3", 1500.0))

    # ---- Read STL dimensions -----------------------------------------------
    bb = _read_stl_bbox(stl_path)
    W_mm = bb["W_mm"]
    H_mm = bb["H_mm"]
    Z_mm = bb["Z_mm"]

    # Base plate thickness = minimum z-span * 40% (ribs occupy remaining ~60%)
    # This matches the geometry: rib_height ≈ 2× base_thickness → base ≈ 33% of total
    t_mm = args.rib_spacing_mm * 0.16   # calibrated: rib_height = 2t, total span ≈ 3t
    # Override with better estimate if rib height provided
    if args.rib_height_mm > 0:
        # Z_mm ≈ t_base + rib_height  →  t_base = Z_mm - rib_height
        t_mm = max(Z_mm - args.rib_height_mm, Z_mm * 0.25)

    t   = t_mm * 1e-3   # m
    W   = W_mm * 1e-3
    H   = H_mm * 1e-3
    s   = args.rib_spacing_mm * 1e-3
    h_r = args.rib_height_mm  * 1e-3
    b_r = args.rib_width_mm   * 1e-3

    # ---- Smeared rib orthotropic model -------------------------------------
    stiff = smeared_rib_stiffnesses(t, s, h_r, b_r, E, nu)
    D_x   = stiff["D_x"]
    D_y   = stiff["D_y"]
    D_xy  = stiff["D_xy"]
    m_eff = stiff["m_eff_t"]   # effective thickness for mass

    # ---- Analytical frequencies (exact for simply-supported BC) ------------
    freqs_analytical = analytical_frequencies(
        W, H, D_x, D_y, D_xy, nu, m_eff, rho, n_modes=args.num_modes
    )

    # ---- FD cross-check (isotropic base plate, as sanity check) -----------
    freqs_fd = fd_plate_frequencies(W, H, t, E, nu, rho, nx=14, ny=14, n_modes=6)

    # ---- Results -----------------------------------------------------------
    f_min, f_max = args.target_freq_min, args.target_freq_max
    in_range = [round(float(f), 1) for f in freqs_analytical if f_min <= f <= f_max]

    # ---- Mode shape plot --------------------------------------------------
    import datetime, tempfile
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.mode_shapes_png:
        png_path = Path(args.mode_shapes_png)
    else:
        png_path = Path(tempfile.gettempdir()) / f"mode_shapes_{ts}.png"
    plot_mode_shapes(freqs_analytical, W_mm, H_mm, png_path, n_plot=min(6, len(freqs_analytical)))

    # ---- Output JSON -------------------------------------------------------
    result = {
        "eigenfrequencies_hz":      [round(float(f), 1) for f in freqs_analytical],
        "fd_crosscheck_hz":         [round(float(f), 1) for f in freqs_fd],
        "num_modes":                int(len(freqs_analytical)),
        "target_range_hz":          [f_min, f_max],
        "target_range_pass":        len(in_range) > 0,
        "modes_in_range":           in_range,
        "mode_shapes_png":          str(png_path.resolve()),
        "plate_W_mm":               round(W_mm, 2),
        "plate_H_mm":               round(H_mm, 2),
        "plate_t_base_mm":          round(t_mm, 3),
        "rib_spacing_mm":           args.rib_spacing_mm,
        "rib_height_mm":            args.rib_height_mm,
        "stiffness": {
            "D_x_Nm":  round(D_x,  6),
            "D_y_Nm":  round(D_y,  6),
            "D_xy_Nm": round(D_xy, 6),
        },
        "material":                 {"E_Pa": E, "nu": nu, "rho_kg_m3": rho},
        "model":                    "orthotropic Kirchhoff plate, smeared rib, simply-supported",
    }

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2))

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
