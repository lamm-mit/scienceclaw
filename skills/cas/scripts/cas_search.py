#!/usr/bin/env python3
"""
CAS Common Chemistry search for ScienceClaw.

Searches and retrieves compound data from CAS Common Chemistry API.
Request API access: https://www.cas.org/services/commonchemistry-api
Reference: references/cas-common-chemistry-api.md
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

# CAS Common Chemistry API (public endpoints; may require key after registration)
CAS_API_BASE = "https://commonchemistry.cas.org/api"
CONFIG_DIR = Path.home() / ".scienceclaw"
CAS_CONFIG = CONFIG_DIR / "cas_config.json"


def get_api_key() -> str:
    """Read API key from env or config file."""
    key = os.environ.get("CAS_API_KEY")
    if key:
        return key.strip()
    if CAS_CONFIG.exists():
        try:
            with open(CAS_CONFIG) as f:
                data = json.load(f)
                return (data.get("api_key") or data.get("CAS_API_KEY") or "").strip()
        except (json.JSONDecodeError, IOError):
            pass
    return ""


def search(q: str, max_results: int = 10) -> dict:
    """Search by name, CAS RN, SMILES, or InChI. Returns API response dict."""
    url = f"{CAS_API_BASE}/search?q={requests.utils.quote(q)}"
    headers = {}
    key = get_api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        r = requests.get(url, timeout=30, headers=headers or None)
        if r.status_code in (401, 403):
            print("CAS Common Chemistry API requires access. Request a key at:")
            print("  https://www.cas.org/services/commonchemistry-api")
            return {}
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"Error: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}")
        return {}


def detail(cas_rn: str) -> dict:
    """Get detail for a CAS Registry Number. Returns API response dict."""
    # Normalize: allow with or without dashes
    cas_clean = str(cas_rn).strip()
    url = f"{CAS_API_BASE}/detail?cas_rn={requests.utils.quote(cas_clean)}"
    headers = {}
    key = get_api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        r = requests.get(url, timeout=30, headers=headers or None)
        if r.status_code in (401, 403):
            print("CAS API requires access. Request key: https://www.cas.org/services/commonchemistry-api")
            return {}
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"Error: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}")
        return {}


def print_summary(d: dict) -> None:
    """Print human-readable summary from detail response."""
    print(f"  CAS RN:     {d.get('rn', 'N/A')}")
    print(f"  Name:       {d.get('name', 'N/A')}")
    print(f"  Formula:    {d.get('molecularFormula', 'N/A')}")
    print(f"  Mass:       {d.get('molecularMass', 'N/A')} g/mol")
    print(f"  SMILES:     {d.get('canonicalSmile') or d.get('smile', 'N/A')}")
    print("")


def print_detailed(d: dict) -> None:
    """Print detailed properties."""
    print_summary(d)
    print(f"  InChI:      {d.get('inchi', 'N/A')}")
    print(f"  InChIKey:   {d.get('inchiKey', 'N/A')}")
    props = d.get("experimentalProperties") or []
    if props:
        print("  Experimental properties:")
        for p in props[:10]:
            name = p.get("name", "?")
            val = p.get("property", "?")
            print(f"    {name}: {val}")
    syn = d.get("synonyms")
    if syn and isinstance(syn, list) and len(syn) > 0:
        print(f"  Synonyms:   {', '.join(str(s) for s in syn[:5])}")
    print("")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search CAS Common Chemistry for compounds"
    )
    parser.add_argument("--query", "-q", help="Name, SMILES, or InChI (name supports trailing *)")
    parser.add_argument("--cas", "-c", help="CAS Registry Number (e.g. 50-78-2)")
    parser.add_argument("--max-results", "-n", type=int, default=10, help="Max search results")
    parser.add_argument("--format", "-f", choices=("summary", "detailed", "json"), default="summary")
    args = parser.parse_args()

    if args.cas:
        data = detail(args.cas)
        if not data:
            print(f"No detail found for CAS RN {args.cas}")
            print("Request API access: https://www.cas.org/services/commonchemistry-api")
            sys.exit(1)
        if args.format == "json":
            print(json.dumps(data, indent=2))
        elif args.format == "detailed":
            print_detailed(data)
        else:
            print_summary(data)
        return

    if not args.query:
        parser.error("Provide --query or --cas")
        return

    data = search(args.query, args.max_results)
    count = data.get("count", 0)
    results = data.get("results") or []

    if args.format == "json":
        print(json.dumps(data, indent=2))
        return

    if not results:
        print("No results found.")
        print("Request API access: https://www.cas.org/services/commonchemistry-api")
        sys.exit(1)

    print(f"Found {count} result(s)")
    print("")
    for i, row in enumerate(results[: args.max_results], 1):
        rn = row.get("rn", "?")
        name = row.get("name", "?")
        print(f"--- Result {i}: {name} (CAS {rn}) ---")
        # Fetch detail for summary/detailed
        det = detail(rn) if rn != "?" else {}
        if det:
            if args.format == "detailed":
                print_detailed(det)
            else:
                print_summary(det)
        else:
            print(f"  CAS RN: {rn}")
            print(f"  Name:  {name}")
            print("")


if __name__ == "__main__":
    main()
