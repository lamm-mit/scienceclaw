#!/usr/bin/env python3
"""
COSMIC Database Query Script

Search COSMIC Cancer Gene Census and resistance mutations.
Credentials read from COSMIC_EMAIL and COSMIC_PASSWORD environment variables.
Uses session-based authentication (COSMIC changed from Basic auth to session cookies).

Usage:
    python query.py --query "KRAS" [--limit 10] [--format json]
    python query.py --search "TP53" --no-resistance

Registration (free for academic): https://cancer.sanger.ac.uk/cosmic/register
"""

import argparse
import csv
import gzip
import io
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

COSMIC_BASE = "https://cancer.sanger.ac.uk/cosmic"
CACHE_DIR = Path.home() / ".scienceclaw" / "cache" / "cosmic"

EMAIL = os.environ.get("COSMIC_EMAIL", "")
PASSWORD = os.environ.get("COSMIC_PASSWORD", "")

# v100+ uses different file naming; v99 has the classic naming (cancer_gene_census.csv)
GENE_CENSUS_PATH = "GRCh38/cosmic/v99/cancer_gene_census.csv"
RESISTANCE_PATH = "GRCh38/cosmic/v99/CosmicResistanceMutations.tsv.gz"


def _make_session() -> requests.Session:
    """Create an authenticated COSMIC session using session cookies."""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})

    if not EMAIL or not PASSWORD:
        raise PermissionError(
            "COSMIC credentials not set. Add to ~/.bashrc:\n"
            "  export COSMIC_EMAIL='your.email@example.com'\n"
            "  export COSMIC_PASSWORD='your_cosmic_password'\n"
            "Register free at: https://cancer.sanger.ac.uk/cosmic/register"
        )

    resp = session.post(
        f"{COSMIC_BASE}/login",
        data={"email": EMAIL, "pass": PASSWORD, "r_url": "", "d": "0"},
        timeout=30,
    )
    # Successful login redirects to COSMIC homepage (not back to /login)
    if resp.url.rstrip("/").endswith("/login"):
        raise PermissionError(
            "COSMIC login failed — check COSMIC_EMAIL and COSMIC_PASSWORD"
        )
    return session


def _get_signed_url(session: requests.Session, filepath: str) -> str:
    """Get a signed S3 download URL for a COSMIC file."""
    r = session.get(
        f"{COSMIC_BASE}/file_download/{filepath}",
        headers={"Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return data["url"]


def _download_file(filepath: str, cache_name: str, cache_hours: int = 168) -> str:
    """Download a COSMIC text file, caching locally."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / cache_name

    if cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < cache_hours:
            return cache_file.read_text(encoding="utf-8", errors="replace")

    session = _make_session()
    url = _get_signed_url(session, filepath)

    r = session.get(url, timeout=120)
    r.raise_for_status()

    content = r.text
    cache_file.write_text(content, encoding="utf-8", errors="replace")
    return content


def _download_gz(filepath: str, cache_name: str, cache_hours: int = 168) -> str:
    """Download a gzipped COSMIC file, caching locally."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / cache_name

    if cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < cache_hours:
            return cache_file.read_text(encoding="utf-8", errors="replace")

    session = _make_session()
    url = _get_signed_url(session, filepath)

    r = session.get(url, timeout=180)
    r.raise_for_status()

    content = gzip.decompress(r.content).decode("utf-8", errors="replace")
    cache_file.write_text(content, encoding="utf-8", errors="replace")
    return content


def search_gene_census(query: str, limit: int = 10) -> list:
    """Search the COSMIC Cancer Gene Census for matching genes."""
    content = _download_file(GENE_CENSUS_PATH, "gene_census.csv")
    q = query.lower()
    matches = []
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        gene_name = row.get("Gene Symbol", row.get("gene_name", "")).strip()
        if q in gene_name.lower() or q in row.get("Name", "").lower():
            matches.append({
                "gene": gene_name,
                "name": row.get("Name", ""),
                "role": row.get("Role in Cancer", row.get("role_in_cancer", "")),
                "tier": row.get("Tier", ""),
                "cancer_types": row.get("Tumour Types(Somatic)", row.get("tumour_types_somatic", ""))[:120],
                "hallmarks": row.get("Hallmark", ""),
                "cosmic_id": row.get("Gene ID", ""),
            })
            if len(matches) >= limit:
                break
    return matches


def search_resistance_mutations(query: str, limit: int = 10) -> list:
    """Search COSMIC resistance mutations for a gene/drug query."""
    content = _download_gz(RESISTANCE_PATH, "resistance_mutations.tsv")
    q = query.lower()
    matches = []
    reader = csv.DictReader(io.StringIO(content), delimiter="\t")
    for row in reader:
        gene = row.get("Gene Name", "").strip()
        drug = row.get("Drug Name", "").strip()
        if q in gene.lower() or q in drug.lower():
            matches.append({
                "gene": gene,
                "mutation": row.get("AA Mutation", ""),
                "drug": drug,
                "cancer_type": row.get("Primary Site", ""),
                "resistance_type": row.get("Resistance Type", ""),
                "publication": row.get("PubMed Id", ""),
            })
            if len(matches) >= limit:
                break
    return matches


def query_cosmic(query: str, limit: int = 10, include_resistance: bool = True) -> dict:
    """Search COSMIC for a gene/drug query."""
    result = {"query": query, "gene_census": [], "resistance_mutations": []}

    try:
        result["gene_census"] = search_gene_census(query, limit)
    except PermissionError as e:
        return {"error": str(e), "query": query}
    except Exception as e:
        result["gene_census_error"] = str(e)

    if include_resistance:
        try:
            result["resistance_mutations"] = search_resistance_mutations(query, limit)
        except PermissionError as e:
            return {"error": str(e), "query": query}
        except Exception as e:
            result["resistance_mutations_error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Query COSMIC cancer mutation database")
    parser.add_argument(
        "--query", "--search", "-q", "-s",
        dest="query",
        required=True,
        help="Gene name or drug query (e.g. KRAS, ibrutinib)"
    )
    parser.add_argument(
        "--limit", "--max-results", "-l",
        dest="limit",
        type=int,
        default=10,
        help="Maximum results per category (default: 10)"
    )
    parser.add_argument(
        "--format", "-f",
        default="json",
        choices=["summary", "json"],
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--no-resistance",
        action="store_true",
        help="Skip resistance mutation search (faster)"
    )

    args = parser.parse_args()

    result = query_cosmic(args.query, args.limit, not args.no_resistance)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        print(f"COSMIC search: '{args.query}'")
        print(f"  Gene census matches: {len(result.get('gene_census', []))}")
        for g in result.get("gene_census", [])[:5]:
            print(f"    {g['gene']}: {g['role']} (Tier {g['tier']})")
        print(f"  Resistance mutations: {len(result.get('resistance_mutations', []))}")
        for m in result.get("resistance_mutations", [])[:5]:
            print(f"    {m['gene']} {m['mutation']} → {m['drug']} resistance")


if __name__ == "__main__":
    main()
