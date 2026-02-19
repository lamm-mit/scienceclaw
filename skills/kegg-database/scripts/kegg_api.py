"""
KEGG REST API Helper Functions

This module provides Python functions for interacting with the KEGG REST API.
All functions return raw response text which can be parsed as needed.

API Base URL: https://rest.kegg.jp
Documentation: https://www.kegg.jp/kegg/rest/keggapi.html

IMPORTANT: KEGG API is made available only for academic use by academic users.
"""

import sys
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, List, Union


KEGG_BASE_URL = "https://rest.kegg.jp"


def kegg_info(database: str) -> str:
    """
    Get database metadata and statistics.

    Args:
        database: KEGG database name (e.g., 'kegg', 'pathway', 'enzyme', 'genes')

    Returns:
        str: Database information and statistics

    Example:
        info = kegg_info('pathway')
    """
    url = f"{KEGG_BASE_URL}/info/{database}"
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return f"Error: {e.code} - {e.reason}"


def kegg_list(database: str, org: Optional[str] = None) -> str:
    """
    List entry identifiers and associated names.

    Args:
        database: KEGG database name or specific entry (e.g., 'pathway', 'enzyme', 'hsa:10458')
        org: Optional organism code for pathway/module listings (e.g., 'hsa' for human)

    Returns:
        str: Tab-delimited list of entries

    Examples:
        pathways = kegg_list('pathway')  # List all reference pathways
        hsa_pathways = kegg_list('pathway', 'hsa')  # List human pathways
        genes = kegg_list('hsa:10458+ece:Z5100')  # List specific genes
    """
    if org:
        url = f"{KEGG_BASE_URL}/list/{database}/{org}"
    else:
        url = f"{KEGG_BASE_URL}/list/{database}"

    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return f"Error: {e.code} - {e.reason}"


def kegg_find(database: str, query: str, option: Optional[str] = None) -> str:
    """
    Search for entries by keywords or molecular properties.

    Args:
        database: Database to search ('genes', 'compound', 'drug', etc.)
        query: Search term or molecular property
        option: Optional parameter for molecular searches:
                'formula' - exact match to chemical formula
                'exact_mass' - range search by exact mass (e.g., '174.05-174.15')
                'mol_weight' - range search by molecular weight

    Returns:
        str: Tab-delimited search results

    Examples:
        # Keyword search
        results = kegg_find('genes', 'shiga toxin')

        # Formula search
        compounds = kegg_find('compound', 'C7H10N4O2', 'formula')

        # Mass range search
        drugs = kegg_find('drug', '300-310', 'exact_mass')
    """
    query_encoded = urllib.parse.quote(query)

    if option:
        url = f"{KEGG_BASE_URL}/find/{database}/{query_encoded}/{option}"
    else:
        url = f"{KEGG_BASE_URL}/find/{database}/{query_encoded}"

    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return f"Error: {e.code} - {e.reason}"


def kegg_get(entries: Union[str, List[str]], option: Optional[str] = None) -> str:
    """
    Retrieve full database entries or specific data formats.

    Args:
        entries: Single entry ID or list of entry IDs (max 10)
        option: Optional output format:
                'aaseq' or 'ntseq' - FASTA sequence
                'mol' - MOL format (for compounds)
                'kcf' - KCF format (for compounds)
                'image' - PNG image (pathway maps, single entry only)
                'kgml' - KGML format (pathway XML, single entry only)
                'json' - JSON format (pathway only, single entry only)

    Returns:
        str: Entry data in requested format

    Examples:
        # Get pathway entry
        pathway = kegg_get('hsa00010')

        # Get multiple entries
        genes = kegg_get(['hsa:10458', 'ece:Z5100'])

        # Get sequence
        sequence = kegg_get('hsa:10458', 'aaseq')

        # Get pathway as JSON
        pathway_json = kegg_get('hsa05130', 'json')
    """
    if isinstance(entries, list):
        entries_str = '+'.join(entries[:10])  # Max 10 entries
    else:
        entries_str = entries

    if option:
        url = f"{KEGG_BASE_URL}/get/{entries_str}/{option}"
    else:
        url = f"{KEGG_BASE_URL}/get/{entries_str}"

    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return f"Error: {e.code} - {e.reason}"


def kegg_conv(target_db: str, source_db: str) -> str:
    """
    Convert identifiers between KEGG and external databases.

    Args:
        target_db: Target database (e.g., 'ncbi-geneid', 'uniprot', 'pubchem')
        source_db: Source database or entry (e.g., 'hsa', 'compound', 'hsa:10458')

    Returns:
        str: Tab-delimited conversion table

    Examples:
        # Convert all human genes to NCBI Gene IDs
        conversions = kegg_conv('ncbi-geneid', 'hsa')

        # Convert specific gene
        gene_id = kegg_conv('ncbi-geneid', 'hsa:10458')

        # Convert compounds to PubChem IDs
        pubchem = kegg_conv('pubchem', 'compound')
    """
    url = f"{KEGG_BASE_URL}/conv/{target_db}/{source_db}"
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return f"Error: {e.code} - {e.reason}"


def kegg_link(target_db: str, source_db: str) -> str:
    """
    Find related entries across KEGG databases.

    Args:
        target_db: Target database (e.g., 'pathway', 'enzyme', 'genes')
        source_db: Source database or entry (e.g., 'hsa', 'pathway', 'hsa:10458')

    Returns:
        str: Tab-delimited list of linked entries

    Examples:
        # Find pathways linked to human genes
        links = kegg_link('pathway', 'hsa')

        # Find genes in a specific pathway
        genes = kegg_link('genes', 'hsa00010')

        # Find pathways for a specific gene
        pathways = kegg_link('pathway', 'hsa:10458')
    """
    url = f"{KEGG_BASE_URL}/link/{target_db}/{source_db}"
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return f"Error: {e.code} - {e.reason}"


def kegg_ddi(drug_entries: Union[str, List[str]]) -> str:
    """
    Check drug-drug interactions.

    Args:
        drug_entries: Single drug entry or list of drug entries (max 10)

    Returns:
        str: Drug interaction information

    Example:
        interactions = kegg_ddi(['D00001', 'D00002'])
    """
    if isinstance(drug_entries, list):
        entries_str = '+'.join(drug_entries[:10])  # Max 10 entries
    else:
        entries_str = drug_entries

    url = f"{KEGG_BASE_URL}/ddi/{entries_str}"
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return f"Error: {e.code} - {e.reason}"


def _cli():
    """CLI for KEGG API (enables --help and scriptable use)."""
    import argparse
    p = argparse.ArgumentParser(
        description="KEGG REST API helper. Academic use only.",
        epilog="Examples: kegg_api.py info pathway | kegg_api.py list pathway | kegg_api.py get hsa00010",
    )
    sub = p.add_subparsers(dest="cmd", help="Command")
    # info
    info_p = sub.add_parser("info", help="Database info (e.g. pathway, kegg)")
    info_p.add_argument("database", help="KEGG database name")
    # list
    list_p = sub.add_parser("list", help="List entries")
    list_p.add_argument("database", help="Database or entry list")
    list_p.add_argument("--org", "-o", help="Organism code (e.g. hsa)")
    # find
    find_p = sub.add_parser("find", help="Search by keyword or property")
    find_p.add_argument("database", help="Database to search")
    find_p.add_argument("query", help="Search term")
    find_p.add_argument("--option", choices=["formula", "exact_mass", "mol_weight"], help="Search option")
    # get
    get_p = sub.add_parser("get", help="Get entry/entries")
    get_p.add_argument("entries", nargs="+", help="Entry ID(s), max 10")
    get_p.add_argument("--format", "-f", choices=["aaseq", "ntseq", "mol", "kcf", "image", "kgml", "json"], help="Output format")
    # conv
    conv_p = sub.add_parser("conv", help="Convert IDs")
    conv_p.add_argument("target_db", help="Target DB (e.g. ncbi-geneid, uniprot)")
    conv_p.add_argument("source_db", help="Source DB or entry")
    # link
    link_p = sub.add_parser("link", help="Link between databases")
    link_p.add_argument("target_db", help="Target database")
    link_p.add_argument("source_db", help="Source database or entry")
    # ddi
    ddi_p = sub.add_parser("ddi", help="Drug-drug interactions")
    ddi_p.add_argument("drugs", nargs="+", help="Drug ID(s), e.g. D00001")
    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return 0
    try:
        if args.cmd == "info":
            print(kegg_info(args.database))
        elif args.cmd == "list":
            print(kegg_list(args.database, getattr(args, "org", None) or None))
        elif args.cmd == "find":
            print(kegg_find(args.database, args.query, getattr(args, "option", None) or None))
        elif args.cmd == "get":
            opt = getattr(args, "format", None) or None
            entries = args.entries[:10]
            print(kegg_get(entries[0] if len(entries) == 1 else entries, opt))
        elif args.cmd == "conv":
            print(kegg_conv(args.target_db, args.source_db))
        elif args.cmd == "link":
            print(kegg_link(args.target_db, args.source_db))
        elif args.cmd == "ddi":
            print(kegg_ddi(args.drugs[0] if len(args.drugs) == 1 else args.drugs[:10]))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
