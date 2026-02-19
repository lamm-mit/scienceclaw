#!/usr/bin/env python3
"""
scvi-tools - Probabilistic models for single-cell data

Basic demonstration script showing how to use scvi-tools.
Consult SKILL.md and references/ for detailed documentation.

Usage:
    python demo.py [--format json]
"""

import argparse
import json
import sys


def demonstrate():
    """Demonstrate basic scvi-tools usage."""
    return {
        "skill": "scvi-tools",
        "status": "available",
        "description": "Probabilistic models for single-cell data",
        "note": "See SKILL.md and references/ for comprehensive documentation"
    }


def main():
    parser = argparse.ArgumentParser(description='scvi-tools demonstration')
    parser.add_argument(
        '--format', '-f',
        default='summary',
        choices=['summary', 'json'],
        help='Output format (default: summary)'
    )

    args = parser.parse_args()

    try:
        result = demonstrate()

        if args.format == 'json':
            print(json.dumps(result, indent=2))
        else:
            print("=" * 70)
            print(f"{result['skill']} - {result['description']}")
            print("=" * 70)
            print(f"Status: {result['status']}")
            print(f"\nNote: {result['note']}")
            print("=" * 70)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
