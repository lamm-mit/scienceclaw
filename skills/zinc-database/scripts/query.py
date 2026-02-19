#!/usr/bin/env python3
"""
ZINC Database Query Script

Search ZINC22 (230M+ purchasable compounds) by ZINC ID, SMILES, or compound name.
For name queries, looks up SMILES via PubChem first then searches ZINC by structure.

Usage:
    python query.py --query "erlotinib" [--limit 10] [--format json]
    python query.py --query "ZINC000000000001" [--format json]
    python query.py --query "c1ccccc1" --smiles [--limit 10]

Note: ZINC is a structure-based database. Name queries resolve to SMILES via PubChem.
"""

import argparse
import json
import re
import sys

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

ZINC_BASE = "https://cartblanche22.docking.org"


def is_smiles(query):
    """Heuristic: does the query look like a SMILES string?"""
    smiles_chars = set('CNOPSFClBrI[]()=#@+\\/-.')
    return len(query) > 4 and sum(c in smiles_chars for c in query) / len(query) > 0.6


def is_zinc_id(query):
    """Check if query is a ZINC ID."""
    return re.match(r'^ZINC\d+$', query.strip(), re.IGNORECASE) is not None


def get_smiles_from_pubchem(name):
    """Resolve compound name to canonical SMILES via PubChem."""
    try:
        r = requests.get(
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(name)}/property/IsomericSMILES,CanonicalSMILES,ConnectivitySMILES,IUPACName,MolecularFormula/JSON",
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
            smiles = (props.get("IsomericSMILES") or props.get("CanonicalSMILES")
                      or props.get("ConnectivitySMILES"))
            return smiles, props.get("IUPACName"), props.get("MolecularFormula")
    except Exception:
        pass
    return None, None, None


def search_by_zinc_id(zinc_id, limit=10):
    """Look up compound by ZINC ID."""
    zinc_id = zinc_id.upper()
    if not zinc_id.startswith("ZINC"):
        zinc_id = f"ZINC{zinc_id}"
    url = f"{ZINC_BASE}/substances.txt:zinc_id={zinc_id}&output_fields=zinc_id,smiles,tranche"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and r.text.strip():
            lines = [l for l in r.text.strip().split('\n') if l and not l.startswith('zinc_id')]
            results = []
            for line in lines[:limit]:
                parts = line.split('\t')
                if len(parts) >= 2:
                    results.append({"zinc_id": parts[0], "smiles": parts[1], "tranche": parts[2] if len(parts) > 2 else None})
            return results
    except Exception:
        pass
    return []


def search_by_smiles(smiles, limit=10, dist=3):
    """Find similar compounds in ZINC22 by SMILES (Tanimoto similarity)."""
    from urllib.parse import quote
    url = f"{ZINC_BASE}/smiles.txt:{quote(smiles, safe='')}=4-Fadist={dist}&output_fields=zinc_id,smiles,tranche"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200 and r.text.strip():
            lines = [l for l in r.text.strip().split('\n') if l]
            results = []
            for line in lines[:limit]:
                parts = line.split('\t')
                if len(parts) >= 2:
                    results.append({"zinc_id": parts[0], "smiles": parts[1], "tranche": parts[2] if len(parts) > 2 else None})
            return results
    except Exception:
        pass
    return []


def main():
    parser = argparse.ArgumentParser(description='Search ZINC22 purchasable compound database')
    parser.add_argument('--query', '--search', '-q', dest='query', required=True,
                        help='Compound name, ZINC ID, or SMILES string')
    parser.add_argument('--limit', '-l', type=int, default=10, help='Max results (default: 10)')
    parser.add_argument('--max-results', type=int, default=None, help='Alias for --limit')
    parser.add_argument('--format', '-f', default='json', choices=['summary', 'json'],
                        help='Output format (default: json)')
    parser.add_argument('--smiles', action='store_true', help='Force treating query as SMILES')

    args = parser.parse_args()
    limit = args.max_results if args.max_results is not None else args.limit
    query = args.query.strip()

    result = {"query": query, "compounds": [], "method": None}

    if is_zinc_id(query):
        result["method"] = "zinc_id"
        result["compounds"] = search_by_zinc_id(query, limit)

    elif args.smiles or is_smiles(query):
        result["method"] = "smiles_similarity"
        result["compounds"] = search_by_smiles(query, limit)

    else:
        # Name query: resolve via PubChem → ZINC similarity search
        smiles, iupac, formula = get_smiles_from_pubchem(query)
        if smiles:
            result["method"] = "name_via_pubchem"
            result["resolved_smiles"] = smiles
            result["resolved_name"] = iupac
            result["formula"] = formula
            result["compounds"] = search_by_smiles(smiles, limit)
        else:
            result["method"] = "not_found"
            result["note"] = f"Could not resolve '{query}' to a SMILES. ZINC requires SMILES or ZINC IDs for structural search."

    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        print(f"ZINC22 search for '{query}' ({result.get('method', 'unknown')})")
        if result.get("resolved_smiles"):
            print(f"  Resolved SMILES: {result['resolved_smiles']}")
        print(f"  Compounds found: {len(result.get('compounds', []))}")
        for c in result.get('compounds', [])[:5]:
            print(f"    {c.get('zinc_id')}: {c.get('smiles', '')[:50]}")


if __name__ == '__main__':
    main()
