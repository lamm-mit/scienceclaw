#!/usr/bin/env python3
"""
UniProt Fetch Tool for ScienceClaw

Queries UniProt database for protein information, sequences, and annotations.
Uses UniProt REST API.
"""

import argparse
import json
import sys
from typing import List, Dict, Optional

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)


UNIPROT_API = "https://rest.uniprot.org/uniprotkb"


def search_uniprot(
    query: str,
    organism: Optional[str] = None,
    reviewed: bool = False,
    max_results: int = 10
) -> List[Dict]:
    """
    Search UniProt for proteins.

    Args:
        query: Search query
        organism: Filter by organism
        reviewed: Only Swiss-Prot entries
        max_results: Maximum results

    Returns:
        List of protein entries
    """
    # Build query
    search_parts = [query]

    if organism:
        # Check if it's a taxonomy ID
        if organism.isdigit():
            search_parts.append(f"organism_id:{organism}")
        else:
            search_parts.append(f"organism_name:{organism}")

    if reviewed:
        search_parts.append("reviewed:true")

    full_query = " AND ".join(search_parts)

    print(f"Searching UniProt: {full_query}")
    print(f"Max results: {max_results}")
    print("")

    # Make request
    params = {
        "query": full_query,
        "format": "json",
        "size": max_results,
        "fields": "accession,id,protein_name,gene_names,organism_name,length,reviewed"
    }

    response = requests.get(f"{UNIPROT_API}/search", params=params)
    response.raise_for_status()

    data = response.json()
    results = data.get("results", [])

    print(f"Found {len(results)} results")
    print("")

    return results


def fetch_protein(
    accession: str,
    include_features: bool = False,
    include_xrefs: bool = False
) -> Dict:
    """
    Fetch a single protein entry.

    Args:
        accession: UniProt accession or entry name
        include_features: Include sequence features
        include_xrefs: Include cross-references

    Returns:
        Protein entry dictionary
    """
    # Build fields to request
    fields = [
        "accession", "id", "protein_name", "gene_names", "organism_name",
        "organism_id", "length", "sequence", "reviewed",
        "cc_function", "cc_subcellular_location", "cc_tissue_specificity",
        "cc_disease", "cc_similarity",
        "go_p", "go_c", "go_f",  # GO terms
        "keyword"
    ]

    if include_features:
        fields.extend(["ft_domain", "ft_region", "ft_site", "ft_mod_res"])

    if include_xrefs:
        fields.extend(["xref_pdb", "xref_pfam", "xref_interpro"])

    params = {
        "format": "json",
        "fields": ",".join(fields)
    }

    response = requests.get(f"{UNIPROT_API}/{accession}", params=params)

    if response.status_code == 404:
        raise ValueError(f"Protein not found: {accession}")

    response.raise_for_status()

    return response.json()


def fetch_fasta(accession: str) -> str:
    """
    Fetch protein sequence in FASTA format.

    Args:
        accession: UniProt accession

    Returns:
        FASTA formatted sequence
    """
    response = requests.get(f"{UNIPROT_API}/{accession}.fasta")

    if response.status_code == 404:
        raise ValueError(f"Protein not found: {accession}")

    response.raise_for_status()

    return response.text


def parse_protein_name(entry: Dict) -> str:
    """Extract primary protein name from entry."""
    protein_desc = entry.get("proteinDescription", {})

    # Try recommended name first
    rec_name = protein_desc.get("recommendedName", {})
    if rec_name:
        full_name = rec_name.get("fullName", {})
        if isinstance(full_name, dict):
            return full_name.get("value", "Unknown")
        return str(full_name)

    # Try submitted name
    sub_names = protein_desc.get("submissionNames", [])
    if sub_names:
        full_name = sub_names[0].get("fullName", {})
        if isinstance(full_name, dict):
            return full_name.get("value", "Unknown")
        return str(full_name)

    return "Unknown"


def parse_gene_names(entry: Dict) -> List[str]:
    """Extract gene names from entry."""
    genes = entry.get("genes", [])
    names = []

    for gene in genes:
        if "geneName" in gene:
            names.append(gene["geneName"].get("value", ""))
        for syn in gene.get("synonyms", []):
            names.append(syn.get("value", ""))

    return [n for n in names if n]


def parse_go_terms(entry: Dict) -> Dict[str, List[str]]:
    """Extract GO terms organized by category."""
    go_terms = {
        "biological_process": [],
        "cellular_component": [],
        "molecular_function": []
    }

    for comment in entry.get("uniProtKBCrossReferences", []):
        if comment.get("database") == "GO":
            term_id = comment.get("id", "")
            props = {p["key"]: p["value"] for p in comment.get("properties", [])}
            term_name = props.get("GoTerm", "")

            if term_name.startswith("P:"):
                go_terms["biological_process"].append(f"{term_id}: {term_name[2:]}")
            elif term_name.startswith("C:"):
                go_terms["cellular_component"].append(f"{term_id}: {term_name[2:]}")
            elif term_name.startswith("F:"):
                go_terms["molecular_function"].append(f"{term_id}: {term_name[2:]}")

    return go_terms


def parse_comments(entry: Dict, comment_type: str) -> List[str]:
    """Extract comments of a specific type."""
    results = []

    for comment in entry.get("comments", []):
        if comment.get("commentType") == comment_type:
            texts = comment.get("texts", [])
            for text in texts:
                if isinstance(text, dict):
                    results.append(text.get("value", ""))
                else:
                    results.append(str(text))

    return results


def format_summary(entries: List[Dict]) -> str:
    """Format entries as a summary table."""
    if not entries:
        return "No proteins found."

    lines = []
    lines.append(f"Found {len(entries)} proteins:\n")
    lines.append("-" * 100)
    lines.append(f"{'Accession':<12} {'Entry':<15} {'Gene':<12} {'Length':<8} {'Reviewed':<10} {'Protein Name'}")
    lines.append("-" * 100)

    for entry in entries:
        accession = entry.get("primaryAccession", "")
        entry_id = entry.get("uniProtkbId", "")
        length = entry.get("sequence", {}).get("length", 0)
        reviewed = "Yes" if entry.get("entryType") == "UniProtKB reviewed (Swiss-Prot)" else "No"

        protein_name = parse_protein_name(entry)
        if len(protein_name) > 40:
            protein_name = protein_name[:37] + "..."

        genes = parse_gene_names(entry)
        gene = genes[0] if genes else "-"

        lines.append(f"{accession:<12} {entry_id:<15} {gene:<12} {length:<8} {reviewed:<10} {protein_name}")

    lines.append("-" * 100)
    return "\n".join(lines)


def format_detailed(entry: Dict) -> str:
    """Format a single entry with full details."""
    lines = []

    # Header
    accession = entry.get("primaryAccession", "")
    entry_id = entry.get("uniProtkbId", "")
    reviewed = "Swiss-Prot (Reviewed)" if entry.get("entryType") == "UniProtKB reviewed (Swiss-Prot)" else "TrEMBL (Unreviewed)"

    lines.append("=" * 80)
    lines.append(f"UniProt Entry: {accession}")
    lines.append("=" * 80)

    lines.append(f"\nAccession: {accession}")
    lines.append(f"Entry Name: {entry_id}")
    lines.append(f"Status: {reviewed}")

    # Protein name
    protein_name = parse_protein_name(entry)
    lines.append(f"\nProtein Name: {protein_name}")

    # Gene names
    genes = parse_gene_names(entry)
    if genes:
        lines.append(f"Gene Names: {', '.join(genes)}")

    # Organism
    organism = entry.get("organism", {})
    org_name = organism.get("scientificName", "")
    org_common = organism.get("commonName", "")
    tax_id = organism.get("taxonId", "")
    org_str = org_name
    if org_common:
        org_str += f" ({org_common})"
    lines.append(f"Organism: {org_str} [TaxID: {tax_id}]")

    # Sequence info
    seq_info = entry.get("sequence", {})
    length = seq_info.get("length", 0)
    mass = seq_info.get("molWeight", 0)
    lines.append(f"\nSequence Length: {length} aa")
    lines.append(f"Molecular Weight: {mass:,} Da")

    # Function
    functions = parse_comments(entry, "FUNCTION")
    if functions:
        lines.append(f"\nFunction:")
        for func in functions:
            lines.append(f"  {func}")

    # Subcellular location
    locations = parse_comments(entry, "SUBCELLULAR LOCATION")
    if locations:
        lines.append(f"\nSubcellular Location:")
        for loc in locations:
            lines.append(f"  {loc}")

    # GO terms
    go_terms = parse_go_terms(entry)
    if any(go_terms.values()):
        lines.append("\nGene Ontology:")
        if go_terms["biological_process"]:
            lines.append("  Biological Process:")
            for term in go_terms["biological_process"][:5]:
                lines.append(f"    - {term}")
        if go_terms["cellular_component"]:
            lines.append("  Cellular Component:")
            for term in go_terms["cellular_component"][:5]:
                lines.append(f"    - {term}")
        if go_terms["molecular_function"]:
            lines.append("  Molecular Function:")
            for term in go_terms["molecular_function"][:5]:
                lines.append(f"    - {term}")

    # Keywords
    keywords = entry.get("keywords", [])
    if keywords:
        kw_list = [kw.get("name", "") for kw in keywords[:10]]
        lines.append(f"\nKeywords: {', '.join(kw_list)}")

    # Disease associations
    diseases = parse_comments(entry, "DISEASE")
    if diseases:
        lines.append(f"\nDisease Associations:")
        for disease in diseases[:3]:
            if len(disease) > 200:
                disease = disease[:197] + "..."
            lines.append(f"  - {disease}")

    # Cross-references
    xrefs = entry.get("uniProtKBCrossReferences", [])
    pdb_refs = [x.get("id") for x in xrefs if x.get("database") == "PDB"]
    if pdb_refs:
        lines.append(f"\nPDB Structures: {', '.join(pdb_refs[:10])}")
        if len(pdb_refs) > 10:
            lines.append(f"  ... and {len(pdb_refs) - 10} more")

    # Sequence
    sequence = seq_info.get("value", "")
    if sequence:
        lines.append(f"\nSequence:")
        # Format sequence in blocks
        for i in range(0, len(sequence), 60):
            lines.append(f"  {sequence[i:i+60]}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Query UniProt for protein information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --accession P53_HUMAN
  %(prog)s --search "insulin human" --reviewed
  %(prog)s --accession P04637 --format fasta
  %(prog)s --search "kinase" --organism human --max-results 20
        """
    )

    parser.add_argument(
        "--accession", "-a",
        help="UniProt accession or entry name (comma-separated for multiple)"
    )
    parser.add_argument(
        "--search", "-s",
        help="Search query"
    )
    parser.add_argument(
        "--organism", "-o",
        help="Filter by organism (name or taxonomy ID)"
    )
    parser.add_argument(
        "--reviewed", "-r",
        action="store_true",
        help="Only Swiss-Prot (reviewed) entries"
    )
    parser.add_argument(
        "--max-results", "-m",
        type=int,
        default=10,
        help="Maximum results for search (default: 10)"
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "fasta", "json"],
        help="Output format (default: summary)"
    )
    parser.add_argument(
        "--include-features",
        action="store_true",
        help="Include sequence features"
    )
    parser.add_argument(
        "--include-xrefs",
        action="store_true",
        help="Include cross-references"
    )

    args = parser.parse_args()

    if not args.accession and not args.search:
        parser.error("Either --accession or --search is required")

    try:
        if args.search:
            # Search mode
            results = search_uniprot(
                query=args.search,
                organism=args.organism,
                reviewed=args.reviewed,
                max_results=args.max_results
            )

            if args.format == "json":
                print(json.dumps(results, indent=2))
            else:
                print(format_summary(results))

        else:
            # Fetch mode
            accessions = [a.strip() for a in args.accession.split(",")]

            if args.format == "fasta":
                for acc in accessions:
                    print(fetch_fasta(acc))
            elif args.format == "json":
                entries = []
                for acc in accessions:
                    entry = fetch_protein(acc, args.include_features, args.include_xrefs)
                    entries.append(entry)
                print(json.dumps(entries if len(entries) > 1 else entries[0], indent=2))
            elif args.format == "detailed":
                for acc in accessions:
                    entry = fetch_protein(acc, args.include_features, args.include_xrefs)
                    print(format_detailed(entry))
                    print("")
            else:
                entries = []
                for acc in accessions:
                    entry = fetch_protein(acc, args.include_features, args.include_xrefs)
                    entries.append(entry)
                print(format_summary(entries))

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
