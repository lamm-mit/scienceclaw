#!/usr/bin/env python3
"""
Browser automation tool - fetch JavaScript-rendered scientific database pages
using Playwright for dynamic content extraction.
"""

import argparse
import json
import os
import sys


def fetch_with_playwright(url: str, wait_for: str, screenshot: str, extract_text: bool) -> dict:
    """Use Playwright to fetch a JavaScript-rendered page."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)

            if wait_for:
                page.wait_for_selector(wait_for, timeout=15000)

            title = page.title()

            if screenshot:
                os.makedirs(os.path.dirname(os.path.abspath(screenshot)), exist_ok=True)
                page.screenshot(path=screenshot, full_page=True)

            if extract_text:
                content = page.inner_text("body")
            else:
                content = page.content()

        finally:
            browser.close()

    result = {
        "url": url,
        "content": content,
        "title": title,
        "status": "success",
    }
    if screenshot:
        result["screenshot"] = screenshot
    return result


def fetch_fallback(url: str) -> dict:
    """Fallback: static requests-based fetch when Playwright is unavailable."""
    try:
        import requests

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        import re

        raw = response.text
        title_m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
        title = title_m.group(1).strip() if title_m else ""
        text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return {
            "url": url,
            "content": text,
            "title": title,
            "status": "success",
            "warning": (
                "Playwright not installed; used static HTTP fallback "
                "(JavaScript not rendered). Install with: pip install playwright && playwright install chromium"
            ),
        }
    except Exception as e:
        return {
            "url": url,
            "content": "",
            "title": "",
            "status": "error",
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Fetch JavaScript-rendered scientific database pages using Playwright"
    )
    parser.add_argument("--url", required=True, help="URL to fetch")
    parser.add_argument(
        "--wait-for",
        default=None,
        metavar="CSS_SELECTOR",
        help="CSS selector to wait for before extracting content",
    )
    parser.add_argument(
        "--screenshot",
        default=None,
        metavar="PATH",
        help="Path to save a PNG screenshot of the page",
    )
    parser.add_argument(
        "--extract-text",
        action="store_true",
        help="Extract text content only (default: return full HTML)",
    )
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        has_playwright = True
    except ImportError:
        has_playwright = False

    try:
        if has_playwright:
            result = fetch_with_playwright(
                url=args.url,
                wait_for=args.wait_for,
                screenshot=args.screenshot,
                extract_text=args.extract_text,
            )
        else:
            result = fetch_fallback(args.url)
    except Exception as e:
        result = {
            "url": args.url,
            "content": "",
            "title": "",
            "status": "error",
            "error": str(e),
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
