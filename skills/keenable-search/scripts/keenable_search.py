#!/usr/bin/env python3
"""
Keenable Search for ScienceClaw

Search the web through the Keenable Search API and optionally read the top
results as Markdown through the Keenable Fetch API.

Uses KEENABLE_API_KEY (or --api-key). Without a key, the keyless public
endpoint is used only when you opt in with --keyless or KEENABLE_KEYLESS=1.
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

KEENABLE_BASE_URL = "https://api.keenable.ai/v1"
APP_TITLE = "scienceclaw"
MAX_RESULTS_LIMIT = 50
SNIPPET_MAX_LENGTH = 500


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def build_search_payload(
    query: str,
    max_results: int,
    site: Optional[str] = None,
    exclude_domains: Optional[List[str]] = None,
    published_after: Optional[str] = None,
    published_before: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the request body for POST /v1/search."""
    payload: Dict[str, Any] = {
        "query": query,
        "max_results": max(1, min(max_results, MAX_RESULTS_LIMIT)),
        "snippet_max_length": SNIPPET_MAX_LENGTH,
    }
    if site:
        payload["site"] = site
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains
    if published_after:
        payload["published_after"] = published_after
    if published_before:
        payload["published_before"] = published_before
    return payload


def endpoint(path: str, keyless: bool) -> str:
    return f"{KEENABLE_BASE_URL}/{path}/public" if keyless else f"{KEENABLE_BASE_URL}/{path}"


def build_headers(api_key: str) -> Dict[str, str]:
    headers = {"Content-Type": "application/json", "X-Keenable-Title": APP_TITLE}
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def post_keenable(url: str, payload: Dict[str, Any], api_key: str, timeout: int) -> Dict[str, Any]:
    """POST to Keenable and return the parsed body, or raise RuntimeError with a usable message."""
    response = requests.post(url, headers=build_headers(api_key), json=payload, timeout=timeout)
    try:
        body = response.json()
    except ValueError:
        raise RuntimeError(f"Keenable returned a non-JSON response (HTTP {response.status_code})")

    if response.status_code >= 400:
        message = body.get("message") or body.get("error") or f"HTTP {response.status_code}"
        if response.status_code in (401, 403):
            message = f"Keenable rejected the API key ({message}). Check KEENABLE_API_KEY or --api-key."
        elif response.status_code == 429:
            wait = body.get("retry_after_seconds") or response.headers.get("Retry-After")
            wait_text = f" Retry in about {wait} seconds." if wait else ""
            message = f"Keenable rate limit reached.{wait_text}"
        raise RuntimeError(message)
    if not isinstance(body, dict):
        raise RuntimeError("Keenable returned an unexpected response shape")
    return body


def normalize_result(item: Dict[str, Any], position: int) -> Dict[str, Any]:
    """Flatten one search hit into the fields other skills expect."""
    url = item.get("url") or ""
    result: Dict[str, Any] = {
        "position": position,
        "title": item.get("title") or url,
        "url": url,
        "description": item.get("snippet") or item.get("description") or "",
    }
    if item.get("published_at"):
        result["published_at"] = item["published_at"]
    return result


def collect_results(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = body.get("results") or []
    hits = [item for item in raw if isinstance(item, dict) and item.get("url")]
    return [normalize_result(item, i) for i, item in enumerate(hits, 1)]


def attach_markdown(
    results: List[Dict[str, Any]], fetch_body: Dict[str, Any], max_content: int
) -> None:
    """Add page Markdown to results. Fetch returns pages in request order. A page Keenable
    could not read comes back with a per-URL `error` inside an HTTP 200; record it on that
    result instead of failing the whole search."""
    pages = fetch_body.get("results") or []
    for result, page in zip(results, pages):
        if not isinstance(page, dict):
            continue
        error = page.get("error")
        if error:
            message = error.get("message") if isinstance(error, dict) else str(error)
            result["fetch_error"] = message or "fetch failed"
            continue
        content = page.get("content") or ""
        if content:
            result["markdown"] = content[:max_content]
            result["markdown_truncated"] = len(content) > max_content


def format_summary(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "No results found."
    lines = [f"Found {len(results)} results:\n", "-" * 70]
    for r in results:
        lines.append(f"\n{r['position']}. {r['title']}")
        lines.append(f"   {r['url']}")
        if r.get("description"):
            desc = " ".join(r["description"].split())
            lines.append(f"   {desc[:200] + '...' if len(desc) > 200 else desc}")
    lines.append("\n" + "-" * 70)
    return "\n".join(lines)


def format_detailed(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "No results found."
    lines = [f"Found {len(results)} results:\n"]
    for r in results:
        lines.append("=" * 70)
        lines.append(f"Result #{r['position']}")
        lines.append(f"Title: {r['title']}")
        lines.append(f"URL: {r['url']}")
        if r.get("published_at"):
            lines.append(f"Published: {r['published_at']}")
        if r.get("description"):
            lines.append(f"\nSnippet:\n{r['description']}")
        if r.get("markdown"):
            lines.append(f"\nContent:\n{r['markdown']}")
            if r.get("markdown_truncated"):
                lines.append("[content truncated]")
        if r.get("fetch_error"):
            lines.append(f"\nFetch error: {r['fetch_error']}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search the web with the Keenable Search API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "CRISPR base editing efficiency"
  %(prog)s --query "protein folding" --site nature.com --format summary
  %(prog)s --query "AlphaFold3 accuracy" --fetch --max-results 3
        """,
    )
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument(
        "--max-results", "--limit", "-m",
        dest="max_results",
        type=int,
        default=10,
        help=f"Maximum results, 1 to {MAX_RESULTS_LIMIT} (default: 10)",
    )
    parser.add_argument("--site", default=None, help="Only return results from this domain, e.g. nature.com")
    parser.add_argument(
        "--exclude-domain",
        dest="exclude_domains",
        action="append",
        default=None,
        help="Leave out results from this domain (repeatable)",
    )
    parser.add_argument("--published-after", default=None, help="Only pages published on or after this date (YYYY-MM-DD)")
    parser.add_argument("--published-before", default=None, help="Only pages published before this date (YYYY-MM-DD)")
    parser.add_argument("--fetch", action="store_true", help="Also read each result as Markdown (one extra fetch call)")
    parser.add_argument("--max-content", type=int, default=4000, help="Characters of Markdown kept per result (default: 4000)")
    parser.add_argument(
        "--format", "-f",
        default="json",
        choices=["summary", "detailed", "json"],
        help="Output format (default: json)",
    )
    parser.add_argument("--api-key", default=None, help="Keenable API key (falls back to KEENABLE_API_KEY)")
    parser.add_argument(
        "--keyless",
        action="store_true",
        help="Use the keyless public endpoint when no key is set (also KEENABLE_KEYLESS=1)",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)")
    args = parser.parse_args()

    api_key = (args.api_key or os.environ.get("KEENABLE_API_KEY", "")).strip()
    keyless = not api_key and (args.keyless or env_flag("KEENABLE_KEYLESS"))

    if not api_key and not keyless:
        message = (
            "No Keenable API key. Set KEENABLE_API_KEY (keys at https://app.keenable.ai), "
            "or opt in to the keyless public endpoint with --keyless or KEENABLE_KEYLESS=1."
        )
        print(f"Error: {message}", file=sys.stderr)
        print(json.dumps({"error": message, "query": args.query, "source": "keenable"}, indent=2))
        sys.exit(1)

    print(f"Searching Keenable for: {args.query}", file=sys.stderr)
    if keyless:
        print("(keyless public endpoint, rate-limited per IP)", file=sys.stderr)

    payload = build_search_payload(
        query=args.query,
        max_results=args.max_results,
        site=args.site,
        exclude_domains=args.exclude_domains,
        published_after=args.published_after,
        published_before=args.published_before,
    )

    try:
        body = post_keenable(endpoint("search", keyless), payload, api_key, args.timeout)
        results = collect_results(body)
        if args.fetch and results:
            fetch_body = post_keenable(
                endpoint("fetch", keyless), {"urls": [r["url"] for r in results]}, api_key, args.timeout + 30
            )
            attach_markdown(results, fetch_body, args.max_content)
    except (RuntimeError, requests.RequestException) as e:
        print(f"Error: {e}", file=sys.stderr)
        print(json.dumps({"error": str(e), "query": args.query, "source": "keenable"}, indent=2))
        sys.exit(1)

    if args.format == "json":
        print(json.dumps({
            "query": args.query,
            "source": "keenable",
            "count": len(results),
            "results": results,
            "summary": f"Found {len(results)} results for '{args.query}'",
        }, indent=2))
    elif args.format == "detailed":
        print(format_detailed(results))
    else:
        print(format_summary(results))


if __name__ == "__main__":
    main()
