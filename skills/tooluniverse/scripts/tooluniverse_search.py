#!/usr/bin/env python3
"""
ToolUniverse search — discover tools from the live ToolUniverse registry.

Uses the ToolUniverse Python SDK to query the actual tool registry by keyword.
No hardcoded data — all results come from the installed tooluniverse package.

Usage:
    python3 tooluniverse_search.py --query "protein structure prediction"
    python3 tooluniverse_search.py --query "drug ADMET" --max-results 20
    python3 tooluniverse_search.py --query "RNA-seq" --format json
"""

import argparse
import json
import sys


def build_parser():
    parser = argparse.ArgumentParser(
        description="Search ToolUniverse for scientific tools by keyword.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 tooluniverse_search.py --query "protein structure"
  python3 tooluniverse_search.py --query "drug ADMET" --max-results 20
  python3 tooluniverse_search.py --query "RNA-seq" --format json
""",
    )
    parser.add_argument("--query", "-q", required=True, help="Keyword search query")
    parser.add_argument("--max-results", "-m", type=int, default=10, help="Max results to return")
    parser.add_argument(
        "--format", "-f", choices=["json", "summary"], default="json",
        help="Output format",
    )
    return parser


def load_tu():
    try:
        from tooluniverse import ToolUniverse
    except ImportError:
        print(
            "Error: tooluniverse is not installed. Install with:\n"
            "  pip install tooluniverse",
            file=sys.stderr,
        )
        sys.exit(1)
    tu = ToolUniverse()
    tu.load_tools()
    return tu


def get_tool_registry(tu) -> dict:
    """Return the tool registry dict from the ToolUniverse instance."""
    for attr in ("_tools", "tools", "_tool_registry", "tool_registry"):
        reg = getattr(tu, attr, None)
        if reg:
            return reg
    return {}


def search_tools(tu, query: str, max_results: int) -> list:
    """Search tool registry by keyword match on name and description."""
    registry = get_tool_registry(tu)
    query_lower = query.lower()
    tokens = query_lower.split()

    results = []
    for name, tool_cls_or_instance in registry.items():
        description = ""
        try:
            if callable(tool_cls_or_instance):
                instance = tool_cls_or_instance({})
            else:
                instance = tool_cls_or_instance
            info = instance.get_tool_info() if hasattr(instance, "get_tool_info") else {}
            description = info.get("description", "")
        except Exception:
            pass

        text = (name + " " + description).lower()
        score = sum(1 for t in tokens if t in text)
        if score > 0:
            results.append({"name": name, "description": description, "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


def main():
    parser = build_parser()
    args = parser.parse_args()

    tu = load_tu()
    tools = search_tools(tu, args.query, args.max_results)

    output = {
        "query": args.query,
        "total": len(tools),
        "tools": [{k: v for k, v in t.items() if k != "score"} for t in tools],
    }

    if args.format == "json":
        print(json.dumps(output, indent=2))
    else:
        print(f"ToolUniverse search: '{args.query}' — {len(tools)} results")
        print("-" * 60)
        for t in tools:
            desc = t.get("description", "")
            desc_short = (desc[:70] + "…") if len(desc) > 70 else desc
            print(f"  {t['name']:<50} {desc_short}")


if __name__ == "__main__":
    main()
