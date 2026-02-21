#!/usr/bin/env python3
"""
OSTI.gov Search Tool for ScienceClaw

Search the DOE Office of Scientific and Technical Information for
technical reports, journal articles, and conference papers.
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)


OSTI_API = "https://www.osti.gov/api/v1/records"

COMMODITY_KEYWORDS = {
    "HREE": "heavy rare earth dysprosium terbium europium yttrium",
    "LREE": "light rare earth lanthanum cerium neodymium praseodymium",
    "CO": "cobalt",
    "LI": "lithium",
    "GA": "gallium",
    "GR": "graphite",
    "NI": "nickel",
    "CU": "copper",
    "GE": "germanium",
    "OTH": "critical mineral",
}


def search_osti_api(
    query: str,
    commodity: Optional[str] = None,
    product_type: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    limit: int = 10,
    sort: str = "relevance",
) -> List[Dict]:
    """
    Search OSTI.gov public API.

    Args:
        query: Search query
        commodity: Commodity code (HREE, LREE, CO, LI, GA, GR, NI, CU, GE, OTH)
        product_type: Product type filter (Technical Report, Journal Article, etc.)
        year_from: Start year
        year_to: End year
        limit: Maximum results
        sort: Sort order (relevance or date)

    Returns:
        List of record dictionaries
    """
    # Build the search query
    search_terms = query
    if commodity and commodity.upper() in COMMODITY_KEYWORDS:
        search_terms = f"{search_terms} {COMMODITY_KEYWORDS[commodity.upper()]}"

    params = {
        "q": search_terms,
        "rows": min(limit, 100),
    }

    if product_type:
        params["product_type"] = product_type

    if year_from:
        params["publication_date_start"] = f"{year_from}-01-01"

    if year_to:
        params["publication_date_end"] = f"{year_to}-12-31"

    if sort == "date":
        params["sort"] = "publication_date"
        params["order"] = "desc"

    print(f"Searching OSTI.gov: {query}", file=sys.stderr)
    if commodity:
        print(f"Commodity: {commodity}", file=sys.stderr)
    if product_type:
        print(f"Product type: {product_type}", file=sys.stderr)
    print(f"Max results: {limit}", file=sys.stderr)
    print("", file=sys.stderr)

    try:
        headers = {"Accept": "application/json"}
        response = requests.get(OSTI_API, params=params, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error querying OSTI API: {e}", file=sys.stderr)
        return []

    try:
        data = response.json()
    except json.JSONDecodeError:
        print("Error: Could not parse OSTI API response", file=sys.stderr)
        return []

    records = []
    for record in data[:limit]:
        records.append({
            "id": str(record.get("osti_id", "")),
            "title": record.get("title", ""),
            "authors": _parse_authors(record.get("authors", [])),
            "publication_date": record.get("publication_date", "")[:10],
            "product_type": record.get("product_type", ""),
            "research_org": ", ".join(record.get("research_orgs", [])) if isinstance(record.get("research_orgs"), list) else record.get("research_org", ""),
            "sponsor_org": ", ".join(record.get("sponsor_orgs", [])) if isinstance(record.get("sponsor_orgs"), list) else record.get("sponsor_org", ""),
            "doi": record.get("doi", ""),
            "description": record.get("description", ""),
            "url": _extract_link(record.get("links", []), "fulltext")
                   or f"https://www.osti.gov/biblio/{record.get('osti_id', '')}",
            "subject": ", ".join(record.get("subjects", [])) if isinstance(record.get("subjects"), list) else record.get("subjects", ""),
        })

    print(f"Found {len(records)} records", file=sys.stderr)
    return records



def _extract_link(links, rel: str) -> str:
    """Extract a link URL from OSTI links list by rel type."""
    if isinstance(links, list):
        for link in links:
            if isinstance(link, dict) and link.get("rel") == rel:
                return link.get("href", "")
    return ""


def _parse_authors(authors_field) -> List[str]:
    """Parse authors from OSTI record (can be string or list)."""
    if isinstance(authors_field, list):
        result = []
        for a in authors_field:
            if isinstance(a, dict):
                name = a.get("full_name", str(a))
            else:
                name = str(a)
            # Strip affiliation brackets: "Name [Affiliation]" -> "Name"
            bracket_idx = name.find(" [")
            if bracket_idx > 0:
                name = name[:bracket_idx]
            # Strip ORCID parenthetical
            orcid_idx = name.find(" (ORCID:")
            if orcid_idx > 0:
                name = name[:orcid_idx]
            result.append(name.strip())
        return result
    if isinstance(authors_field, str) and authors_field:
        return [a.strip() for a in authors_field.split(";")]
    return []


def format_summary(records: List[Dict]) -> str:
    """Format records as summary list."""
    if not records:
        return "No records found."

    lines = [f"\nFound {len(records)} OSTI records:\n"]
    lines.append("-" * 80)

    for i, record in enumerate(records, 1):
        authors_str = ", ".join(record["authors"][:3])
        if len(record["authors"]) > 3:
            authors_str += " et al."

        lines.append(f"\n{i}. {record['title']}")
        lines.append(f"   {authors_str}")
        lines.append(f"   OSTI:{record['id']} [{record['product_type']}] ({record['publication_date']})")
        if record.get("research_org"):
            lines.append(f"   Org: {record['research_org']}")

    lines.append("\n" + "-" * 80)
    return "\n".join(lines)


def format_detailed(records: List[Dict]) -> str:
    """Format records with full details."""
    if not records:
        return "No records found."

    lines = []

    for i, record in enumerate(records, 1):
        lines.append("=" * 80)
        lines.append(f"Record #{i}: OSTI:{record['id']}")
        lines.append("=" * 80)

        lines.append(f"\nTitle: {record['title']}")
        lines.append(f"\nAuthors: {', '.join(record['authors'])}")
        lines.append(f"\nDate: {record['publication_date']}")
        lines.append(f"Type: {record['product_type']}")
        lines.append(f"Organization: {record['research_org']}")
        lines.append(f"Sponsor: {record['sponsor_org']}")
        if record.get("doi"):
            lines.append(f"DOI: {record['doi']}")
        if record.get("description"):
            lines.append(f"\nAbstract:\n{record['description'][:500]}...")
        if record.get("subject"):
            lines.append(f"\nSubjects: {record['subject']}")
        lines.append(f"\nURL: {record['url']}")
        lines.append("")

    return "\n".join(lines)


def format_bibtex(records: List[Dict]) -> str:
    """Format records as BibTeX."""
    if not records:
        return "% No records found."

    lines = ["% BibTeX entries from OSTI.gov\n"]

    for record in records:
        first_author = record["authors"][0].split(",")[0].split()[-1] if record["authors"] else "Unknown"
        year = record["publication_date"][:4] if record["publication_date"] else "0000"
        key = f"{first_author}{year}_OSTI{record['id']}"

        entry_type = "techreport" if "report" in record.get("product_type", "").lower() else "article"

        lines.append(f"@{entry_type}{{{key},")
        lines.append(f"  title = {{{record['title']}}},")

        if record["authors"]:
            authors_bibtex = " and ".join(record["authors"])
            lines.append(f"  author = {{{authors_bibtex}}},")

        lines.append(f"  year = {{{year}}},")

        if record.get("research_org"):
            lines.append(f"  institution = {{{record['research_org']}}},")

        if record.get("doi"):
            lines.append(f"  doi = {{{record['doi']}}},")

        lines.append(f"  url = {{{record['url']}}},")
        lines.append(f"  note = {{OSTI ID: {record['id']}}},")
        lines.append("}\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search OSTI.gov for DOE technical reports and publications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commodity codes:
  HREE  Heavy Rare Earth Elements    LREE  Light Rare Earth Elements
  CO    Cobalt                       LI    Lithium
  GA    Gallium                      GR    Graphite
  NI    Nickel                       CU    Copper
  GE    Germanium                    OTH   Other critical minerals

Examples:
  %(prog)s --query "rare earth separation"
  %(prog)s --query "lithium extraction" --commodity LI --sort date
  %(prog)s --query "cobalt recycling" --format bibtex
  %(prog)s --query "critical minerals" --year-from 2020 --limit 20
        """
    )

    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Search query"
    )
    parser.add_argument(
        "--commodity", "-c",
        choices=["HREE", "LREE", "CO", "LI", "GA", "GR", "NI", "CU", "GE", "OTH"],
        help="Commodity code filter"
    )
    parser.add_argument(
        "--product-type", "-p",
        help="Product type filter (e.g., 'Technical Report', 'Journal Article')"
    )
    parser.add_argument(
        "--year-from",
        type=int,
        help="Start year for date filter"
    )
    parser.add_argument(
        "--year-to",
        type=int,
        help="End year for date filter"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Maximum results (default: 10)"
    )
    parser.add_argument(
        "--sort", "-s",
        default="relevance",
        choices=["relevance", "date"],
        help="Sort order (default: relevance)"
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json", "bibtex"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    records = search_osti_api(
        query=args.query,
        commodity=args.commodity,
        product_type=args.product_type,
        year_from=args.year_from,
        year_to=args.year_to,
        limit=args.limit,
        sort=args.sort,
    )

    if args.format == "json":
        print(json.dumps(records, indent=2))
    elif args.format == "bibtex":
        print(format_bibtex(records))
    elif args.format == "detailed":
        print(format_detailed(records))
    else:
        print(format_summary(records))


if __name__ == "__main__":
    main()
