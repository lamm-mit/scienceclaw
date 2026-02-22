#!/usr/bin/env python3
"""
Commodity Profile Generator for ScienceClaw

Generate comprehensive one-page commodity profiles by orchestrating
calls to multiple mineral-claw skills: bgs-production, comtrade-trade,
supply-chain-analysis, literature-meta-search, export-restrictions,
and critical-minerals web intelligence monitors.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
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

    python_exec = sys.executable or "python3"
    cmd = [python_exec, script_path] + args + ["--format", "json"]
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


def _parse_json(output: Optional[str], fallback: Any) -> Any:
    if not output:
        return fallback
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return fallback


def _dedupe_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for rec in records:
        url = str(rec.get("url", "")).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(rec)
    return out


def _count_policy_signals(records: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for rec in records:
        signal = rec.get("policy_signal")
        if not signal:
            continue
        signal_key = str(signal)
        counts[signal_key] = counts.get(signal_key, 0) + 1
    return counts


def get_production_data(commodity: str, year: Optional[int] = None) -> Dict[str, Any]:
    """Get production data from bgs-production."""
    print("  Fetching production data...", file=sys.stderr)
    script = os.path.join(SCIENCECLAW_SKILLS, "bgs-production", "scripts", "bgs_query.py")
    args = ["--query", commodity, "--ranking", "--top-n", "10"]
    if year:
        args.extend(["--year-from", str(year), "--year-to", str(year)])

    output = _run_skill(script, args)
    ranking = _parse_json(output, [])
    if isinstance(ranking, list):
        return {"ranking": ranking, "error": None}
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
    records = _parse_json(output, [])
    if isinstance(records, list):
        return {"records": records, "error": None}
    return {"records": [], "error": "Failed to fetch trade data"}


def get_risk_data(commodity: str, year: Optional[int] = None) -> Dict[str, Any]:
    """Get risk metrics from supply-chain-analysis."""
    print("  Computing risk metrics...", file=sys.stderr)
    script = os.path.join(SCIENCECLAW_SKILLS, "supply-chain-analysis", "scripts", "supply_chain_metrics.py")
    args = ["--commodity", commodity]
    if year:
        args.extend(["--year", str(year)])

    output = _run_skill(script, args, timeout=90)
    risk = _parse_json(output, {})
    if isinstance(risk, dict) and risk:
        return risk
    return {"error": "Failed to compute risk metrics"}


def get_research_data(commodity: str) -> Dict[str, Any]:
    """Get research from literature-meta-search."""
    print("  Searching literature...", file=sys.stderr)
    script = os.path.join(SCIENCECLAW_SKILLS, "literature-meta-search", "scripts", "meta_search.py")
    args = ["--query", f"{commodity} critical minerals", "--top-n", "5", "--sources", "osti,scholar"]

    output = _run_skill(script, args, timeout=90)
    papers = _parse_json(output, [])
    if isinstance(papers, list):
        return {"papers": papers, "error": None}
    return {"papers": [], "error": "Failed to fetch research"}


def get_policy_data(commodity: str) -> Dict[str, Any]:
    """Get policy data from export-restrictions."""
    print("  Checking export restrictions...", file=sys.stderr)
    script = os.path.join(SCIENCECLAW_SKILLS, "export-restrictions", "scripts", "restrictions_query.py")
    args = ["--commodity", commodity]

    output = _run_skill(script, args)
    policy = _parse_json(output, {})
    if isinstance(policy, dict) and policy:
        return policy
    return {"error": "Failed to fetch policy data"}


def get_web_intel(commodity: str, max_results: int = 20) -> Dict[str, Any]:
    """Get web intelligence by chaining news, government, and ingest skills."""
    print("  Collecting web intelligence...", file=sys.stderr)

    news_script = os.path.join(SCIENCECLAW_SKILLS, "minerals-news-monitor", "scripts", "news_monitor.py")
    gov_script = os.path.join(SCIENCECLAW_SKILLS, "minerals-gov-monitor", "scripts", "gov_monitor.py")
    ingest_script = os.path.join(SCIENCECLAW_SKILLS, "minerals-web-ingest", "scripts", "web_ingest.py")

    news_output = _run_skill(
        news_script,
        [
            "--query",
            f"{commodity} critical minerals",
            "--commodity",
            commodity,
            "--max-results",
            str(max(5, max_results)),
            "--source-type",
            "all",
        ],
        timeout=90,
    )
    news_records = _parse_json(news_output, [])
    if not isinstance(news_records, list):
        news_records = []

    gov_output = _run_skill(
        gov_script,
        ["--commodity", commodity, "--max-results", str(max(5, max_results))],
        timeout=90,
    )
    gov_records = _parse_json(gov_output, [])
    if not isinstance(gov_records, list):
        gov_records = []

    candidate_records = _dedupe_records(news_records + gov_records)[: max(10, max_results * 2)]
    monitor_stats = {
        "news_records": len(news_records),
        "government_records": len(gov_records),
        "candidate_urls": len(candidate_records),
    }

    if not candidate_records:
        return {
            "monitor_stats": monitor_stats,
            "ingest_stats": {},
            "top_signals": {},
            "high_confidence": [],
            "errors": [],
            "error": "Failed to collect monitor records from web intelligence skills",
        }

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp_file:
            json.dump(candidate_records, tmp_file)
            temp_path = tmp_file.name

        ingest_output = _run_skill(
            ingest_script,
            ["--input-json", temp_path, "--max-chars", "6000"],
            timeout=180,
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    ingest_result = _parse_json(ingest_output, {})
    if not isinstance(ingest_result, dict) or not ingest_result:
        return {
            "monitor_stats": monitor_stats,
            "ingest_stats": {},
            "top_signals": {},
            "high_confidence": [],
            "errors": [],
            "error": "Failed to ingest web intelligence content",
        }

    ingested = ingest_result.get("ingested", [])
    if not isinstance(ingested, list):
        ingested = []

    sorted_records = sorted(
        ingested,
        key=lambda r: float(r.get("confidence", 0.0)) if isinstance(r, dict) else 0.0,
        reverse=True,
    )
    high_confidence = [r for r in sorted_records if isinstance(r, dict)][: max(1, min(8, max_results))]

    errors = ingest_result.get("errors", [])
    if not isinstance(errors, list):
        errors = []

    return {
        "monitor_stats": monitor_stats,
        "ingest_stats": ingest_result.get("stats", {}),
        "top_signals": _count_policy_signals(sorted_records),
        "high_confidence": high_confidence,
        "errors": errors,
        "error": None,
    }


def generate_profile(
    commodity: str,
    year: Optional[int] = None,
    sections: Optional[List[str]] = None,
    intel_max_results: int = 20,
) -> Dict[str, Any]:
    """Generate comprehensive commodity profile."""
    if sections is None:
        sections = ["production", "trade", "risk", "research", "policy", "intel"]

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

    if "intel" in sections:
        profile["intel"] = get_web_intel(commodity, max_results=intel_max_results)

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
                    lines.append(
                        f"    {r.get('rank', '?'):>2}. {r.get('country', 'Unknown'):<30} "
                        f"{r.get('quantity', 0):>12,.0f} {r.get('units', '')} "
                        f"({r.get('share_percent', 0):.1f}%)"
                    )

    # Trade
    if "trade" in profile:
        trade = profile["trade"]
        lines.append("\n--- TRADE ---")
        if trade.get("error"):
            lines.append(f"  {trade['error']}")
        else:
            records = trade.get("records", [])
            lines.append(f"  {len(records)} trade records")
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

    # Web intelligence
    if "intel" in profile:
        intel = profile["intel"]
        lines.append("\n--- WEB INTELLIGENCE ---")
        if intel.get("error"):
            lines.append(f"  {intel['error']}")
        else:
            monitor_stats = intel.get("monitor_stats", {})
            ingest_stats = intel.get("ingest_stats", {})
            lines.append(
                f"  Monitor records: news={monitor_stats.get('news_records', 0)} "
                f"government={monitor_stats.get('government_records', 0)}"
            )
            if ingest_stats:
                lines.append(
                    f"  Ingested pages: {ingest_stats.get('ingested', 0)} "
                    f"(skipped={ingest_stats.get('skipped', 0)}, errors={ingest_stats.get('errors', 0)})"
                )

            top_signals = intel.get("top_signals", {})
            if top_signals:
                ranked = sorted(top_signals.items(), key=lambda item: item[1], reverse=True)
                lines.append("  Top policy signals:")
                for signal, count in ranked[:3]:
                    lines.append(f"    - {signal}: {count}")

            findings = intel.get("high_confidence", [])
            if findings:
                lines.append("  High-confidence web findings:")
                for finding in findings[:3]:
                    title = finding.get("title", "Untitled")[:72]
                    signal = finding.get("policy_signal") or "none"
                    confidence = finding.get("confidence", 0)
                    lines.append(f"    - {title} [policy={signal}, confidence={confidence}]")

    lines.append("\n" + "=" * 75)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive commodity profile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sections: production, trade, risk, research, policy, intel

Examples:
  %(prog)s --commodity "Lithium"
  %(prog)s --commodity "Cobalt" --sections production,risk,intel
  %(prog)s --commodity "Rare earths" --format json
        """
    )

    parser.add_argument("--commodity", "-c", required=True, help="Commodity name")
    parser.add_argument("--year", "-y", type=int, help="Target year")
    parser.add_argument(
        "--sections", "-s",
        default="production,trade,risk,research,policy,intel",
        help="Comma-separated sections (default: all)"
    )
    parser.add_argument(
        "--intel-max-results",
        type=int,
        default=20,
        help="Maximum web intelligence records to process (default: 20)",
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "json"],
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    sections = [s.strip() for s in args.sections.split(",") if s.strip()]

    profile = generate_profile(
        commodity=args.commodity,
        year=args.year,
        sections=sections,
        intel_max_results=max(1, args.intel_max_results),
    )

    if args.format == "json":
        print(json.dumps(profile, indent=2, default=str))
    else:
        print(format_summary(profile))


if __name__ == "__main__":
    main()
