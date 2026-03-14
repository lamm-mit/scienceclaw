#!/usr/bin/env python3
"""
BGS World Mineral Statistics Query Tool for ScienceClaw

Query the British Geological Survey's World Mineral Statistics for
production, imports, and exports data by commodity, country, and year.
"""

import argparse
import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

try:
    sys.path.insert(0, "/Users/nancywashton/cmm-data/src")
    from cmm_data.clients import BGSClient
except ImportError:
    print("Error: cmm_data package is required. Ensure cmm-data is installed.", file=sys.stderr)
    sys.exit(1)


# Map common/short names to BGS bgs_commodity_trans values.
# The BGS API requires exact, case-sensitive commodity names.
BGS_COMMODITY_MAP = {
    "cobalt": "cobalt, mine",
    "copper": "copper, mine",
    "nickel": "nickel, mine",
    "lithium": "lithium minerals",
    "rare earth": "rare earth minerals",
    "rare earths": "rare earth minerals",
    "graphite": "graphite",
    "gold": "gold, mine",
    "silver": "silver, mine",
    "tin": "tin, mine",
    "zinc": "zinc, mine",
    "lead": "lead, mine",
    "iron ore": "iron ore",
    "manganese": "manganese ore",
    "tungsten": "tungsten, mine",
    "bauxite": "bauxite",
    "chromite": "chromite",
    "antimony": "antimony, mine",
    "barytes": "barytes",
    "feldspar": "feldspar",
    "fluorspar": "fluorspar",
    "phosphate rock": "phosphate rock",
    "potash": "potash",
    "titanium": "titanium minerals",
    "vanadium": "vanadium",
    "cobalt refined": "cobalt, refined",
    "copper refined": "copper, refined",
    "nickel refined": "nickel, smelter/refinery",
}


def resolve_commodity(user_input: str) -> str:
    """Resolve user input to a BGS commodity name."""
    lowered = user_input.lower().strip()
    # Exact match in map
    if lowered in BGS_COMMODITY_MAP:
        return BGS_COMMODITY_MAP[lowered]
    # Already a valid BGS name (contains comma or known suffix)
    if "," in lowered or lowered in BGS_COMMODITY_MAP.values():
        return lowered
    # Fallback: return as-is (lowercase)
    return lowered


async def query_bgs(
    commodity: str,
    country: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    statistic_type: str = "Production",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Query BGS World Mineral Statistics."""
    client = BGSClient()

    print(f"Querying BGS: {commodity}", file=sys.stderr)
    if country:
        print(f"Country: {country}", file=sys.stderr)
    if year_from or year_to:
        print(f"Years: {year_from or '...'}-{year_to or '...'}", file=sys.stderr)
    print(f"Statistic type: {statistic_type}", file=sys.stderr)
    print("", file=sys.stderr)

    bgs_commodity = resolve_commodity(commodity)
    print(f"BGS commodity: {bgs_commodity}", file=sys.stderr)

    records = await client.search_production(
        commodity=bgs_commodity,
        country=country,
        year_from=year_from,
        year_to=year_to,
        statistic_type=statistic_type,
        limit=limit,
    )

    results = []
    for r in records:
        results.append({
            "commodity": r.commodity,
            "country": r.country or "Unknown",
            "country_iso3": r.country_iso3 or "",
            "year": r.year,
            "quantity": r.quantity,
            "units": r.units or "",
            "statistic_type": r.statistic_type or statistic_type,
            "notes": r.notes or "",
        })

    print(f"Found {len(results)} records", file=sys.stderr)
    return results


async def get_ranking(
    commodity: str,
    year: Optional[int] = None,
    top_n: int = 15,
) -> List[Dict[str, Any]]:
    """Get country ranking for a commodity."""
    client = BGSClient()

    print(f"Getting ranking for: {commodity}", file=sys.stderr)
    if year:
        print(f"Year: {year}", file=sys.stderr)
    print(f"Top N: {top_n}", file=sys.stderr)
    print("", file=sys.stderr)

    bgs_commodity = resolve_commodity(commodity)
    print(f"BGS commodity: {bgs_commodity}", file=sys.stderr)

    ranked = await client.get_ranking(commodity=bgs_commodity, year=year, top_n=top_n)

    print(f"Found {len(ranked)} countries in ranking", file=sys.stderr)
    return ranked


def format_summary(records: List[Dict[str, Any]], is_ranking: bool = False) -> str:
    """Format records as summary list."""
    if not records:
        return "No records found."

    if is_ranking:
        lines = [f"\nCountry ranking ({len(records)} countries):\n"]
        lines.append("-" * 70)
        for r in records:
            rank = r.get("rank", "?")
            country = r.get("country", "Unknown")
            quantity = r.get("quantity", 0)
            units = r.get("units", "")
            share = r.get("share_percent", 0)
            lines.append(f"  {rank:>3}. {country:<35} {quantity:>12,.0f} {units:<10} ({share:.1f}%)")
        lines.append("-" * 70)
        return "\n".join(lines)

    lines = [f"\nFound {len(records)} BGS records:\n"]
    lines.append("-" * 80)

    for i, r in enumerate(records, 1):
        lines.append(f"\n{i}. {r['commodity']} - {r['country']}")
        lines.append(f"   Year: {r['year']}  Quantity: {r['quantity']} {r['units']}")
        lines.append(f"   Type: {r['statistic_type']}")
        if r.get("notes"):
            lines.append(f"   Notes: {r['notes'][:100]}")

    lines.append("\n" + "-" * 80)
    return "\n".join(lines)


def format_detailed(records: List[Dict[str, Any]]) -> str:
    """Format records with full details."""
    if not records:
        return "No records found."

    lines = []
    for i, r in enumerate(records, 1):
        lines.append("=" * 70)
        lines.append(f"Record #{i}")
        lines.append("=" * 70)
        lines.append(f"  Commodity: {r['commodity']}")
        lines.append(f"  Country: {r['country']} ({r.get('country_iso3', '')})")
        lines.append(f"  Year: {r['year']}")
        lines.append(f"  Quantity: {r['quantity']} {r['units']}")
        lines.append(f"  Statistic Type: {r['statistic_type']}")
        if r.get("notes"):
            lines.append(f"  Notes: {r['notes']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Query BGS World Mineral Statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "Lithium" --ranking --top-n 10
  %(prog)s --query "Cobalt" --country "Congo" --year-from 2015
  %(prog)s --query "Rare earths" --statistic-type "Exports" --format json
        """
    )

    parser.add_argument("--query", "-q", required=True, help="Commodity name")
    parser.add_argument("--country", "-c", help="Filter by country name")
    parser.add_argument("--year-from", type=int, help="Start year")
    parser.add_argument("--year-to", type=int, help="End year")
    parser.add_argument(
        "--statistic-type", "-t",
        default="Production",
        help="Statistic type: Production, Imports, Exports (default: Production)"
    )
    parser.add_argument("--ranking", "-r", action="store_true", help="Show country ranking")
    parser.add_argument("--top-n", type=int, default=15, help="Top N countries for ranking (default: 15)")
    parser.add_argument("--limit", "-l", type=int, default=50, help="Maximum records (default: 50)")
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    if args.ranking:
        year = args.year_from or args.year_to
        records = asyncio.run(get_ranking(
            commodity=args.query,
            year=year,
            top_n=args.top_n,
        ))
        is_ranking = True
    else:
        records = asyncio.run(query_bgs(
            commodity=args.query,
            country=args.country,
            year_from=args.year_from,
            year_to=args.year_to,
            statistic_type=args.statistic_type,
            limit=args.limit,
        ))
        is_ranking = False

    if args.format == "json":
        print(json.dumps(records, indent=2))
    elif args.format == "detailed":
        print(format_detailed(records))
    else:
        print(format_summary(records, is_ranking=is_ranking))


if __name__ == "__main__":
    main()
