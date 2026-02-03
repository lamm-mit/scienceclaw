#!/usr/bin/env python3
"""
NIST Chemistry WebBook lookup for ScienceClaw.

Searches or looks up compounds in NIST Chemistry WebBook (thermochemistry,
spectra, properties). Uses nistchempy if installed; otherwise prints WebBook URLs.
"""

import argparse
import json
import sys
import urllib.parse

try:
    import requests
except ImportError:
    requests = None

NIST_SEARCH_BASE = "https://webbook.nist.gov/cgi/cbook.cgi"


def webbook_search_url(query: str) -> str:
    """Return NIST WebBook name search URL."""
    return f"{NIST_SEARCH_BASE}?Name={urllib.parse.quote(query)}&Units=SI"


def webbook_cas_url(cas: str) -> str:
    """Return NIST WebBook compound URL by CAS RN (ID=C + digits no dashes)."""
    cas_clean = str(cas).replace("-", "")
    return f"{NIST_SEARCH_BASE}?ID=C{cas_clean}&Mask=1E9F"


def run_with_nistchempy(query: str = None, cas: str = None, max_results: int = 5, as_json: bool = False):
    """Use nistchempy if available. Returns list of compound dicts or None if error/not installed."""
    try:
        import nistchempy
    except ImportError:
        return None

    try:
        if cas:
            # Search by CAS RN
            results = nistchempy.run_search(cas)
        elif query:
            results = nistchempy.run_search(query)
        else:
            return None

        if results is None:
            return []
        # NistChemPy may return list of NistCompound or similar
        out = []
        if hasattr(results, "__iter__") and not isinstance(results, (str, dict)):
            for i, c in enumerate(results):
                if i >= max_results:
                    break
                if hasattr(c, "__dict__"):
                    out.append({k: getattr(c, k, None) for k in dir(c) if not k.startswith("_")})
                elif isinstance(c, dict):
                    out.append(c)
                else:
                    out.append({"compound": str(c)})
        else:
            out = [results] if results is not None else []
        return out
    except Exception as e:
        print(f"nistchempy error: {e}", file=sys.stderr)
        return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Look up chemicals in NIST Chemistry WebBook"
    )
    parser.add_argument("--query", "-q", help="Compound name or formula")
    parser.add_argument("--cas", "-c", help="CAS Registry Number (e.g. 7732-18-5)")
    parser.add_argument("--max-results", "-n", type=int, default=5, help="Max results")
    parser.add_argument("--url-only", action="store_true", help="Only print WebBook URL")
    parser.add_argument("--format", "-f", choices=("summary", "json"), default="summary")
    args = parser.parse_args()

    if not args.query and not args.cas:
        parser.error("Provide --query or --cas")
        return

    if args.url_only:
        if args.cas:
            print(webbook_cas_url(args.cas))
        else:
            print(webbook_search_url(args.query))
        return

    # Try nistchempy
    compounds = run_with_nistchempy(
        query=args.query, cas=args.cas, max_results=args.max_results, as_json=(args.format == "json")
    )

    if compounds is None:
        # nistchempy not installed
        print("NIST Chemistry WebBook lookup")
        print("Install nistchempy for programmatic search: pip install nistchempy")
        print("")
        if args.cas:
            url = webbook_cas_url(args.cas)
            print(f"Open in browser: {url}")
        else:
            url = webbook_search_url(args.query)
            print(f"Search in browser: {url}")
        return

    if not compounds:
        print("No results found.")
        if args.cas:
            print(f"WebBook link: {webbook_cas_url(args.cas)}")
        elif args.query:
            print(f"Search: {webbook_search_url(args.query)}")
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(compounds, indent=2, default=str))
        return

    for i, c in enumerate(compounds, 1):
        print(f"--- Result {i} ---")
        if isinstance(c, dict):
            for k, v in c.items():
                if v is not None and k != "compound" or (k == "compound" and v):
                    print(f"  {k}: {v}")
        else:
            print(f"  {c}")
        print("")
    print("More data (thermochemistry, spectra): https://webbook.nist.gov/chemistry/")


if __name__ == "__main__":
    main()
