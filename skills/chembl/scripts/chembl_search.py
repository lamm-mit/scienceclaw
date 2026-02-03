#!/usr/bin/env python3
"""
ChEMBL Search Tool for ScienceClaw

Searches ChEMBL for drug-like molecules, targets, and bioactivity data.
Uses ChEMBL REST API (EBI).
"""

import argparse
import json
import sys
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"


def search_molecules(query: str, max_results: int = 10) -> List[Dict]:
    """Search ChEMBL molecules by query string."""
    url = f"{CHEMBL_BASE}/molecule/search.json"
    params = {"q": query, "limit": max_results}
    print(f"Searching ChEMBL: {query}")
    print(f"Max results: {max_results}")
    print("")
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        molecules = data.get("molecules", [])
        print(f"Found {len(molecules)} molecule(s)")
        print("")
        return molecules
    except requests.RequestException as e:
        print(f"Error: {e}")
        return []
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing response: {e}")
        return []


def get_molecule(chembl_id: str) -> Optional[Dict]:
    """Fetch single molecule by ChEMBL ID."""
    cid = chembl_id.upper()
    if not cid.startswith("CHEMBL"):
        cid = f"CHEMBL{cid}"
    url = f"{CHEMBL_BASE}/molecule/{cid}.json"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None
    except json.JSONDecodeError:
        return None


def _mol_props(m: Dict) -> Dict:
    """Extract key properties from molecule dict."""
    struct = (m.get("molecule_structures") or {}).get("canonical_smiles") or "N/A"
    props = m.get("molecule_properties") or {}
    return {
        "chembl_id": m.get("molecule_chembl_id"),
        "pref_name": m.get("pref_name"),
        "formula": props.get("molecular_formula") or "N/A",
        "mw": props.get("molecular_weight"),
        "smiles": struct,
        "max_phase": m.get("max_phase"),
        "drug_type": m.get("drug_type"),
        "first_approval": m.get("first_approval"),
        "indication": (m.get("indication") or [None])[0] if m.get("indication") else None,
    }


def print_summary(p: Dict) -> None:
    """Print human-readable summary."""
    print(f"  ChEMBL ID:   {p.get('chembl_id', 'N/A')}")
    print(f"  Name:        {p.get('pref_name') or 'N/A'}")
    print(f"  Formula:     {p.get('formula', 'N/A')}")
    print(f"  MW:          {p.get('mw', 'N/A')} g/mol")
    print(f"  SMILES:      {p.get('smiles', 'N/A')}")
    print(f"  Max phase:   {p.get('max_phase', 'N/A')}")
    print("")


def print_detailed(p: Dict) -> None:
    """Print detailed output."""
    print_summary(p)
    if p.get("drug_type"):
        print(f"  Drug type:   {p['drug_type']}")
    if p.get("first_approval") is not None:
        print(f"  First approval: {p['first_approval']}")
    if p.get("indication"):
        print(f"  Indication:  {p['indication']}")
    print("")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search ChEMBL for drug-like molecules and bioactivity data"
    )
    parser.add_argument("--query", "-q", help="Compound or drug name or search term")
    parser.add_argument("--chembl-id", "-c", help="ChEMBL molecule ID (e.g. CHEMBL25)")
    parser.add_argument("--max-results", "-n", type=int, default=10, help="Max search results")
    parser.add_argument(
        "--format", "-f",
        choices=("summary", "detailed", "json"),
        default="summary",
        help="Output format",
    )
    args = parser.parse_args()

    if args.chembl_id:
        mol = get_molecule(args.chembl_id)
        if not mol:
            print(f"No data for ChEMBL ID {args.chembl_id}")
            sys.exit(1)
        p = _mol_props(mol)
        if args.format == "json":
            print(json.dumps(mol, indent=2))
        elif args.format == "detailed":
            print_detailed(p)
        else:
            print_summary(p)
        return

    if not args.query:
        parser.error("Provide --query or --chembl-id")
        return

    molecules = search_molecules(args.query, args.max_results)
    if not molecules:
        print("No molecules found.")
        sys.exit(1)

    for i, m in enumerate(molecules, 1):
        print(f"--- Result {i} ---")
        p = _mol_props(m)
        if args.format == "json":
            print(json.dumps(m, indent=2))
        elif args.format == "detailed":
            print_detailed(p)
        else:
            print_summary(p)


if __name__ == "__main__":
    main()
