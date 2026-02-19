#!/usr/bin/env python3
"""
Get status of an Adaptyv experiment.

This script checks the current status of a submitted experiment including
processing stage and completion percentage.

Usage:
    python get_status.py --experiment-id exp_abc123xyz [--format json]
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


def get_experiment_status(
    experiment_id: str,
    api_key: Optional[str] = None
) -> Dict:
    """
    Get the status of an experiment.

    Args:
        experiment_id: Experiment ID
        api_key: Adaptyv API key

    Returns:
        Dictionary with experiment status and progress
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

    # Get experiment status
    response = requests.get(
        f"{BASE_URL}/experiments/{experiment_id}",
        headers=headers,
        timeout=30
    )

    if response.status_code == 404:
        raise Exception(f"Experiment not found: {experiment_id}")
    elif response.status_code != 200:
        error_msg = f"API error ({response.status_code}): {response.text}"
        raise Exception(error_msg)

    return response.json()


def format_summary(result: Dict) -> str:
    """Format result as human-readable summary."""
    lines = []
    lines.append("=" * 60)
    lines.append("EXPERIMENT STATUS")
    lines.append("=" * 60)
    lines.append(f"Experiment ID: {result.get('experiment_id', 'N/A')}")
    lines.append(f"Status: {result.get('status', 'N/A').upper()}")
    lines.append(f"Created: {result.get('created_at', 'N/A')}")
    lines.append(f"Updated: {result.get('updated_at', 'N/A')}")
    lines.append("")

    progress = result.get('progress', {})
    if progress:
        lines.append(f"Current Stage: {progress.get('stage', 'N/A')}")
        lines.append(f"Progress: {progress.get('percentage', 0)}%")
        lines.append("")

    status = result.get('status', '')
    if status == 'submitted':
        lines.append("Experiment has been submitted and is queued for processing.")
    elif status == 'processing':
        lines.append("Experiment is currently being processed in the laboratory.")
    elif status == 'completed':
        lines.append("Experiment is complete! Use get_results.py to download results.")
    elif status == 'failed':
        lines.append("Experiment failed. Contact support@adaptyvbio.com for assistance.")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Get status of an Adaptyv experiment'
    )
    parser.add_argument(
        '--experiment-id', '-e',
        required=True,
        help='Experiment ID (e.g., exp_abc123xyz)'
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
        # Get experiment status
        result = get_experiment_status(
            experiment_id=args.experiment_id,
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
