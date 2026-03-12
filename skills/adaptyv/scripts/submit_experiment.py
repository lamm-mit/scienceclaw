#!/usr/bin/env python3
"""
Submit protein sequences to Adaptyv for experimental testing.

This script submits protein sequences to the Adaptyv cloud laboratory platform
for automated testing including binding assays, expression testing, thermostability
measurements, and enzyme activity assays.

Usage:
    python submit_experiment.py --sequences sequences.fasta --type binding [--target TARGET_ID] [--format json]

Arguments:
    --sequences: Path to FASTA file with protein sequences
    --type: Experiment type (binding, expression, thermostability, enzyme_activity)
    --target: Optional target identifier
    --webhook: Optional webhook URL for notifications
    --project: Optional project name
    --notes: Optional notes
    --format: Output format (summary, json)
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


def submit_experiment(
    sequences: str,
    experiment_type: str,
    target_id: Optional[str] = None,
    webhook_url: Optional[str] = None,
    project: Optional[str] = None,
    notes: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict:
    """
    Submit protein sequences for experimental testing.

    Args:
        sequences: FASTA-formatted protein sequences
        experiment_type: Type of experiment (binding, expression, thermostability, enzyme_activity)
        target_id: Optional target identifier
        webhook_url: Optional webhook URL for completion notifications
        project: Optional project name
        notes: Optional notes
        api_key: Adaptyv API key

    Returns:
        Dictionary with experiment ID and status
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

    # Prepare request body
    body = {
        "sequences": sequences,
        "experiment_type": experiment_type
    }

    if target_id:
        body["target_id"] = target_id

    if webhook_url:
        body["webhook_url"] = webhook_url

    metadata = {}
    if project:
        metadata["project"] = project
    if notes:
        metadata["notes"] = notes
    if metadata:
        body["metadata"] = metadata

    # Submit experiment
    response = requests.post(
        f"{BASE_URL}/experiments",
        headers=headers,
        json=body,
        timeout=30
    )

    if response.status_code != 200:
        error_msg = f"API error ({response.status_code}): {response.text}"
        raise Exception(error_msg)

    return response.json()


def format_summary(result: Dict) -> str:
    """Format result as human-readable summary."""
    lines = []
    lines.append("=" * 60)
    lines.append("EXPERIMENT SUBMITTED")
    lines.append("=" * 60)
    lines.append(f"Experiment ID: {result.get('experiment_id', 'N/A')}")
    lines.append(f"Status: {result.get('status', 'N/A')}")
    lines.append(f"Created: {result.get('created_at', 'N/A')}")
    lines.append(f"Estimated Completion: {result.get('estimated_completion', 'N/A')}")
    lines.append("")
    lines.append("Results will be available in approximately 21 days.")
    lines.append("Use get_status.py to check experiment status.")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Submit protein sequences to Adaptyv for experimental testing'
    )
    parser.add_argument(
        '--sequences', '-s',
        required=True,
        help='Path to FASTA file with protein sequences'
    )
    parser.add_argument(
        '--type', '-t',
        required=True,
        choices=['binding', 'expression', 'thermostability', 'enzyme_activity'],
        help='Type of experiment'
    )
    parser.add_argument(
        '--target',
        help='Target identifier (optional)'
    )
    parser.add_argument(
        '--webhook',
        help='Webhook URL for completion notifications (optional)'
    )
    parser.add_argument(
        '--project',
        help='Project name (optional)'
    )
    parser.add_argument(
        '--notes',
        help='Additional notes (optional)'
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
        # Read sequences from file
        with open(args.sequences, 'r') as f:
            sequences = f.read()

        # Submit experiment
        result = submit_experiment(
            sequences=sequences,
            experiment_type=args.type,
            target_id=args.target,
            webhook_url=args.webhook,
            project=args.project,
            notes=args.notes,
            api_key=args.api_key
        )

        # Output result
        if args.format == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(format_summary(result))

    except FileNotFoundError:
        print(f"Error: Sequences file not found: {args.sequences}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
