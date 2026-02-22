#!/usr/bin/env python3
"""
Critical minerals news/blog discovery monitor.

Discovers relevant web links via DuckDuckGo and emits normalized records for
policy and market intelligence pipelines.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, quote_plus, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: requests and beautifulsoup4 are required.", file=sys.stderr)
    print("Install with: pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)


COMMODITY_KEYWORDS: Dict[str, Sequence[str]] = {
    "lithium": ["lithium", "lce"],
    "cobalt": ["cobalt"],
    "nickel": ["nickel"],
    "graphite": ["graphite"],
    "rare_earth": ["rare earth", "ree", "neodymium", "dysprosium", "lanthanide"],
    "manganese": ["manganese"],
    "gallium": ["gallium"],
    "germanium": ["germanium"],
    "copper": ["copper"],
    "tungsten": ["tungsten"],
}

COUNTRY_KEYWORDS: Dict[str, Sequence[str]] = {
    "united_states": ["united states", "u.s.", "us"],
    "china": ["china", "prc"],
    "canada": ["canada"],
    "australia": ["australia"],
    "chile": ["chile"],
    "argentina": ["argentina"],
    "congo_drc": ["drc", "democratic republic of congo", "congo"],
    "indonesia": ["indonesia"],
    "eu": ["european union", "eu"],
}

POLICY_SIGNALS: Dict[str, Sequence[str]] = {
    "export_ban": ["export ban", "ban exports", "shipment ban"],
    "export_quota": ["export quota", "quota"],
    "export_license": ["export license", "licensing requirement"],
    "tariff": ["tariff", "duty"],
    "sanctions": ["sanction", "embargo"],
    "subsidy": ["subsidy", "tax credit", "incentive"],
    "investment": ["investment", "financing", "grant", "loan"],
    "mine_permitting": ["permit", "permitting", "environmental review"],
}

BLOG_DOMAIN_HINTS = (
    "blog",
    "substack",
    "medium.com",
    "wordpress",
    "ghost.io",
)

USER_AGENT = "Mozilla/5.0 (compatible; ScienceClawMineralsNews/1.0; +https://github.com/lamm-mit/scienceclaw)"


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str


def _unwrap_ddg_url(url: str) -> str:
    if "duckduckgo.com/l/" not in url:
        return url
    query = parse_qs(urlparse(url).query)
    return query.get("uddg", [url])[0]


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _extract_date(text: str) -> Optional[str]:
    if not text:
        return None
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)
    match = re.search(r"\b(20\d{2}/\d{2}/\d{2})\b", text)
    if match:
        return match.group(1).replace("/", "-")
    return None


def _tags_from_keywords(text: str, mapping: Dict[str, Sequence[str]]) -> List[str]:
    haystack = text.lower()
    tags = []
    for tag, keywords in mapping.items():
        if any(k in haystack for k in keywords):
            tags.append(tag)
    return tags


def _policy_signal(text: str) -> Optional[str]:
    haystack = text.lower()
    scores: List[Tuple[int, str]] = []
    for signal, keywords in POLICY_SIGNALS.items():
        score = sum(1 for k in keywords if k in haystack)
        if score > 0:
            scores.append((score, signal))
    if not scores:
        return None
    scores.sort(reverse=True)
    return scores[0][1]


def _confidence(commodity_tags: List[str], country_tags: List[str], policy_signal: Optional[str], source: str) -> float:
    score = 0.35
    if commodity_tags:
        score += min(0.25, 0.08 * len(commodity_tags))
    if country_tags:
        score += min(0.15, 0.05 * len(country_tags))
    if policy_signal:
        score += 0.2
    if source and source not in ("", "duckduckgo.com"):
        score += 0.05
    return round(min(score, 0.95), 2)


def _record_from_result(result: SearchResult) -> Dict[str, object]:
    text = f"{result.title} {result.snippet}"
    commodity_tags = _tags_from_keywords(text, COMMODITY_KEYWORDS)
    country_tags = _tags_from_keywords(text, COUNTRY_KEYWORDS)
    policy_signal = _policy_signal(text)
    published_at = _extract_date(text)

    return {
        "url": result.url,
        "source": result.source,
        "published_at": published_at,
        "title": result.title,
        "summary": result.snippet,
        "commodity_tags": commodity_tags,
        "country_tags": country_tags,
        "policy_signal": policy_signal,
        "confidence": _confidence(commodity_tags, country_tags, policy_signal, result.source),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "blog" if any(h in result.source for h in BLOG_DOMAIN_HINTS) else "news",
    }


def search_duckduckgo(query: str, max_results: int = 20) -> List[SearchResult]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Search error for '{query}': {exc}", file=sys.stderr)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results: List[SearchResult] = []

    for block in soup.select(".result"):
        if len(results) >= max_results:
            break
        title_link = block.select_one(".result__title a")
        snippet_elem = block.select_one(".result__snippet")
        if not title_link:
            continue

        href = _unwrap_ddg_url(title_link.get("href", ""))
        source = _domain(href)
        if not href.startswith("http"):
            continue

        results.append(
            SearchResult(
                title=title_link.get_text(" ", strip=True),
                url=href,
                snippet=snippet_elem.get_text(" ", strip=True) if snippet_elem else "",
                source=source,
            )
        )

    return results


def build_query(base_query: str, commodities: List[str], countries: List[str]) -> str:
    terms = [base_query.strip() or "critical minerals"]
    if commodities:
        terms.append("(" + " OR ".join(commodities) + ")")
    if countries:
        terms.append("(" + " OR ".join(countries) + ")")
    terms.append("(news OR analysis OR market OR policy OR supply chain)")
    return " ".join(terms)


def monitor_news(base_query: str, commodities: List[str], countries: List[str], max_results: int, source_type: str) -> List[Dict[str, object]]:
    query = build_query(base_query, commodities, countries)
    raw_results = search_duckduckgo(query, max_results=max_results * 2)

    seen = set()
    records: List[Dict[str, object]] = []
    for res in raw_results:
        if res.url in seen:
            continue
        seen.add(res.url)
        record = _record_from_result(res)
        if source_type == "blogs" and record["source_type"] != "blog":
            continue
        if source_type == "news" and record["source_type"] != "news":
            continue
        records.append(record)
        if len(records) >= max_results:
            break
    return records


def format_summary(records: List[Dict[str, object]], query: str) -> str:
    if not records:
        return "No relevant news/blog records found."
    lines = [f"Critical minerals monitor query: {query}", f"Records: {len(records)}", "-" * 90]
    for i, r in enumerate(records, 1):
        lines.append(f"{i:>2}. [{r['source_type']}] {r['title']}")
        lines.append(f"    {r['source']} | policy={r['policy_signal'] or 'none'} | confidence={r['confidence']}")
        lines.append(f"    {r['url']}")
    return "\n".join(lines)


def format_detailed(records: List[Dict[str, object]]) -> str:
    if not records:
        return "No relevant records found."
    lines = []
    for i, r in enumerate(records, 1):
        lines.append("=" * 90)
        lines.append(f"Record #{i}")
        for key in (
            "title",
            "url",
            "source",
            "source_type",
            "published_at",
            "summary",
            "commodity_tags",
            "country_tags",
            "policy_signal",
            "confidence",
            "retrieved_at",
        ):
            lines.append(f"{key}: {r.get(key)}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monitor internet news/blog signals for critical minerals and materials.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "critical minerals" --max-results 15
  %(prog)s --commodity lithium --commodity cobalt --country china --country canada
  %(prog)s --query "battery materials" --source-type blogs --format json
        """,
    )
    parser.add_argument("--query", default="critical minerals", help="Base monitoring query")
    parser.add_argument("--commodity", action="append", default=[], help="Commodity term (repeatable)")
    parser.add_argument("--country", action="append", default=[], help="Country term (repeatable)")
    parser.add_argument("--max-results", type=int, default=20, help="Maximum records to return (default: 20)")
    parser.add_argument("--source-type", choices=["all", "news", "blogs"], default="all")
    parser.add_argument("--format", choices=["summary", "detailed", "json"], default="summary")
    args = parser.parse_args()

    records = monitor_news(
        base_query=args.query,
        commodities=args.commodity,
        countries=args.country,
        max_results=max(1, args.max_results),
        source_type=args.source_type,
    )

    if args.format == "json":
        print(json.dumps(records, indent=2))
    elif args.format == "detailed":
        print(format_detailed(records))
    else:
        full_query = build_query(args.query, args.commodity, args.country)
        print(format_summary(records, full_query))


if __name__ == "__main__":
    main()
