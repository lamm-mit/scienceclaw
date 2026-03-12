#!/usr/bin/env python3
"""
Web Search Tool for ScienceClaw

Search the web for scientific information using DuckDuckGo.
No API key required.
"""

import argparse
import json
import re
import sys
from typing import Dict, List
from urllib.parse import quote_plus

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: requests and beautifulsoup4 are required.")
    print("Install with: pip install requests beautifulsoup4")
    sys.exit(1)


def search_duckduckgo(query: str, max_results: int = 10) -> List[Dict]:
    """
    Search DuckDuckGo and return results.

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        List of result dictionaries
    """
    # DuckDuckGo HTML search
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ScienceClaw/1.0; +https://github.com/lamm-mit/scienceclaw)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Search error: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    # Parse DuckDuckGo results
    for result in soup.select(".result"):
        if len(results) >= max_results:
            break

        title_elem = result.select_one(".result__title")
        snippet_elem = result.select_one(".result__snippet")
        url_elem = result.select_one(".result__url")

        if title_elem:
            title = title_elem.get_text(strip=True)
            link = title_elem.find("a")
            href = link.get("href", "") if link else ""

            # Extract actual URL from DuckDuckGo redirect
            if "uddg=" in href:
                import urllib.parse
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                href = parsed.get("uddg", [href])[0]

            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            display_url = url_elem.get_text(strip=True) if url_elem else href

            results.append({
                "title": title,
                "url": href,
                "display_url": display_url,
                "snippet": snippet
            })

    return results


def search_science(query: str, max_results: int = 10) -> List[Dict]:
    """
    Search with science-focused modifiers.

    Adds terms to focus on scientific sources.
    """
    # Add scientific source hints
    science_query = f"{query} site:ncbi.nlm.nih.gov OR site:nature.com OR site:science.org OR site:pubmed.gov OR site:biorxiv.org"

    return search_duckduckgo(science_query, max_results)


def format_summary(results: List[Dict]) -> str:
    """Format results as summary."""
    if not results:
        return "No results found."

    lines = [f"Found {len(results)} results:\n"]
    lines.append("-" * 70)

    for i, r in enumerate(results, 1):
        lines.append(f"\n{i}. {r['title']}")
        lines.append(f"   {r['display_url']}")
        if r['snippet']:
            # Truncate long snippets
            snippet = r['snippet'][:200] + "..." if len(r['snippet']) > 200 else r['snippet']
            lines.append(f"   {snippet}")

    lines.append("\n" + "-" * 70)
    return "\n".join(lines)


def format_detailed(results: List[Dict]) -> str:
    """Format results with full details."""
    if not results:
        return "No results found."

    lines = [f"Found {len(results)} results:\n"]

    for i, r in enumerate(results, 1):
        lines.append("=" * 70)
        lines.append(f"Result #{i}")
        lines.append(f"Title: {r['title']}")
        lines.append(f"URL: {r['url']}")
        if r['snippet']:
            lines.append(f"\nSnippet:\n{r['snippet']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search the web for scientific information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "CRISPR mechanism"
  %(prog)s --query "protein folding" --science
  %(prog)s --query "AlphaFold" --max-results 20 --format json
        """
    )

    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Search query"
    )
    parser.add_argument(
        "--max-results", "-m",
        type=int,
        default=10,
        help="Maximum results (default: 10)"
    )
    parser.add_argument(
        "--science", "-s",
        action="store_true",
        help="Focus on scientific sources"
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    print(f"Searching for: {args.query}")
    if args.science:
        print("(Science-focused search)")
    print("")

    if args.science:
        results = search_science(args.query, args.max_results)
    else:
        results = search_duckduckgo(args.query, args.max_results)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    elif args.format == "detailed":
        print(format_detailed(results))
    else:
        print(format_summary(results))


if __name__ == "__main__":
    main()
