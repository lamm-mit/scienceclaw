#!/usr/bin/env python3
"""
Firecrawl Search for ScienceClaw

Search the web through the Firecrawl Search API and optionally return page
content for each result as Markdown in the same call.

Works without an API key on Firecrawl's keyless tier. Set FIRECRAWL_API_KEY
(or pass --api-key) for higher rate limits.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Run: pip install requests", file=sys.stderr)
    print(json.dumps({"error": "requests library not installed. Run: pip install requests"}))
    sys.exit(1)

FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search"

# Same academic hosts the websearch skill targets with --science.
SCIENCE_DOMAINS = [
    "ncbi.nlm.nih.gov",
    "nature.com",
    "science.org",
    "pubmed.gov",
    "biorxiv.org",
]


def build_payload(
    query: str,
    max_results: int,
    science: bool,
    category: Optional[str],
    tbs: Optional[str],
    scrape: bool,
    timeout: int,
) -> Dict[str, Any]:
    """Build the request body for POST /v2/search."""
    payload: Dict[str, Any] = {
        "query": query,
        "limit": max(1, min(max_results, 100)),
        "timeout": timeout * 1000,
    }
    if science:
        payload["includeDomains"] = SCIENCE_DOMAINS
    if category:
        payload["categories"] = [category]
    if tbs:
        payload["tbs"] = tbs
    if scrape:
        payload["scrapeOptions"] = {"formats": ["markdown"], "onlyMainContent": True}
    return payload


def url_from_identifier(primary_id: Any) -> str:
    """Resolve a paper identifier such as 'arxiv:2105.05233' to a URL when the prefix is known."""
    if not isinstance(primary_id, str):
        return ""
    prefix, _, ident = primary_id.partition(":")
    if prefix == "arxiv" and ident:
        return f"https://arxiv.org/abs/{ident}"
    if prefix == "doi" and ident:
        return f"https://doi.org/{ident}"
    return ""


def normalize_result(item: Dict[str, Any], position: int, max_content: int) -> Dict[str, Any]:
    """Flatten one search hit into the fields other skills expect."""
    result: Dict[str, Any] = {
        "position": item.get("position", position),
        "title": item.get("title", ""),
        "url": item.get("url", "") or url_from_identifier(item.get("primaryId")),
        # Web hits carry `description`; research paper records carry `abstract`.
        "description": item.get("description") or item.get("abstract") or item.get("snippet", ""),
    }
    if item.get("category"):
        result["category"] = item["category"]
    # Research Index paper records carry identifiers instead of a page URL.
    for key in ("paperId", "primaryId", "ids", "score"):
        if key in item:
            result[key] = item[key]
    markdown = item.get("markdown")
    if markdown:
        result["markdown"] = markdown[:max_content]
        result["markdown_truncated"] = len(markdown) > max_content
    return result


def search_firecrawl(payload: Dict[str, Any], api_key: str, timeout: int) -> Dict[str, Any]:
    """Call the Firecrawl Search API and return the parsed JSON body."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.post(FIRECRAWL_SEARCH_URL, headers=headers, json=payload, timeout=timeout + 10)
    try:
        body = response.json()
    except ValueError:
        response.raise_for_status()
        raise ValueError(f"Firecrawl returned a non-JSON response (HTTP {response.status_code})")

    if response.status_code >= 400 or not body.get("success", False):
        message = body.get("error") or f"HTTP {response.status_code}"
        if response.status_code == 401:
            message = "Invalid Firecrawl API key. Check FIRECRAWL_API_KEY or --api-key."
        elif response.status_code == 429 or body.get("reason") == "credits":
            wait = body.get("retry_after_seconds")
            wait_text = f" Retry in about {int(wait) // 60 + 1} minutes." if wait else ""
            if api_key:
                message = f"Firecrawl rate limit or credit limit reached.{wait_text}"
            else:
                message = (
                    "Firecrawl keyless tier rate limit reached. Set FIRECRAWL_API_KEY "
                    f"(free key at https://www.firecrawl.dev/) for higher limits.{wait_text}"
                )
        raise RuntimeError(message)

    return body


def collect_results(body: Dict[str, Any], max_content: int) -> List[Dict[str, Any]]:
    """Read web hits and research paper records from the response envelope."""
    data = body.get("data", {})
    raw: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        raw.extend(data.get("web", []) or [])
        raw.extend(data.get("research", []) or [])
    elif isinstance(data, list):
        # Older envelope: flat list of results.
        raw.extend(data)
    return [normalize_result(item, i, max_content) for i, item in enumerate(raw, 1)]


def result_locator(r: Dict[str, Any]) -> str:
    """URL when there is one, otherwise the paper identifier."""
    return r.get("url") or r.get("primaryId") or r.get("paperId") or ""


def format_summary(results: List[Dict[str, Any]]) -> str:
    """Format results as a short summary."""
    if not results:
        return "No results found."

    lines = [f"Found {len(results)} results:\n", "-" * 70]
    for r in results:
        lines.append(f"\n{r['position']}. {r['title']}")
        locator = result_locator(r)
        if locator:
            lines.append(f"   {locator}")
        if r.get("description"):
            desc = r["description"]
            lines.append(f"   {desc[:200] + '...' if len(desc) > 200 else desc}")
    lines.append("\n" + "-" * 70)
    return "\n".join(lines)


def format_detailed(results: List[Dict[str, Any]]) -> str:
    """Format results with full details, including scraped Markdown when present."""
    if not results:
        return "No results found."

    lines = [f"Found {len(results)} results:\n"]
    for r in results:
        lines.append("=" * 70)
        lines.append(f"Result #{r['position']}")
        lines.append(f"Title: {r['title']}")
        if r.get("url"):
            lines.append(f"URL: {r['url']}")
        elif result_locator(r):
            lines.append(f"ID: {result_locator(r)}")
        if r.get("category"):
            lines.append(f"Category: {r['category']}")
        if r.get("description"):
            lines.append(f"\nSnippet:\n{r['description']}")
        if r.get("markdown"):
            lines.append(f"\nContent:\n{r['markdown']}")
            if r.get("markdown_truncated"):
                lines.append("[content truncated]")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search the web with the Firecrawl Search API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "CRISPR base editing efficiency"
  %(prog)s --query "protein folding" --science --format summary
  %(prog)s --query "AlphaFold3 benchmarks" --scrape --max-results 3
        """,
    )
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument(
        "--max-results", "--limit", "-m",
        dest="max_results",
        type=int,
        default=10,
        help="Maximum results, 1 to 100 (default: 10)",
    )
    parser.add_argument("--science", "-s", action="store_true", help="Restrict to academic hosts")
    parser.add_argument(
        "--category", "-c",
        choices=["research", "pdf", "developer"],
        default=None,
        help="Filter results by category",
    )
    parser.add_argument("--tbs", default=None, help="Time filter, e.g. qdr:d, qdr:w, qdr:m, qdr:y, sbd:1")
    parser.add_argument("--scrape", action="store_true", help="Also return page Markdown for each result")
    parser.add_argument("--max-content", type=int, default=4000, help="Characters of Markdown kept per result (default: 4000)")
    parser.add_argument(
        "--format", "-f",
        default="json",
        choices=["summary", "detailed", "json"],
        help="Output format (default: json)",
    )
    parser.add_argument("--api-key", default=None, help="Firecrawl API key (falls back to FIRECRAWL_API_KEY env var)")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("FIRECRAWL_API_KEY", "")

    # Status goes to stderr so stdout stays parseable for --format json.
    print(f"Searching Firecrawl for: {args.query}", file=sys.stderr)
    if not api_key:
        print("(keyless tier; set FIRECRAWL_API_KEY for higher limits)", file=sys.stderr)

    payload = build_payload(
        query=args.query,
        max_results=args.max_results,
        science=args.science,
        category=args.category,
        tbs=args.tbs,
        scrape=args.scrape,
        timeout=args.timeout,
    )

    try:
        body = search_firecrawl(payload, api_key, args.timeout)
    except (RuntimeError, ValueError, requests.RequestException) as e:
        print(f"Error: {e}", file=sys.stderr)
        print(json.dumps({"error": str(e), "query": args.query, "source": "firecrawl"}, indent=2))
        sys.exit(1)

    results = collect_results(body, args.max_content)
    warnings = body.get("warnings") or []

    if args.format == "json":
        output: Dict[str, Any] = {
            "query": args.query,
            "source": "firecrawl",
            "count": len(results),
            "results": results,
            "summary": f"Found {len(results)} results for '{args.query}'",
        }
        if warnings:
            output["warnings"] = warnings
        print(json.dumps(output, indent=2))
    else:
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        if args.format == "detailed":
            print(format_detailed(results))
        else:
            print(format_summary(results))


if __name__ == "__main__":
    main()
