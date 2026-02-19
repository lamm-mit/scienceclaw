#!/usr/bin/env python3
"""
PDB Database Query Script

Search RCSB Protein Data Bank via REST API.

Usage:
    python query.py --query "KRAS" [--limit 5] [--format json]
    python query.py --search "insulin receptor" --limit 3
"""

import argparse
import json
import sys

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

RCSB_SEARCH = "https://search.rcsb.org/rcsbsearch/v2/query"
RCSB_DATA = "https://data.rcsb.org/rest/v1/core/entry"


def search_pdb(query, limit=10):
    """Search RCSB PDB for structures matching query."""
    payload = {
        "query": {
            "type": "terminal",
            "service": "full_text",
            "parameters": {"value": query}
        },
        "request_options": {
            "results_verbosity": "compact",
            "paginate": {"start": 0, "rows": limit}
        },
        "return_type": "entry"
    }
    try:
        import json as _json
        r = requests.get(RCSB_SEARCH, params={"json": _json.dumps(payload)}, timeout=15)
        r.raise_for_status()
        data = r.json()
        hits = data.get("result_set", [])
        return [h if isinstance(h, str) else h.get("identifier") for h in hits if h]
    except Exception:
        return []


def fetch_entry(pdb_id):
    """Fetch metadata for a PDB entry."""
    try:
        r = requests.get(f"{RCSB_DATA}/{pdb_id.upper()}", timeout=10)
        if r.status_code == 200:
            d = r.json()
            struct = d.get("struct", {})
            entry = d.get("entry", {})
            polymer_entities = d.get("polymer_entities", [])

            # Get organism and method
            exptl = d.get("exptl", [{}])
            method = exptl[0].get("method", "") if exptl else ""

            # Get resolution
            refine = d.get("refine", [{}])
            resolution = refine[0].get("ls_d_res_high") if refine else None

            # Get deposited year
            deposition_date = d.get("rcsb_accession_info", {}).get("deposit_date", "")
            year = deposition_date[:4] if deposition_date else ""

            return {
                "pdb_id": pdb_id.upper(),
                "title": struct.get("title", ""),
                "method": method,
                "resolution": resolution,
                "year": year,
                "organisms": list(set(
                    pe.get("rcsb_entity_source_organism", [{}])[0].get("scientific_name", "")
                    for pe in polymer_entities
                    if pe.get("rcsb_entity_source_organism")
                ))[:3],
            }
    except Exception:
        pass
    return {"pdb_id": pdb_id.upper()}


def query_pdb(search_term, limit=10):
    """Search PDB and return structure entries."""
    pdb_ids = search_pdb(search_term, limit)
    results = []
    for pdb_id in pdb_ids[:limit]:
        entry = fetch_entry(pdb_id)
        if entry:
            results.append(entry)
    return {"query": search_term, "structures": results, "total": len(results)}


def main():
    parser = argparse.ArgumentParser(description="Search RCSB Protein Data Bank")
    parser.add_argument(
        "--query", "--search", "-q", "-s",
        dest="search",
        required=True,
        help="Search term"
    )
    parser.add_argument(
        "--limit", "--max-results", "-l",
        dest="limit",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)"
    )
    parser.add_argument(
        "--format", "-f",
        default="json",
        choices=["summary", "json", "mmcif", "mmCIF", "pdb"],
        help="Output format (default: json)"
    )

    args = parser.parse_args()

    try:
        result = query_pdb(args.search, args.limit)

        if args.format in ("json", "mmcif"):
            print(json.dumps(result, indent=2))
        else:
            print(f"PDB search: '{args.search}'")
            print(f"Structures found: {result['total']}")
            for s in result["structures"][:5]:
                res = f" @ {s['resolution']}Å" if s.get("resolution") else ""
                print(f"  {s['pdb_id']}: {s.get('title', '')[:60]}{res}")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
