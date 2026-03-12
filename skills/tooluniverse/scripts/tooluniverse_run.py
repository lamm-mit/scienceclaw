#!/usr/bin/env python3
"""
ToolUniverse wrapper — call any of the 1000+ ToolUniverse tools and return JSON.

Usage:
    python3 tooluniverse_run.py --tool UniProt_get_entry_by_accession \
        --args '{"accession": "P05067"}'

    python3 tooluniverse_run.py --tool PubMed_search_articles \
        --args '{"query": "CRISPR delivery", "max_results": 5}' --format json
"""

import argparse
import json
import sys


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run any ToolUniverse tool and return JSON output.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 tooluniverse_run.py --tool UniProt_get_entry_by_accession \\
      --args '{"accession": "P05067"}'

  python3 tooluniverse_run.py --tool PubChem_get_compound_properties_by_CID \\
      --args '{"cid": 1983}'

  python3 tooluniverse_run.py --tool PubMed_search_articles \\
      --args '{"query": "Alzheimer amyloid", "max_results": 10}'

  python3 tooluniverse_run.py --tool ChEMBL_get_molecule_by_chembl_id \\
      --args '{"chembl_id": "CHEMBL25"}'
""",
    )
    parser.add_argument(
        "--tool", "-t", required=True,
        help="ToolUniverse tool name (exact, case-sensitive). Use tooluniverse_list.py to discover names.",
    )
    parser.add_argument(
        "--args", "-a", default="{}",
        help="Tool arguments as a JSON string. Default: {}",
    )
    parser.add_argument(
        "--format", "-f", choices=["json", "summary"], default="json",
        help="Output format. 'json' prints full result; 'summary' prints a brief human-readable version.",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable result caching (cache is on by default).",
    )
    return parser


def run_tool(tool_name: str, arguments: dict, use_cache: bool = True) -> dict:
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

    result = tu.run(
        {"name": tool_name, "arguments": arguments},
        use_cache=use_cache,
    )
    return result


def to_serializable(obj):
    """Recursively convert non-serializable objects to strings."""
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_serializable(v) for v in obj]
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


def print_summary(result, tool_name: str):
    """Print a brief human-readable summary of the result."""
    print(f"Tool: {tool_name}")
    if isinstance(result, str):
        print(result[:2000])
    elif isinstance(result, list):
        print(f"Results: {len(result)} items")
        for i, item in enumerate(result[:5], 1):
            if isinstance(item, dict):
                # Print first few key-value pairs
                preview = {k: v for i, (k, v) in enumerate(item.items()) if i < 4}
                print(f"  [{i}] {preview}")
            else:
                print(f"  [{i}] {str(item)[:120]}")
        if len(result) > 5:
            print(f"  ... and {len(result) - 5} more")
    elif isinstance(result, dict):
        for k, v in list(result.items())[:8]:
            print(f"  {k}: {str(v)[:120]}")
    else:
        print(str(result)[:2000])


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        tool_args = json.loads(args.args)
    except json.JSONDecodeError as exc:
        print(f"Error: --args is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        result = run_tool(args.tool, tool_args, use_cache=not args.no_cache)
    except Exception as exc:
        error_payload = {
            "error": str(exc),
            "tool": args.tool,
            "arguments": tool_args,
        }
        print(json.dumps(error_payload, indent=2))
        sys.exit(1)

    if args.format == "summary":
        print_summary(result, args.tool)
    else:
        safe = to_serializable(result)
        print(json.dumps(safe, indent=2))


if __name__ == "__main__":
    main()
