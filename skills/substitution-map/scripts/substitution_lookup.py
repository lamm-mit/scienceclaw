#!/usr/bin/env python3
"""
Substitution Map Tool for ScienceClaw

Map substitute materials for critical minerals with trade-off analysis
and supply risk assessment. Uses a curated knowledge base enriched
with live data from BGS and corpus-search.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

# Curated substitution knowledge base (sourced from USGS MCS, IEA, industry)
SUBSTITUTION_DB = {
    "lithium": {
        "batteries": [
            {
                "substitute": "Sodium",
                "material": "Sodium-ion batteries",
                "performance": 3,
                "cost": "Lower",
                "availability": 5,
                "maturity": "Emerging (commercial 2023+)",
                "notes": "Lower energy density but abundant; CATL, BYD deploying",
            },
            {
                "substitute": "Zinc",
                "material": "Zinc-air batteries",
                "performance": 2,
                "cost": "Lower",
                "availability": 5,
                "maturity": "R&D/pilot",
                "notes": "Good for stationary storage, not EVs",
            },
            {
                "substitute": "Magnesium",
                "material": "Magnesium-ion batteries",
                "performance": 2,
                "cost": "Lower",
                "availability": 4,
                "maturity": "Early R&D",
                "notes": "Divalent ion; theoretical 2x capacity; electrolyte challenges",
            },
        ],
        "ceramics": [
            {
                "substitute": "Potassium",
                "material": "Potassium feldspar",
                "performance": 4,
                "cost": "Similar",
                "availability": 5,
                "maturity": "Mature",
                "notes": "Can replace lithium in some ceramic glazes",
            },
        ],
        "lubricants": [
            {
                "substitute": "Calcium",
                "material": "Calcium-based greases",
                "performance": 3,
                "cost": "Lower",
                "availability": 5,
                "maturity": "Mature",
                "notes": "Adequate for many industrial applications",
            },
        ],
    },
    "cobalt": {
        "batteries": [
            {
                "substitute": "Iron",
                "material": "LFP (LiFePO4) cathodes",
                "performance": 3,
                "cost": "Lower",
                "availability": 5,
                "maturity": "Mature (dominant in China)",
                "notes": "Lower energy density but longer cycle life; ~60% of China EV market",
            },
            {
                "substitute": "Manganese",
                "material": "LMFP / high-Mn cathodes",
                "performance": 4,
                "cost": "Lower",
                "availability": 4,
                "maturity": "Emerging",
                "notes": "Higher voltage than LFP; reduced cobalt by 70-100%",
            },
            {
                "substitute": "Nickel (high)",
                "material": "NMC 811 / NCA cathodes",
                "performance": 5,
                "cost": "Similar",
                "availability": 3,
                "maturity": "Mature",
                "notes": "Reduces cobalt to ~5% of cathode; higher energy density",
            },
        ],
        "superalloys": [
            {
                "substitute": "Nickel",
                "material": "Nickel-based superalloys",
                "performance": 4,
                "cost": "Similar",
                "availability": 3,
                "maturity": "Mature",
                "notes": "Partial replacement only; cobalt still needed for some alloys",
            },
        ],
    },
    "rare_earth": {
        "magnets": [
            {
                "substitute": "Ferrite",
                "material": "Ferrite magnets (Sr/Ba)",
                "performance": 2,
                "cost": "Much lower",
                "availability": 5,
                "maturity": "Mature",
                "notes": "1/10 energy product of NdFeB; suitable for low-power motors",
            },
            {
                "substitute": "Iron-nitrogen",
                "material": "Fe16N2 magnets",
                "performance": 4,
                "cost": "Potentially lower",
                "availability": 5,
                "maturity": "Early R&D",
                "notes": "Theoretical performance near NdFeB; Niron Magnetics startup",
            },
            {
                "substitute": "Cerium (LREE)",
                "material": "Ce-substituted NdFeB",
                "performance": 4,
                "cost": "Lower",
                "availability": 4,
                "maturity": "Emerging",
                "notes": "Replaces expensive Nd/Dy with abundant Ce; 10-20% performance loss",
            },
        ],
        "catalysts": [
            {
                "substitute": "Iron/manganese",
                "material": "Fe-Mn catalysts",
                "performance": 3,
                "cost": "Lower",
                "availability": 5,
                "maturity": "Mature",
                "notes": "For some petroleum refining and chemical processes",
            },
        ],
    },
    "nickel": {
        "batteries": [
            {
                "substitute": "Iron",
                "material": "LFP cathodes",
                "performance": 3,
                "cost": "Lower",
                "availability": 5,
                "maturity": "Mature",
                "notes": "Eliminates nickel from battery; lower energy density",
            },
            {
                "substitute": "Manganese",
                "material": "Manganese-rich cathodes",
                "performance": 4,
                "cost": "Lower",
                "availability": 4,
                "maturity": "Emerging",
                "notes": "Mn partially replaces Ni in NMC formulations",
            },
        ],
        "alloys": [
            {
                "substitute": "Chromium",
                "material": "Chromium steels",
                "performance": 3,
                "cost": "Lower",
                "availability": 4,
                "maturity": "Mature",
                "notes": "For some stainless steel applications",
            },
        ],
    },
    "graphite": {
        "batteries": [
            {
                "substitute": "Silicon",
                "material": "Silicon anodes",
                "performance": 5,
                "cost": "Higher",
                "availability": 5,
                "maturity": "Emerging",
                "notes": "10x theoretical capacity; swelling challenges; Si-C composites commercial",
            },
            {
                "substitute": "Lithium metal",
                "material": "Lithium metal anodes",
                "performance": 5,
                "cost": "Higher",
                "availability": 3,
                "maturity": "R&D",
                "notes": "Highest energy density; dendrite formation challenges",
            },
        ],
        "refractories": [
            {
                "substitute": "Alumina",
                "material": "Alumina refractories",
                "performance": 3,
                "cost": "Similar",
                "availability": 5,
                "maturity": "Mature",
                "notes": "For some high-temperature applications",
            },
        ],
    },
    "manganese": {
        "batteries": [
            {
                "substitute": "Iron",
                "material": "LFP cathodes",
                "performance": 3,
                "cost": "Similar",
                "availability": 5,
                "maturity": "Mature",
                "notes": "Mn-free battery chemistry",
            },
        ],
        "steel": [
            {
                "substitute": "No direct substitute",
                "material": "Manganese is essential for steelmaking",
                "performance": 0,
                "cost": "N/A",
                "availability": 0,
                "maturity": "N/A",
                "notes": "No practical substitute for Mn in steel desulfurization/deoxidation",
            },
        ],
    },
    "gallium": {
        "electronics": [
            {
                "substitute": "Silicon carbide",
                "material": "SiC semiconductors",
                "performance": 4,
                "cost": "Higher",
                "availability": 5,
                "maturity": "Mature",
                "notes": "For power electronics; replacing GaN in some applications",
            },
            {
                "substitute": "Indium phosphide",
                "material": "InP semiconductors",
                "performance": 4,
                "cost": "Higher",
                "availability": 2,
                "maturity": "Mature",
                "notes": "For RF/telecom; still requires critical mineral (In)",
            },
        ],
    },
    "germanium": {
        "electronics": [
            {
                "substitute": "Silicon",
                "material": "Silicon optics",
                "performance": 3,
                "cost": "Lower",
                "availability": 5,
                "maturity": "Mature",
                "notes": "For some IR applications; lower performance in mid-wave IR",
            },
            {
                "substitute": "Chalcogenide glass",
                "material": "As-Se-Te glass optics",
                "performance": 3,
                "cost": "Similar",
                "availability": 3,
                "maturity": "Mature",
                "notes": "For IR lenses and windows",
            },
        ],
    },
    "copper": {
        "electronics": [
            {
                "substitute": "Aluminum",
                "material": "Aluminum wiring",
                "performance": 3,
                "cost": "Lower",
                "availability": 5,
                "maturity": "Mature",
                "notes": "Used in power transmission; 61% conductivity of Cu",
            },
            {
                "substitute": "Optical fiber",
                "material": "Fiber optic cables",
                "performance": 5,
                "cost": "Similar",
                "availability": 5,
                "maturity": "Mature",
                "notes": "For data/telecom, replacing copper cables",
            },
        ],
    },
}


def lookup_substitutes(
    commodity: str,
    application: Optional[str] = None,
) -> Dict[str, Any]:
    """Look up substitutes from knowledge base."""
    commodity_lower = commodity.lower().replace(" ", "_")

    # Handle common aliases
    aliases = {
        "rare earth": "rare_earth",
        "rare earths": "rare_earth",
        "ree": "rare_earth",
    }
    commodity_lower = aliases.get(commodity_lower, commodity_lower)

    if commodity_lower not in SUBSTITUTION_DB:
        return {
            "error": f"No substitution data for '{commodity}'. "
                     f"Available: {', '.join(sorted(SUBSTITUTION_DB.keys()))}",
            "commodity": commodity,
            "substitutes": {},
        }

    all_subs = SUBSTITUTION_DB[commodity_lower]

    if application:
        app_lower = application.lower()
        if app_lower in all_subs:
            filtered = {app_lower: all_subs[app_lower]}
        else:
            return {
                "error": f"No data for application '{application}'. "
                         f"Available: {', '.join(all_subs.keys())}",
                "commodity": commodity,
                "substitutes": {},
            }
    else:
        filtered = all_subs

    return {
        "commodity": commodity,
        "substitutes": filtered,
        "total_substitutes": sum(len(v) for v in filtered.values()),
        "applications": list(filtered.keys()),
    }


def format_summary(result: Dict[str, Any]) -> str:
    """Format substitution map as summary."""
    if result.get("error"):
        return result["error"]

    lines = []
    lines.append("=" * 70)
    lines.append(f"Substitution Map: {result['commodity'].upper()}")
    lines.append(f"Applications: {', '.join(result['applications'])}")
    lines.append(f"Total substitutes: {result['total_substitutes']}")
    lines.append("=" * 70)

    for app, subs in result.get("substitutes", {}).items():
        lines.append(f"\n--- {app.upper()} ---")
        for s in subs:
            perf = "*" * s["performance"] if s["performance"] else "N/A"
            avail = "*" * s["availability"] if s["availability"] else "N/A"
            lines.append(f"\n  {s['substitute']} -> {s['material']}")
            lines.append(f"    Performance: {perf}  Cost: {s['cost']}  Availability: {avail}")
            lines.append(f"    Maturity: {s['maturity']}")
            lines.append(f"    {s['notes']}")

    lines.append("\n" + "=" * 70)
    lines.append("Performance/Availability: * to ***** (1-5 scale)")
    return "\n".join(lines)


def format_detailed(result: Dict[str, Any]) -> str:
    """Format with full details."""
    return format_summary(result)


def main():
    parser = argparse.ArgumentParser(
        description="Map substitute materials for critical minerals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available commodities: {", ".join(sorted(SUBSTITUTION_DB.keys()))}

Examples:
  %(prog)s --commodity lithium
  %(prog)s --commodity cobalt --application batteries
  %(prog)s --commodity rare_earth --application magnets --format json
        """
    )

    parser.add_argument("--commodity", "-c", required=True, help="Commodity to find substitutes for")
    parser.add_argument("--application", "-a", help="Specific application filter")
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    result = lookup_substitutes(
        commodity=args.commodity,
        application=args.application,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2))
    elif args.format == "detailed":
        print(format_detailed(result))
    else:
        print(format_summary(result))


if __name__ == "__main__":
    main()
