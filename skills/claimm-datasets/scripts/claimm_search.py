#!/usr/bin/env python3
"""
CLAIMM Dataset Search Tool for ScienceClaw

Search and discover NETL EDX CLAIMM datasets with 200+ US-focused
critical minerals datasets.
"""

import argparse
import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

try:
    sys.path.insert(0, "/Users/nancywashton/cmm-data/src")
    from cmm_data.clients import CLAIMMClient
except ImportError:
    print("Error: cmm_data package is required. Ensure cmm-data is installed.", file=sys.stderr)
    sys.exit(1)


async def search_claimm(
    query: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Search CLAIMM datasets."""
    client = CLAIMMClient()

    print(f"Searching CLAIMM datasets", file=sys.stderr)
    if query:
        print(f"Query: {query}", file=sys.stderr)
    if tags:
        print(f"Tags: {', '.join(tags)}", file=sys.stderr)
    print(f"Max results: {limit}", file=sys.stderr)
    print("", file=sys.stderr)

    try:
        datasets = await client.search_datasets(
            query=query,
            tags=tags,
            limit=limit,
        )
    except Exception as e:
        print(f"Error searching CLAIMM: {e}", file=sys.stderr)
        return []

    results = []
    for ds in datasets:
        resources = []
        for r in ds.resources:
            resources.append({
                "id": r.id,
                "name": r.name or "",
                "format": r.format or "",
                "size": r.size,
                "url": r.url or "",
            })
        results.append({
            "id": ds.id,
            "title": ds.title,
            "description": (ds.description or "")[:500],
            "tags": ds.tags,
            "resource_count": len(ds.resources),
            "resources": resources,
        })

    print(f"Found {len(results)} datasets", file=sys.stderr)
    return results


async def get_dataset_detail(dataset_id: str) -> Optional[Dict[str, Any]]:
    """Get details for a specific dataset."""
    client = CLAIMMClient()

    print(f"Getting dataset: {dataset_id}", file=sys.stderr)
    print("", file=sys.stderr)

    try:
        ds = await client.get_dataset(dataset_id)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

    if ds is None:
        print("Dataset not found", file=sys.stderr)
        return None

    resources = []
    for r in ds.resources:
        resources.append({
            "id": r.id,
            "name": r.name or "",
            "format": r.format or "",
            "size": r.size,
            "url": r.url or "",
        })

    return {
        "id": ds.id,
        "title": ds.title,
        "description": ds.description or "",
        "tags": ds.tags,
        "resource_count": len(ds.resources),
        "resources": resources,
    }


def format_summary(datasets: List[Dict[str, Any]]) -> str:
    """Format datasets as summary list."""
    if not datasets:
        return "No datasets found."

    lines = [f"\nFound {len(datasets)} CLAIMM datasets:\n"]
    lines.append("-" * 80)

    for i, ds in enumerate(datasets, 1):
        tags_str = ", ".join(ds["tags"][:5]) if ds["tags"] else "none"
        lines.append(f"\n{i}. {ds['title']}")
        lines.append(f"   ID: {ds['id']}")
        lines.append(f"   Tags: {tags_str}")
        lines.append(f"   Resources: {ds['resource_count']} files")

    lines.append("\n" + "-" * 80)
    return "\n".join(lines)


def format_detailed(datasets: List[Dict[str, Any]]) -> str:
    """Format datasets with full details."""
    if not datasets:
        return "No datasets found."

    # Handle single dataset (from --dataset-id)
    if not isinstance(datasets, list):
        datasets = [datasets]

    lines = []
    for i, ds in enumerate(datasets, 1):
        lines.append("=" * 80)
        lines.append(f"Dataset #{i}: {ds['title']}")
        lines.append("=" * 80)
        lines.append(f"\nID: {ds['id']}")
        if ds.get("description"):
            lines.append(f"\nDescription:\n{ds['description'][:1000]}")
        if ds.get("tags"):
            lines.append(f"\nTags: {', '.join(ds['tags'])}")
        lines.append(f"\nResources ({ds['resource_count']} files):")
        for r in ds.get("resources", []):
            size_str = f" ({r['size']} bytes)" if r.get("size") else ""
            lines.append(f"  - {r['name']} [{r['format']}]{size_str}")
            if r.get("url"):
                lines.append(f"    URL: {r['url']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search NETL EDX CLAIMM datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "lithium deposits"
  %(prog)s --query "rare earth" --tags "geochemistry,geology"
  %(prog)s --dataset-id "abc123" --format detailed
  %(prog)s --query "critical minerals" --format json --limit 50
        """
    )

    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--tags", help="Comma-separated tags to filter by")
    parser.add_argument("--dataset-id", help="Specific dataset ID to retrieve")
    parser.add_argument("--limit", "-l", type=int, default=20, help="Maximum results (default: 20)")
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    if not args.query and not args.dataset_id:
        parser.error("Either --query or --dataset-id is required")

    if args.dataset_id:
        result = asyncio.run(get_dataset_detail(args.dataset_id))
        if result is None:
            sys.exit(1)
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print(format_detailed(result))
    else:
        tags = [t.strip() for t in args.tags.split(",")] if args.tags else None
        datasets = asyncio.run(search_claimm(
            query=args.query,
            tags=tags,
            limit=args.limit,
        ))

        if args.format == "json":
            print(json.dumps(datasets, indent=2))
        elif args.format == "detailed":
            print(format_detailed(datasets))
        else:
            print(format_summary(datasets))


if __name__ == "__main__":
    main()
