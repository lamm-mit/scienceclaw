#!/usr/bin/env python3
"""
Export Restrictions Query Tool for ScienceClaw

Query OECD export restriction policies on critical raw materials.
Combines OECD Supply Chain metadata with corpus-search for policy text.
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

try:
    sys.path.insert(0, "/Users/nancywashton/cmm-data/src")
    from cmm_data.loaders.oecd_supply import OECDSupplyChainLoader
except ImportError:
    OECDSupplyChainLoader = None

SKILLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCIENCECLAW_SKILLS = os.path.dirname(SKILLS_DIR)


def get_oecd_metadata() -> Dict[str, Any]:
    """Get OECD export restriction metadata."""
    if OECDSupplyChainLoader is None:
        return {"error": "cmm_data package not available"}

    try:
        loader = OECDSupplyChainLoader()
        coverage = loader.get_minerals_coverage()
        available = loader.list_available()

        result = {
            "available_datasets": available,
            "coverage": coverage.get("export_restrictions", {}),
        }

        # Get file listing if export_restrictions is available
        if "export_restrictions" in available:
            df = loader.load("export_restrictions")
            result["files"] = df.to_dict("records")
            result["file_count"] = len(df)
        else:
            result["files"] = []
            result["file_count"] = 0

        return result

    except Exception as e:
        return {"error": str(e)}


def search_corpus_for_restrictions(
    commodity: Optional[str] = None,
    country: Optional[str] = None,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search local corpus for export restriction policy text."""
    script = os.path.join(SCIENCECLAW_SKILLS, "corpus-search", "scripts", "search_corpus.py")
    if not os.path.exists(script):
        print("  Warning: corpus-search skill not found", file=sys.stderr)
        return []

    # Build search query
    search_terms = []
    if query:
        search_terms.append(query)
    else:
        search_terms.append("export restriction")
        if commodity:
            search_terms.append(commodity)
        if country:
            search_terms.append(country)

    search_query = " ".join(search_terms)

    cmd = ["python3", script, "--query", search_query, "--format", "json", "--top-k", "10"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"  Warning: corpus search failed: {result.stderr[:200]}", file=sys.stderr)
            return []
        output = result.stdout.strip()
        if not output:
            return []
        return json.loads(output)
    except Exception as e:
        print(f"  Warning: corpus search error: {e}", file=sys.stderr)
        return []


def query_restrictions(
    commodity: Optional[str] = None,
    country: Optional[str] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """Query export restrictions combining OECD metadata and corpus search."""
    result = {
        "commodity": commodity,
        "country": country,
        "query": query,
    }

    # Get OECD metadata
    print("Querying OECD export restriction metadata...", file=sys.stderr)
    oecd_data = get_oecd_metadata()

    if oecd_data.get("error"):
        result["oecd_metadata"] = {"error": oecd_data["error"]}
    else:
        result["oecd_metadata"] = {
            "coverage": oecd_data.get("coverage", {}),
            "file_count": oecd_data.get("file_count", 0),
        }

        # Filter files by commodity/country if provided
        files = oecd_data.get("files", [])
        if commodity or country:
            filtered = []
            for f in files:
                filename_lower = f.get("filename", "").lower()
                path_lower = f.get("path", "").lower()
                combined = filename_lower + " " + path_lower

                if commodity and commodity.lower() not in combined:
                    continue
                if country and country.lower() not in combined:
                    continue
                filtered.append(f)
            result["oecd_metadata"]["matching_files"] = filtered
        else:
            result["oecd_metadata"]["matching_files"] = files[:20]

    # Search corpus for policy text
    print("Searching corpus for policy documents...", file=sys.stderr)
    corpus_results = search_corpus_for_restrictions(commodity, country, query)

    result["corpus_results"] = []
    for r in corpus_results:
        result["corpus_results"].append({
            "title": r.get("title", r.get("source_file", "")),
            "text": r.get("text", r.get("chunk", ""))[:500],
            "score": r.get("score", 0),
            "source": r.get("source_org", ""),
            "commodity": r.get("commodity", ""),
        })

    result["total_corpus_hits"] = len(corpus_results)

    print(f"Found {len(result.get('oecd_metadata', {}).get('matching_files', []))} OECD files", file=sys.stderr)
    print(f"Found {len(corpus_results)} corpus matches", file=sys.stderr)

    return result


def format_summary(result: Dict[str, Any]) -> str:
    """Format restrictions as summary."""
    lines = []
    lines.append("=" * 70)
    title_parts = ["Export Restrictions"]
    if result.get("commodity"):
        title_parts.append(f"Commodity: {result['commodity']}")
    if result.get("country"):
        title_parts.append(f"Country: {result['country']}")
    lines.append(" | ".join(title_parts))
    lines.append("=" * 70)

    # OECD metadata
    oecd = result.get("oecd_metadata", {})
    if oecd.get("error"):
        lines.append(f"\nOECD Data: {oecd['error']}")
    else:
        coverage = oecd.get("coverage", {})
        lines.append(f"\nOECD Coverage: {coverage.get('commodities', '?')} commodities, "
                     f"{coverage.get('countries', '?')} countries, {coverage.get('years', '?')}")
        lines.append(f"Matching files: {len(oecd.get('matching_files', []))}")

        for f in oecd.get("matching_files", [])[:10]:
            lines.append(f"  - {f.get('filename', '')} ({f.get('size_mb', 0):.1f} MB)")

    # Corpus results
    corpus = result.get("corpus_results", [])
    if corpus:
        lines.append(f"\nCorpus matches ({len(corpus)}):")
        for i, r in enumerate(corpus[:5], 1):
            title = r.get("title", "Unknown")
            text = r.get("text", "")[:150]
            lines.append(f"\n  {i}. {title}")
            lines.append(f"     {text}...")
    else:
        lines.append("\nNo corpus matches found.")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Query OECD export restriction policies on raw materials",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --commodity "lithium"
  %(prog)s --country "China" --commodity "rare earths"
  %(prog)s --query "export quota critical minerals"
  %(prog)s --commodity "cobalt" --format json
        """
    )

    parser.add_argument("--commodity", "-c", help="Commodity name")
    parser.add_argument("--country", help="Country name")
    parser.add_argument("--query", "-q", help="Free-text policy search")
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    if not args.commodity and not args.country and not args.query:
        parser.error("At least one of --commodity, --country, or --query is required")

    result = query_restrictions(
        commodity=args.commodity,
        country=args.country,
        query=args.query,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2, default=str))
    elif args.format == "detailed":
        # Detailed is same as summary but with more corpus text
        for r in result.get("corpus_results", []):
            r["text"] = r.get("text", "")  # Don't truncate
        print(format_summary(result))
    else:
        print(format_summary(result))


if __name__ == "__main__":
    main()
