#!/usr/bin/env python3
"""
ClinicalTrials.gov Query Script

Search clinical trials by condition, intervention, or general query.
Uses ClinicalTrials.gov API v2 (no authentication required).

Usage:
    python query.py --query "KRAS G12C" [--limit 10] [--format json]
    python query.py --condition "lung cancer" --status RECRUITING --limit 5

API documentation: https://clinicaltrials.gov/data-api/api
"""

import argparse
import json
import sys

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

BASE_URL = "https://clinicaltrials.gov/api/v2"


def search_trials(
    query: str = None,
    condition: str = None,
    intervention: str = None,
    status: str = None,
    limit: int = 10,
) -> dict:
    """Search ClinicalTrials.gov and return structured trial data."""
    params = {
        "pageSize": min(limit, 100),
        "sort": "LastUpdatePostDate:desc",
        "format": "json",
    }

    if condition:
        params["query.cond"] = condition
    elif query:
        # Use query as both condition and intervention search
        params["query.term"] = query

    if intervention:
        params["query.intr"] = intervention

    if status:
        params["filter.overallStatus"] = status

    try:
        r = requests.get(f"{BASE_URL}/studies", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": str(e), "trials": [], "total": 0}

    trials = []
    for study in data.get("studies", []):
        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status_mod = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        desc = protocol.get("descriptionModule", {})
        arms = protocol.get("armsInterventionsModule", {})

        interventions = [
            f"{iv.get('type', '')}: {iv.get('name', '')}"
            for iv in arms.get("interventions", [])[:3]
        ]

        trials.append({
            "nct_id": ident.get("nctId", ""),
            "title": ident.get("briefTitle", ident.get("officialTitle", "")),
            "status": status_mod.get("overallStatus", ""),
            "phase": design.get("phases", []),
            "enrollment": design.get("enrollmentInfo", {}).get("count"),
            "conditions": protocol.get("conditionsModule", {}).get("conditions", [])[:5],
            "interventions": interventions,
            "brief_summary": (desc.get("briefSummary") or "")[:300],
            "last_update": status_mod.get("lastUpdatePostDateStruct", {}).get("date", ""),
        })

    return {
        "query": query or condition or "",
        "trials": trials,
        "total": data.get("totalCount", len(trials)),
    }


def main():
    parser = argparse.ArgumentParser(description="Search ClinicalTrials.gov")
    parser.add_argument(
        "--query", "--search", "-q", "-s",
        dest="query",
        help="General search term"
    )
    parser.add_argument(
        "--condition", "-c",
        help="Disease or condition (overrides --query for condition search)"
    )
    parser.add_argument(
        "--intervention", "-i",
        help="Drug, treatment, or intervention"
    )
    parser.add_argument(
        "--status",
        choices=["RECRUITING", "COMPLETED", "ACTIVE_NOT_RECRUITING",
                 "NOT_YET_RECRUITING", "TERMINATED", "SUSPENDED", "WITHDRAWN"],
        help="Filter by trial status"
    )
    parser.add_argument(
        "--limit", "--max-results", "-l",
        dest="limit",
        type=int,
        default=10,
        help="Maximum results (default: 10)"
    )
    parser.add_argument(
        "--format", "-f",
        default="json",
        choices=["summary", "json"],
        help="Output format (default: json)"
    )

    args = parser.parse_args()

    if not args.query and not args.condition and not args.intervention:
        parser.error("At least one of --query, --condition, or --intervention is required")

    result = search_trials(
        query=args.query,
        condition=args.condition,
        intervention=args.intervention,
        status=args.status,
        limit=args.limit,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        print(f"ClinicalTrials.gov search: '{result['query']}'")
        print(f"Total trials found: {result['total']}")
        for t in result["trials"][:5]:
            phases = "/".join(t.get("phase", [])) or "N/A"
            print(f"  [{t['nct_id']}] {t['title'][:70]}")
            print(f"    Status: {t['status']} | Phase: {phases} | n={t.get('enrollment', '?')}")


if __name__ == "__main__":
    main()
