#!/usr/bin/env python3
"""
PubChem Search Tool for ScienceClaw

Searches PubChem for chemical compounds and retrieves properties (SMILES,
molecular formula, weight, InChI, etc.). Uses PubChem PUG REST API.
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def search_compound(query: str, max_results: int = 10) -> List[int]:
    """Search PubChem by compound name; returns list of CIDs."""
    url = f"{PUBCHEM_BASE}/compound/name/{requests.utils.quote(query)}/cids/JSON"
    print(f"Searching PubChem: {query}")
    print(f"Max results: {max_results}")
    print("")
    time.sleep(0.25)  # respect rate limit
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        cids = data.get("IdentifierList", {}).get("CID", [])[:max_results]
        print(f"Found {len(cids)} compound(s)")
        print("")
        return cids
    except requests.RequestException as e:
        print(f"Error: {e}")
        return []
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing response: {e}")
        return []


def get_compound_properties(cid: int, detailed: bool = False) -> Optional[Dict]:
    """Fetch compound properties by CID."""
    props = "MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName,InChI,InChIKey"
    if detailed:
        props += ",Title,XLogP,ExactMass"
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/{props}/JSON"
    time.sleep(0.25)
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        items = data.get("PropertyTable", {}).get("Properties", [])
        return items[0] if items else None
    except (requests.RequestException, KeyError, json.JSONDecodeError, IndexError):
        return None


def print_summary(prop: Dict) -> None:
    """Print human-readable summary."""
    print(f"  CID:        {prop.get('CID', 'N/A')}")
    print(f"  Name:       {prop.get('IUPACName') or prop.get('Title') or 'N/A'}")
    print(f"  Formula:    {prop.get('MolecularFormula', 'N/A')}")
    print(f"  MW:         {prop.get('MolecularWeight', 'N/A')} g/mol")
    print(f"  SMILES:     {prop.get('CanonicalSMILES', 'N/A')}")
    print("")


def print_detailed(prop: Dict) -> None:
    """Print detailed properties."""
    print_summary(prop)
    print(f"  InChI:      {prop.get('InChI', 'N/A')}")
    print(f"  InChIKey:   {prop.get('InChIKey', 'N/A')}")
    if prop.get("XLogP") is not None:
        print(f"  XLogP:      {prop.get('XLogP')}")
    if prop.get("ExactMass") is not None:
        print(f"  Exact mass: {prop.get('ExactMass')}")
    print("")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search PubChem for chemical compounds and properties"
    )
    parser.add_argument("--query", "-q", help="Compound name or search term")
    parser.add_argument("--cid", "-c", type=int, help="PubChem Compound ID")
    parser.add_argument("--max-results", "-n", type=int, default=10, help="Max search results")
    parser.add_argument(
        "--format", "-f",
        choices=("summary", "detailed", "json"),
        default="summary",
        help="Output format",
    )
    args = parser.parse_args()

    if args.cid:
        prop = get_compound_properties(args.cid, detailed=(args.format == "detailed"))
        if not prop:
            print(f"No data for CID {args.cid}")
            sys.exit(1)
        if args.format == "json":
            print(json.dumps(prop, indent=2))
        elif args.format == "detailed":
            print_detailed(prop)
        else:
            print_summary(prop)
        return

    if not args.query:
        parser.error("Provide --query or --cid")
        return

    cids = search_compound(args.query, args.max_results)
    if not cids:
        print("No compounds found.")
        sys.exit(1)

    for i, cid in enumerate(cids, 1):
        print(f"--- Result {i} (CID {cid}) ---")
        prop = get_compound_properties(cid, detailed=(args.format == "detailed"))
        if prop:
            if args.format == "json":
                print(json.dumps(prop, indent=2))
            elif args.format == "detailed":
                print_detailed(prop)
            else:
                print_summary(prop)


if __name__ == "__main__":
    main()
