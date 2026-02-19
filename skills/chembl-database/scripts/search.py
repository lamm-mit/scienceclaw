#!/usr/bin/env python3
"""
ChEMBL Database Search

Search ChEMBL for molecules and protein targets by name.
Returns compound data with ChEMBL IDs, SMILES, and properties.

Usage:
    python search.py --query "erlotinib" [--limit 10] [--format json]
    python search.py --query "EGFR kinase" --type target
    python search.py --query "kinase inhibitor" --type both --limit 5

Output (JSON, suitable for downstream processing):
    {
        "query": "erlotinib",
        "compounds": [{"name": ..., "chembl_id": ..., "smiles": ..., "formula": ...}],
        "targets": [{"name": ..., "chembl_id": ..., "organism": ...}]
    }
"""

import argparse
import json
import sys


def search_chembl(query, limit=10, search_type='both'):
    """Search ChEMBL molecules and/or targets by name."""
    try:
        from chembl_webresource_client.new_client import new_client
    except ImportError:
        return {"error": "chembl_webresource_client not installed. Run: pip install chembl-webresource-client"}

    result = {"query": query, "compounds": [], "targets": []}

    if search_type in ('molecule', 'both'):
        try:
            mol_client = new_client.molecule
            mols = list(mol_client.filter(pref_name__icontains=query)[:limit])
            result["compounds"] = [
                {
                    "name": m.get("pref_name"),
                    "chembl_id": m.get("molecule_chembl_id"),
                    "formula": (m.get("molecule_properties") or {}).get("full_molformula"),
                    "mw": (m.get("molecule_properties") or {}).get("mw_freebase"),
                    "smiles": (m.get("molecule_structures") or {}).get("canonical_smiles"),
                    "max_phase": m.get("max_phase"),
                }
                for m in mols
            ]
        except Exception as e:
            result["molecule_error"] = str(e)

    if search_type in ('target', 'both'):
        try:
            tgt_client = new_client.target
            targets = list(tgt_client.filter(
                pref_name__icontains=query,
                target_type='SINGLE PROTEIN'
            )[:limit])
            result["targets"] = [
                {
                    "name": t.get("pref_name"),
                    "chembl_id": t.get("target_chembl_id"),
                    "organism": t.get("organism"),
                    "type": t.get("target_type"),
                }
                for t in targets
            ]
        except Exception as e:
            result["target_error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description='Search ChEMBL database')
    parser.add_argument('--query', '-q', required=True, help='Search term (molecule name or target)')
    parser.add_argument('--limit', '-l', type=int, default=10, help='Max results per category (default: 10)')
    parser.add_argument('--max-results', type=int, default=None, help='Alias for --limit')
    parser.add_argument('--type', choices=['molecule', 'target', 'both'], default='both',
                        help='What to search (default: both)')
    parser.add_argument('--format', '-f', default='json', choices=['summary', 'json'],
                        help='Output format (default: json)')

    args = parser.parse_args()
    limit = args.max_results if args.max_results is not None else args.limit

    result = search_chembl(args.query, limit=limit, search_type=args.type)

    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        print(f"ChEMBL search: '{args.query}'")
        print(f"  Molecules found: {len(result.get('compounds', []))}")
        print(f"  Targets found:   {len(result.get('targets', []))}")
        for c in result.get('compounds', [])[:5]:
            print(f"    {c.get('chembl_id')}: {c.get('name')} ({c.get('formula', 'N/A')})")
        for t in result.get('targets', [])[:5]:
            print(f"    {t.get('chembl_id')}: {t.get('name')} [{t.get('organism', 'N/A')}]")


if __name__ == '__main__':
    main()
