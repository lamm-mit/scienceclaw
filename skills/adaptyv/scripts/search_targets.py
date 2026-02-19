#!/usr/bin/env python3
"""
Search the Adaptyv target catalog (ACROBiosystems antigens).

This script searches for available targets including species, category filtering.

Usage:
    python search_targets.py --search "PD-L1" [--species "Homo sapiens"] [--format json]
"""

import argparse
import json
import os
import sys
from typing import Dict, Optional

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


BASE_URL = "https://kq5jp7qj7wdqklhsxmovkzn4l40obksv.lambda-url.eu-central-1.on.aws"


def search_targets(
    search: str,
    species: Optional[str] = None,
    category: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict:
    """
    Search the target catalog.

    Args:
        search: Search term (protein name, UniProt ID, etc.)
        species: Filter by species
        category: Filter by category
        api_key: Adaptyv API key

    Returns:
        Dictionary with matching targets
    """
    # Get API key
    if not api_key:
        api_key = os.environ.get("ADAPTYV_API_KEY")

    if not api_key:
        raise ValueError("ADAPTYV_API_KEY not found. Set environment variable or use --api-key")

    # Prepare headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Prepare query parameters
    params = {"search": search}
    if species:
        params["species"] = species
    if category:
        params["category"] = category

    # Search targets
    response = requests.get(
        f"{BASE_URL}/targets",
        headers=headers,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        error_msg = f"API error ({response.status_code}): {response.text}"
        raise Exception(error_msg)

    return response.json()


def format_summary(result: Dict) -> str:
    """Format result as human-readable summary."""
    lines = []
    lines.append("=" * 90)
    lines.append("TARGET CATALOG SEARCH RESULTS")
    lines.append("=" * 90)

    targets = result.get('targets', [])
    if targets:
        lines.append(f"Found {len(targets)} targets:")
        lines.append("")
        lines.append(f"{'Target ID':<15} {'Name':<25} {'Species':<20} {'Availability':<15} {'Price':<10}")
        lines.append("-" * 90)

        for target in targets:
            target_id = target.get('target_id', 'N/A')[:13]
            name = target.get('name', 'N/A')[:23]
            species = target.get('species', 'N/A')[:18]
            availability = target.get('availability', 'N/A')[:13]
            price = target.get('price_usd', 0)

            lines.append(f"{target_id:<15} {name:<25} {species:<20} {availability:<15} ${price:<9.2f}")

            # Show UniProt ID if available
            uniprot = target.get('uniprot_id', '')
            if uniprot:
                lines.append(f"  UniProt: {uniprot}")
    else:
        lines.append("No targets found matching your search criteria.")

    lines.append("=" * 90)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Search the Adaptyv target catalog'
    )
    parser.add_argument(
        '--query', '--search', '-s',
        dest='search',
        required=True,
        help='Search term (protein name, UniProt ID, etc.)'
    )
    parser.add_argument(
        '--species',
        help='Filter by species (e.g., "Homo sapiens")'
    )
    parser.add_argument(
        '--category',
        help='Filter by category'
    )
    parser.add_argument(
        '--api-key',
        help='Adaptyv API key (or use ADAPTYV_API_KEY env var)'
    )
    parser.add_argument(
        '--format', '-f',
        default='summary',
        choices=['summary', 'json'],
        help='Output format (default: summary)'
    )

    args = parser.parse_args()

    try:
        # Search targets
        result = search_targets(
            search=args.search,
            species=args.species,
            category=args.category,
            api_key=args.api_key
        )

        # Output result
        if args.format == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(format_summary(result))

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
