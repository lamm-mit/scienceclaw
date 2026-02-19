#!/usr/bin/env python3
"""
AlphaFold Database Query Script

Search AlphaFold EBI database for protein structure predictions.
Looks up proteins by name (via UniProt search) then fetches AlphaFold prediction metadata.

Usage:
    python query.py --query "BTK" [--limit 5] [--format json]
    python query.py --search "KRAS" --limit 3
"""

import argparse
import json
import sys

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

ALPHAFOLD_API = "https://alphafold.ebi.ac.uk/api"
UNIPROT_SEARCH = "https://rest.uniprot.org/uniprotkb/search"


def search_uniprot_accessions(query: str, limit: int = 5) -> list:
    """Search UniProt for protein accessions matching the query."""
    params = {
        "query": f"({query}) AND (organism_id:9606)",  # Human proteins
        "fields": "accession,protein_name,gene_names",
        "format": "json",
        "size": limit,
    }
    try:
        r = requests.get(UNIPROT_SEARCH, params=params, timeout=15)
        r.raise_for_status()
        results = r.json().get("results", [])
        accessions = []
        for entry in results:
            acc = entry.get("primaryAccession", "")
            gene = ""
            genes = entry.get("genes", [])
            if genes:
                gene = genes[0].get("geneName", {}).get("value", "")
            name = ""
            pnames = entry.get("proteinDescription", {})
            rec = pnames.get("recommendedName", {})
            if rec:
                name = rec.get("fullName", {}).get("value", "")
            if not name:
                sub = pnames.get("submissionNames", [])
                if sub:
                    name = sub[0].get("fullName", {}).get("value", "")
            if acc:
                accessions.append({"accession": acc, "gene": gene, "name": name})
        return accessions
    except Exception:
        return []


def fetch_alphafold_prediction(uniprot_id: str) -> dict:
    """Fetch AlphaFold prediction metadata for a UniProt ID."""
    try:
        r = requests.get(f"{ALPHAFOLD_API}/prediction/{uniprot_id}", timeout=15)
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        entries = r.json()
        if not entries:
            return {}
        entry = entries[0]
        seq_start = entry.get("sequenceStart", 1)
        seq_end = entry.get("sequenceEnd", 0)
        return {
            "uniprot_id": uniprot_id,
            "entry_id": entry.get("modelEntityId", ""),
            "gene": entry.get("gene", ""),
            "uniprot_description": entry.get("uniprotDescription", ""),
            "organism": entry.get("organismScientificName", ""),
            "sequence_length": seq_end - seq_start + 1 if seq_end else None,
            "model_created_date": (entry.get("modelCreatedDate") or "")[:10],
            "latest_version": entry.get("latestVersion"),
            "mean_plddt": entry.get("globalMetricValue"),
            "fraction_very_high": entry.get("fractionPlddtVeryHigh"),
            "pdb_url": entry.get("pdbUrl", ""),
            "cif_url": entry.get("cifUrl", ""),
            "pae_image_url": entry.get("paeImageUrl", ""),
        }
    except Exception:
        return {}


def query_alphafold(search_term: str, limit: int = 5) -> dict:
    """Search AlphaFold database for structures matching a protein query."""
    accessions = search_uniprot_accessions(search_term, limit)
    if not accessions:
        return {"query": search_term, "structures": [], "total": 0}

    structures = []
    for acc_info in accessions:
        prediction = fetch_alphafold_prediction(acc_info["accession"])
        if prediction:
            prediction["gene"] = prediction.get("gene") or acc_info.get("gene", "")
            prediction["uniprot_description"] = prediction.get("uniprot_description") or acc_info.get("name", "")
            structures.append(prediction)

    return {
        "query": search_term,
        "structures": structures,
        "total": len(structures),
    }


def main():
    parser = argparse.ArgumentParser(description="Search AlphaFold EBI protein structure database")
    parser.add_argument(
        "--query", "--search", "-q", "-s",
        dest="search",
        required=True,
        help="Protein name or gene (e.g. BTK, KRAS, p53)"
    )
    parser.add_argument(
        "--limit", "--max-results", "-l",
        dest="limit",
        type=int,
        default=5,
        help="Maximum results (default: 5)"
    )
    parser.add_argument(
        "--format", "-f",
        default="json",
        choices=["summary", "json"],
        help="Output format (default: json)"
    )

    args = parser.parse_args()

    try:
        result = query_alphafold(args.search, args.limit)

        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print(f"AlphaFold search: '{args.search}'")
            print(f"Structures found: {result['total']}")
            for s in result["structures"][:5]:
                plddt = f", mean pLDDT={s['mean_plddt']:.1f}" if s.get("mean_plddt") else ""
                length = f", {s['sequence_length']} aa" if s.get("sequence_length") else ""
                print(f"  {s.get('gene', s['uniprot_id'])}: {s.get('uniprot_description','')[:60]}{length}{plddt}")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
