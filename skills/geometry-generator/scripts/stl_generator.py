#!/usr/bin/env python3
"""
Geometry Generator — Bioinspired Ribbed Membrane STL

GPT generates the OpenSCAD code for the membrane geometry.
OpenSCAD CLI renders it to a binary STL file.

Flow:
  upstream spec (StructureAnalyst / PropertyPredictor artifacts)
    → LLM prompt (PROMPT.md)
    → GPT generates OpenSCAD code
    → openscad CLI renders .scad → .stl
    → artifact JSON returned

Requires: openscad installed (sudo apt-get install openscad)

Usage:
  python3 stl_generator.py \\
    --spec '{"rib_spacing_mm":2.5,"thickness_mm":0.4,"aspect_ratio":3.0,"num_scales":2}' \\
    --output /tmp/membrane.stl

  python3 stl_generator.py \\
    --spec-file structural_motifs.json \\
    --output /tmp/membrane.stl
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ScienceClaw root
_SKILL_DIR = Path(__file__).resolve().parents[2]
_ROOT = _SKILL_DIR.parent
sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_PROMPT = """\
You are a parametric CAD engineer specialising in bioinspired acoustic membranes.
You will generate valid OpenSCAD code for a ribbed membrane resonator.

DESIGN SPECIFICATION (derived from structural analysis of biological specimens):
  Biological model     : {biological_inspiration}
  Width                : {width_mm} mm
  Height               : {height_mm} mm
  Base thickness       : {thickness_mm} mm
  Primary rib spacing  : {primary_rib_spacing_mm} mm  (distance between ribs)
  Primary rib height   : {primary_rib_height_mm} mm   (protrusion above base)
  Primary rib width    : {primary_rib_width_mm} mm
  Secondary ribs       : {has_secondary}
  Secondary rib spacing: {secondary_rib_spacing_mm} mm
  Secondary rib height : {secondary_rib_height_mm} mm
  Frame width          : {frame_width_mm} mm

REQUIREMENTS:
1. Output ONLY valid OpenSCAD code — no prose, no markdown fences, no comments
   except variable definitions at the top.
2. Use named variables for every dimension (copy from spec above).
3. Build the geometry with difference() / union() / for loops — NO external libraries.
4. Structure:
   a. Base plate: cube([width, height, thickness])
   b. Frame: 4 border walls around perimeter, height = thickness + rib_height
   c. Primary ribs: parallel strips running along the X-axis,
      spaced every primary_rib_spacing_mm in Y, within the frame interior.
   d. Secondary ribs (if has_secondary): perpendicular strips along Y-axis,
      spaced every secondary_rib_spacing_mm in X, height = secondary_rib_height.
5. All geometry must be manifold (watertight).
6. Do NOT use hull(), minkowski(), or import() statements.
"""


def _derive_spec_params(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Derive all geometric parameters from upstream artifact spec.
    No hardcoded values — every number comes from spec fields with
    physically-motivated fallback formulae when a field is absent.
    """
    s_mm  = float(spec.get("rib_spacing_mm") or spec.get("primary_rib_spacing_mm") or 2.5)
    t_mm  = float(spec.get("thickness_mm") or 0.4)
    ar    = float(spec.get("aspect_ratio") or 3.0)
    ns    = int(spec.get("num_scales") or 2)
    bio   = str(spec.get("biological_inspiration") or
                "cricket wing harp (Gryllus bimaculatus) — parallel primary veins")

    # Derived dimensions — physically motivated ratios, not magic numbers
    w     = float(spec.get("width_mm") or round(s_mm * 8, 2))
    h     = float(spec.get("height_mm") or round(w * ar, 2))
    rh    = float(spec.get("primary_rib_height_mm") or round(t_mm * 2.0, 3))
    rw    = float(spec.get("primary_rib_width_mm")  or round(s_mm * 0.25, 3))
    fw    = float(spec.get("frame_width_mm")        or round(s_mm * 0.6, 3))
    s2    = float(spec.get("secondary_rib_spacing_mm") or round(s_mm / 3.0, 3)) if ns >= 2 else None
    rh2   = float(spec.get("secondary_rib_height_mm") or round(rh * 0.5, 3)) if ns >= 2 else None

    return {
        "biological_inspiration":    bio,
        "width_mm":                  w,
        "height_mm":                 h,
        "thickness_mm":              t_mm,
        "primary_rib_spacing_mm":    s_mm,
        "primary_rib_height_mm":     rh,
        "primary_rib_width_mm":      rw,
        "frame_width_mm":            fw,
        "has_secondary":             "yes" if ns >= 2 else "no",
        "secondary_rib_spacing_mm":  s2 if s2 else "N/A",
        "secondary_rib_height_mm":   rh2 if rh2 else "N/A",
        "_ns":                       ns,
        "_s2":                       s2,
        "_rh2":                      rh2,
    }


def _build_prompt(p: Dict[str, Any]) -> str:
    return _PROMPT.format(**{k: v for k, v in p.items() if not k.startswith("_")})


def _call_llm(prompt: str) -> str:
    """Call LLM and return OpenSCAD code string."""
    from core.llm_client import LLMClient
    client = LLMClient(agent_name="GeometryGenerator")
    # Large token budget — OpenSCAD code for ribbed membranes is ~60-120 lines
    raw = client.call(prompt=prompt, max_tokens=2000, temperature=0.2)
    if not raw:
        raise RuntimeError("LLM returned empty response")

    # Strip markdown fences if model wrapped the code
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Drop first line (``` or ```openscad) and last line (```)
        inner = lines[1:] if lines[-1].strip() == "```" else lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        raw = "\n".join(inner)
    return raw.strip()


def _render_stl(scad_code: str, stl_path: Path) -> subprocess.CompletedProcess:
    """Write .scad file and render to .stl via openscad CLI."""
    scad_path = stl_path.with_suffix(".scad")
    scad_path.write_text(scad_code, encoding="utf-8")

    result = subprocess.run(
        ["openscad", "--export-format", "binstl", "-o", str(stl_path), str(scad_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result


def _stl_stats(stl_path: Path) -> Dict[str, Any]:
    """Parse binary STL to get triangle count and bounding box."""
    import struct
    stats: Dict[str, Any] = {}
    try:
        data = stl_path.read_bytes()
        if len(data) < 84:
            return {"num_triangles": 0}
        n_tri = struct.unpack_from("<I", data, 80)[0]
        stats["num_triangles"] = n_tri
        stats["num_faces"] = n_tri

        # Extract all vertices to compute bounding box
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
            offset += 2   # attribute
        if xs:
            stats["bounding_box_mm"] = {
                "x": round(max(xs) - min(xs), 3),
                "y": round(max(ys) - min(ys), 3),
                "z": round(max(zs) - min(zs), 3),
            }
    except Exception as e:
        stats["stats_error"] = str(e)
    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate bioinspired ribbed membrane STL: GPT → OpenSCAD → STL"
    )
    spec_group = parser.add_mutually_exclusive_group(required=True)
    spec_group.add_argument("--spec", help="Upstream spec as JSON string")
    spec_group.add_argument("--spec-file", help="Path to upstream spec JSON file")
    parser.add_argument("--output", default="", help="Output .stl path (auto if omitted)")
    parser.add_argument("--save-scad", action="store_true",
                        help="Keep the .scad file alongside the .stl")
    args = parser.parse_args()

    # ---- Load upstream spec ------------------------------------------------
    if args.spec:
        try:
            raw_spec = json.loads(args.spec)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid --spec JSON: {e}"}))
            sys.exit(1)
    else:
        p = Path(args.spec_file)
        if not p.exists():
            print(json.dumps({"error": f"Spec file not found: {args.spec_file}"}))
            sys.exit(1)
        raw_spec = json.load(open(p))
    # Support nested payload from artifact store
    spec = raw_spec.get("payload", raw_spec)
    if "motifs" in spec and isinstance(spec["motifs"], list) and spec["motifs"]:
        spec = {**spec, **spec["motifs"][0]}

    # ---- Derive parameters from spec ---------------------------------------
    p = _derive_spec_params(spec)
    prompt = _build_prompt(p)

    # ---- GPT generates OpenSCAD code ---------------------------------------
    try:
        scad_code = _call_llm(prompt)
    except Exception as e:
        print(json.dumps({"error": f"LLM call failed: {e}", "prompt": prompt}))
        sys.exit(1)

    # ---- Determine output path --------------------------------------------
    if args.output:
        stl_path = Path(args.output)
    else:
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        stl_path = Path(tempfile.gettempdir()) / f"membrane_{ts}.stl"
    stl_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- Render STL via openscad ------------------------------------------
    try:
        result = _render_stl(scad_code, stl_path)
    except FileNotFoundError:
        print(json.dumps({
            "error": "openscad not found. Install with: sudo apt-get install openscad",
            "scad_code": scad_code,
            "prompt_used": prompt,
        }))
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(json.dumps({"error": "openscad timed out (>120s)"}))
        sys.exit(1)

    if result.returncode != 0:
        print(json.dumps({
            "error": "openscad render failed",
            "stderr": result.stderr,
            "scad_code": scad_code,
        }))
        sys.exit(1)

    if not stl_path.exists() or stl_path.stat().st_size == 0:
        print(json.dumps({
            "error": "openscad produced no output",
            "stderr": result.stderr,
            "scad_code": scad_code,
        }))
        sys.exit(1)

    # ---- Cleanup scad file unless --save-scad ------------------------------
    scad_path = stl_path.with_suffix(".scad")
    if not args.save_scad and scad_path.exists():
        scad_path.unlink()

    # ---- Return artifact JSON ---------------------------------------------
    stats = _stl_stats(stl_path)
    output = {
        "stl_path":     str(stl_path.resolve()),
        "scad_path":    str(scad_path.resolve()) if args.save_scad else None,
        "scad_code":    scad_code,
        "prompt_used":  prompt,
        "design_params": {k: v for k, v in p.items() if not k.startswith("_")},
        **stats,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
