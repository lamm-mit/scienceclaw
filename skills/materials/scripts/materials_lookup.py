#!/usr/bin/env python3
"""
Materials Project lookup for ScienceClaw.
Requires: pip install pymatgen (or requests for fallback).
API key: https://next-gen.materialsproject.org/api → set MP_API_KEY or ~/.scienceclaw/materials_config.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from pymatgen.ext.matproj import MPRester, MPRestError
except ImportError:
    MPRester = None
    MPRestError = Exception

try:
    import requests
except ImportError:
    requests = None

CONFIG_PATH = Path.home() / ".scienceclaw" / "materials_config.json"
MP_BASE = "https://api.materialsproject.org"


def get_api_key():
    key = os.environ.get("MP_API_KEY")
    if key:
        return key
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f).get("api_key")
        except Exception:
            pass
    return None


def _norm_density(d):
    val = d.get("density")
    if val is None:
        return None
    try:
        return round(float(val), 4)
    except (TypeError, ValueError):
        return val


def _norm_spacegroup(d, key="symmetry"):
    sg = d.get(key) or d.get("spacegroup")
    if sg is None:
        return None
    if isinstance(sg, dict):
        return sg.get("symbol") or sg.get("point_group")
    return str(sg)


def lookup_direct_api(mp_id: str, api_key: str) -> dict:
    """Next-gen API: GET summary by material_id (no 'fields' param)."""
    if not requests:
        return {"error": "requests required for direct API fallback (pip install requests)"}
    url = f"{MP_BASE}/materials/summary/"
    params = {"material_ids": mp_id}
    headers = {"X-API-KEY": api_key}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": str(e)}
    # Response may be {"data": [doc, ...]} or a list
    if isinstance(data, list) and len(data) > 0:
        d = data[0]
    elif isinstance(data, dict) and data.get("data") and len(data["data"]) > 0:
        d = data["data"][0]
    else:
        return {"error": f"No material found for {mp_id}"}
    return {
        "material_id": d.get("material_id") or mp_id,
        "formula": d.get("formula_pretty") or d.get("formula") or d.get("pretty_formula"),
        "band_gap": d.get("band_gap"),
        "density": _norm_density(d),
        "volume": d.get("volume"),
        "spacegroup": _norm_spacegroup(d),
    }


def lookup(mp_id: str, api_key: str) -> dict:
    # Try pymatgen first (get_summary_by_material_id uses _all_fields=True, no forbidden 'fields' param)
    if MPRester is not None:
        try:
            with MPRester(api_key) as mpr:
                d = mpr.get_summary_by_material_id(mp_id)
                if not d:
                    return {"error": f"No material found for {mp_id}"}
                return {
                    "material_id": d.get("material_id") or mp_id,
                    "formula": d.get("formula_pretty") or d.get("formula") or d.get("pretty_formula"),
                    "band_gap": d.get("band_gap"),
                    "density": _norm_density(d),
                    "volume": d.get("volume"),
                    "spacegroup": _norm_spacegroup(d),
                }
        except (MPRestError, KeyError) as e:
            # API may return different shape (e.g. next-gen); fall back to direct request
            pass
    # Fallback: direct REST call (next-gen API shape)
    return lookup_direct_api(mp_id, api_key)


def main():
    parser = argparse.ArgumentParser(description="Materials Project lookup by ID")
    parser.add_argument("--mp-id", "-m", required=True, help="Materials Project ID (e.g. mp-149)")
    parser.add_argument("--format", choices=["summary", "json"], default="summary")
    args = parser.parse_args()

    if MPRester is None and requests is None:
        print("Error: install pymatgen or requests. E.g.: pip install pymatgen  or  pip install requests", file=sys.stderr)
        sys.exit(1)

    api_key = get_api_key()
    if not api_key:
        print("Error: Materials Project API key required.", file=sys.stderr)
        print("Get one at https://materialsproject.org/ then set MP_API_KEY or add to ~/.scienceclaw/materials_config.json", file=sys.stderr)
        sys.exit(1)

    out = lookup(args.mp_id.strip(), api_key)
    if "error" in out:
        print(out["error"], file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(out, indent=2))
        return

    print(f"  material_id: {out.get('material_id')}")
    print(f"  formula:     {out.get('formula')}")
    print(f"  band_gap:    {out.get('band_gap')} eV")
    print(f"  density:     {out.get('density')} g/cm³")
    print(f"  volume:      {out.get('volume')}")
    print(f"  spacegroup:  {out.get('spacegroup')}")


if __name__ == "__main__":
    main()
