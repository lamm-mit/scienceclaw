#!/usr/bin/env python3
"""
Government release monitor for critical minerals and materials.

Performs domain-targeted discovery over government and regulator websites and
emits normalized records for policy intelligence workflows.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Dict, List, Sequence
from urllib.parse import parse_qs, quote_plus, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: requests and beautifulsoup4 are required.", file=sys.stderr)
    sys.exit(1)


DEFAULT_DOMAINS = [
    "usgs.gov",
    "energy.gov",
    "eia.gov",
    "doi.gov",
    "commerce.gov",
    "state.gov",
    "whitehouse.gov",
    "europa.eu",
    "gov.uk",
    "canada.ca",
    "ga.gov.au",
    "oecd.org",
]

COMMODITY_KEYWORDS: Dict[str, Sequence[str]] = {
    "lithium": ["lithium"],
    "cobalt": ["cobalt"],
    "nickel": ["nickel"],
    "graphite": ["graphite"],
    "rare_earth": ["rare earth", "ree", "lanthanide", "neodymium", "dysprosium"],
    "gallium": ["gallium"],
    "germanium": ["germanium"],
    "manganese": ["manganese"],
    "copper": ["copper"],
}

COUNTRY_KEYWORDS: Dict[str, Sequence[str]] = {
    "united_states": ["united states", "u.s.", "us"],
    "china": ["china"],
    "eu": ["european union", "eu"],
    "canada": ["canada"],
    "united_kingdom": ["united kingdom", "uk"],
    "australia": ["australia"],
}

POLICY_SIGNALS: Dict[str, Sequence[str]] = {
    "critical_minerals_strategy": ["critical minerals strategy", "critical raw materials act"],
    "export_control": ["export control", "export restriction", "export licensing", "quota"],
    "tariff_trade_remedy": ["tariff", "anti-dumping", "countervailing", "trade remedy"],
    "domestic_processing": ["refining", "processing", "value chain", "smelter"],
    "permitting": ["permit", "permitting", "environmental review"],
    "funding_support": ["grant", "loan", "tax credit", "funding", "incentive", "subsidy"],
}

USER_AGENT = "Mozilla/5.0 (compatible; ScienceClawGovMineralsMonitor/1.0; +https://github.com/lamm-mit/scienceclaw)"


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


def _tags(text: str, mapping: Dict[str, Sequence[str]]) -> List[str]:
    haystack = text.lower()
    out: List[str] = []
    for tag, terms in mapping.items():
        if any(t in haystack for t in terms):
            out.append(tag)
    return out


def _best_policy_signal(text: str) -> str:
    haystack = text.lower()
    best_signal = ""
    best_score = 0
    for signal, terms in POLICY_SIGNALS.items():
        score = sum(1 for t in terms if t in haystack)
        if score > best_score:
            best_signal = signal
            best_score = score
    return best_signal


def _confidence(commodity_tags: List[str], country_tags: List[str], policy_signal: str) -> float:
    score = 0.45
    if commodity_tags:
        score += min(0.2, 0.07 * len(commodity_tags))
    if country_tags:
        score += min(0.15, 0.05 * len(country_tags))
    if policy_signal:
        score += 0.15
    return round(min(score, 0.97), 2)


def _search(query: str, max_results: int) -> List[Dict[str, str]]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Search error: {exc}", file=sys.stderr)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    rows: List[Dict[str, str]] = []
    for block in soup.select(".result"):
        if len(rows) >= max_results:
            break
        link = block.select_one(".result__title a")
        snippet = block.select_one(".result__snippet")
        if not link:
            continue
        final_url = _unwrap_ddg_url(link.get("href", ""))
        if not final_url.startswith("http"):
            continue
        rows.append(
            {
                "title": link.get_text(" ", strip=True),
                "url": final_url,
                "summary": snippet.get_text(" ", strip=True) if snippet else "",
                "source": _domain(final_url),
            }
        )
    return rows


def monitor(domains: List[str], commodity_terms: List[str], country_terms: List[str], max_results: int) -> List[Dict[str, object]]:
    queries = []
    commodity_clause = " OR ".join(commodity_terms) if commodity_terms else "critical minerals OR battery materials"
    country_clause = f"({' OR '.join(country_terms)})" if country_terms else ""

    for domain in domains:
        q = f"site:{domain} ({commodity_clause}) (press release OR announcement OR policy OR strategy OR guidance) {country_clause}".strip()
        queries.append((domain, q))

    out: List[Dict[str, object]] = []
    seen = set()
    per_domain_budget = max(1, max_results // max(1, len(domains)))

    for domain, q in queries:
        hits = _search(q, max_results=per_domain_budget * 2)
        for hit in hits:
            if hit["url"] in seen:
                continue
            seen.add(hit["url"])
            text = f"{hit['title']} {hit['summary']}"
            commodity_tags = _tags(text, COMMODITY_KEYWORDS)
            country_tags = _tags(text, COUNTRY_KEYWORDS)
            policy_signal = _best_policy_signal(text)
            record = {
                "url": hit["url"],
                "source": hit["source"],
                "published_at": None,
                "title": hit["title"],
                "summary": hit["summary"],
                "commodity_tags": commodity_tags,
                "country_tags": country_tags,
                "policy_signal": policy_signal or None,
                "confidence": _confidence(commodity_tags, country_tags, policy_signal),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "source_type": "government",
                "monitor_domain": domain,
            }
            out.append(record)
            if len(out) >= max_results:
                return out

    return out


def format_summary(records: List[Dict[str, object]]) -> str:
    if not records:
        return "No government releases found."
    lines = [f"Government monitor records: {len(records)}", "-" * 90]
    for idx, rec in enumerate(records, 1):
        lines.append(f"{idx:>2}. {rec['title']}")
        lines.append(f"    source={rec['source']} policy={rec['policy_signal'] or 'none'} confidence={rec['confidence']}")
        lines.append(f"    {rec['url']}")
    return "\n".join(lines)


def format_detailed(records: List[Dict[str, object]]) -> str:
    if not records:
        return "No government records found."
    lines: List[str] = []
    for idx, rec in enumerate(records, 1):
        lines.append("=" * 90)
        lines.append(f"Record #{idx}")
        for key in (
            "title",
            "url",
            "source",
            "monitor_domain",
            "summary",
            "commodity_tags",
            "country_tags",
            "policy_signal",
            "confidence",
            "retrieved_at",
        ):
            lines.append(f"{key}: {rec.get(key)}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monitor government releases relevant to critical minerals and materials.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --commodity lithium --commodity cobalt
  %(prog)s --domains usgs.gov,energy.gov,europa.eu --country united states --country china
  %(prog)s --format json --max-results 30
        """,
    )
    parser.add_argument("--domains", default=",".join(DEFAULT_DOMAINS), help="Comma-separated domain allowlist")
    parser.add_argument("--commodity", action="append", default=[], help="Commodity term (repeatable)")
    parser.add_argument("--country", action="append", default=[], help="Country term (repeatable)")
    parser.add_argument("--max-results", type=int, default=25, help="Maximum records (default: 25)")
    parser.add_argument("--format", choices=["summary", "detailed", "json"], default="summary")
    args = parser.parse_args()

    domains = [d.strip().lower() for d in args.domains.split(",") if d.strip()]
    records = monitor(domains, args.commodity, args.country, max(1, args.max_results))

    if args.format == "json":
        print(json.dumps(records, indent=2))
    elif args.format == "detailed":
        print(format_detailed(records))
    else:
        print(format_summary(records))


if __name__ == "__main__":
    main()
