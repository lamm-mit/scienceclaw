#!/usr/bin/env python3
"""
PubMed Database Query Script

Search PubMed biomedical literature via NCBI E-utilities.

Usage:
    python query.py --query "CRISPR gene editing" [--limit 10] [--format json]
    python query.py --search "cancer immunotherapy" --limit 5
"""

import argparse
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EMAIL = os.environ.get("NCBI_EMAIL", "scienceclaw@example.com")
API_KEY = os.environ.get("NCBI_API_KEY", "")


def esearch(query, limit=10, date_range=None):
    """Run NCBI esearch and return list of PMIDs."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": limit,
        "retmode": "json",
        "sort": "relevance",
        "email": EMAIL,
    }
    if API_KEY:
        params["api_key"] = API_KEY
    # Apply date range if provided (e.g., "2020:2024")
    if date_range:
        parts = str(date_range).split(":")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            params["datetype"] = "pdat"
            params["mindate"] = parts[0]
            params["maxdate"] = parts[1]
    r = requests.get(f"{NCBI_BASE}/esearch.fcgi", params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("esearchresult", {}).get("idlist", [])


def efetch(pmids):
    """Fetch paper details for a list of PMIDs."""
    if not pmids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "email": EMAIL,
    }
    if API_KEY:
        params["api_key"] = API_KEY
    r = requests.get(f"{NCBI_BASE}/efetch.fcgi", params=params, timeout=20)
    r.raise_for_status()
    return parse_xml(r.text)


def parse_xml(xml_text):
    """Parse PubMed XML into a list of paper dicts."""
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_text)
    except Exception:
        return []

    papers = []
    for article in root.findall(".//PubmedArticle"):
        try:
            citation = article.find("MedlineCitation")
            art = citation.find("Article")

            pmid = citation.findtext("PMID", "")
            title = art.findtext("ArticleTitle", "").strip()
            abstract_parts = [e.text or "" for e in art.findall(".//AbstractText")]
            abstract = " ".join(abstract_parts).strip()

            # Authors
            authors = []
            for auth in art.findall(".//Author"):
                last = auth.findtext("LastName", "")
                initials = auth.findtext("Initials", "")
                if last:
                    authors.append(f"{last} {initials}".strip())

            # Journal + year
            journal = art.findtext(
                ".//Journal/Title",
                art.findtext(".//Journal/ISOAbbreviation", "")
            )
            pubdate = art.find(".//PubDate")
            year = ""
            if pubdate is not None:
                year = pubdate.findtext("Year", "")
                if not year:
                    medline = pubdate.findtext("MedlineDate", "")
                    year = medline[:4] if medline else ""

            doi = ""
            for aid in art.findall(".//ELocationID"):
                if aid.get("EIdType") == "doi":
                    doi = aid.text or ""

            papers.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors[:6],
                "journal": journal,
                "year": year,
                "doi": doi,
            })
        except Exception:
            continue
    return papers


def search_pubmed(query, limit=10, filters=None):
    """Search PubMed and return papers."""
    # Extract date range from filters (e.g., "2020:2024")
    date_range = None
    if filters:
        for f in filters:
            if ":" in f and all(p.isdigit() for p in f.split(":")):
                date_range = f
                break
    pmids = esearch(query, limit, date_range=date_range)
    if not pmids:
        return {"query": query, "papers": [], "total": 0}
    time.sleep(0.35)  # NCBI rate limit: 3 req/s without key
    papers = efetch(pmids)
    return {"query": query, "papers": papers, "total": len(papers)}

def main():
    parser = argparse.ArgumentParser(description="Search PubMed via NCBI E-utilities")
    parser.add_argument(
        "--query", "--search", "-q", "-s",
        dest="search",
        required=True,
        help="Search term"
    )
    parser.add_argument(
        "--limit", "--max-results", "-l",
        dest="limit",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)"
    )
    parser.add_argument(
        "--format", "-f",
        default="json",
        choices=["summary", "json"],
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--filters",
        nargs="+",
        default=None,
        help="Optional filters, e.g. '2020:2024' for date range"
    )

    args = parser.parse_args()

    try:
        result = search_pubmed(args.search, args.limit, filters=args.filters)

        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print(f"PubMed search: '{args.search}'")
            print(f"Papers found: {result['total']}")
            for p in result["papers"][:5]:
                print(f"  [{p['pmid']}] {p['title'][:80]}")
                print(f"    {p['journal']} ({p['year']})")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
