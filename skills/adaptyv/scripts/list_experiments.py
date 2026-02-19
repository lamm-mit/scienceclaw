#!/usr/bin/env python3
"""
List all Adaptyv experiments for your organization.

This script retrieves a list of all experiments with optional filtering by status.

Usage:
    python list_experiments.py [--status submitted|processing|completed|failed] [--format json]
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


def list_experiments(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    api_key: Optional[str] = None
) -> Dict:
    """
    List all experiments for your organization.

    Args:
        status: Filter by status (submitted, processing, completed, failed)
        limit: Number of results per page
        offset: Pagination offset
        api_key: Adaptyv API key

    Returns:
        Dictionary with experiments list and pagination info
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
    params = {
        "limit": limit,
        "offset": offset
    }
    if status:
        params["status"] = status

    # List experiments
    response = requests.get(
        f"{BASE_URL}/experiments",
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
    lines.append("=" * 80)
    lines.append("EXPERIMENTS LIST")
    lines.append("=" * 80)

    total = result.get('total', 0)
    limit = result.get('limit', 0)
    offset = result.get('offset', 0)
    lines.append(f"Total experiments: {total}")
    lines.append(f"Showing: {offset + 1}-{min(offset + limit, total)}")
    lines.append("")

    experiments = result.get('experiments', [])
    if experiments:
        lines.append(f"{'Experiment ID':<20} {'Type':<15} {'Status':<12} {'Created':<20}")
        lines.append("-" * 80)

        for exp in experiments:
            exp_id = exp.get('experiment_id', 'N/A')[:18]
            exp_type = exp.get('experiment_type', 'N/A')[:13]
            status = exp.get('status', 'N/A')[:10]
            created = exp.get('created_at', 'N/A')[:18]

            lines.append(f"{exp_id:<20} {exp_type:<15} {status:<12} {created:<20}")
    else:
        lines.append("No experiments found.")

    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='List all Adaptyv experiments'
    )
    parser.add_argument(
        '--status',
        choices=['submitted', 'processing', 'completed', 'failed'],
        help='Filter by status (optional)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Number of results per page (default: 50)'
    )
    parser.add_argument(
        '--offset',
        type=int,
        default=0,
        help='Pagination offset (default: 0)'
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
        # List experiments
        result = list_experiments(
            status=args.status,
            limit=args.limit,
            offset=args.offset,
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
