#!/usr/bin/env python3
"""
OpenAlex Search CLI

Search OpenAlex for scholarly works with structured JSON output compatible
with the ScienceClaw artifact reactor.

Outputs: {"papers": [...], "query": "...", "total": N}
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

# Allow running from within the scripts dir
sys.path.insert(0, os.path.dirname(__file__))

from openalex_client import OpenAlexClient


SCHEMA = {
    "input_json_fields": [],
    "output_fields": ["papers", "query", "total"],
    "paper_fields": ["id", "title", "authors", "year", "abstract", "doi", "url", "citations"],
}


def _normalise_work(work: dict) -> dict:
    """Map an OpenAlex work object to the canonical paper schema."""
    title = work.get("title") or ""

    authors = []
    for auth in work.get("authorships", []):
        name = (auth.get("author") or {}).get("display_name")
        if name:
            authors.append(name)

    abstract = work.get("abstract") or ""
    # OpenAlex sometimes stores abstract as inverted index
    if not abstract:
        inv = work.get("abstract_inverted_index")
        if inv and isinstance(inv, dict):
            # Reconstruct from inverted index
            max_pos = max(pos for positions in inv.values() for pos in positions)
            words = [""] * (max_pos + 1)
            for word, positions in inv.items():
                for pos in positions:
                    words[pos] = word
            abstract = " ".join(words)

    doi = work.get("doi") or ""
    url = work.get("id") or ""  # OpenAlex URL
    if doi:
        url = f"https://doi.org/{doi.replace('https://doi.org/', '')}"

    return {
        "id": work.get("id", ""),
        "title": title,
        "authors": authors,
        "year": work.get("publication_year"),
        "abstract": abstract[:800] if abstract else "",
        "doi": doi,
        "url": url,
        "citations": work.get("cited_by_count", 0),
    }


def search_openalex(
    query: str,
    max_results: int = 10,
    sort: Optional[str] = None,
    email: Optional[str] = None,
) -> List[Dict]:
    client = OpenAlexClient(email=email)
    response = client.search_works(
        search=query,
        per_page=min(max_results, 200),
        sort=sort,
    )
    works = response.get("results", [])[:max_results]
    return [_normalise_work(w) for w in works]


def main():
    parser = argparse.ArgumentParser(
        description="Search OpenAlex for scholarly works",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "protein structure prediction"
  %(prog)s --query "CRISPR delivery" --max-results 20
  %(prog)s --query "kinase inhibitor" --sort "cited_by_count:desc"
        """,
    )

    parser.add_argument(
        "--describe-schema",
        action="store_true",
        help="Print JSON schema for reactor compatibility and exit",
    )
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument(
        "--max-results", "-m",
        type=int,
        default=10,
        help="Maximum results (default: 10)",
    )
    parser.add_argument(
        "--sort", "-s",
        default=None,
        help="Sort order e.g. 'cited_by_count:desc' or 'publication_date:desc'",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("OPENALEX_EMAIL") or os.environ.get("NCBI_EMAIL"),
        help="Email for polite pool (faster rate limit)",
    )

    args = parser.parse_args()

    if args.describe_schema:
        print(json.dumps(SCHEMA))
        return

    if not args.query:
        parser.error("--query is required")

    papers = search_openalex(
        query=args.query,
        max_results=args.max_results,
        sort=args.sort,
        email=args.email,
    )

    print(json.dumps({"papers": papers, "query": args.query, "total": len(papers)}, indent=2))


if __name__ == "__main__":
    main()
