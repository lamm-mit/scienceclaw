#!/usr/bin/env python3
"""
Supply Chain Risk Metrics Tool for ScienceClaw

Compute supply chain risk metrics for critical minerals:
- HHI (Herfindahl-Hirschman Index) for production concentration
- NIR (Net Import Reliance) from USGS data
- Top-3 country share
- Multi-year trend analysis
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
    print("Error: cmm_data package is required.", file=sys.stderr)
    sys.exit(1)


# Map common names to BGS bgs_commodity_trans values (case-sensitive, exact match).
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
    "manganese": "manganese ore",
    "tungsten": "tungsten, mine",
    "chromite": "chromite",
    "titanium": "titanium minerals",
}


def resolve_bgs_commodity(name: str) -> str:
    """Resolve a user-friendly commodity name to BGS API name."""
    lowered = name.lower().strip()
    if lowered in BGS_COMMODITY_MAP:
        return BGS_COMMODITY_MAP[lowered]
    if "," in lowered or lowered in BGS_COMMODITY_MAP.values():
        return lowered
    return lowered


def classify_hhi(hhi: float) -> str:
    """Classify HHI score into risk category."""
    if hhi < 1500:
        return "LOW"
    elif hhi < 2500:
        return "MODERATE"
    else:
        return "HIGH"


def classify_nir(nir: float) -> str:
    """Classify Net Import Reliance into risk category."""
    if nir < 25:
        return "LOW"
    elif nir < 75:
        return "MODERATE"
    else:
        return "HIGH"


def classify_top3(share: float) -> str:
    """Classify top-3 share into risk category."""
    if share < 50:
        return "LOW"
    elif share < 75:
        return "MODERATE"
    else:
        return "HIGH"


async def compute_hhi_and_top3(
    commodity: str,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """Compute HHI and top-3 share from BGS data."""
    client = BGSClient()
    bgs_name = resolve_bgs_commodity(commodity)

    print(f"Computing HHI for: {commodity} (BGS: {bgs_name})", file=sys.stderr)

    # Get ranking (which includes shares)
    ranked = await client.get_ranking(commodity=bgs_name, year=year, top_n=50)

    if not ranked:
        return {"error": f"No production data for {commodity}"}

    actual_year = ranked[0].get("year", year)

    # Compute HHI = sum of squared market shares
    hhi = sum(item["share_percent"] ** 2 for item in ranked)

    # Top-3 share
    top3 = ranked[:3]
    top3_share = sum(item["share_percent"] for item in top3)

    top3_detail = [
        {
            "country": item["country"],
            "country_iso": item.get("country_iso"),
            "quantity": item["quantity"],
            "units": item.get("units", ""),
            "share_percent": item["share_percent"],
        }
        for item in top3
    ]

    return {
        "commodity": commodity,
        "year": actual_year,
        "hhi": round(hhi, 1),
        "hhi_category": classify_hhi(hhi),
        "top3_share_percent": round(top3_share, 1),
        "top3_category": classify_top3(top3_share),
        "top3_countries": top3_detail,
        "total_countries": len(ranked),
    }


def compute_nir(commodity: str) -> Dict[str, Any]:
    """Compute NIR from USGS salient statistics."""
    try:
        from cmm_data.loaders.usgs_commodity import USGSCommodityLoader, COMMODITY_NAMES

        # Map commodity name to USGS code
        name_lower = commodity.lower()
        usgs_code = None
        for code, full_name in COMMODITY_NAMES.items():
            if name_lower in full_name.lower() or full_name.lower() in name_lower:
                usgs_code = code
                break

        if not usgs_code:
            return {"error": f"No USGS mapping for '{commodity}'", "nir_percent": None}

        loader = USGSCommodityLoader()
        if usgs_code not in loader.list_available():
            return {"error": f"USGS data not available for '{usgs_code}'", "nir_percent": None}

        df = loader.load_salient_statistics(usgs_code)

        if "NIR_pct_clean" in df.columns:
            # Get the most recent NIR value
            valid = df[df["NIR_pct_clean"].notna()].sort_values("Year", ascending=False)
            if not valid.empty:
                nir_val = float(valid.iloc[0]["NIR_pct_clean"])
                year = valid.iloc[0].get("Year", "unknown")
                return {
                    "commodity": commodity,
                    "usgs_code": usgs_code,
                    "nir_percent": round(nir_val, 1),
                    "nir_category": classify_nir(nir_val),
                    "year": year,
                }

        return {"error": "NIR data not found in salient statistics", "nir_percent": None}

    except Exception as e:
        return {"error": str(e), "nir_percent": None}


async def compute_trend(
    commodity: str,
    year_from: Optional[int] = None,
) -> Dict[str, Any]:
    """Compute production trend over time."""
    client = BGSClient()

    bgs_name = resolve_bgs_commodity(commodity)
    print(f"Computing trend for: {commodity} (BGS: {bgs_name})", file=sys.stderr)

    records = await client.search_production(
        commodity=bgs_name,
        year_from=year_from,
        limit=5000,
    )

    if not records:
        return {"error": f"No production data for {commodity}"}

    # Aggregate by year
    yearly_totals: Dict[int, float] = {}
    for r in records:
        if r.year and r.quantity is not None:
            yearly_totals[r.year] = yearly_totals.get(r.year, 0) + float(r.quantity)

    if len(yearly_totals) < 2:
        return {"error": "Not enough years for trend analysis"}

    sorted_years = sorted(yearly_totals.items())
    first_year, first_val = sorted_years[0]
    last_year, last_val = sorted_years[-1]

    if first_val > 0:
        total_change_pct = ((last_val - first_val) / first_val) * 100
    else:
        total_change_pct = 0

    # Determine direction
    if total_change_pct > 10:
        direction = "INCREASING"
    elif total_change_pct < -10:
        direction = "DECLINING"
    else:
        direction = "STABLE"

    # Year-over-year changes
    yoy_changes = []
    for i in range(1, len(sorted_years)):
        prev_year, prev_val = sorted_years[i - 1]
        curr_year, curr_val = sorted_years[i]
        if prev_val > 0:
            change = ((curr_val - prev_val) / prev_val) * 100
        else:
            change = 0
        yoy_changes.append({
            "year": curr_year,
            "production": round(curr_val, 1),
            "change_pct": round(change, 1),
        })

    return {
        "commodity": commodity,
        "period": f"{first_year}-{last_year}",
        "direction": direction,
        "total_change_pct": round(total_change_pct, 1),
        "years_analyzed": len(sorted_years),
        "yearly_data": yoy_changes,
    }


async def run_analysis(
    commodity: str,
    year: Optional[int] = None,
    year_from: Optional[int] = None,
    metrics: List[str] = None,
) -> Dict[str, Any]:
    """Run full supply chain analysis."""
    if metrics is None:
        metrics = ["hhi", "nir", "top3share", "trend"]

    result = {"commodity": commodity}

    if "hhi" in metrics or "top3share" in metrics:
        hhi_data = await compute_hhi_and_top3(commodity, year)
        if "hhi" in metrics:
            result["hhi"] = {
                "score": hhi_data.get("hhi"),
                "category": hhi_data.get("hhi_category"),
                "year": hhi_data.get("year"),
                "total_countries": hhi_data.get("total_countries"),
            }
        if "top3share" in metrics:
            result["top3_share"] = {
                "percent": hhi_data.get("top3_share_percent"),
                "category": hhi_data.get("top3_category"),
                "countries": hhi_data.get("top3_countries"),
            }

    if "nir" in metrics:
        nir_data = compute_nir(commodity)
        result["nir"] = nir_data

    if "trend" in metrics:
        trend_data = await compute_trend(commodity, year_from)
        result["trend"] = trend_data

    # Overall risk assessment
    risk_scores = []
    if result.get("hhi", {}).get("category"):
        risk_map = {"LOW": 1, "MODERATE": 2, "HIGH": 3}
        risk_scores.append(risk_map.get(result["hhi"]["category"], 0))
    if result.get("top3_share", {}).get("category"):
        risk_map = {"LOW": 1, "MODERATE": 2, "HIGH": 3}
        risk_scores.append(risk_map.get(result["top3_share"]["category"], 0))
    if result.get("nir", {}).get("nir_category"):
        risk_map = {"LOW": 1, "MODERATE": 2, "HIGH": 3}
        risk_scores.append(risk_map.get(result["nir"]["nir_category"], 0))

    if risk_scores:
        avg_risk = sum(risk_scores) / len(risk_scores)
        if avg_risk >= 2.5:
            result["overall_risk"] = "HIGH"
        elif avg_risk >= 1.5:
            result["overall_risk"] = "MODERATE"
        else:
            result["overall_risk"] = "LOW"

    return result


def format_summary(result: Dict[str, Any]) -> str:
    """Format analysis as human-readable summary."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"Supply Chain Risk Assessment: {result['commodity']}")
    lines.append("=" * 70)

    if result.get("overall_risk"):
        lines.append(f"\nOverall Risk: {result['overall_risk']}")
        lines.append("")

    if "hhi" in result and result["hhi"].get("score") is not None:
        h = result["hhi"]
        lines.append(f"HHI Concentration Index: {h['score']} ({h['category']})")
        lines.append(f"  Year: {h.get('year', 'N/A')}, Countries: {h.get('total_countries', 'N/A')}")

    if "top3_share" in result and result["top3_share"].get("percent") is not None:
        t = result["top3_share"]
        lines.append(f"\nTop-3 Producer Share: {t['percent']}% ({t['category']})")
        if t.get("countries"):
            for c in t["countries"]:
                lines.append(f"  {c['country']}: {c['share_percent']}%"
                             f" ({c['quantity']:,.0f} {c.get('units', '')})")

    if "nir" in result:
        n = result["nir"]
        if n.get("nir_percent") is not None:
            lines.append(f"\nUS Net Import Reliance: {n['nir_percent']}% ({n.get('nir_category', 'N/A')})")
        elif n.get("error"):
            lines.append(f"\nUS Net Import Reliance: {n['error']}")

    if "trend" in result:
        tr = result["trend"]
        if tr.get("direction"):
            lines.append(f"\nProduction Trend: {tr['direction']} ({tr.get('total_change_pct', 0):+.1f}%)")
            lines.append(f"  Period: {tr.get('period', 'N/A')}, Years analyzed: {tr.get('years_analyzed', 0)}")
        elif tr.get("error"):
            lines.append(f"\nProduction Trend: {tr['error']}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Compute supply chain risk metrics for critical minerals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Metrics: hhi, nir, top3share, trend, all

Examples:
  %(prog)s --commodity "Lithium"
  %(prog)s --commodity "Cobalt" --metrics hhi,top3share
  %(prog)s --commodity "Rare earths" --metrics trend --year-from 2015
  %(prog)s --commodity "Graphite" --format json
        """
    )

    parser.add_argument("--commodity", "-c", required=True, help="Commodity name (BGS naming)")
    parser.add_argument("--year", "-y", type=int, help="Target year (default: latest)")
    parser.add_argument("--year-from", type=int, help="Start year for trend analysis")
    parser.add_argument(
        "--metrics", "-m",
        default="all",
        help="Comma-separated metrics: hhi, nir, top3share, trend, all (default: all)"
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    if args.metrics == "all":
        metrics = ["hhi", "nir", "top3share", "trend"]
    else:
        metrics = [m.strip() for m in args.metrics.split(",")]

    result = asyncio.run(run_analysis(
        commodity=args.commodity,
        year=args.year,
        year_from=args.year_from,
        metrics=metrics,
    ))

    if args.format == "json":
        print(json.dumps(result, indent=2, default=str))
    else:
        print(format_summary(result))


if __name__ == "__main__":
    main()
