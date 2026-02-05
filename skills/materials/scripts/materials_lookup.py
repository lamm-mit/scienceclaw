#!/usr/bin/env python3
"""
Materials Project lookup for ScienceClaw.
Requires: pip install mp-api (recommended), or pymatgen, or requests for fallback.
API key: https://next-gen.materialsproject.org/api → set MP_API_KEY or ~/.scienceclaw/materials_config.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Prefer next-gen mp_api client (full data); then pymatgen; then requests fallback.
_MP_API_Rester = None
try:
    from mp_api.client import MPRester as _MP_API_Rester
except ImportError:
    pass

try:
    from pymatgen.ext.matproj import MPRester as _PymatgenRester, MPRestError
except ImportError:
    _PymatgenRester = None
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
    if hasattr(sg, "symbol"):
        return getattr(sg, "symbol", None)
    return str(sg)


def _doc_to_dict_fixed(d, mp_id: str) -> dict:
    """Convert MP doc (object or dict) to our standard dict, with mp_id for fallback."""
    if d is None:
        return {}
    get = getattr(d, "get", None)
    if get is not None and callable(get):
        raw = d
    else:
        raw = {
            "material_id": getattr(d, "material_id", None),
            "formula_pretty": getattr(d, "formula_pretty", None) or getattr(d, "formula", None),
            "formula": getattr(d, "formula", None),
            "band_gap": getattr(d, "band_gap", None),
            "density": getattr(d, "density", None),
            "volume": getattr(d, "volume", None),
            "symmetry": getattr(d, "symmetry", None),
            "spacegroup": getattr(d, "spacegroup", None),
        }
    return {
        "material_id": raw.get("material_id") or mp_id,
        "formula": raw.get("formula_pretty") or raw.get("formula") or raw.get("pretty_formula"),
        "band_gap": raw.get("band_gap"),
        "density": _norm_density(raw),
        "volume": raw.get("volume"),
        "spacegroup": _norm_spacegroup(raw),
    }


def lookup_mp_api(mp_id: str, api_key: str) -> dict:
    """Next-gen mp_api client (full summary data)."""
    if _MP_API_Rester is None:
        return {}
    try:
        with _MP_API_Rester(api_key) as mpr:
            fields = ["material_id", "formula_pretty", "formula", "band_gap", "density", "volume", "symmetry", "spacegroup"]
            docs = list(mpr.materials.summary.search(material_ids=[mp_id], fields=fields))
            if not docs:
                return {"error": f"No material found for {mp_id}"}
            return _doc_to_dict_fixed(docs[0], mp_id)
    except Exception:
        return {}  # fall through to pymatgen or direct API


def lookup_direct_api(mp_id: str, api_key: str) -> dict:
    """Direct API fallback: GET with _all_fields=True so we get formula, band_gap, density (no mp-api/pymatgen)."""
    if not requests:
        return {"error": "requests required for direct API fallback (pip install requests)"}
    # Next-gen API: same params as mp-api client — request all fields so we get real data.
    url = f"{MP_BASE}/materials/summary/"
    params = {
        "material_ids": mp_id,
        "_all_fields": True,
        "_limit": 1,
    }
    headers = {"x-api-key": api_key}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": f"API request failed: {str(e)}"}
    if isinstance(data, dict) and data.get("data") and len(data["data"]) > 0:
        d = data["data"][0]
    elif isinstance(data, list) and len(data) > 0:
        d = data[0]
    else:
        return {"error": f"No material found for {mp_id}"}
    # Normalize keys (API may use formula_pretty, formula, or pretty_formula; symmetry as dict or object)
    formula = d.get("formula_pretty") or d.get("formula") or d.get("pretty_formula")
    band_gap = d.get("band_gap")
    if band_gap is not None and isinstance(band_gap, dict):
        band_gap = band_gap.get("min") or band_gap.get("max") or band_gap.get("value")
    return {
        "material_id": d.get("material_id") or mp_id,
        "formula": formula,
        "band_gap": band_gap,
        "density": _norm_density(d),
        "volume": d.get("volume"),
        "spacegroup": _norm_spacegroup(d),
    }


def lookup(mp_id: str, api_key: str) -> dict:
    # 1) Next-gen mp_api client (full data when mp-api is installed)
    out = lookup_mp_api(mp_id, api_key)
    if out and "error" not in out:
        return out
    if out and out.get("error"):
        return out  # e.g. "No material found"
    # 2) Pymatgen (legacy)
    if _PymatgenRester is not None:
        try:
            with _PymatgenRester(api_key) as mpr:
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
        except (MPRestError, KeyError):
            pass
    # 3) Direct REST fallback (may return limited fields)
    return lookup_direct_api(mp_id, api_key)


def main():
    parser = argparse.ArgumentParser(description="Materials Project lookup by ID")
    parser.add_argument("--mp-id", "-m", required=True, help="Materials Project ID (e.g. mp-149)")
    parser.add_argument("--format", choices=["summary", "json"], default="summary")
    args = parser.parse_args()

    if _MP_API_Rester is None and _PymatgenRester is None and requests is None:
        print("Error: install mp-api (recommended), pymatgen, or requests.", file=sys.stderr)
        print("  pip install mp-api     # Next-gen client, full data (band gap, density, formula)", file=sys.stderr)
        print("  pip install pymatgen   # Legacy client, full data", file=sys.stderr)
        print("  pip install requests   # Fallback (limited to material_id only)", file=sys.stderr)
        sys.exit(1)

    if _MP_API_Rester is None and _PymatgenRester is None:
        print("Warning: mp-api and pymatgen not installed. Install 'pip install mp-api' for full data.", file=sys.stderr)
        print("  Falling back to direct API (may return limited fields).", file=sys.stderr)

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
