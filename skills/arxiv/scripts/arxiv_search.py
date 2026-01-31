#!/usr/bin/env python3
"""
ArXiv Search Tool for ScienceClaw

Search ArXiv for scientific preprints.
Uses the ArXiv API (no authentication required).
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote_plus

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)


ARXIV_API = "http://export.arxiv.org/api/query"

# Namespace for Atom feed
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom"
}


def search_arxiv(
    query: str,
    category: Optional[str] = None,
    max_results: int = 10,
    sort_by: str = "relevance"
) -> List[Dict]:
    """
    Search ArXiv API.

    Args:
        query: Search query
        category: ArXiv category (e.g., q-bio, cs.LG)
        max_results: Maximum results
        sort_by: Sort order (relevance, lastUpdatedDate, submittedDate)

    Returns:
        List of paper dictionaries
    """
    # Build search query
    search_query = f"all:{query}"
    if category:
        search_query = f"cat:{category} AND {search_query}"

    # Map sort options
    sort_map = {
        "relevance": "relevance",
        "date": "lastUpdatedDate",
        "submitted": "submittedDate"
    }
    sort_order = sort_map.get(sort_by, "relevance")

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_order,
        "sortOrder": "descending"
    }

    print(f"Searching ArXiv: {query}")
    if category:
        print(f"Category: {category}")
    print(f"Max results: {max_results}")
    print("")

    try:
        response = requests.get(ARXIV_API, params=params, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        return []

    # Parse XML response
    root = ET.fromstring(response.content)

    papers = []

    for entry in root.findall("atom:entry", NS):
        # Extract fields
        arxiv_id = entry.find("atom:id", NS)
        arxiv_id = arxiv_id.text if arxiv_id is not None else ""
        # Clean up ID
        arxiv_id = arxiv_id.replace("http://arxiv.org/abs/", "")

        title = entry.find("atom:title", NS)
        title = title.text.strip().replace("\n", " ") if title is not None else ""

        summary = entry.find("atom:summary", NS)
        summary = summary.text.strip().replace("\n", " ") if summary is not None else ""

        published = entry.find("atom:published", NS)
        published = published.text[:10] if published is not None else ""

        updated = entry.find("atom:updated", NS)
        updated = updated.text[:10] if updated is not None else ""

        # Authors
        authors = []
        for author in entry.findall("atom:author", NS):
            name = author.find("atom:name", NS)
            if name is not None:
                authors.append(name.text)

        # Categories
        categories = []
        for cat in entry.findall("atom:category", NS):
            term = cat.get("term")
            if term:
                categories.append(term)

        # Links
        pdf_url = ""
        abs_url = ""
        for link in entry.findall("atom:link", NS):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
            elif link.get("type") == "text/html":
                abs_url = link.get("href", "")

        # Primary category
        primary_cat = entry.find("arxiv:primary_category", NS)
        primary_category = primary_cat.get("term") if primary_cat is not None else ""

        papers.append({
            "id": arxiv_id,
            "title": title,
            "authors": authors,
            "summary": summary,
            "published": published,
            "updated": updated,
            "categories": categories,
            "primary_category": primary_category,
            "pdf_url": pdf_url,
            "abs_url": abs_url or f"https://arxiv.org/abs/{arxiv_id}"
        })

    print(f"Found {len(papers)} papers")
    return papers


def format_summary(papers: List[Dict]) -> str:
    """Format papers as summary list."""
    if not papers:
        return "No papers found."

    lines = [f"\nFound {len(papers)} papers:\n"]
    lines.append("-" * 80)

    for i, paper in enumerate(papers, 1):
        authors_str = ", ".join(paper["authors"][:3])
        if len(paper["authors"]) > 3:
            authors_str += " et al."

        lines.append(f"\n{i}. {paper['title']}")
        lines.append(f"   {authors_str}")
        lines.append(f"   arXiv:{paper['id']} [{paper['primary_category']}] ({paper['published']})")

    lines.append("\n" + "-" * 80)
    return "\n".join(lines)


def format_detailed(papers: List[Dict]) -> str:
    """Format papers with abstracts."""
    if not papers:
        return "No papers found."

    lines = []

    for i, paper in enumerate(papers, 1):
        lines.append("=" * 80)
        lines.append(f"Paper #{i}: arXiv:{paper['id']}")
        lines.append("=" * 80)

        lines.append(f"\nTitle: {paper['title']}")
        lines.append(f"\nAuthors: {', '.join(paper['authors'])}")
        lines.append(f"\nPublished: {paper['published']}")
        lines.append(f"Categories: {', '.join(paper['categories'])}")
        lines.append(f"\nAbstract:\n{paper['summary'][:500]}...")
        lines.append(f"\nURL: {paper['abs_url']}")
        lines.append(f"PDF: {paper['pdf_url']}")
        lines.append("")

    return "\n".join(lines)


def format_bibtex(papers: List[Dict]) -> str:
    """Format papers as BibTeX."""
    if not papers:
        return "% No papers found."

    lines = ["% BibTeX entries from ArXiv\n"]

    for paper in papers:
        # Generate citation key
        first_author = paper["authors"][0].split()[-1] if paper["authors"] else "Unknown"
        year = paper["published"][:4]
        key = f"{first_author}{year}_{paper['id'].replace('.', '_').replace('/', '_')}"

        lines.append(f"@article{{{key},")
        lines.append(f"  title = {{{paper['title']}}},")

        if paper["authors"]:
            authors_bibtex = " and ".join(paper["authors"])
            lines.append(f"  author = {{{authors_bibtex}}},")

        lines.append(f"  year = {{{year}}},")
        lines.append(f"  eprint = {{{paper['id']}}},")
        lines.append(f"  archivePrefix = {{arXiv}},")
        lines.append(f"  primaryClass = {{{paper['primary_category']}}},")
        lines.append(f"  url = {{{paper['abs_url']}}},")
        lines.append("}\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search ArXiv for scientific preprints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "protein structure prediction"
  %(prog)s --query "deep learning" --category q-bio
  %(prog)s --query "AlphaFold" --sort date --format bibtex
        """
    )

    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Search query"
    )
    parser.add_argument(
        "--category", "-c",
        help="ArXiv category (e.g., q-bio, cs.LG, q-bio.BM)"
    )
    parser.add_argument(
        "--max-results", "-m",
        type=int,
        default=10,
        help="Maximum results (default: 10)"
    )
    parser.add_argument(
        "--sort", "-s",
        default="relevance",
        choices=["relevance", "date", "submitted"],
        help="Sort order (default: relevance)"
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json", "bibtex"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    papers = search_arxiv(
        query=args.query,
        category=args.category,
        max_results=args.max_results,
        sort_by=args.sort
    )

    if args.format == "json":
        print(json.dumps(papers, indent=2))
    elif args.format == "bibtex":
        print(format_bibtex(papers))
    elif args.format == "detailed":
        print(format_detailed(papers))
    else:
        print(format_summary(papers))


if __name__ == "__main__":
    main()
