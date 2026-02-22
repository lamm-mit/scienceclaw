#!/usr/bin/env python3
"""
Literature Meta-Search Tool for ScienceClaw

Unified search across OSTI, Google Scholar, ArXiv, and corpus-search
with deduplication and reciprocal rank fusion ranking.
"""

import argparse
import json
import os
import subprocess
import sys
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

SKILLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCIENCECLAW_SKILLS = os.path.dirname(SKILLS_DIR)


def _run_skill_script(script_path: str, args: List[str]) -> Optional[List[Dict]]:
    """Run a skill script and parse JSON output."""
    cmd = ["python3", script_path] + args + ["--format", "json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"  Warning: {os.path.basename(script_path)} failed: {result.stderr[:200]}", file=sys.stderr)
            return None
        output = result.stdout.strip()
        if not output:
            return []
        return json.loads(output)
    except subprocess.TimeoutExpired:
        print(f"  Warning: {os.path.basename(script_path)} timed out", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"  Warning: Could not parse output from {os.path.basename(script_path)}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Warning: Error running {os.path.basename(script_path)}: {e}", file=sys.stderr)
        return None


def search_osti(query: str, year_from: Optional[int] = None, year_to: Optional[int] = None) -> List[Dict]:
    """Search OSTI via skill script."""
    script = os.path.join(SCIENCECLAW_SKILLS, "osti-database", "scripts", "osti_search.py")
    if not os.path.exists(script):
        return []

    args = ["--query", query, "--limit", "15"]
    if year_from:
        args.extend(["--year-from", str(year_from)])
    if year_to:
        args.extend(["--year-to", str(year_to)])

    results = _run_skill_script(script, args)
    if results is None:
        return []

    normalized = []
    for r in results:
        normalized.append({
            "title": r.get("title", ""),
            "authors": ", ".join(r.get("authors", [])) if isinstance(r.get("authors"), list) else r.get("authors", ""),
            "year": r.get("publication_date", "")[:4],
            "source": "osti",
            "url": r.get("url", ""),
            "snippet": (r.get("description") or "")[:300],
            "citations": 0,
            "id": r.get("id", ""),
        })
    return normalized


def search_scholar(query: str, year_from: Optional[int] = None, year_to: Optional[int] = None) -> List[Dict]:
    """Search Google Scholar via skill script."""
    script = os.path.join(SCIENCECLAW_SKILLS, "scholar-search", "scripts", "scholar_search.py")
    if not os.path.exists(script):
        return []

    args = ["--query", query, "--num-results", "15"]
    if year_from:
        args.extend(["--year-from", str(year_from)])
    if year_to:
        args.extend(["--year-to", str(year_to)])

    results = _run_skill_script(script, args)
    if results is None:
        return []

    normalized = []
    for r in results:
        normalized.append({
            "title": r.get("title", ""),
            "authors": r.get("authors", ""),
            "year": r.get("year", ""),
            "source": "scholar",
            "url": r.get("url", ""),
            "snippet": r.get("snippet", ""),
            "citations": r.get("citations", 0),
            "id": "",
        })
    return normalized


def search_arxiv(query: str, year_from: Optional[int] = None, year_to: Optional[int] = None) -> List[Dict]:
    """Search ArXiv via API directly."""
    try:
        import httpx
        import xml.etree.ElementTree as ET
    except ImportError:
        print("  Warning: httpx required for ArXiv search", file=sys.stderr)
        return []

    ARXIV_API = "https://export.arxiv.org/api/query"
    NS = {"atom": "http://www.w3.org/2005/Atom"}

    params = {"search_query": f"all:{query}", "max_results": "15", "sortBy": "relevance"}

    try:
        response = httpx.get(ARXIV_API, params=params, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"  Warning: ArXiv request failed: {e}", file=sys.stderr)
        return []

    root = ET.fromstring(response.text)
    entries = root.findall("atom:entry", NS)

    results = []
    for entry in entries:
        title = entry.find("atom:title", NS)
        title_text = title.text.strip().replace("\n", " ") if title is not None else ""

        published = entry.find("atom:published", NS)
        pub_year = published.text[:4] if published is not None else ""

        # Filter by year
        if year_from and pub_year and int(pub_year) < year_from:
            continue
        if year_to and pub_year and int(pub_year) > year_to:
            continue

        authors = entry.findall("atom:author/atom:name", NS)
        author_str = ", ".join(a.text for a in authors[:5]) if authors else ""

        summary = entry.find("atom:summary", NS)
        snippet = summary.text.strip()[:300] if summary is not None else ""

        link = entry.find("atom:id", NS)
        url = link.text if link is not None else ""

        arxiv_id = url.split("/abs/")[-1] if "/abs/" in url else ""

        results.append({
            "title": title_text,
            "authors": author_str,
            "year": pub_year,
            "source": "arxiv",
            "url": url,
            "snippet": snippet,
            "citations": 0,
            "id": arxiv_id,
        })

    return results


def search_corpus(query: str) -> List[Dict]:
    """Search local corpus via skill script."""
    script = os.path.join(SCIENCECLAW_SKILLS, "corpus-search", "scripts", "search_corpus.py")
    if not os.path.exists(script):
        return []

    args = ["--query", query, "--top-k", "10"]
    results = _run_skill_script(script, args)
    if results is None:
        return []

    normalized = []
    for r in results:
        normalized.append({
            "title": r.get("title", r.get("source_file", "")),
            "authors": "",
            "year": "",
            "source": "corpus",
            "url": "",
            "snippet": r.get("text", r.get("chunk", ""))[:300],
            "citations": 0,
            "id": r.get("id", ""),
            "score": r.get("score", 0),
            "in_corpus": True,
        })
    return normalized


def deduplicate(results: List[Dict], threshold: float = 0.8) -> List[Dict]:
    """Deduplicate results by fuzzy title matching."""
    unique = []
    seen_titles = []

    for r in results:
        title = r.get("title", "").lower().strip()
        if not title:
            unique.append(r)
            continue

        is_dup = False
        for seen in seen_titles:
            similarity = SequenceMatcher(None, title, seen).ratio()
            if similarity > threshold:
                is_dup = True
                break

        if not is_dup:
            seen_titles.append(title)
            unique.append(r)

    return unique


def reciprocal_rank_fusion(source_results: Dict[str, List[Dict]], k: int = 60) -> List[Dict]:
    """Merge results using reciprocal rank fusion."""
    scores: Dict[str, float] = {}  # title -> RRF score
    result_map: Dict[str, Dict] = {}  # title -> best result dict

    for source, results in source_results.items():
        for rank, r in enumerate(results):
            title_key = r.get("title", "").lower().strip()
            if not title_key:
                continue

            rrf_score = 1.0 / (k + rank + 1)

            if title_key in scores:
                scores[title_key] += rrf_score
                # Keep the result with more info
                existing = result_map[title_key]
                if len(r.get("snippet", "")) > len(existing.get("snippet", "")):
                    r["_rrf_score"] = scores[title_key]
                    # Merge source info
                    existing_sources = existing.get("sources", [existing.get("source", "")])
                    if source not in existing_sources:
                        existing_sources.append(source)
                    r["sources"] = existing_sources
                    result_map[title_key] = r
                else:
                    existing_sources = existing.get("sources", [existing.get("source", "")])
                    if source not in existing_sources:
                        existing_sources.append(source)
                    existing["sources"] = existing_sources
                    existing["_rrf_score"] = scores[title_key]
            else:
                scores[title_key] = rrf_score
                r["_rrf_score"] = rrf_score
                r["sources"] = [source]
                result_map[title_key] = r

    # Sort by RRF score
    merged = sorted(result_map.values(), key=lambda x: x.get("_rrf_score", 0), reverse=True)
    return merged


def mark_in_corpus(results: List[Dict], corpus_titles: set) -> List[Dict]:
    """Mark which results are in the local corpus."""
    for r in results:
        if r.get("in_corpus"):
            continue
        title = r.get("title", "").lower().strip()
        r["in_corpus"] = any(
            SequenceMatcher(None, title, ct).ratio() > 0.8
            for ct in corpus_titles
        )
    return results


def format_summary(results: List[Dict]) -> str:
    """Format results as summary."""
    if not results:
        return "No results found."

    lines = [f"\nMeta-search results ({len(results)} papers):\n"]
    lines.append("-" * 85)

    for i, r in enumerate(results, 1):
        sources = ", ".join(r.get("sources", [r.get("source", "?")]))
        corpus_flag = " [IN CORPUS]" if r.get("in_corpus") else ""
        citations_str = f" [{r['citations']} cit.]" if r.get("citations") else ""

        lines.append(f"\n{i}. {r['title']}")
        lines.append(f"   {r.get('authors', 'Unknown')[:80]}")
        lines.append(f"   ({r.get('year', '?')}) Sources: {sources}{citations_str}{corpus_flag}")

    lines.append("\n" + "-" * 85)
    return "\n".join(lines)


def format_detailed(results: List[Dict]) -> str:
    """Format results with full details."""
    if not results:
        return "No results found."

    lines = []
    for i, r in enumerate(results, 1):
        lines.append("=" * 80)
        lines.append(f"Result #{i}")
        lines.append("=" * 80)
        lines.append(f"Title: {r['title']}")
        lines.append(f"Authors: {r.get('authors', 'Unknown')}")
        lines.append(f"Year: {r.get('year', 'Unknown')}")
        sources = ", ".join(r.get("sources", [r.get("source", "?")]))
        lines.append(f"Sources: {sources}")
        if r.get("citations"):
            lines.append(f"Citations: {r['citations']}")
        lines.append(f"In Corpus: {'Yes' if r.get('in_corpus') else 'No'}")
        if r.get("url"):
            lines.append(f"URL: {r['url']}")
        if r.get("snippet"):
            lines.append(f"\nSnippet: {r['snippet'][:400]}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Unified literature search across OSTI, Scholar, ArXiv, and corpus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sources: osti, scholar, arxiv, corpus

Examples:
  %(prog)s --query "lithium extraction brine"
  %(prog)s --query "rare earth separation" --sources osti,scholar
  %(prog)s --query "cobalt supply chain" --year-from 2020 --format json
        """
    )

    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument(
        "--sources", "-s",
        default="osti,scholar,arxiv,corpus",
        help="Comma-separated sources (default: osti,scholar,arxiv,corpus)"
    )
    parser.add_argument("--year-from", type=int, help="Start year")
    parser.add_argument("--year-to", type=int, help="End year")
    parser.add_argument("--top-n", "-n", type=int, default=15, help="Number of results (default: 15)")
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",")]
    source_results = {}
    corpus_titles = set()

    print(f"Meta-search: {args.query}", file=sys.stderr)
    print(f"Sources: {', '.join(sources)}", file=sys.stderr)
    print("", file=sys.stderr)

    # Search each source
    if "osti" in sources:
        print("  Searching OSTI...", file=sys.stderr)
        source_results["osti"] = search_osti(args.query, args.year_from, args.year_to)
        print(f"  OSTI: {len(source_results['osti'])} results", file=sys.stderr)

    if "scholar" in sources:
        print("  Searching Google Scholar...", file=sys.stderr)
        source_results["scholar"] = search_scholar(args.query, args.year_from, args.year_to)
        print(f"  Scholar: {len(source_results['scholar'])} results", file=sys.stderr)

    if "arxiv" in sources:
        print("  Searching ArXiv...", file=sys.stderr)
        source_results["arxiv"] = search_arxiv(args.query, args.year_from, args.year_to)
        print(f"  ArXiv: {len(source_results['arxiv'])} results", file=sys.stderr)

    if "corpus" in sources:
        print("  Searching local corpus...", file=sys.stderr)
        corpus_results = search_corpus(args.query)
        source_results["corpus"] = corpus_results
        corpus_titles = {r.get("title", "").lower().strip() for r in corpus_results if r.get("title")}
        print(f"  Corpus: {len(source_results['corpus'])} results", file=sys.stderr)

    print("", file=sys.stderr)

    # Merge with RRF
    merged = reciprocal_rank_fusion(source_results)

    # Deduplicate
    merged = deduplicate(merged)

    # Mark corpus membership
    if corpus_titles:
        merged = mark_in_corpus(merged, corpus_titles)

    # Trim to top-n
    merged = merged[:args.top_n]

    # Clean internal fields for output
    for r in merged:
        r.pop("_rrf_score", None)
        r.pop("score", None)

    total = sum(len(v) for v in source_results.values())
    print(f"Total: {total} results -> {len(merged)} after merge/dedup", file=sys.stderr)

    if args.format == "json":
        print(json.dumps(merged, indent=2))
    elif args.format == "detailed":
        print(format_detailed(merged))
    else:
        print(format_summary(merged))


if __name__ == "__main__":
    main()
