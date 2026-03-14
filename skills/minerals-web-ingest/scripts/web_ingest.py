#!/usr/bin/env python3
"""
Critical minerals web ingestion pipeline.

Ingests URLs from monitors or direct input, fetches page content (Firecrawl when
available, requests/BeautifulSoup fallback), and outputs normalized records for
storage, indexing, and downstream analysis.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: requests and beautifulsoup4 are required.", file=sys.stderr)
    sys.exit(1)


FIRECRAWL_API_BASE = "https://api.firecrawl.dev/v1"
DEFAULT_MANIFEST = Path.home() / ".scienceclaw" / "minerals_web_ingest_manifest.json"

COMMODITY_KEYWORDS: Dict[str, Sequence[str]] = {
    "lithium": ["lithium", "lce"],
    "cobalt": ["cobalt"],
    "nickel": ["nickel"],
    "graphite": ["graphite"],
    "rare_earth": ["rare earth", "ree", "lanthanide", "neodymium", "dysprosium"],
    "manganese": ["manganese"],
    "gallium": ["gallium"],
    "germanium": ["germanium"],
    "copper": ["copper"],
    "tungsten": ["tungsten"],
}

COUNTRY_KEYWORDS: Dict[str, Sequence[str]] = {
    "united_states": ["united states", "u.s.", "us"],
    "china": ["china"],
    "canada": ["canada"],
    "australia": ["australia"],
    "eu": ["european union", "eu"],
    "argentina": ["argentina"],
    "chile": ["chile"],
    "congo_drc": ["drc", "democratic republic of congo", "congo"],
    "indonesia": ["indonesia"],
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


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _tags(text: str, mapping: Dict[str, Sequence[str]]) -> List[str]:
    haystack = text.lower()
    out = []
    for tag, kws in mapping.items():
        if any(k in haystack for k in kws):
            out.append(tag)
    return out


def _policy_signal(text: str) -> Optional[str]:
    haystack = text.lower()
    best = (0, None)
    for signal, kws in POLICY_SIGNALS.items():
        score = sum(1 for k in kws if k in haystack)
        if score > best[0]:
            best = (score, signal)
    return best[1]


def _extract_date(text: str) -> Optional[str]:
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)
    match = re.search(r"\b(20\d{2}/\d{2}/\d{2})\b", text)
    if match:
        return match.group(1).replace("/", "-")
    return None


def _estimate_confidence(commodity_tags: List[str], country_tags: List[str], policy_signal: Optional[str], content_len: int) -> float:
    score = 0.4
    if commodity_tags:
        score += min(0.2, 0.06 * len(commodity_tags))
    if country_tags:
        score += min(0.15, 0.05 * len(country_tags))
    if policy_signal:
        score += 0.15
    if content_len > 1200:
        score += 0.05
    return round(min(score, 0.98), 2)


def _load_manifest(path: Path) -> Dict[str, str]:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
    return {}


def _save_manifest(path: Path, manifest: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _firecrawl_fetch(url: str, api_key: str, timeout: int) -> Dict[str, object]:
    payload = {"url": url, "formats": ["markdown"]}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(f"{FIRECRAWL_API_BASE}/scrape", headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success"):
        raise RuntimeError(body.get("error", "Firecrawl scrape failed"))

    data = body.get("data", {})
    meta = data.get("metadata", {})
    content = data.get("markdown", "") or ""

    return {
        "title": meta.get("title", ""),
        "content": content,
        "published_at": meta.get("publishedTime") or meta.get("publishedDate"),
    }


def _fallback_fetch(url: str, timeout: int) -> Dict[str, object]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ScienceClawMineralsIngest/1.0; +https://github.com/lamm-mit/scienceclaw)"
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""

    for bad in soup(["script", "style", "noscript"]):
        bad.extract()
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()

    return {
        "title": title,
        "content": text,
        "published_at": None,
    }


def _fetch_url(url: str, timeout: int, prefer_firecrawl: bool, firecrawl_api_key: str) -> Dict[str, object]:
    if prefer_firecrawl and firecrawl_api_key:
        try:
            return _firecrawl_fetch(url, firecrawl_api_key, timeout)
        except Exception as exc:
            print(f"Warning: Firecrawl failed for {url}: {exc}; falling back to requests.", file=sys.stderr)
    return _fallback_fetch(url, timeout)


def _iter_input_records(input_json: Optional[str], direct_urls: List[str]) -> Iterable[Dict[str, object]]:
    for url in direct_urls:
        yield {"url": url}

    if not input_json:
        return

    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        for rec in data:
            if isinstance(rec, dict) and rec.get("url"):
                yield rec
    elif isinstance(data, dict):
        if isinstance(data.get("records"), list):
            for rec in data["records"]:
                if isinstance(rec, dict) and rec.get("url"):
                    yield rec
        elif data.get("url"):
            yield data


def ingest(input_json: Optional[str], direct_urls: List[str], manifest_path: Path, timeout: int, prefer_firecrawl: bool, firecrawl_api_key: str, max_chars: int) -> Dict[str, object]:
    manifest = _load_manifest(manifest_path)
    ingested: List[Dict[str, object]] = []
    skipped: List[str] = []
    errors: List[Dict[str, str]] = []

    seen_urls = set()
    for rec in _iter_input_records(input_json, direct_urls):
        url = str(rec.get("url", "")).strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        try:
            fetched = _fetch_url(url, timeout=timeout, prefer_firecrawl=prefer_firecrawl, firecrawl_api_key=firecrawl_api_key)
            raw_content = str(fetched.get("content", ""))
            content = raw_content[:max_chars] if max_chars > 0 else raw_content
            content_hash = _hash_text(content)

            if manifest.get(url) == content_hash:
                skipped.append(url)
                continue

            title = str(rec.get("title") or fetched.get("title") or "").strip()
            summary = str(rec.get("summary") or "").strip() or content[:320]

            text_for_tags = f"{title} {summary} {content[:4000]}"
            commodity_tags = sorted(set((rec.get("commodity_tags") or []) + _tags(text_for_tags, COMMODITY_KEYWORDS)))
            country_tags = sorted(set((rec.get("country_tags") or []) + _tags(text_for_tags, COUNTRY_KEYWORDS)))
            policy_signal = rec.get("policy_signal") or _policy_signal(text_for_tags)

            published_at = rec.get("published_at") or fetched.get("published_at") or _extract_date(text_for_tags)
            source = rec.get("source") or _domain(url)

            out_rec = {
                "url": url,
                "source": source,
                "published_at": published_at,
                "title": title,
                "summary": summary,
                "commodity_tags": commodity_tags,
                "country_tags": country_tags,
                "policy_signal": policy_signal,
                "confidence": _estimate_confidence(commodity_tags, country_tags, policy_signal, len(content)),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "source_type": rec.get("source_type") or ("government" if any(k in source for k in (".gov", "europa.eu", "gov.uk", "canada.ca")) else "web"),
                "content": content,
                "content_hash": content_hash,
            }

            ingested.append(out_rec)
            manifest[url] = content_hash
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})

    _save_manifest(manifest_path, manifest)

    return {
        "ingested": ingested,
        "skipped": skipped,
        "errors": errors,
        "stats": {
            "input_urls": len(seen_urls),
            "ingested": len(ingested),
            "skipped": len(skipped),
            "errors": len(errors),
            "manifest_path": str(manifest_path),
        },
    }


def format_summary(result: Dict[str, object]) -> str:
    stats = result["stats"]
    lines = [
        "Minerals web ingest complete",
        f"input_urls={stats['input_urls']} ingested={stats['ingested']} skipped={stats['skipped']} errors={stats['errors']}",
        "-" * 90,
    ]

    for idx, rec in enumerate(result.get("ingested", [])[:20], 1):
        lines.append(f"{idx:>2}. {rec.get('title') or rec.get('url')}")
        lines.append(f"    source={rec.get('source')} policy={rec.get('policy_signal') or 'none'} confidence={rec.get('confidence')}")

    if result.get("errors"):
        lines.append("\nErrors:")
        for err in result["errors"][:10]:
            lines.append(f"- {err['url']}: {err['error']}")

    return "\n".join(lines)


def format_detailed(result: Dict[str, object]) -> str:
    lines = [json.dumps(result.get("stats", {}), indent=2), ""]
    for idx, rec in enumerate(result.get("ingested", []), 1):
        lines.append("=" * 90)
        lines.append(f"Record #{idx}")
        for key in (
            "title",
            "url",
            "source",
            "published_at",
            "commodity_tags",
            "country_tags",
            "policy_signal",
            "confidence",
            "content_hash",
            "summary",
        ):
            lines.append(f"{key}: {rec.get(key)}")
    if result.get("errors"):
        lines.append("\nErrors:")
        lines.append(json.dumps(result["errors"], indent=2))
    return "\n".join(lines)


def write_jsonl(path: str, records: List[Dict[str, object]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest and normalize web content for critical minerals intelligence.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input-json monitor_results.json --output-jsonl ingest.jsonl
  %(prog)s --url https://www.energy.gov/articles/example --url https://www.usgs.gov/news/example
  %(prog)s --input-json gov_records.json --prefer-firecrawl --format json
        """,
    )
    parser.add_argument("--input-json", help="Path to JSON list/object containing URL records")
    parser.add_argument("--url", action="append", default=[], help="Direct URL input (repeatable)")
    parser.add_argument("--output-jsonl", help="Optional JSONL output path for ingested records")
    parser.add_argument("--manifest-path", default=str(DEFAULT_MANIFEST), help=f"Manifest path (default: {DEFAULT_MANIFEST})")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds (default: 30)")
    parser.add_argument("--max-chars", type=int, default=12000, help="Max characters stored per page (default: 12000)")
    parser.add_argument("--prefer-firecrawl", action="store_true", help="Use Firecrawl first when FIRECRAWL_API_KEY is set")
    parser.add_argument("--format", choices=["summary", "detailed", "json"], default="summary")
    args = parser.parse_args()

    if not args.input_json and not args.url:
        parser.error("Provide at least one --url or --input-json")

    firecrawl_key = os.environ.get("FIRECRAWL_API_KEY", "")
    result = ingest(
        input_json=args.input_json,
        direct_urls=args.url,
        manifest_path=Path(args.manifest_path),
        timeout=max(5, args.timeout),
        prefer_firecrawl=bool(args.prefer_firecrawl),
        firecrawl_api_key=firecrawl_key,
        max_chars=max(500, args.max_chars),
    )

    if args.output_jsonl:
        write_jsonl(args.output_jsonl, result.get("ingested", []))

    if args.format == "json":
        print(json.dumps(result, indent=2))
    elif args.format == "detailed":
        print(format_detailed(result))
    else:
        print(format_summary(result))


if __name__ == "__main__":
    main()
