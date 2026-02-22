#!/usr/bin/env python3
"""
Google Scholar Search Tool for ScienceClaw

Search Google Scholar via SerpAPI for academic papers on critical minerals
with citation counts and metadata.
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

try:
    sys.path.insert(0, "/Users/nancywashton/cmm-data/src")
    from cmm_data.clients import GoogleScholarClient
except ImportError:
    print("Error: cmm_data package is required. Ensure cmm-data is installed.", file=sys.stderr)
    sys.exit(1)


def search_scholar(
    query: str,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    num_results: int = 10,
    sort_by: str = "relevance",
) -> List[Dict[str, Any]]:
    """Search Google Scholar and return results."""
    client = GoogleScholarClient()

    print(f"Searching Google Scholar: {query}", file=sys.stderr)
    if year_from:
        print(f"Year from: {year_from}", file=sys.stderr)
    if year_to:
        print(f"Year to: {year_to}", file=sys.stderr)
    print(f"Max results: {num_results}", file=sys.stderr)
    print("", file=sys.stderr)

    result = client.search_scholar(
        query=query,
        year_from=year_from,
        year_to=year_to,
        num_results=num_results,
    )

    if result.error:
        print(f"Error: {result.error}", file=sys.stderr)
        return []

    papers = []
    for p in result.papers:
        papers.append({
            "title": p.title,
            "authors": p.authors,
            "venue": p.venue,
            "year": p.year,
            "snippet": p.snippet,
            "citations": p.citations,
            "url": p.url,
            "pdf_url": p.pdf_url,
        })

    # Sort by citations if requested
    if sort_by == "citations":
        papers.sort(key=lambda x: x["citations"], reverse=True)

    print(f"Found {len(papers)} papers", file=sys.stderr)
    return papers


def format_summary(papers: List[Dict[str, Any]]) -> str:
    """Format papers as summary list."""
    if not papers:
        return "No papers found."

    lines = [f"\nFound {len(papers)} Google Scholar results:\n"]
    lines.append("-" * 80)

    for i, p in enumerate(papers, 1):
        citations_str = f"[{p['citations']} citations]" if p["citations"] else ""
        lines.append(f"\n{i}. {p['title']}")
        lines.append(f"   {p['authors']}")
        lines.append(f"   {p['venue']} ({p['year']}) {citations_str}")

    lines.append("\n" + "-" * 80)
    return "\n".join(lines)


def format_detailed(papers: List[Dict[str, Any]]) -> str:
    """Format papers with full details."""
    if not papers:
        return "No papers found."

    lines = []
    for i, p in enumerate(papers, 1):
        lines.append("=" * 80)
        lines.append(f"Paper #{i}")
        lines.append("=" * 80)
        lines.append(f"\nTitle: {p['title']}")
        lines.append(f"Authors: {p['authors']}")
        lines.append(f"Venue: {p['venue']}")
        lines.append(f"Year: {p['year']}")
        lines.append(f"Citations: {p['citations']}")
        if p.get("snippet"):
            lines.append(f"\nSnippet: {p['snippet']}")
        lines.append(f"\nURL: {p['url']}")
        if p.get("pdf_url"):
            lines.append(f"PDF: {p['pdf_url']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search Google Scholar for academic papers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "lithium extraction brine"
  %(prog)s --query "rare earth separation" --year-from 2020 --sort-by citations
  %(prog)s --query "critical minerals policy" --format json
        """
    )

    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--year-from", type=int, help="Start year filter")
    parser.add_argument("--year-to", type=int, help="End year filter")
    parser.add_argument(
        "--num-results", "-n",
        type=int, default=10,
        help="Number of results (max 20, default: 10)"
    )
    parser.add_argument(
        "--sort-by", "-s",
        default="relevance",
        choices=["relevance", "citations"],
        help="Sort order (default: relevance)"
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    papers = search_scholar(
        query=args.query,
        year_from=args.year_from,
        year_to=args.year_to,
        num_results=args.num_results,
        sort_by=args.sort_by,
    )

    if args.format == "json":
        print(json.dumps(papers, indent=2))
    elif args.format == "detailed":
        print(format_detailed(papers))
    else:
        print(format_summary(papers))


if __name__ == "__main__":
    main()
