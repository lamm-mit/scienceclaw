#!/usr/bin/env python3
"""
Semantic Search over Critical Minerals PDF Corpus

Queries a Pinecone index containing chunked PDF documents from the
critical minerals corpus. Supports filtering by commodity and source
organization, optional reranking, and multiple output formats.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

try:
    from pinecone import Pinecone
except ImportError:
    print("Error: pinecone is required. Install with: pip install pinecone>=5.0.0", file=sys.stderr)
    sys.exit(1)


DEFAULT_INDEX = "scienceclaw-minerals-corpus"
DEFAULT_TOP_K = 10
RERANK_MODEL = "bge-reranker-v2-m3"


def build_filter(commodity: Optional[str] = None, source: Optional[str] = None) -> Optional[Dict]:
    """Build Pinecone metadata filter using MongoDB-style syntax."""
    conditions = []
    if commodity:
        conditions.append({"commodity": {"$eq": commodity.lower().replace(" ", "_")}})
    if source:
        # Case-insensitive matching via exact known values
        conditions.append({"source_org": {"$eq": source}})
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def search_corpus(
    query: str,
    index,
    namespace: str = "__default__",
    top_k: int = DEFAULT_TOP_K,
    commodity: Optional[str] = None,
    source: Optional[str] = None,
    rerank: bool = False,
) -> List[Dict[str, Any]]:
    """
    Search the corpus index.

    Args:
        query: Semantic search query
        index: Pinecone index object
        namespace: Pinecone namespace
        top_k: Number of results
        commodity: Filter by commodity
        source: Filter by source organization
        rerank: Whether to rerank results

    Returns:
        List of result dicts with text, metadata, and score
    """
    metadata_filter = build_filter(commodity, source)

    search_params: Dict[str, Any] = {
        "namespace": namespace,
        "query": {
            "inputs": {"text": query},
            "top_k": top_k * 2 if rerank else top_k,
        },
    }

    if metadata_filter:
        search_params["query"]["filter"] = metadata_filter

    if rerank:
        search_params["rerank"] = {
            "model": RERANK_MODEL,
            "rank_fields": ["text"],
            "top_n": top_k,
        }

    print(f"Searching corpus: \"{query}\"", file=sys.stderr)
    if commodity:
        print(f"  Commodity filter: {commodity}", file=sys.stderr)
    if source:
        print(f"  Source filter: {source}", file=sys.stderr)
    if rerank:
        print(f"  Reranking: {RERANK_MODEL} (topK={top_k*2} -> topN={top_k})", file=sys.stderr)
    print("", file=sys.stderr)

    try:
        response = index.search(**search_params)
    except Exception as e:
        print(f"Error searching index: {e}", file=sys.stderr)
        return []

    results = []
    hits = response.get("result", {}).get("hits", [])
    for hit in hits:
        fields = hit.get("fields", {})
        results.append({
            "id": hit.get("_id", ""),
            "score": hit.get("_score", 0),
            "text": fields.get("text", ""),
            "source_file": fields.get("source_file", ""),
            "source_org": fields.get("source_org", ""),
            "page_number": fields.get("page_number", 0),
            "chunk_index": fields.get("chunk_index", 0),
            "commodity": fields.get("commodity", ""),
        })

    print(f"Found {len(results)} results", file=sys.stderr)
    return results


def format_summary(results: List[Dict], query: str) -> str:
    """Format results as summary with citations and snippets."""
    if not results:
        return "No results found."

    lines = [f"\nCorpus search: \"{query}\"", f"Found {len(results)} passages:\n", "-" * 80]

    for i, r in enumerate(results, 1):
        snippet = r["text"][:300].replace("\n", " ")
        if len(r["text"]) > 300:
            snippet += "..."

        score_str = f"{r['score']:.4f}" if isinstance(r["score"], float) else str(r["score"])
        lines.append(f"\n{i}. [{r['source_org']}] {r['source_file']} (p.{r['page_number']})")
        lines.append(f"   Score: {score_str} | Commodity: {r['commodity']}")
        lines.append(f"   {snippet}")

    lines.append("\n" + "-" * 80)
    return "\n".join(lines)


def format_detailed(results: List[Dict], query: str) -> str:
    """Format results with full text."""
    if not results:
        return "No results found."

    lines = []
    for i, r in enumerate(results, 1):
        lines.append("=" * 80)
        lines.append(f"Result #{i}")
        lines.append("=" * 80)
        lines.append(f"Source: {r['source_org']} / {r['source_file']}")
        lines.append(f"Page: {r['page_number']} | Chunk: {r['chunk_index']}")
        lines.append(f"Commodity: {r['commodity']}")
        score_str = f"{r['score']:.4f}" if isinstance(r["score"], float) else str(r["score"])
        lines.append(f"Score: {score_str}")
        lines.append(f"\n{r['text']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Semantic search over critical minerals PDF corpus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "rare earth separation techniques"
  %(prog)s --query "trade flows" --source Comtrade --rerank
  %(prog)s --query "cobalt supply chain" --commodity cobalt --format json
  %(prog)s --query "lithium extraction" --top-k 20 --rerank
        """,
    )
    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Semantic search query",
    )
    parser.add_argument(
        "--commodity", "-c",
        help="Filter by commodity (e.g., lithium, cobalt, rare_earth, nickel)",
    )
    parser.add_argument(
        "--source", "-s",
        help="Filter by source organization (e.g., USGS, Comtrade, SEC, World Bank)",
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Number of results (default: {DEFAULT_TOP_K})",
    )
    parser.add_argument(
        "--rerank",
        action="store_true",
        help="Enable reranking with pinecone-rerank-v0",
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json"],
        help="Output format (default: summary)",
    )
    parser.add_argument(
        "--index-name",
        default=DEFAULT_INDEX,
        help=f"Pinecone index name (default: {DEFAULT_INDEX})",
    )
    parser.add_argument(
        "--namespace",
        default="__default__",
        help="Pinecone namespace (default: __default__)",
    )

    args = parser.parse_args()

    # Initialize Pinecone
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        print("Error: PINECONE_API_KEY environment variable is required", file=sys.stderr)
        sys.exit(1)

    pc = Pinecone(api_key=api_key)
    index = pc.Index(args.index_name)

    # Search
    results = search_corpus(
        query=args.query,
        index=index,
        namespace=args.namespace,
        top_k=args.top_k,
        commodity=args.commodity,
        source=args.source,
        rerank=args.rerank,
    )

    # Output
    if args.format == "json":
        print(json.dumps(results, indent=2))
    elif args.format == "detailed":
        print(format_detailed(results, args.query))
    else:
        print(format_summary(results, args.query))


if __name__ == "__main__":
    main()
