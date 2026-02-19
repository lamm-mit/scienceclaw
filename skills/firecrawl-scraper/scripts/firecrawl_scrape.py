#!/usr/bin/env python3
"""
Firecrawl web scraper - extract clean content from JavaScript-rendered
scientific websites and databases using the Firecrawl API.
"""

import argparse
import json
import os
import sys

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

FIRECRAWL_API_BASE = "https://api.firecrawl.dev/v1"


def scrape_with_firecrawl(url: str, fmt: str, api_key: str) -> dict:
    """Call Firecrawl API to scrape the given URL."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": url,
        "formats": [fmt],
    }

    response = requests.post(
        f"{FIRECRAWL_API_BASE}/scrape",
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    if not data.get("success"):
        raise ValueError(f"Firecrawl API error: {data.get('error', 'Unknown error')}")

    page_data = data.get("data", {})
    content = page_data.get(fmt, page_data.get("markdown", page_data.get("content", "")))
    metadata = page_data.get("metadata", {})
    links = page_data.get("links", [])

    return {
        "url": url,
        "content": content,
        "format": fmt,
        "title": metadata.get("title", ""),
        "links": links[:50],  # cap at 50 links
    }


def scrape_fallback(url: str, fmt: str) -> dict:
    """Fallback: plain requests-based scrape without JS rendering."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    raw_html = response.text
    title = ""

    # Extract title from HTML
    import re
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()

    # Extract links
    links = re.findall(r'href=["\']([^"\']+)["\']', raw_html)
    links = [l for l in links if l.startswith("http")][:50]

    if fmt == "html":
        content = raw_html
    else:
        # Rough HTML to text stripping
        text = re.sub(r"<script[^>]*>.*?</script>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        content = text

    return {
        "url": url,
        "content": content,
        "format": fmt,
        "title": title,
        "links": links,
        "warning": "Firecrawl API unavailable or no API key; used static fallback (no JS rendering)",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scrape JavaScript-rendered scientific websites using Firecrawl"
    )
    parser.add_argument("--url", required=True, help="URL to scrape")
    parser.add_argument(
        "--format",
        choices=["markdown", "html", "text"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Firecrawl API key (falls back to FIRECRAWL_API_KEY env var)",
    )
    args = parser.parse_args()

    if not HAS_REQUESTS:
        result = {
            "error": "requests library not installed. Run: pip install requests",
            "url": args.url,
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    api_key = args.api_key or os.environ.get("FIRECRAWL_API_KEY", "")

    try:
        if api_key:
            result = scrape_with_firecrawl(args.url, args.format, api_key)
        else:
            result = scrape_fallback(args.url, args.format)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        if status == 401:
            error_msg = "Invalid or missing Firecrawl API key. Set FIRECRAWL_API_KEY or use --api-key."
        elif status == 429:
            error_msg = "Firecrawl rate limit exceeded. Try again later."
        else:
            error_msg = f"HTTP {status}: {str(e)}"
        result = {"error": error_msg, "url": args.url, "format": args.format}
        print(json.dumps(result, indent=2))
        sys.exit(1)
    except Exception as e:
        result = {"error": str(e), "url": args.url, "format": args.format}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
