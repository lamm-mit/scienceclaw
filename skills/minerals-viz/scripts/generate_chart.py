#!/usr/bin/env python3
"""
Minerals Visualization Tool for ScienceClaw

Generate charts (PNG/SVG) for critical minerals data using the
cmm_data visualizations module.
"""

import argparse
import json
import os
import re
import sys
from typing import Optional

try:
    sys.path.insert(0, "/Users/nancywashton/cmm-data/src")
    from cmm_data.loaders.usgs_commodity import USGSCommodityLoader, COMMODITY_NAMES
except ImportError:
    print("Error: cmm_data package is required.", file=sys.stderr)
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
except ImportError:
    print("Error: matplotlib is required. Install with: pip install matplotlib", file=sys.stderr)
    sys.exit(1)

try:
    from cmm_data.visualizations import (
        plot_world_production,
        plot_production_timeseries,
        plot_import_reliance,
    )
except ImportError:
    print("Error: cmm_data.visualizations not available.", file=sys.stderr)
    sys.exit(1)


def _detect_production_year_col(df) -> str:
    """Auto-detect the production estimate column (varies by MCS year)."""
    # Look for Prod_t_est_YYYY columns (the estimate for the latest year)
    import re
    est_cols = [c for c in df.columns if re.match(r"Prod_t_est_\d{4}$", c)]
    if est_cols:
        # Pick the latest year
        return sorted(est_cols)[-1]
    # Fallback to any Prod_t_YYYY column
    prod_cols = [c for c in df.columns if re.match(r"Prod_t_\d{4}$", c)]
    if prod_cols:
        return sorted(prod_cols)[-1]
    return "Prod_t_est_2022"


def generate_production_chart(
    commodity: str,
    output: Optional[str] = None,
    fmt: str = "png",
    top_n: int = 10,
) -> str:
    """Generate world production bar chart."""
    loader = USGSCommodityLoader()
    df = loader.load_world_production(commodity)
    commodity_name = COMMODITY_NAMES.get(commodity, commodity.title())
    year_col = _detect_production_year_col(df)

    fig = plot_world_production(df, commodity_name, top_n=top_n, year_col=year_col)

    if output is None:
        output = f"{commodity}_production.{fmt}"

    fig.savefig(output, dpi=150, bbox_inches="tight", format=fmt)
    plt.close(fig)

    return output


def _ensure_usprod_column(df):
    """Ensure USprod_t column exists for the timeseries viz.

    Some commodities split US production into Mine/Secondary/etc.
    The visualization expects a single USprod_t column.
    """
    if "USprod_t" not in df.columns and "USprod_t_clean" not in df.columns:
        # Sum all USprod_*_t columns to create a unified production column
        prod_cols = [c for c in df.columns if c.startswith("USprod_") and c.endswith("_t")]
        if prod_cols:
            df = df.copy()
            df["USprod_t"] = df[prod_cols].sum(axis=1, min_count=1)
    return df


def generate_timeseries_chart(
    commodity: str,
    output: Optional[str] = None,
    fmt: str = "png",
) -> str:
    """Generate production time series chart."""
    loader = USGSCommodityLoader()
    df = loader.load_salient_statistics(commodity)
    df = _ensure_usprod_column(df)
    commodity_name = COMMODITY_NAMES.get(commodity, commodity.title())

    fig = plot_production_timeseries(df, commodity_name)

    if output is None:
        output = f"{commodity}_timeseries.{fmt}"

    fig.savefig(output, dpi=150, bbox_inches="tight", format=fmt)
    plt.close(fig)

    return output


def generate_import_reliance_chart(
    commodity: str,
    output: Optional[str] = None,
    fmt: str = "png",
) -> str:
    """Generate import reliance chart."""
    loader = USGSCommodityLoader()
    df = loader.load_salient_statistics(commodity)
    commodity_name = COMMODITY_NAMES.get(commodity, commodity.title())

    fig = plot_import_reliance(df, commodity_name)

    if output is None:
        output = f"{commodity}_import_reliance.{fmt}"

    fig.savefig(output, dpi=150, bbox_inches="tight", format=fmt)
    plt.close(fig)

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Generate charts for critical minerals data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Chart types: production, timeseries, import-reliance

USGS commodity codes: {", ".join(sorted(COMMODITY_NAMES.keys())[:20])}...

Examples:
  %(prog)s --chart-type production --commodity lithi --top-n 10
  %(prog)s --chart-type timeseries --commodity cobal --output cobalt_trend.png
  %(prog)s --chart-type import-reliance --commodity raree --format svg
        """
    )

    parser.add_argument(
        "--chart-type", "-t",
        required=True,
        choices=["production", "timeseries", "import-reliance"],
        help="Chart type to generate"
    )
    parser.add_argument("--commodity", "-c", required=True, help="USGS commodity code")
    parser.add_argument("--output", "-o", help="Output file path (auto-generated if not set)")
    parser.add_argument(
        "--format", "-f",
        default="png",
        choices=["png", "svg"],
        help="Image format (default: png)"
    )
    parser.add_argument("--top-n", type=int, default=10, help="Top N countries for production chart (default: 10)")

    args = parser.parse_args()

    # Validate commodity
    if args.commodity not in COMMODITY_NAMES:
        # Try fuzzy match
        matches = [c for c in COMMODITY_NAMES if args.commodity.lower() in c.lower()]
        if matches:
            print(f"Did you mean: {', '.join(matches)}?", file=sys.stderr)
        else:
            print(f"Available codes: {', '.join(sorted(COMMODITY_NAMES.keys())[:30])}...", file=sys.stderr)
        sys.exit(1)

    print(f"Generating {args.chart_type} chart for {COMMODITY_NAMES[args.commodity]}...", file=sys.stderr)

    try:
        if args.chart_type == "production":
            output_path = generate_production_chart(
                args.commodity, args.output, args.format, args.top_n
            )
        elif args.chart_type == "timeseries":
            output_path = generate_timeseries_chart(
                args.commodity, args.output, args.format
            )
        elif args.chart_type == "import-reliance":
            output_path = generate_import_reliance_chart(
                args.commodity, args.output, args.format
            )

        abs_path = os.path.abspath(output_path)
        print(f"Chart saved to: {abs_path}", file=sys.stderr)

        # Output JSON result
        print(json.dumps({
            "chart_type": args.chart_type,
            "commodity": args.commodity,
            "commodity_name": COMMODITY_NAMES.get(args.commodity, args.commodity),
            "output_path": abs_path,
            "format": args.format,
        }, indent=2))

    except Exception as e:
        print(f"Error generating chart: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
