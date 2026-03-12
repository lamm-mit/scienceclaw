#!/usr/bin/env python3
"""
Get results from a completed Adaptyv experiment.

This script downloads experimental results including measurements, quality metrics,
and download URLs for raw data packages.

Usage:
    python get_results.py --experiment-id exp_abc123xyz [--format json]
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


def get_experiment_results(
    experiment_id: str,
    api_key: Optional[str] = None
) -> Dict:
    """
    Get results from a completed experiment.

    Args:
        experiment_id: Experiment ID
        api_key: Adaptyv API key

    Returns:
        Dictionary with experimental results and download URLs
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

    # Get experiment results
    response = requests.get(
        f"{BASE_URL}/experiments/{experiment_id}/results",
        headers=headers,
        timeout=30
    )

    if response.status_code == 404:
        raise Exception(f"Experiment not found or results not available: {experiment_id}")
    elif response.status_code != 200:
        error_msg = f"API error ({response.status_code}): {response.text}"
        raise Exception(error_msg)

    return response.json()


def format_summary(result: Dict) -> str:
    """Format result as human-readable summary."""
    lines = []
    lines.append("=" * 60)
    lines.append("EXPERIMENT RESULTS")
    lines.append("=" * 60)
    lines.append(f"Experiment ID: {result.get('experiment_id', 'N/A')}")
    lines.append("")

    # Display results for each sequence
    results = result.get('results', [])
    if results:
        lines.append(f"Total Sequences Tested: {len(results)}")
        lines.append("")

        for i, seq_result in enumerate(results, 1):
            lines.append(f"Sequence {i}: {seq_result.get('sequence_id', 'N/A')}")
            lines.append("-" * 60)

            measurements = seq_result.get('measurements', {})
            if measurements:
                lines.append("Measurements:")
                for key, value in measurements.items():
                    if isinstance(value, float) and value < 0.01:
                        lines.append(f"  {key}: {value:.2e}")
                    else:
                        lines.append(f"  {key}: {value}")

            quality = seq_result.get('quality_metrics', {})
            if quality:
                lines.append("Quality Metrics:")
                for key, value in quality.items():
                    lines.append(f"  {key}: {value}")

            lines.append("")

    # Display download URLs
    download_urls = result.get('download_urls', {})
    if download_urls:
        lines.append("Download Links:")
        for key, url in download_urls.items():
            lines.append(f"  {key}: {url}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Get results from a completed Adaptyv experiment'
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
        # Get experiment results
        result = get_experiment_results(
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
