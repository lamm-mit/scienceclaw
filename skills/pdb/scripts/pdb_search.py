#!/usr/bin/env python3
"""
PDB Search Tool for ScienceClaw

Search and fetch protein structures from RCSB PDB.
Uses the RCSB PDB REST API.
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


PDB_SEARCH_API = "https://search.rcsb.org/rcsbsearch/v2/query"
PDB_DATA_API = "https://data.rcsb.org/rest/v1/core/entry"


def search_pdb(query: str, max_results: int = 10) -> List[str]:
    """
    Search PDB by text query.

    Args:
        query: Search query
        max_results: Maximum results

    Returns:
        List of PDB IDs
    """
    search_request = {
        "query": {
            "type": "terminal",
            "service": "full_text",
            "parameters": {
                "value": query
            }
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {
                "start": 0,
                "rows": max_results
            },
            "results_content_type": ["experimental"],
            "sort": [
                {
                    "sort_by": "score",
                    "direction": "desc"
                }
            ]
        }
    }

    print(f"Searching PDB: {query}")
    print(f"Max results: {max_results}")
    print("")

    try:
        response = requests.post(
            PDB_SEARCH_API,
            json=search_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Search error: {e}", file=sys.stderr)
        return []

    data = response.json()
    pdb_ids = [hit["identifier"] for hit in data.get("result_set", [])]

    print(f"Found {len(pdb_ids)} structures")
    return pdb_ids


def search_by_sequence(
    sequence: str,
    identity_cutoff: float = 0.9,
    max_results: int = 10
) -> List[str]:
    """
    Search PDB by sequence similarity.

    Args:
        sequence: Amino acid sequence
        identity_cutoff: Minimum sequence identity (0-1)
        max_results: Maximum results

    Returns:
        List of PDB IDs
    """
    search_request = {
        "query": {
            "type": "terminal",
            "service": "sequence",
            "parameters": {
                "evalue_cutoff": 1,
                "identity_cutoff": identity_cutoff,
                "sequence_type": "protein",
                "value": sequence
            }
        },
        "return_type": "polymer_entity",
        "request_options": {
            "paginate": {
                "start": 0,
                "rows": max_results
            }
        }
    }

    print(f"Searching PDB by sequence ({len(sequence)} residues)")
    print(f"Identity cutoff: {identity_cutoff * 100:.0f}%")
    print("")

    try:
        response = requests.post(
            PDB_SEARCH_API,
            json=search_request,
            headers={"Content-Type": "application/json"},
            timeout=60  # Sequence search can be slow
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Search error: {e}", file=sys.stderr)
        return []

    data = response.json()

    # Extract PDB IDs from polymer entity IDs (format: XXXX_Y)
    pdb_ids = []
    for hit in data.get("result_set", []):
        entity_id = hit["identifier"]
        pdb_id = entity_id.split("_")[0]
        if pdb_id not in pdb_ids:
            pdb_ids.append(pdb_id)

    print(f"Found {len(pdb_ids)} structures")
    return pdb_ids[:max_results]


def fetch_structure(pdb_id: str) -> Optional[Dict]:
    """
    Fetch structure details.

    Args:
        pdb_id: PDB ID

    Returns:
        Structure data dictionary
    """
    url = f"{PDB_DATA_API}/{pdb_id.upper()}"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            return None
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Fetch error: {e}", file=sys.stderr)
        return None

    data = response.json()

    # Extract key fields
    entry = data.get("entry", {})
    struct = data.get("struct", {})
    exptl = data.get("exptl", [{}])[0] if data.get("exptl") else {}
    refine = data.get("refine", [{}])[0] if data.get("refine") else {}
    cell = data.get("cell", {})
    citation = data.get("citation", [{}])[0] if data.get("citation") else {}

    # Get polymer entities for organism info
    polymer_entities = data.get("polymer_entities", [])
    organisms = []
    for entity in polymer_entities:
        src = entity.get("rcsb_entity_source_organism", [])
        for s in src:
            org = s.get("ncbi_scientific_name", "")
            if org and org not in organisms:
                organisms.append(org)

    structure = {
        "pdb_id": pdb_id.upper(),
        "title": struct.get("title", ""),
        "method": exptl.get("method", ""),
        "resolution": refine.get("ls_d_res_high"),
        "release_date": entry.get("rcsb_accession_info", {}).get("initial_release_date", "")[:10],
        "deposit_date": entry.get("rcsb_accession_info", {}).get("deposit_date", "")[:10],
        "organisms": organisms,
        "citation_title": citation.get("title", ""),
        "citation_journal": citation.get("journal_abbrev", ""),
        "citation_year": citation.get("year"),
        "num_entities": len(polymer_entities),
        "url": f"https://www.rcsb.org/structure/{pdb_id.upper()}",
        "view_3d": f"https://www.rcsb.org/3d-view/{pdb_id.upper()}"
    }

    return structure


def format_summary(structures: List[Dict]) -> str:
    """Format structures as summary list."""
    if not structures:
        return "No structures found."

    lines = [f"\nFound {len(structures)} structures:\n"]
    lines.append("-" * 80)

    for i, s in enumerate(structures, 1):
        resolution = f"{s['resolution']:.2f}Å" if s.get('resolution') else "N/A"
        organism = s['organisms'][0] if s.get('organisms') else "Unknown"

        lines.append(f"\n{i}. [{s['pdb_id']}] {s['title'][:60]}...")
        lines.append(f"   Method: {s['method']} | Resolution: {resolution}")
        lines.append(f"   Organism: {organism} | Released: {s['release_date']}")

    lines.append("\n" + "-" * 80)
    return "\n".join(lines)


def format_detailed(structures: List[Dict]) -> str:
    """Format structures with full details."""
    if not structures:
        return "No structures found."

    lines = []

    for i, s in enumerate(structures, 1):
        lines.append("=" * 80)
        lines.append(f"Structure #{i}: {s['pdb_id']}")
        lines.append("=" * 80)

        lines.append(f"\nTitle: {s['title']}")
        lines.append(f"\nMethod: {s['method']}")
        if s.get('resolution'):
            lines.append(f"Resolution: {s['resolution']:.2f} Å")

        lines.append(f"\nRelease Date: {s['release_date']}")
        lines.append(f"Deposit Date: {s['deposit_date']}")

        if s.get('organisms'):
            lines.append(f"\nOrganism(s): {', '.join(s['organisms'])}")

        lines.append(f"\nPolymer Entities: {s['num_entities']}")

        if s.get('citation_title'):
            lines.append(f"\nCitation: {s['citation_title']}")
            if s.get('citation_journal'):
                lines.append(f"  {s['citation_journal']} ({s.get('citation_year', '')})")

        lines.append(f"\nPDB URL: {s['url']}")
        lines.append(f"3D View: {s['view_3d']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search and fetch protein structures from PDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "kinase human"
  %(prog)s --pdb-id 1ATP
  %(prog)s --sequence "MTEYKLVVVGAGGVGKSALTIQLIQ" --identity 70
        """
    )

    parser.add_argument(
        "--query", "-q",
        help="Text search query"
    )
    parser.add_argument(
        "--pdb-id", "-p",
        help="Specific PDB ID to fetch"
    )
    parser.add_argument(
        "--sequence", "-s",
        help="Amino acid sequence for similarity search"
    )
    parser.add_argument(
        "--identity", "-i",
        type=float,
        default=90,
        help="Minimum sequence identity %% (default: 90)"
    )
    parser.add_argument(
        "--max-results", "-m",
        type=int,
        default=10,
        help="Maximum results (default: 10)"
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    if not any([args.query, args.pdb_id, args.sequence]):
        parser.error("One of --query, --pdb-id, or --sequence is required")

    structures = []

    if args.pdb_id:
        # Fetch specific structure
        structure = fetch_structure(args.pdb_id)
        if structure:
            structures = [structure]
        else:
            print(f"Structure {args.pdb_id} not found")

    elif args.sequence:
        # Search by sequence
        pdb_ids = search_by_sequence(
            args.sequence,
            identity_cutoff=args.identity / 100,
            max_results=args.max_results
        )
        for pdb_id in pdb_ids:
            structure = fetch_structure(pdb_id)
            if structure:
                structures.append(structure)

    else:
        # Text search
        pdb_ids = search_pdb(args.query, args.max_results)
        for pdb_id in pdb_ids:
            structure = fetch_structure(pdb_id)
            if structure:
                structures.append(structure)

    if args.format == "json":
        print(json.dumps(structures, indent=2))
    elif args.format == "detailed":
        print(format_detailed(structures))
    else:
        print(format_summary(structures))


if __name__ == "__main__":
    main()
