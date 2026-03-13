#!/usr/bin/env python3
"""
L-System executor and renderer.

Takes an axiom + rewrite rules, iterates the grammar, and renders
the result using turtle graphics into SVG, PNG, and optionally STL.

Usage:
  python3 lsystem_render.py --axiom "A" --rules '{"A":"A[+B]A[-B]A","B":"BB"}' --angle 25 --steps 4 --output out/
  python3 lsystem_render.py --grammar grammar.json --steps 4 --output out/
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import LineCollection
import numpy as np


# ============================================================================
# Grammar engine
# ============================================================================


def iterate(axiom: str, rules: Dict[str, str], steps: int) -> List[str]:
    """Apply rewrite rules for N steps, returning the string at each step."""
    derivations = [axiom]
    current = axiom
    for _ in range(steps):
        next_str = []
        for ch in current:
            next_str.append(rules.get(ch, ch))
        current = "".join(next_str)
        derivations.append(current)
    return derivations


# ============================================================================
# Turtle interpreter
# ============================================================================


def interpret(
    string: str,
    angle_deg: float = 25.0,
    step_length: float = 10.0,
    length_scale: float = 1.0,
    initial_width: float = 2.0,
    width_decay: float = 0.8,
) -> List[Tuple[float, float, float, float, float]]:
    """Interpret an L-system string as turtle graphics.

    Returns list of (x0, y0, x1, y1, width) line segments.
    """
    angle_rad = math.radians(angle_deg)
    x, y, heading = 0.0, 0.0, math.pi / 2  # start facing up
    width = initial_width
    step = step_length
    stack = []
    segments = []

    draw_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    for ch in string:
        if ch in draw_chars:
            nx = x + step * math.cos(heading)
            ny = y + step * math.sin(heading)
            segments.append((x, y, nx, ny, width))
            x, y = nx, ny
        elif ch == "f":
            x += step * math.cos(heading)
            y += step * math.sin(heading)
        elif ch == "+":
            heading += angle_rad
        elif ch == "-":
            heading -= angle_rad
        elif ch == "[":
            stack.append((x, y, heading, width, step))
        elif ch == "]":
            if stack:
                x, y, heading, width, step = stack.pop()
        elif ch == "!":
            width *= width_decay
        elif ch == ">":
            step *= length_scale

    return segments


# ============================================================================
# Rendering
# ============================================================================


def render_segments(
    segments: List[Tuple[float, float, float, float, float]],
    title: str = "",
    figsize: Tuple[int, int] = (10, 10),
    bg_color: str = "#1a1a2e",
    line_color: str = "#e94560",
    dpi: int = 300,
) -> plt.Figure:
    """Render line segments to a matplotlib figure."""
    fig, ax = plt.subplots(1, 1, figsize=figsize, facecolor=bg_color)
    ax.set_facecolor(bg_color)

    if not segments:
        ax.text(0.5, 0.5, "No segments to render",
                transform=ax.transAxes, ha="center", va="center",
                color="white", fontsize=14)
        return fig

    # Build line collection for efficient rendering
    lines = [[(s[0], s[1]), (s[2], s[3])] for s in segments]
    widths = [s[4] for s in segments]

    # Color gradient based on drawing order
    n = len(segments)
    colors = plt.cm.plasma(np.linspace(0.2, 0.9, n))

    lc = LineCollection(lines, linewidths=widths, colors=colors)
    ax.add_collection(lc)

    # Set bounds
    all_x = [s[0] for s in segments] + [s[2] for s in segments]
    all_y = [s[1] for s in segments] + [s[3] for s in segments]
    margin_x = (max(all_x) - min(all_x)) * 0.1 + 1
    margin_y = (max(all_y) - min(all_y)) * 0.1 + 1
    ax.set_xlim(min(all_x) - margin_x, max(all_x) + margin_x)
    ax.set_ylim(min(all_y) - margin_y, max(all_y) + margin_y)
    ax.set_aspect("equal")
    ax.axis("off")

    if title:
        ax.set_title(title, color="white", fontsize=14, pad=20)

    fig.tight_layout()
    return fig


def render_steps_grid(
    derivations: List[str],
    angle_deg: float,
    step_length: float,
    length_scale: float,
    title: str = "",
    max_show: int = 6,
) -> plt.Figure:
    """Render a grid showing each derivation step side by side."""
    n = min(len(derivations), max_show)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4), facecolor="#1a1a2e")
    if n == 1:
        axes = [axes]

    for i, (ax, deriv) in enumerate(zip(axes, derivations[:n])):
        ax.set_facecolor("#1a1a2e")
        segments = interpret(deriv, angle_deg, step_length, length_scale)

        if segments:
            lines = [[(s[0], s[1]), (s[2], s[3])] for s in segments]
            widths = [max(s[4] * 0.5, 0.3) for s in segments]
            colors = plt.cm.plasma(np.linspace(0.2, 0.9, len(segments)))
            lc = LineCollection(lines, linewidths=widths, colors=colors)
            ax.add_collection(lc)

            all_x = [s[0] for s in segments] + [s[2] for s in segments]
            all_y = [s[1] for s in segments] + [s[3] for s in segments]
            mx = (max(all_x) - min(all_x)) * 0.15 + 1
            my = (max(all_y) - min(all_y)) * 0.15 + 1
            ax.set_xlim(min(all_x) - mx, max(all_x) + mx)
            ax.set_ylim(min(all_y) - my, max(all_y) + my)
        else:
            ax.text(0.5, 0.5, deriv[:20], transform=ax.transAxes,
                    ha="center", va="center", color="white", fontsize=8,
                    fontfamily="monospace")

        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"Step {i}", color="white", fontsize=10)

    if title:
        fig.suptitle(title, color="white", fontsize=13, y=1.02)

    fig.tight_layout()
    return fig


# ============================================================================
# STL export (simple 2D extrusion)
# ============================================================================


def segments_to_stl(
    segments: List[Tuple[float, float, float, float, float]],
    extrude_height: float = 5.0,
    output_path: Path = None,
) -> str:
    """Extrude 2D line segments into a simple 3D STL mesh.

    Each segment becomes a rectangular prism (4 triangles for the sides,
    2 for top, 2 for bottom = 8 triangles per segment).
    """
    triangles = []

    for x0, y0, x1, y1, w in segments:
        # Direction and perpendicular
        dx, dy = x1 - x0, y1 - y0
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-10:
            continue
        nx, ny = -dy / length * w * 0.5, dx / length * w * 0.5

        # 8 corners of the rectangular prism
        b0 = (x0 + nx, y0 + ny, 0)
        b1 = (x0 - nx, y0 - ny, 0)
        b2 = (x1 - nx, y1 - ny, 0)
        b3 = (x1 + nx, y1 + ny, 0)
        t0 = (x0 + nx, y0 + ny, extrude_height)
        t1 = (x0 - nx, y0 - ny, extrude_height)
        t2 = (x1 - nx, y1 - ny, extrude_height)
        t3 = (x1 + nx, y1 + ny, extrude_height)

        # Bottom face
        triangles.append((b0, b1, b2))
        triangles.append((b0, b2, b3))
        # Top face
        triangles.append((t0, t3, t2))
        triangles.append((t0, t2, t1))
        # Front
        triangles.append((b0, b3, t3))
        triangles.append((b0, t3, t0))
        # Back
        triangles.append((b1, t1, t2))
        triangles.append((b1, t2, b2))
        # Left
        triangles.append((b0, t0, t1))
        triangles.append((b0, t1, b1))
        # Right
        triangles.append((b3, b2, t2))
        triangles.append((b3, t2, t3))

    # Write ASCII STL
    lines = ["solid lsystem"]
    for v0, v1, v2 in triangles:
        # Compute normal
        u = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        v = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        n = (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )
        mag = math.sqrt(n[0]**2 + n[1]**2 + n[2]**2)
        if mag > 0:
            n = (n[0] / mag, n[1] / mag, n[2] / mag)
        else:
            n = (0, 0, 1)

        lines.append(f"  facet normal {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}")
        lines.append("    outer loop")
        lines.append(f"      vertex {v0[0]:.6f} {v0[1]:.6f} {v0[2]:.6f}")
        lines.append(f"      vertex {v1[0]:.6f} {v1[1]:.6f} {v1[2]:.6f}")
        lines.append(f"      vertex {v2[0]:.6f} {v2[1]:.6f} {v2[2]:.6f}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid lsystem")

    stl_text = "\n".join(lines)

    if output_path:
        output_path.write_text(stl_text)
        print(f"  ✓ STL: {output_path} ({len(triangles)} triangles)")

    return stl_text


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="L-System executor and renderer")
    parser.add_argument("--grammar", type=str, help="Path to grammar JSON file")
    parser.add_argument("--axiom", type=str, help="Axiom string (inline mode)")
    parser.add_argument("--rules", type=str, help="Rules as JSON string (inline mode)")
    parser.add_argument("--angle", type=float, default=25.0, help="Turn angle in degrees")
    parser.add_argument("--step-length", type=float, default=10.0, help="Step length")
    parser.add_argument("--length-scale", type=float, default=1.0, help="Length scale per '>'")
    parser.add_argument("--steps", type=int, default=4, help="Number of derivation steps")
    parser.add_argument("--title", type=str, default="", help="Title for the render")
    parser.add_argument("--stl", action="store_true", help="Export 3D STL mesh")
    parser.add_argument("--stl-height", type=float, default=5.0, help="STL extrusion height")
    parser.add_argument("--output", type=str, required=True, help="Output directory")

    args = parser.parse_args()

    # Load grammar
    if args.grammar:
        grammar = json.loads(Path(args.grammar).read_text())
        axiom = grammar["axiom"]
        rules = grammar["rules"]
        angle = grammar.get("angle", args.angle)
        step_length = grammar.get("step_length", args.step_length)
        length_scale = grammar.get("length_scale", args.length_scale)
        title = grammar.get("title", args.title)
    elif args.axiom and args.rules:
        axiom = args.axiom
        rules = json.loads(args.rules)
        angle = args.angle
        step_length = args.step_length
        length_scale = args.length_scale
        title = args.title
    else:
        print("Error: provide --grammar or --axiom + --rules")
        sys.exit(1)

    steps = args.steps
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    # Save grammar for reproducibility
    grammar_data = {
        "axiom": axiom,
        "rules": rules,
        "angle": angle,
        "step_length": step_length,
        "length_scale": length_scale,
        "steps": steps,
        "title": title,
    }
    (out / "grammar.json").write_text(json.dumps(grammar_data, indent=2))

    # Derive
    print(f"\n{'=' * 60}")
    print(f"  L-SYSTEM EXECUTOR")
    print(f"{'=' * 60}")
    print(f"\n  Axiom: {axiom}")
    print(f"  Rules: {json.dumps(rules)}")
    print(f"  Angle: {angle}°")
    print(f"  Steps: {steps}")
    print()

    derivations = iterate(axiom, rules, steps)

    # Write derivation log
    deriv_lines = []
    for i, d in enumerate(derivations):
        truncated = d if len(d) <= 200 else d[:200] + f"... ({len(d)} chars)"
        deriv_lines.append(f"Step {i}: {truncated}")
        print(f"  Step {i}: {truncated}")

    (out / "derivation.txt").write_text("\n".join(deriv_lines))
    print(f"\n  ✓ Derivation: {out / 'derivation.txt'}")

    # Render final step
    final = derivations[-1]
    segments = interpret(final, angle, step_length, length_scale)
    print(f"  Segments: {len(segments)}")

    if segments:
        fig = render_segments(segments, title=title or "L-System Render")
        fig.savefig(out / "render.png", dpi=300, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        fig.savefig(out / "render.svg", format="svg", bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"  ✓ PNG: {out / 'render.png'}")
        print(f"  ✓ SVG: {out / 'render.svg'}")

        # Render step-by-step grid
        fig_steps = render_steps_grid(
            derivations, angle, step_length, length_scale,
            title=title or "Derivation Steps"
        )
        fig_steps.savefig(out / "render_steps.png", dpi=200, bbox_inches="tight",
                          facecolor=fig_steps.get_facecolor())
        plt.close(fig_steps)
        print(f"  ✓ Steps: {out / 'render_steps.png'}")

        # STL export
        if args.stl:
            segments_to_stl(segments, args.stl_height, out / "render.stl")
    else:
        print("  ⚠  No drawable segments produced")

    print(f"\n  All outputs in: {out}")
    print()


if __name__ == "__main__":
    main()
