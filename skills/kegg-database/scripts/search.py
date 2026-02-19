#!/usr/bin/env python3
"""
KEGG Database Search Script

Search KEGG for pathways, genes, drugs, and diseases by keyword.
Maps --query to kegg find across multiple databases and returns JSON.

Usage:
    python search.py --query "mTOR inhibitor" [--limit 10] [--format json]
    python search.py --search "PI3K signaling" --db pathway

KEGG API is free for academic use: https://www.kegg.jp/kegg/rest/keggapi.html
"""

import argparse
import json
import sys
import urllib.request
import urllib.parse
import urllib.error

KEGG_BASE = "https://rest.kegg.jp"


def kegg_find(database: str, query: str) -> list:
    """Search a KEGG database by keyword. Returns list of (id, name) tuples."""
    encoded = urllib.parse.quote(query, safe="")
    url = f"{KEGG_BASE}/find/{database}/{encoded}"
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            text = r.read().decode("utf-8")
        rows = []
        for line in text.strip().splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                rows.append({"id": parts[0].strip(), "name": parts[1].strip()})
        return rows
    except Exception:
        return []


def kegg_get_pathway(pathway_id: str) -> dict:
    """Get KEGG PATHWAY entry details in KGML-like summary."""
    url = f"{KEGG_BASE}/get/{pathway_id}"
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            text = r.read().decode("utf-8")
        entry = {"id": pathway_id, "raw": text[:500]}
        for line in text.splitlines():
            if line.startswith("NAME"):
                entry["name"] = line[12:].strip()
            elif line.startswith("DESCRIPTION"):
                entry["description"] = line[12:].strip()
            elif line.startswith("CLASS"):
                entry["class"] = line[12:].strip()
        return entry
    except Exception:
        return {"id": pathway_id}


def search_kegg(query: str, databases: list = None, limit: int = 10) -> dict:
    """Search KEGG across multiple databases for a query."""
    if databases is None:
        databases = ["pathway", "genes", "drug", "disease"]

    result = {"query": query, "pathways": [], "genes": [], "drugs": [], "diseases": []}

    db_map = {
        "pathway": "pathways",
        "genes": "genes",
        "drug": "drugs",
        "disease": "diseases",
        "compound": "compounds",
    }

    for db in databases:
        hits = kegg_find(db, query)[:limit]
        key = db_map.get(db, db)
        result[key] = hits

    # For pathways, try to get more detail on top hit
    if result.get("pathways"):
        top = result["pathways"][0]
        detail = kegg_get_pathway(top["id"])
        if "name" in detail:
            result["pathways"][0]["detail"] = detail.get("description", "")

    result["total"] = sum(len(result.get(k, [])) for k in db_map.values())
    return result


def main():
    parser = argparse.ArgumentParser(description="Search KEGG databases by keyword")
    parser.add_argument(
        "--query", "--search", "-q", "-s",
        dest="query",
        required=True,
        help="Search term (e.g. 'mTOR', 'PI3K signaling', 'rapamycin')"
    )
    parser.add_argument(
        "--db",
        default="all",
        choices=["all", "pathway", "genes", "drug", "disease", "compound"],
        help="Database to search (default: all)"
    )
    parser.add_argument(
        "--limit", "--max-results", "-l",
        dest="limit",
        type=int,
        default=10,
        help="Max results per database (default: 10)"
    )
    parser.add_argument(
        "--format", "-f",
        default="json",
        choices=["summary", "json"],
        help="Output format (default: json)"
    )

    args = parser.parse_args()

    if args.db == "all":
        dbs = ["pathway", "genes", "drug", "disease"]
    else:
        dbs = [args.db]

    result = search_kegg(args.query, dbs, args.limit)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"KEGG search: '{args.query}'")
        print(f"  Total hits: {result.get('total', 0)}")
        for db_key in ["pathways", "genes", "drugs", "diseases"]:
            items = result.get(db_key, [])
            if items:
                print(f"  {db_key.capitalize()} ({len(items)}):")
                for item in items[:3]:
                    print(f"    {item['id']}: {item['name'][:60]}")


if __name__ == "__main__":
    main()
