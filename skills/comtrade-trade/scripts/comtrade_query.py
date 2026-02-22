#!/usr/bin/env python3
"""
UN Comtrade Trade Data Query Tool for ScienceClaw

Query UN Comtrade for bilateral trade flows of critical minerals
by HS commodity code, country, and year.
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

try:
    sys.path.insert(0, "/Users/nancywashton/critical-minerals-data-tools/UNComtrade_MCP/src")
    from uncomtrade_mcp.client import ComtradeClient
    from uncomtrade_mcp.models import CRITICAL_MINERAL_HS_CODES, MINERAL_NAMES
except ImportError:
    print("Error: uncomtrade_mcp package is required.", file=sys.stderr)
    sys.exit(1)


async def query_comtrade(
    mineral: Optional[str] = None,
    hs_code: Optional[str] = None,
    reporter: str = "0",
    partner: str = "0",
    flow: str = "M,X",
    year: str = "2023",
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """Query UN Comtrade for trade data."""
    client = ComtradeClient()

    if not client.is_available():
        print("Error: UNCOMTRADE_API_KEY not set", file=sys.stderr)
        return []

    print(f"Querying UN Comtrade", file=sys.stderr)
    if mineral:
        print(f"Mineral: {mineral} ({MINERAL_NAMES.get(mineral.lower(), mineral)})", file=sys.stderr)
    if hs_code:
        print(f"HS Code: {hs_code}", file=sys.stderr)
    print(f"Reporter: {reporter}, Partner: {partner}", file=sys.stderr)
    print(f"Flow: {flow}, Year: {year}", file=sys.stderr)
    print("", file=sys.stderr)

    try:
        if mineral:
            records = await client.get_critical_mineral_trade(
                mineral=mineral,
                reporter=reporter,
                partner=partner,
                flow=flow,
                period=year,
                max_records=limit,
            )
        elif hs_code:
            records = await client.get_trade_data(
                reporter=reporter,
                partner=partner,
                commodity=hs_code,
                flow=flow,
                period=year,
                max_records=limit,
            )
        else:
            print("Error: Either --mineral or --hs-code is required", file=sys.stderr)
            return []
    except Exception as e:
        print(f"Error querying Comtrade: {e}", file=sys.stderr)
        return []

    results = []
    for r in records:
        results.append({
            "period": r.period,
            "reporter": r.reporter_name,
            "reporter_code": r.reporter_code,
            "partner": r.partner_name,
            "partner_code": r.partner_code,
            "flow": r.flow or r.flow_code,
            "flow_code": r.flow_code,
            "commodity_code": r.commodity_code,
            "commodity": r.commodity or "",
            "trade_value_usd": r.trade_value,
            "net_weight_kg": r.net_weight,
            "quantity": r.quantity,
            "quantity_unit": r.quantity_unit or "",
        })

    print(f"Found {len(results)} trade records", file=sys.stderr)
    return results


def format_summary(records: List[Dict[str, Any]]) -> str:
    """Format records as summary list."""
    if not records:
        return "No trade records found."

    lines = [f"\nFound {len(records)} trade records:\n"]
    lines.append("-" * 90)

    for i, r in enumerate(records, 1):
        value_str = f"${r['trade_value_usd']:,.0f}" if r.get("trade_value_usd") else "N/A"
        weight_str = f"{r['net_weight_kg']:,.0f} kg" if r.get("net_weight_kg") else "N/A"
        lines.append(f"\n{i}. {r['reporter']} -> {r['partner']} ({r['flow']}) [{r['period']}]")
        lines.append(f"   HS {r['commodity_code']}: {r['commodity'][:60]}")
        lines.append(f"   Value: {value_str}  Weight: {weight_str}")

    lines.append("\n" + "-" * 90)
    return "\n".join(lines)


def format_detailed(records: List[Dict[str, Any]]) -> str:
    """Format records with full details."""
    if not records:
        return "No trade records found."

    lines = []
    for i, r in enumerate(records, 1):
        lines.append("=" * 70)
        lines.append(f"Trade Record #{i}")
        lines.append("=" * 70)
        lines.append(f"  Period: {r['period']}")
        lines.append(f"  Reporter: {r['reporter']} (code: {r['reporter_code']})")
        lines.append(f"  Partner: {r['partner']} (code: {r['partner_code']})")
        lines.append(f"  Flow: {r['flow']} ({r['flow_code']})")
        lines.append(f"  HS Code: {r['commodity_code']}")
        lines.append(f"  Commodity: {r['commodity']}")
        value_str = f"${r['trade_value_usd']:,.2f}" if r.get("trade_value_usd") else "N/A"
        weight_str = f"{r['net_weight_kg']:,.0f} kg" if r.get("net_weight_kg") else "N/A"
        lines.append(f"  Trade Value: {value_str}")
        lines.append(f"  Net Weight: {weight_str}")
        if r.get("quantity"):
            lines.append(f"  Quantity: {r['quantity']} {r['quantity_unit']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Query UN Comtrade for critical mineral trade data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available minerals: {", ".join(sorted(CRITICAL_MINERAL_HS_CODES.keys()))}

Examples:
  %(prog)s --mineral lithium --reporter 842 --flow M
  %(prog)s --mineral cobalt --format json --year 2022
  %(prog)s --hs-code 2604 --reporter 156 --flow X
        """
    )

    parser.add_argument("--mineral", "-m", help="Critical mineral name")
    parser.add_argument("--hs-code", help="HS commodity code (alternative to --mineral)")
    parser.add_argument("--reporter", "-r", default="0", help="Reporter country code (default: 0 = all)")
    parser.add_argument("--partner", "-p", default="0", help="Partner country code (default: 0 = world)")
    parser.add_argument("--flow", default="M,X", help="Trade flow: M, X, or M,X (default: M,X)")
    parser.add_argument("--year", "-y", default="2023", help="Year(s), comma-separated (default: 2023)")
    parser.add_argument("--limit", "-l", type=int, default=500, help="Maximum records (default: 500)")
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    if not args.mineral and not args.hs_code:
        parser.error("Either --mineral or --hs-code is required")

    records = asyncio.run(query_comtrade(
        mineral=args.mineral,
        hs_code=args.hs_code,
        reporter=args.reporter,
        partner=args.partner,
        flow=args.flow,
        year=args.year,
        limit=args.limit,
    ))

    if args.format == "json":
        print(json.dumps(records, indent=2))
    elif args.format == "detailed":
        print(format_detailed(records))
    else:
        print(format_summary(records))


if __name__ == "__main__":
    main()
