#!/usr/bin/env python3
"""
Mechanism-Aware Modal Analysis — Pre-stressed Orthotropic Kirchhoff Plate

Extends the smeared-rib model with:
  1. Membrane pre-tension (T_x, T_y) — modifies effective stiffness
  2. Boundary condition comparison (simply-supported vs. clamped)
  3. Attribution decomposition: how much of f₀ comes from
       (a) rib-induced stiffness anisotropy   — the BIOLOGICAL STRUCTURE mechanism
       (b) membrane pre-tension               — the BIOLOGICAL LOADING mechanism
       (c) generic isotropic plate stiffening — the NULL baseline
  4. Mechanism confirmation test: resonant behaviour must arise from
     the intended biological feature, not just generic plate thickening.

Physics (simply-supported BC, Lekhnitskii/Whitney exact formula):
  ω²_mn = (1/m_surf) * [D_x·(mπ/a)⁴ + 2·(D₁₂+2·D₆₆)·(mπ/a)²·(nπ/b)²
                        + D_y·(nπ/b)⁴ + T_x·(mπ/a)² + T_y·(nπ/b)²]

Pre-stress term adds T·k² to the plate's ω²:
  T_x·(mπ/a)²  — tension along X raises frequency of X-bending modes
  T_y·(nπ/b)²  — tension along Y raises frequency of Y-bending modes

For clamped BCs a finite-difference eigenvalue solve is used, with the
pre-stress term added as a geometric stiffness matrix.

Topology-specific physics:
  cricket_harp:   ribs along X → D_x >> D_y (file-ridge anisotropy)
                  pre-tension T isotropic (wing venation ~20 N/m)
                  mechanism: anisotropy drives frequency separation
  cicada_tymbal:  corrugations along X → D_x enhanced
                  pre-tension T_y from corrugation geometry (~50 N/m)
                  mechanism: T_y + anisotropy together create target band

Attribution columns (fundamental mode 1,1):
  Baseline (iso plate, T=0)  →  f_generic
  +anisotropy (T=0)          →  f_aniso
  +tension (iso plate)       →  f_tension
  Full model                 →  f_full
  Anisotropy contribution  = f_aniso   - f_generic
  Tension contribution     = f_tension - f_generic
  Interaction              = f_full - f_aniso - f_tension + f_generic
  Mechanism confirmed if anisotropy_share > 20% OR tension_share > 15%
    (where share = contribution / (f_full - f_generic))

References:
  Whitney (1987) Structural Analysis of Laminated Anisotropic Plates
  Bennet-Clark (1989) Songs and mechanics of the cricket harp
  Michelsen & Nocke (1974) Influence of frequency on the directivity of
    cricket song
  Pringle (1954) The mechanism of the myogenic rhythm of certain insect
    striated muscles [tymbal]

Usage:
  python3 mechanism_analysis.py \\
    --stl /path/to/membrane.stl \\
    --topology cricket_harp \\
    --material '{"E_Pa":3e9,"nu":0.35,"rho_kg_m3":1500}' \\
    --rib-spacing-mm 2.5 --rib-height-mm 0.8 \\
    --pre-tension-N-m 20.0 \\
    --target-freq-min 2000 --target-freq-max 8000 \\
    --output results.json
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
import matplotlib.gridspec as gridspec


# ---------------------------------------------------------------------------
# STL reader
# ---------------------------------------------------------------------------

def _read_stl_bbox(path: Path) -> Dict[str, float]:
    data = path.read_bytes()
    n_tri = struct.unpack_from("<I", data, 80)[0]
    xs, ys, zs = [], [], []
    offset = 84
    for _ in range(n_tri):
        if offset + 50 > len(data):
            break
        offset += 12
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
# Smeared-rib orthotropic stiffnesses
# ---------------------------------------------------------------------------

def _smeared_stiffnesses(
    t: float, s: float, h_r: float, b_r: float,
    E: float, nu: float, topology: str,
) -> Dict[str, float]:
    """
    Compute D_x, D_y, D_xy for the topology-appropriate rib orientation.

    cricket_harp:   ribs (veins) along X → enhance D_x
                    file ridge adds additional D_x term (2× rib height, 3× rib width)
    cicada_tymbal:  corrugations along X → enhance D_x
                    graded-height ribs: use RMS height for equivalent stiffness
    """
    G = E / (2.0 * (1.0 + nu))
    D_base = E * t**3 / (12.0 * (1.0 - nu**2))
    nu_eff = nu  # Poisson coupling

    def _T_section_D(rib_h, rib_b, spacing):
        """EI per unit width for a T-section (base + rib), centroidal."""
        A_base = t
        A_rib  = rib_h * rib_b / spacing
        y_base = t / 2.0
        y_rib  = t + rib_h / 2.0
        A_tot  = A_base + A_rib
        y_c    = (A_base * y_base + A_rib * y_rib) / A_tot
        I_base = t**3 / 12.0 + A_base * (y_c - y_base)**2
        I_rib  = (rib_b / spacing) * rib_h**3 / 12.0 + A_rib * (y_c - y_rib)**2
        return E * (I_base + I_rib), A_rib

    if topology == "cricket_harp":
        # Primary harp veins along X → D_x from vein smearing
        D_x_vein, A_vein = _T_section_D(h_r, b_r, s)
        # File ridge: single diagonal ridge, approximate contribution as
        # one additional rib per 2*spacing interval with 1.5× height, 3× width
        ridge_h = h_r * 1.5
        ridge_b = b_r * 3.0
        ridge_s = s * 2.0
        D_x_ridge, _ = _T_section_D(ridge_h, ridge_b, ridge_s)
        # Project ridge at ~45° → contributes ~cos⁴(45°)=0.25 to D_x
        D_x = D_x_vein + 0.25 * (D_x_ridge - D_base)
        D_y = D_base            # no ribs along Y
        # Torsional: rib torsion from veins
        J_rib = b_r * h_r**3 / (3.0 * s)
        D_xy  = D_base * (1.0 + nu_eff) + G * J_rib
        m_eff = t + h_r * b_r / s + ridge_h * ridge_b / ridge_s

    elif topology == "cicada_tymbal":
        # Graded-height corrugations along X: RMS rib height for equivalent D
        # Peak height = h_r, graded cosine envelope → RMS = h_r * sqrt(π/8) ≈ 0.627*h_r
        h_rms = h_r * math.sqrt(math.pi / 8.0)
        D_x, A_rib = _T_section_D(h_rms, b_r, s)
        D_y = D_base
        J_rib = b_r * h_rms**3 / (3.0 * s)
        D_xy  = D_base * (1.0 + nu_eff) + G * J_rib
        m_eff = t + h_rms * b_r / s

    else:
        # Generic: uniform ribs along X
        D_x, A_rib = _T_section_D(h_r, b_r, s)
        D_y = D_base
        J_rib = b_r * h_r**3 / (3.0 * s)
        D_xy  = D_base * (1.0 + nu_eff) + G * J_rib
        m_eff = t + h_r * b_r / s

    return {
        "D_base": D_base,
        "D_x":    D_x,
        "D_y":    D_y,
        "D_xy":   D_xy,
        "m_eff":  m_eff,
        "D_iso":  math.sqrt(D_x * D_y),   # geometric mean — isotropic baseline
        "anisotropy_ratio": D_x / D_y,
    }


# ---------------------------------------------------------------------------
# Pre-tension from corrugation geometry (cicada tymbal)
# ---------------------------------------------------------------------------

def _corrugation_pretension(
    h_r: float, s: float, E: float, t: float, nu: float
) -> float:
    """
    Estimate in-plane pre-stress resultant from corrugation geometry.
    Corrugation strain: ε_corr ≈ (h_r/s)² * π²/4  (sinusoidal corrugation)
    T_y = E * t * ε_corr / (1 - ν²)   [N/m, acts perpendicular to corrugations]
    """
    epsilon = (math.pi**2 / 4.0) * (h_r / s)**2
    T = E * t * epsilon / (1.0 - nu**2)
    return T


# ---------------------------------------------------------------------------
# Analytical frequencies — pre-stressed orthotropic SS plate
# ---------------------------------------------------------------------------

def _analytical_freqs(
    W: float, H: float,
    D_x: float, D_y: float, D_xy: float,
    nu: float,
    T_x: float, T_y: float,
    m_surf: float,
    n_modes: int = 20,
) -> np.ndarray:
    """
    Exact natural frequencies for simply-supported pre-stressed orthotropic plate.

      ω²_mn = (1/m_surf) * [D_x·(mπ/a)⁴ + 2·(D₁₂+2·D₆₆)·(mπ/a)²·(nπ/b)²
                            + D_y·(nπ/b)⁴ + T_x·(mπ/a)² + T_y·(nπ/b)²]

    D₁₂ = ν·√(D_x·D_y)  (coupling term, Tsai-Pagano)
    D₆₆ = D_xy           (torsional term)
    """
    D12 = nu * math.sqrt(D_x * D_y)
    D66 = D_xy
    freqs = []
    for m in range(1, 15):
        for n in range(1, 15):
            lx = m * math.pi / W
            ly = n * math.pi / H
            bending  = D_x * lx**4 + 2.0*(D12 + 2.0*D66)*lx**2*ly**2 + D_y*ly**4
            prestress = T_x * lx**2 + T_y * ly**2
            omega2 = (bending + prestress) / m_surf
            freqs.append((math.sqrt(max(omega2, 0.0)) / (2.0*math.pi), m, n))
    freqs.sort(key=lambda x: x[0])
    return np.array([(f, m, n) for f, m, n in freqs[:n_modes]])


# ---------------------------------------------------------------------------
# Finite-difference solver — clamped BC with pre-stress
# ---------------------------------------------------------------------------

def _fd_clamped_freqs(
    W: float, H: float,
    D_x: float, D_y: float, D_xy: float,
    nu: float,
    T_x: float, T_y: float,
    m_surf: float,
    nx: int = 14, ny: int = 14,
    n_modes: int = 8,
) -> np.ndarray:
    """
    Finite-difference eigenvalue solve for clamped orthotropic plate + pre-stress.
    Uses 13-point anisotropic biharmonic stencil + 5-point Laplacian for T term.
    Clamped BC: w=0, ∂w/∂n=0 on boundary (ghost points enforce ∂w/∂n=0).
    """
    hx = W / (nx + 1)
    hy = H / (ny + 1)
    N = nx * ny

    def ij(i, j): return i * ny + j

    K = np.zeros((N, N))
    M_diag = np.full(N, m_surf * hx * hy)

    for i in range(nx):
        for j in range(ny):
            r = ij(i, j)
            # Biharmonic (orthotropic): D_x·∂⁴/∂x⁴ + 2(D₁₂+2D₆₆)·∂⁴/∂x²∂y² + D_y·∂⁴/∂y⁴
            D12 = nu * math.sqrt(D_x * D_y)
            cx  = D_x / hx**4
            cy  = D_y / hy**4
            cxy = 2.0 * (D12 + 2.0*D_xy) / (hx**2 * hy**2)
            # Pre-stress: T_x·∂²/∂x² + T_y·∂²/∂y²
            tx  = T_x / hx**2
            ty  = T_y / hy**2

            # Diagonal (central)
            K[r, r] += 6.0*cx + 6.0*cy + 8.0*cxy - 2.0*tx - 2.0*ty

            stencil = [
                # (di, dj, K_weight, T_weight)
                (-1,  0, -(4.0*cx + 2.0*cxy),  tx),
                ( 1,  0, -(4.0*cx + 2.0*cxy),  tx),
                ( 0, -1, -(4.0*cy + 2.0*cxy),  ty),
                ( 0,  1, -(4.0*cy + 2.0*cxy),  ty),
                (-2,  0, cx,  0.0),
                ( 2,  0, cx,  0.0),
                ( 0, -2, cy,  0.0),
                ( 0,  2, cy,  0.0),
                (-1, -1, cxy, 0.0),
                (-1,  1, cxy, 0.0),
                ( 1, -1, cxy, 0.0),
                ( 1,  1, cxy, 0.0),
            ]
            for di, dj, wK, wT in stencil:
                ni, nj = i + di, j + dj
                if 0 <= ni < nx and 0 <= nj < ny:
                    K[r, ij(ni, nj)] += wK + wT
                # Clamped BC ghost points: w_ghost = -w_interior (Δ²w=0 → ∂w/∂n=0)
                # When boundary is at depth 1, ghost is outside → contributes -wK * w_interior
                elif abs(di) == 1 or abs(dj) == 1:
                    K[r, r] += -(wK + wT)   # anti-symmetric ghost

    M = np.diag(M_diag)
    try:
        n_req = min(n_modes, N - 2)
        vals, _ = eigh(K, M, subset_by_index=[0, n_req - 1])
        freqs = np.sqrt(np.maximum(vals, 0.0)) / (2.0 * math.pi)
        return np.sort(freqs[freqs > 10.0])[:n_modes]
    except Exception:
        return np.array([])


# ---------------------------------------------------------------------------
# Attribution decomposition
# ---------------------------------------------------------------------------

def _attribution(
    W: float, H: float,
    stiff: Dict[str, float],
    T_x: float, T_y: float,
    nu: float,
    m_surf: float,
) -> Dict[str, Any]:
    """
    Decompose f₀ (fundamental, m=n=1) into:
      f_generic  : isotropic plate, T=0
      f_aniso    : anisotropic D, T=0
      f_tension  : isotropic D, T>0
      f_full     : anisotropic D, T>0

    Returns attribution dict with contributions and mechanism confirmation.
    """
    D_x   = stiff["D_x"]
    D_y   = stiff["D_y"]
    D_xy  = stiff["D_xy"]
    D_iso = stiff["D_iso"]

    def f11(Dx, Dy, Dxy, tx, ty):
        D12 = nu * math.sqrt(Dx * Dy)
        lx  = math.pi / W
        ly  = math.pi / H
        omega2 = (Dx*lx**4 + 2.0*(D12+2.0*Dxy)*lx**2*ly**2 + Dy*ly**4
                  + tx*lx**2 + ty*ly**2) / m_surf
        return math.sqrt(max(omega2, 0.0)) / (2.0 * math.pi)

    # D_xy_iso: torsional for fully isotropic case
    # Use: D_xy_iso = D_iso (roughly) preserving structure
    D_xy_iso = D_iso * (D_xy / math.sqrt(D_x * D_y)) if D_x * D_y > 0 else D_xy

    f_generic = f11(D_iso, D_iso, D_xy_iso, 0.0, 0.0)
    f_aniso   = f11(D_x,   D_y,   D_xy,     0.0, 0.0)
    f_tension = f11(D_iso, D_iso, D_xy_iso, T_x, T_y)
    f_full    = f11(D_x,   D_y,   D_xy,     T_x, T_y)

    delta_total   = f_full - f_generic
    delta_aniso   = f_aniso   - f_generic
    delta_tension = f_tension - f_generic
    delta_interact = f_full - f_aniso - f_tension + f_generic

    def pct(d): return round(100.0 * d / delta_total, 1) if abs(delta_total) > 1e-6 else 0.0

    aniso_share   = pct(delta_aniso)
    tension_share = pct(delta_tension)
    interact_share = pct(delta_interact)

    mechanism_confirmed = aniso_share > 20.0 or tension_share > 15.0

    return {
        "f_generic_hz":        round(f_generic, 1),
        "f_aniso_only_hz":     round(f_aniso, 1),
        "f_tension_only_hz":   round(f_tension, 1),
        "f_full_hz":           round(f_full, 1),
        "delta_total_hz":      round(delta_total, 1),
        "anisotropy_contribution_hz":  round(delta_aniso, 1),
        "tension_contribution_hz":     round(delta_tension, 1),
        "interaction_hz":              round(delta_interact, 1),
        "anisotropy_share_pct":  aniso_share,
        "tension_share_pct":     tension_share,
        "interaction_share_pct": interact_share,
        "anisotropy_ratio_Dx_Dy": round(stiff["anisotropy_ratio"], 2),
        "T_x_N_m":  round(T_x, 2),
        "T_y_N_m":  round(T_y, 2),
        "mechanism_confirmed":   mechanism_confirmed,
        "mechanism_interpretation": _interpret(aniso_share, tension_share, stiff["anisotropy_ratio"]),
    }


def _interpret(aniso_pct: float, tension_pct: float, ratio: float) -> str:
    lines = []
    if ratio > 3.0:
        lines.append(
            f"Rib-induced anisotropy (D_x/D_y={ratio:.1f}×) contributes {aniso_pct:.0f}% of "
            f"frequency shift above generic baseline — structural mechanism active."
        )
    else:
        lines.append(
            f"Low anisotropy ratio ({ratio:.1f}×); rib stiffening close to isotropic plate baseline."
        )
    if tension_pct > 10.0:
        lines.append(
            f"Membrane pre-tension contributes {tension_pct:.0f}% — biological pre-loading active."
        )
    if aniso_pct <= 20.0 and tension_pct <= 15.0:
        lines.append(
            "Neither anisotropy nor tension exceeds threshold — resonance dominated by "
            "generic plate stiffening, not biological mechanism."
        )
    return " ".join(lines)


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def _plot_mechanism(
    attr: Dict[str, Any],
    freqs_ss_full: np.ndarray,
    freqs_ss_generic: np.ndarray,
    freqs_clamped_full: np.ndarray,
    f_min: float, f_max: float,
    topology: str,
    out_png: Path,
) -> None:
    fig = plt.figure(figsize=(14, 9))
    gs  = gridspec.GridSpec(2, 3, figure=fig, wspace=0.4, hspace=0.45)

    # ── Panel 1: mode spectrum comparison (SS full vs generic) ─────────────
    ax1 = fig.add_subplot(gs[0, :2])
    modes_full    = freqs_ss_full[:, 0]
    modes_generic = freqs_ss_generic[:, 0]
    n = min(len(modes_full), len(modes_generic), 12)
    idx = np.arange(n)
    ax1.bar(idx - 0.2, modes_full[:n] / 1e3,    width=0.35, label="Full model (aniso + T)", color="#2176ae")
    ax1.bar(idx + 0.2, modes_generic[:n] / 1e3, width=0.35, label="Generic (iso, T=0)",    color="#adb5bd")
    ax1.axhline(f_min/1e3, color="green", lw=1.2, ls="--", label=f"{f_min/1e3:.1f} kHz target min")
    ax1.axhline(f_max/1e3, color="red",   lw=1.2, ls="--", label=f"{f_max/1e3:.1f} kHz target max")
    ax1.set_xlabel("Mode index"); ax1.set_ylabel("Frequency (kHz)")
    ax1.set_title(f"Mode Spectrum: Full vs. Generic — {topology.replace('_',' ').title()}", fontsize=10)
    ax1.legend(fontsize=7); ax1.grid(axis="y", alpha=0.3)

    # ── Panel 2: SS vs clamped BC comparison ───────────────────────────────
    ax2 = fig.add_subplot(gs[0, 2])
    nc = min(len(modes_full), len(freqs_clamped_full), 8)
    ax2.plot(np.arange(nc), modes_full[:nc] / 1e3,          "o-", label="SS BC",     color="#2176ae")
    ax2.plot(np.arange(nc), freqs_clamped_full[:nc] / 1e3,  "s--", label="Clamped BC", color="#d62246")
    ax2.set_xlabel("Mode index"); ax2.set_ylabel("Frequency (kHz)")
    ax2.set_title("BC Sensitivity\n(SS vs Clamped)", fontsize=10)
    ax2.legend(fontsize=7); ax2.grid(alpha=0.3)

    # ── Panel 3: attribution bar (f₀ decomposition) ────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    labels = ["Generic\n(iso,T=0)", "+Anisotropy\n(T=0)", "+Tension\n(iso)", "Full\nmodel"]
    values = [
        attr["f_generic_hz"],
        attr["f_aniso_only_hz"],
        attr["f_tension_only_hz"],
        attr["f_full_hz"],
    ]
    colors = ["#adb5bd", "#2176ae", "#f4a261", "#2a9d8f"]
    bars = ax3.bar(labels, np.array(values)/1e3, color=colors, edgecolor="k", linewidth=0.5)
    ax3.axhline(f_min/1e3, color="green", lw=1.0, ls="--")
    ax3.axhline(f_max/1e3, color="red",   lw=1.0, ls="--")
    for bar, v in zip(bars, values):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                 f"{v:.0f} Hz", ha="center", va="bottom", fontsize=7)
    ax3.set_ylabel("f₀ (kHz)"); ax3.set_title("Mechanism Attribution\n(Fundamental Mode)", fontsize=10)
    ax3.grid(axis="y", alpha=0.3)

    # ── Panel 4: contribution breakdown (Δ from generic) ───────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    contrib_labels = ["Anisotropy\n(rib structure)", "Tension\n(pre-loading)", "Interaction"]
    contrib_vals   = [
        attr["anisotropy_share_pct"],
        attr["tension_share_pct"],
        attr["interaction_share_pct"],
    ]
    contrib_colors = ["#2176ae", "#f4a261", "#e9c46a"]
    bars4 = ax4.bar(contrib_labels, contrib_vals, color=contrib_colors, edgecolor="k", linewidth=0.5)
    ax4.axhline(20, color="#2176ae", ls="--", lw=1.0, label="Aniso threshold 20%")
    ax4.axhline(15, color="#f4a261", ls=":",  lw=1.0, label="Tension threshold 15%")
    for bar, v in zip(bars4, contrib_vals):
        ax4.text(bar.get_x() + bar.get_width()/2, max(bar.get_height(), 0) + 0.5,
                 f"{v:.1f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax4.set_ylabel("Share of Δf₀ (%)"); ax4.set_title("Mechanism Share\n(% above generic)", fontsize=10)
    ax4.legend(fontsize=6); ax4.grid(axis="y", alpha=0.3)

    # ── Panel 5: mode shapes (SS full) ─────────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 2])
    top_modes = freqs_ss_full[:6]
    mode_labels = [f"({int(r[1])},{int(r[2])})\n{r[0]:.0f}Hz" for r in top_modes]
    ypos = np.arange(len(mode_labels))
    ax5.barh(ypos, [r[0]/1e3 for r in top_modes], color="#2176ae", alpha=0.7)
    ax5.axvline(f_min/1e3, color="green", ls="--", lw=1.0)
    ax5.axvline(f_max/1e3, color="red",   ls="--", lw=1.0)
    ax5.set_yticks(ypos); ax5.set_yticklabels(mode_labels, fontsize=7)
    ax5.set_xlabel("Frequency (kHz)"); ax5.set_title("First 6 Modes\n(m,n) labels", fontsize=10)
    ax5.grid(axis="x", alpha=0.3)

    # ── Confirmation banner ─────────────────────────────────────────────────
    confirmed = attr["mechanism_confirmed"]
    banner_color = "#2a9d8f" if confirmed else "#e76f51"
    banner_text  = (
        f"✓ MECHANISM CONFIRMED — {attr['anisotropy_share_pct']:.0f}% anisotropy, "
        f"{attr['tension_share_pct']:.0f}% tension"
        if confirmed else
        f"✗ MECHANISM NOT CONFIRMED — generic plate stiffening dominates "
        f"({attr['anisotropy_share_pct']:.0f}% aniso, {attr['tension_share_pct']:.0f}% tension)"
    )
    fig.text(0.5, 0.01, banner_text, ha="center", va="bottom",
             fontsize=11, fontweight="bold", color="white",
             bbox=dict(boxstyle="round,pad=0.3", facecolor=banner_color, alpha=0.9))

    fig.suptitle(
        f"Mechanism-Aware Modal Analysis — {topology.replace('_',' ').title()}\n"
        f"D_x/D_y = {attr['anisotropy_ratio_Dx_Dy']:.1f}×  |  "
        f"T_x={attr['T_x_N_m']:.1f} N/m  T_y={attr['T_y_N_m']:.1f} N/m",
        fontsize=12
    )
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_png), dpi=140, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mechanism-aware modal analysis: anisotropy + pre-stress attribution"
    )
    parser.add_argument("--stl", required=True)
    parser.add_argument("--topology", default="generic",
                        choices=["cricket_harp", "cicada_tymbal", "generic"])
    parser.add_argument("--material",
                        default='{"E_Pa":3e9,"nu":0.35,"rho_kg_m3":1500}')
    parser.add_argument("--rib-spacing-mm", type=float, default=2.5)
    parser.add_argument("--rib-height-mm",  type=float, default=0.8)
    parser.add_argument("--rib-width-mm",   type=float, default=0.0,
                        help="0 = derive as rib_spacing * 0.25")
    parser.add_argument("--pre-tension-N-m", type=float, default=-1.0,
                        help="-1 = auto-compute from topology and geometry")
    parser.add_argument("--target-freq-min", type=float, default=2000.0)
    parser.add_argument("--target-freq-max", type=float, default=8000.0)
    parser.add_argument("--output", default="")
    parser.add_argument("--plot-png", default="")
    args = parser.parse_args()

    stl_path = Path(args.stl)
    if not stl_path.exists():
        print(json.dumps({"error": f"STL not found: {args.stl}"}))
        sys.exit(1)

    mat = json.loads(args.material)
    E   = float(mat.get("E_Pa",      3e9))
    nu  = float(mat.get("nu",        0.35))
    rho = float(mat.get("rho_kg_m3", 1500.0))

    bb   = _read_stl_bbox(stl_path)
    W    = bb["W_mm"] * 1e-3
    H    = bb["H_mm"] * 1e-3
    Z_mm = bb["Z_mm"]

    s    = args.rib_spacing_mm * 1e-3
    h_r  = args.rib_height_mm  * 1e-3
    b_r  = (args.rib_width_mm if args.rib_width_mm > 0 else args.rib_spacing_mm * 0.25) * 1e-3
    t    = max(Z_mm * 1e-3 - h_r, Z_mm * 1e-3 * 0.25)   # base plate thickness

    stiff  = _smeared_stiffnesses(t, s, h_r, b_r, E, nu, args.topology)
    m_surf = rho * stiff["m_eff"]

    # Pre-tension
    if args.pre_tension_N_m >= 0:
        T_given = args.pre_tension_N_m
        T_x = T_given
        T_y = T_given
    else:
        if args.topology == "cricket_harp":
            T_x = 20.0;   T_y = 20.0   # wing venation isotropic ~20 N/m
        elif args.topology == "cicada_tymbal":
            T_y = _corrugation_pretension(h_r, s, E, t, nu)
            T_x = 0.0     # corrugation pre-stress acts perpendicular to corrugations (Y)
        else:
            T_x = 0.0;    T_y = 0.0

    # ── Full model (anisotropic + pre-stress, SS) ───────────────────────────
    freqs_ss_full = _analytical_freqs(
        W, H, stiff["D_x"], stiff["D_y"], stiff["D_xy"], nu,
        T_x, T_y, m_surf, n_modes=20
    )

    # ── Generic baseline (isotropic D, T=0, SS) ─────────────────────────────
    D_iso    = stiff["D_iso"]
    D_xy_iso = D_iso * (stiff["D_xy"] / math.sqrt(stiff["D_x"] * stiff["D_y"]))
    freqs_ss_generic = _analytical_freqs(
        W, H, D_iso, D_iso, D_xy_iso, nu,
        0.0, 0.0, m_surf, n_modes=20
    )

    # ── Clamped BC (full model, FD) ─────────────────────────────────────────
    freqs_clamped = _fd_clamped_freqs(
        W, H, stiff["D_x"], stiff["D_y"], stiff["D_xy"], nu,
        T_x, T_y, m_surf, nx=12, ny=12, n_modes=8
    )

    # ── Attribution decomposition ────────────────────────────────────────────
    attr = _attribution(W, H, stiff, T_x, T_y, nu, m_surf)

    # ── Target range metrics ─────────────────────────────────────────────────
    f_min, f_max = args.target_freq_min, args.target_freq_max
    full_in_range    = [round(float(r[0]),1) for r in freqs_ss_full    if f_min <= r[0] <= f_max]
    generic_in_range = [round(float(r[0]),1) for r in freqs_ss_generic if f_min <= r[0] <= f_max]

    # ── Plot ─────────────────────────────────────────────────────────────────
    import datetime, tempfile
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_path = Path(args.plot_png) if args.plot_png else \
        stl_path.parent / f"mechanism_{ts}.png"
    _plot_mechanism(
        attr, freqs_ss_full, freqs_ss_generic, freqs_clamped,
        f_min, f_max, args.topology, plot_path
    )

    # ── JSON output ──────────────────────────────────────────────────────────
    result = {
        "topology":                  args.topology,
        "plate_W_mm":                round(bb["W_mm"], 2),
        "plate_H_mm":                round(bb["H_mm"], 2),
        "stiffness": {
            "D_x_Nm":    round(stiff["D_x"],  8),
            "D_y_Nm":    round(stiff["D_y"],  8),
            "D_xy_Nm":   round(stiff["D_xy"], 8),
            "D_iso_Nm":  round(D_iso,         8),
            "anisotropy_ratio": round(stiff["anisotropy_ratio"], 2),
        },
        "pre_tension": {"T_x_N_m": round(T_x, 2), "T_y_N_m": round(T_y, 2)},
        "attribution":               attr,
        "freqs_full_SS_hz":          [round(float(r[0]),1) for r in freqs_ss_full],
        "freqs_generic_SS_hz":       [round(float(r[0]),1) for r in freqs_ss_generic],
        "freqs_full_clamped_hz":     [round(float(f), 1) for f in freqs_clamped],
        "modes_in_range_full":       full_in_range,
        "modes_in_range_generic":    generic_in_range,
        "target_range_pass":         len(full_in_range) > 0,
        "mechanism_confirmed":       attr["mechanism_confirmed"],
        "plot_png":                  str(plot_path.resolve()),
        "model": "pre-stressed orthotropic Kirchhoff plate, smeared rib, SS+clamped",
    }

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2))

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
