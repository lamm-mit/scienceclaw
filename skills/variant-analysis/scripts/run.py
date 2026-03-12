#!/usr/bin/env python3
"""
ToolUniverse workflow: tooluniverse-variant-analysis

Calls the ToolUniverse AgenticTool for this workflow and returns JSON output.
Requires: pip install tooluniverse

Usage:
    python3 run.py --query "Your research question or input"
    python3 run.py --query "Alzheimer disease" --format summary
"""

import argparse
import json
import sys


WORKFLOW = "tooluniverse-variant-analysis"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run the ToolUniverse '" + WORKFLOW + "' research workflow.",
    )
    parser.add_argument("--query", "-q", required=True, help="Research query or input")
    parser.add_argument(
        "--format", "-f", choices=["json", "summary"], default="json",
        help="Output format",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable result caching",
    )
    return parser


def to_serializable(obj):
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_serializable(v) for v in obj]
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        from tooluniverse import ToolUniverse
    except ImportError:
        print("Error: tooluniverse is not installed. Run: pip install tooluniverse", file=sys.stderr)
        sys.exit(1)

    tu = ToolUniverse()
    tu.load_tools()

    try:
        result = tu.run(
            {"name": WORKFLOW, "arguments": {"query": args.query}},
            use_cache=not args.no_cache,
        )
    except Exception as exc:
        error = {"error": str(exc), "workflow": WORKFLOW, "query": args.query}
        print(json.dumps(error, indent=2))
        sys.exit(1)

    safe = to_serializable(result)
    if args.format == "summary":
        if isinstance(safe, str):
            print(safe[:3000])
        else:
            print(json.dumps(safe, indent=2)[:3000])
    else:
        print(json.dumps(safe, indent=2))


if __name__ == "__main__":
    main()
