#!/usr/bin/env python3
"""
Commodity Profile Generator for ScienceClaw

Generate comprehensive one-page commodity profiles by orchestrating
calls to multiple mineral-claw skills: bgs-production, comtrade-trade,
supply-chain-analysis, literature-meta-search, export-restrictions.
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

SKILLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCIENCECLAW_SKILLS = os.path.dirname(SKILLS_DIR)

# Map commodity names to comtrade mineral keys
COMTRADE_MINERAL_MAP = {
    "lithium": "lithium",
    "cobalt": "cobalt",
    "rare earths": "rare_earth",
    "rare earth": "rare_earth",
    "graphite": "graphite",
    "nickel": "nickel",
    "manganese": "manganese",
    "gallium": "gallium",
    "germanium": "germanium",
    "copper": "copper",
}


def _run_skill(script_path: str, args: List[str], timeout: int = 60) -> Optional[str]:
    """Run a skill script and return raw JSON output."""
    if not os.path.exists(script_path):
        return None

    cmd = ["python3", script_path] + args + ["--format", "json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            skill_name = os.path.basename(os.path.dirname(os.path.dirname(script_path)))
            print(f"  Warning: {skill_name} failed: {result.stderr[:200]}", file=sys.stderr)
            return None
        return result.stdout.strip() or None
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        print(f"  Warning: {e}", file=sys.stderr)
        return None


def get_production_data(commodity: str, year: Optional[int] = None) -> Dict[str, Any]:
    """Get production data from bgs-production."""
    print("  Fetching production data...", file=sys.stderr)
    script = os.path.join(SCIENCECLAW_SKILLS, "bgs-production", "scripts", "bgs_query.py")
    args = ["--query", commodity, "--ranking", "--top-n", "10"]
    if year:
        args.extend(["--year-from", str(year), "--year-to", str(year)])

    output = _run_skill(script, args)
    if output:
        try:
            return {"ranking": json.loads(output), "error": None}
        except json.JSONDecodeError:
            pass
    return {"ranking": [], "error": "Failed to fetch production data"}


def get_trade_data(commodity: str, year: Optional[int] = None, reporter: str = "842") -> Dict[str, Any]:
    """Get trade data from comtrade-trade.

    Default reporter is US (842). The Comtrade API returns empty results
    when querying all reporters (0) in a single request.
    """
    mineral_key = COMTRADE_MINERAL_MAP.get(commodity.lower())
    if not mineral_key:
        return {"records": [], "error": f"No Comtrade mapping for '{commodity}'"}

    print("  Fetching trade data...", file=sys.stderr)
    script = os.path.join(SCIENCECLAW_SKILLS, "comtrade-trade", "scripts", "comtrade_query.py")
    args = ["--mineral", mineral_key, "--reporter", reporter, "--limit", "20"]
    if year:
        args.extend(["--year", str(year)])

    output = _run_skill(script, args)
    if output:
        try:
            return {"records": json.loads(output), "error": None}
        except json.JSONDecodeError:
            pass
    return {"records": [], "error": "Failed to fetch trade data"}


def get_risk_data(commodity: str, year: Optional[int] = None) -> Dict[str, Any]:
    """Get risk metrics from supply-chain-analysis."""
    print("  Computing risk metrics...", file=sys.stderr)
    script = os.path.join(SCIENCECLAW_SKILLS, "supply-chain-analysis", "scripts", "supply_chain_metrics.py")
    args = ["--commodity", commodity]
    if year:
        args.extend(["--year", str(year)])

    output = _run_skill(script, args, timeout=90)
    if output:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass
    return {"error": "Failed to compute risk metrics"}


def get_research_data(commodity: str) -> Dict[str, Any]:
    """Get research from literature-meta-search."""
    print("  Searching literature...", file=sys.stderr)
    script = os.path.join(SCIENCECLAW_SKILLS, "literature-meta-search", "scripts", "meta_search.py")
    args = ["--query", f"{commodity} critical minerals", "--top-n", "5", "--sources", "osti,scholar"]

    output = _run_skill(script, args, timeout=90)
    if output:
        try:
            return {"papers": json.loads(output), "error": None}
        except json.JSONDecodeError:
            pass
    return {"papers": [], "error": "Failed to fetch research"}


def get_policy_data(commodity: str) -> Dict[str, Any]:
    """Get policy data from export-restrictions."""
    print("  Checking export restrictions...", file=sys.stderr)
    script = os.path.join(SCIENCECLAW_SKILLS, "export-restrictions", "scripts", "restrictions_query.py")
    args = ["--commodity", commodity]

    output = _run_skill(script, args)
    if output:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass
    return {"error": "Failed to fetch policy data"}


def generate_profile(
    commodity: str,
    year: Optional[int] = None,
    sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate comprehensive commodity profile."""
    if sections is None:
        sections = ["production", "trade", "risk", "research", "policy"]

    print(f"Generating profile for: {commodity}", file=sys.stderr)
    print(f"Sections: {', '.join(sections)}", file=sys.stderr)
    print("", file=sys.stderr)

    profile = {
        "commodity": commodity,
        "year": year or "latest",
    }

    if "production" in sections:
        profile["production"] = get_production_data(commodity, year)

    if "trade" in sections:
        profile["trade"] = get_trade_data(commodity, year)

    if "risk" in sections:
        profile["risk"] = get_risk_data(commodity, year)

    if "research" in sections:
        profile["research"] = get_research_data(commodity)

    if "policy" in sections:
        profile["policy"] = get_policy_data(commodity)

    return profile


def format_summary(profile: Dict[str, Any]) -> str:
    """Format profile as human-readable summary."""
    lines = []
    lines.append("=" * 75)
    lines.append(f"  COMMODITY PROFILE: {profile['commodity'].upper()}")
    lines.append(f"  Year: {profile.get('year', 'latest')}")
    lines.append("=" * 75)

    # Production
    if "production" in profile:
        prod = profile["production"]
        lines.append("\n--- PRODUCTION ---")
        if prod.get("error"):
            lines.append(f"  {prod['error']}")
        else:
            ranking = prod.get("ranking", [])
            if ranking:
                lines.append(f"  Top producers ({len(ranking)} countries):")
                for r in ranking[:5]:
                    lines.append(f"    {r.get('rank', '?'):>2}. {r.get('country', 'Unknown'):<30} "
                                 f"{r.get('quantity', 0):>12,.0f} {r.get('units', '')} "
                                 f"({r.get('share_percent', 0):.1f}%)")

    # Trade
    if "trade" in profile:
        trade = profile["trade"]
        lines.append("\n--- TRADE ---")
        if trade.get("error"):
            lines.append(f"  {trade['error']}")
        else:
            records = trade.get("records", [])
            lines.append(f"  {len(records)} trade records")
            # Summarize imports/exports
            imports = [r for r in records if r.get("flow_code") == "M"]
            exports = [r for r in records if r.get("flow_code") == "X"]
            total_import_value = sum(r.get("trade_value_usd", 0) or 0 for r in imports)
            total_export_value = sum(r.get("trade_value_usd", 0) or 0 for r in exports)
            if total_import_value:
                lines.append(f"  Total import value: ${total_import_value:,.0f}")
            if total_export_value:
                lines.append(f"  Total export value: ${total_export_value:,.0f}")

    # Risk
    if "risk" in profile:
        risk = profile["risk"]
        lines.append("\n--- SUPPLY CHAIN RISK ---")
        if risk.get("error"):
            lines.append(f"  {risk['error']}")
        else:
            if risk.get("overall_risk"):
                lines.append(f"  Overall risk: {risk['overall_risk']}")
            hhi = risk.get("hhi", {})
            if hhi.get("score"):
                lines.append(f"  HHI: {hhi['score']} ({hhi.get('category', '')})")
            top3 = risk.get("top3_share", {})
            if top3.get("percent"):
                lines.append(f"  Top-3 share: {top3['percent']}% ({top3.get('category', '')})")
            nir = risk.get("nir", {})
            if nir.get("nir_percent") is not None:
                lines.append(f"  US NIR: {nir['nir_percent']}% ({nir.get('nir_category', '')})")

    # Research
    if "research" in profile:
        research = profile["research"]
        lines.append("\n--- RECENT RESEARCH ---")
        if research.get("error"):
            lines.append(f"  {research['error']}")
        else:
            papers = research.get("papers", [])
            lines.append(f"  {len(papers)} recent publications:")
            for p in papers[:3]:
                title = p.get("title", "Unknown")[:70]
                year = p.get("year", "?")
                lines.append(f"    - {title} ({year})")

    # Policy
    if "policy" in profile:
        policy = profile["policy"]
        lines.append("\n--- EXPORT RESTRICTIONS ---")
        if policy.get("error"):
            lines.append(f"  {policy['error']}")
        else:
            corpus = policy.get("corpus_results", [])
            if corpus:
                lines.append(f"  {len(corpus)} policy document matches")
                for c in corpus[:2]:
                    lines.append(f"    - {c.get('title', 'Unknown')[:60]}")
            else:
                lines.append("  No specific restriction data found")

    lines.append("\n" + "=" * 75)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive commodity profile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sections: production, trade, risk, research, policy

Examples:
  %(prog)s --commodity "Lithium"
  %(prog)s --commodity "Cobalt" --sections production,risk
  %(prog)s --commodity "Rare earths" --format json
        """
    )

    parser.add_argument("--commodity", "-c", required=True, help="Commodity name")
    parser.add_argument("--year", "-y", type=int, help="Target year")
    parser.add_argument(
        "--sections", "-s",
        default="production,trade,risk,research,policy",
        help="Comma-separated sections (default: all)"
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    sections = [s.strip() for s in args.sections.split(",")]

    profile = generate_profile(
        commodity=args.commodity,
        year=args.year,
        sections=sections,
    )

    if args.format == "json":
        print(json.dumps(profile, indent=2, default=str))
    else:
        print(format_summary(profile))


if __name__ == "__main__":
    main()
