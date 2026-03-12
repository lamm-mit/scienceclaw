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
            fields = ["material_id", "formula_pretty", "band_gap", "density", "volume", "symmetry"]
            docs = list(mpr.materials.summary.search(material_ids=[mp_id], fields=fields))
            if not docs:
                return {"error": f"No material found for {mp_id}"}
            return _doc_to_dict_fixed(docs[0], mp_id)
    except Exception:
        return {}  # fall through to pymatgen or direct API


def lookup_mp_api_by_formula(formula: str, api_key: str) -> dict:
    """Next-gen mp_api client lookup by chemical formula."""
    if _MP_API_Rester is None:
        return {
            "error": (
                "Formula lookup requires mp-api. "
                "Install with 'pip install mp-api' or provide --mp-id instead."
            )
        }
    try:
        with _MP_API_Rester(api_key) as mpr:
            fields = ["material_id", "formula_pretty", "band_gap", "density", "volume", "symmetry"]
            docs = list(mpr.materials.summary.search(formula=formula, fields=fields))[:1]
            if not docs:
                return {"error": f"No material found for formula {formula}"}
            mp_id = getattr(docs[0], "material_id", None) or formula
            return _doc_to_dict_fixed(docs[0], mp_id)
    except Exception as e:
        return {"error": f"Formula lookup failed: {str(e)}"}


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


DEFAULT_SCREEN_CHEMSYS = "Si-C,B-C,Al-N,Ti-B,Ti-C,Ti-N,Zr-O,Al-O,Si-N,W-C"


def screen_ceramics(
    chemsys: str,
    max_density: float,
    min_band_gap: float,
    limit: int,
    api_key: str,
) -> dict:
    """Screen Materials Project for ceramic candidates matching property constraints.

    Uses the MP API's server-side property filters (density_max, band_gap_min) so
    the entire database is searched — not just a fixed chemsys list.  Results are
    paginated in batches of 500 until ``limit`` passing candidates are collected or
    the API returns no more data.  chemsys is still accepted but used only as a
    secondary element-system hint when provided (comma-separated).
    """
    if not requests:
        return {"error": "requests required for screening (pip install requests)"}

    url = f"{MP_BASE}/materials/summary/"
    headers = {"x-api-key": api_key}
    fields = "material_id,formula_pretty,density,band_gap,volume,symmetry"
    PAGE = 500  # MP API allows up to 1000; 500 is safe and fast

    seen_ids: set = set()
    all_candidates: list = []

    # Build base filter params — let the API do the heavy filtering server-side.
    base_params: dict = {
        "_fields": fields,
        "density_max": max_density,
        "band_gap_min": min_band_gap,
        "_limit": PAGE,
    }

    # If a specific chemsys list was given, query each system separately so we
    # honour the user's domain restriction.  Otherwise do one broad paginated scan.
    chemsys_list = [c.strip() for c in chemsys.split(",") if c.strip()] if chemsys else []
    use_chemsys = bool(chemsys_list)

    def _fetch_page(extra_params: dict) -> list:
        try:
            r = requests.get(url, params={**base_params, **extra_params},
                             headers=headers, timeout=60)
            r.raise_for_status()
            data = r.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            return items if isinstance(items, list) else []
        except Exception as e:
            print(f"Warning: MP API request failed: {e}", file=sys.stderr)
            return []

    def _ingest(items: list) -> None:
        for d in items:
            mid = d.get("material_id")
            if not mid or mid in seen_ids:
                continue
            density_raw = d.get("density")
            band_gap_raw = d.get("band_gap")
            if density_raw is None or band_gap_raw is None:
                continue
            try:
                density_val = float(density_raw)
                band_gap_val = float(band_gap_raw)
            except (TypeError, ValueError):
                continue
            # Double-check client-side (server filters may be approximate)
            if density_val > max_density or band_gap_val < min_band_gap:
                continue
            seen_ids.add(mid)
            all_candidates.append({
                "material_id": mid,
                "formula": d.get("formula_pretty") or d.get("formula"),
                "density": round(density_val, 4),
                "band_gap": round(band_gap_val, 4),
                "volume": d.get("volume"),
                "spacegroup": _norm_spacegroup(d),
            })

    if use_chemsys:
        # Paginate within each chemical system
        for cs in chemsys_list:
            skip = 0
            while True:
                items = _fetch_page({"chemsys": cs, "_skip": skip})
                if not items:
                    break
                _ingest(items)
                if len(items) < PAGE:
                    break
                skip += PAGE
    else:
        # Broad paginated scan — no chemsys restriction
        skip = 0
        while True:
            items = _fetch_page({"_skip": skip})
            if not items:
                break
            _ingest(items)
            print(f"   ↳ screened {len(all_candidates)} candidates so far…", file=sys.stderr)
            if len(items) < PAGE:
                break  # last page
            if len(all_candidates) >= limit * 10:
                # Have plenty to choose from — stop early to keep runtime reasonable
                break
            skip += PAGE

    total_screened = len(all_candidates)
    all_candidates.sort(key=lambda x: x["density"])
    candidates = all_candidates[:limit]

    return {
        "candidates": candidates,
        "total_screened": total_screened,
        "filters": {
            "max_density": max_density,
            "min_band_gap": min_band_gap,
            "chemsys": chemsys,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Materials Project lookup by ID or formula")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--mp-id", "-m", dest="mp_id", help="Materials Project ID (e.g. mp-149)")
    group.add_argument("--formula", "-f", help="Chemical formula (e.g. Fe2O3)")
    # --query / --search / --term: generic entry point used by the skill executor.
    # Auto-routes: "mp-NNN" → --mp-id, anything else → --formula.
    parser.add_argument("--query", "--search", "--term", dest="query", default="",
                        help="MP ID (mp-NNN) or formula/name; auto-routed to --mp-id or --formula")
    parser.add_argument("--format", choices=["summary", "json"], default="summary")
    # Screening mode
    parser.add_argument("--screen", action="store_true",
                        help="Enable screening mode: query MP for ceramic candidates matching property constraints")
    parser.add_argument("--chemsys", default=None,
                        help=f"Comma-separated element systems to screen (default: {DEFAULT_SCREEN_CHEMSYS})")
    parser.add_argument("--max-density", type=float, default=5.0,
                        help="Maximum density in g/cm³ (default: 5.0)")
    parser.add_argument("--min-band-gap", type=float, default=0.5,
                        help="Minimum band gap in eV for ceramic character (default: 0.5)")
    parser.add_argument("--limit", type=int, default=200,
                        help="Max candidates to return in screen mode (default: 200)")
    args = parser.parse_args()

    # Auto-route --query: mp-NNN → single lookup, anything else → screening
    if not args.screen and not args.mp_id and not args.formula:
        q = (args.query or "").strip()
        if not q:
            parser.error("one of the arguments --mp-id/-m --formula/-f --query/--screen is required")
        import re as _re
        if _re.match(r'^mp-\d+$', q, _re.IGNORECASE):
            args.mp_id = q
        else:
            # Any non-MP-ID query triggers screening — never fall back to single-material lookup
            args.screen = True

    if _MP_API_Rester is None and _PymatgenRester is None and requests is None:
        print("Error: install mp-api (recommended), pymatgen, or requests.", file=sys.stderr)
        print("  pip install mp-api     # Next-gen client, full data (band gap, density, formula)", file=sys.stderr)
        print("  pip install pymatgen   # Legacy client, full data", file=sys.stderr)
        print("  pip install requests   # Fallback (limited to material_id only)", file=sys.stderr)
        sys.exit(1)

    if _MP_API_Rester is None and _PymatgenRester is None and not args.screen:
        print("Warning: mp-api and pymatgen not installed. Install 'pip install mp-api' for full data.", file=sys.stderr)
        print("  Falling back to direct API (may return limited fields).", file=sys.stderr)

    api_key = get_api_key()
    if not api_key:
        print("Error: Materials Project API key required.", file=sys.stderr)
        print("Get one at https://materialsproject.org/ then set MP_API_KEY or add to ~/.scienceclaw/materials_config.json", file=sys.stderr)
        sys.exit(1)

    # --- Screening mode ---
    if args.screen:
        chemsys = args.chemsys or DEFAULT_SCREEN_CHEMSYS
        out = screen_ceramics(
            chemsys=chemsys,
            max_density=args.max_density,
            min_band_gap=args.min_band_gap,
            limit=args.limit,
            api_key=api_key,
        )
        if "error" in out:
            print(out["error"], file=sys.stderr)
            sys.exit(1)
        if args.format == "json":
            print(json.dumps(out, indent=2))
            return
        # Summary table
        candidates = out["candidates"]
        filters = out["filters"]
        print(f"  Screened chemsys : {filters['chemsys']}")
        print(f"  Filters          : density <= {filters['max_density']} g/cm³, band_gap >= {filters['min_band_gap']} eV")
        print(f"  Matching         : {out['total_screened']} candidates (showing up to {args.limit})")
        print()
        if candidates:
            print(f"  {'#':>3}  {'material_id':<12}  {'formula':<10}  {'density(g/cm³)':>14}  {'band_gap(eV)':>12}  spacegroup")
            for i, c in enumerate(candidates, 1):
                sg = c.get("spacegroup") or "-"
                print(f"  {i:>3}  {c['material_id']:<12}  {c['formula'] or '?':<10}  {c['density']:>14.3f}  {c['band_gap']:>12.3f}  {sg}")
        else:
            print("  No candidates matched the given constraints.")
        return

    if args.mp_id:
        out = lookup(args.mp_id.strip(), api_key)
    else:
        out = lookup_mp_api_by_formula(args.formula.strip(), api_key)
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
