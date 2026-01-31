#!/usr/bin/env python3
"""
PubMed Search Tool for ScienceClaw

Searches PubMed for scientific literature and retrieves abstracts.
Uses NCBI E-utilities API via Biopython's Entrez module.
"""

import argparse
import json
import os
import sys
import time
from typing import List, Dict, Optional

try:
    from Bio import Entrez
except ImportError:
    print("Error: Biopython is required. Install with: pip install biopython")
    sys.exit(1)


# Configure Entrez
Entrez.email = os.environ.get("NCBI_EMAIL", "scienceclaw@example.com")
if os.environ.get("NCBI_API_KEY"):
    Entrez.api_key = os.environ.get("NCBI_API_KEY")


def search_pubmed(
    query: str,
    max_results: int = 10,
    sort: str = "relevance",
    year: Optional[int] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    author: Optional[str] = None,
    journal: Optional[str] = None
) -> List[str]:
    """
    Search PubMed and return list of PMIDs.

    Args:
        query: Search query
        max_results: Maximum number of results
        sort: Sort order (relevance, date, first_author)
        year: Specific publication year
        year_start: Start of date range
        year_end: End of date range
        author: Author name filter
        journal: Journal name filter

    Returns:
        List of PubMed IDs
    """
    # Build search query with filters
    search_terms = [query]

    if author:
        search_terms.append(f"{author}[Author]")

    if journal:
        search_terms.append(f"{journal}[Journal]")

    if year:
        search_terms.append(f"{year}[Date - Publication]")
    elif year_start or year_end:
        start = year_start or 1900
        end = year_end or 2100
        search_terms.append(f"{start}:{end}[Date - Publication]")

    full_query = " AND ".join(search_terms)

    # Map sort options
    sort_map = {
        "relevance": "relevance",
        "date": "pub_date",
        "first_author": "first_author"
    }
    sort_order = sort_map.get(sort, "relevance")

    print(f"Searching PubMed: {full_query}")
    print(f"Max results: {max_results}, Sort: {sort_order}")
    print("")

    handle = Entrez.esearch(
        db="pubmed",
        term=full_query,
        retmax=max_results,
        sort=sort_order
    )
    record = Entrez.read(handle)
    handle.close()

    pmids = record.get("IdList", [])
    total_count = record.get("Count", "0")

    print(f"Found {total_count} total results, returning {len(pmids)}")
    print("")

    return pmids


def fetch_articles(pmids: List[str]) -> List[Dict]:
    """
    Fetch article details for given PMIDs.

    Args:
        pmids: List of PubMed IDs

    Returns:
        List of article dictionaries
    """
    if not pmids:
        return []

    # Fetch article details
    handle = Entrez.efetch(
        db="pubmed",
        id=",".join(pmids),
        rettype="xml",
        retmode="xml"
    )
    records = Entrez.read(handle)
    handle.close()

    articles = []

    for article in records.get("PubmedArticle", []):
        medline = article.get("MedlineCitation", {})
        article_data = medline.get("Article", {})
        pubmed_data = article.get("PubmedData", {})

        # Extract PMID
        pmid = str(medline.get("PMID", ""))

        # Extract title
        title = article_data.get("ArticleTitle", "")

        # Extract abstract
        abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
        if isinstance(abstract_parts, list):
            abstract = " ".join(str(part) for part in abstract_parts)
        else:
            abstract = str(abstract_parts)

        # Extract authors
        author_list = article_data.get("AuthorList", [])
        authors = []
        for auth in author_list:
            if isinstance(auth, dict):
                last = auth.get("LastName", "")
                first = auth.get("ForeName", "")
                initials = auth.get("Initials", "")
                if last:
                    if first:
                        authors.append(f"{last} {initials}")
                    else:
                        authors.append(last)

        # Extract journal info
        journal_info = article_data.get("Journal", {})
        journal_title = journal_info.get("Title", "")
        journal_abbrev = journal_info.get("ISOAbbreviation", "")
        journal_issue = journal_info.get("JournalIssue", {})
        volume = journal_issue.get("Volume", "")
        issue = journal_issue.get("Issue", "")

        # Extract publication date
        pub_date = journal_issue.get("PubDate", {})
        year = pub_date.get("Year", "")
        month = pub_date.get("Month", "")

        # Extract pagination
        pagination = article_data.get("Pagination", {})
        pages = pagination.get("MedlinePgn", "")

        # Extract DOI
        doi = ""
        article_ids = pubmed_data.get("ArticleIdList", [])
        for aid in article_ids:
            if hasattr(aid, "attributes") and aid.attributes.get("IdType") == "doi":
                doi = str(aid)
                break

        # Extract MeSH terms
        mesh_list = medline.get("MeshHeadingList", [])
        mesh_terms = []
        for mesh in mesh_list:
            if isinstance(mesh, dict):
                descriptor = mesh.get("DescriptorName", "")
                if descriptor:
                    mesh_terms.append(str(descriptor))

        # Extract keywords
        keyword_list = medline.get("KeywordList", [])
        keywords = []
        for kw_group in keyword_list:
            for kw in kw_group:
                keywords.append(str(kw))

        articles.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal_title,
            "journal_abbrev": journal_abbrev,
            "year": year,
            "month": month,
            "volume": volume,
            "issue": issue,
            "pages": pages,
            "doi": doi,
            "mesh_terms": mesh_terms,
            "keywords": keywords
        })

    return articles


def format_summary(articles: List[Dict]) -> str:
    """Format articles as a summary list."""
    if not articles:
        return "No articles found."

    lines = []
    lines.append(f"Found {len(articles)} articles:\n")
    lines.append("-" * 90)

    for i, article in enumerate(articles, 1):
        authors_str = ", ".join(article["authors"][:3])
        if len(article["authors"]) > 3:
            authors_str += " et al."

        lines.append(f"\n{i}. {article['title']}")
        lines.append(f"   {authors_str}")
        lines.append(f"   {article['journal']} ({article['year']})")
        lines.append(f"   PMID: {article['pmid']}", )
        if article["doi"]:
            lines.append(f"   DOI: {article['doi']}")

    lines.append("\n" + "-" * 90)
    return "\n".join(lines)


def format_detailed(articles: List[Dict]) -> str:
    """Format articles with full abstracts."""
    if not articles:
        return "No articles found."

    lines = []
    lines.append(f"Found {len(articles)} articles:\n")

    for i, article in enumerate(articles, 1):
        lines.append("=" * 80)
        lines.append(f"Article #{i}")
        lines.append("=" * 80)
        lines.append(f"\nTitle: {article['title']}")
        lines.append(f"\nAuthors: {', '.join(article['authors'])}")
        lines.append(f"\nJournal: {article['journal']}")

        citation = f"  {article['year']}"
        if article["volume"]:
            citation += f"; {article['volume']}"
            if article["issue"]:
                citation += f"({article['issue']})"
            if article["pages"]:
                citation += f": {article['pages']}"
        lines.append(citation)

        lines.append(f"\nPMID: {article['pmid']}")
        if article["doi"]:
            lines.append(f"DOI: {article['doi']}")

        if article["abstract"]:
            lines.append(f"\nAbstract:\n{article['abstract']}")

        if article["mesh_terms"]:
            lines.append(f"\nMeSH Terms: {', '.join(article['mesh_terms'][:10])}")

        if article["keywords"]:
            lines.append(f"\nKeywords: {', '.join(article['keywords'])}")

        lines.append("")

    return "\n".join(lines)


def format_bibtex(articles: List[Dict]) -> str:
    """Format articles as BibTeX entries."""
    if not articles:
        return "% No articles found."

    lines = ["% BibTeX entries generated by ScienceClaw\n"]

    for article in articles:
        # Generate citation key
        first_author = article["authors"][0].split()[0] if article["authors"] else "Unknown"
        key = f"{first_author}{article['year']}"

        lines.append(f"@article{{{key},")
        lines.append(f"  title = {{{article['title']}}},")

        if article["authors"]:
            authors_bibtex = " and ".join(article["authors"])
            lines.append(f"  author = {{{authors_bibtex}}},")

        lines.append(f"  journal = {{{article['journal']}}},")
        lines.append(f"  year = {{{article['year']}}},")

        if article["volume"]:
            lines.append(f"  volume = {{{article['volume']}}},")
        if article["issue"]:
            lines.append(f"  number = {{{article['issue']}}},")
        if article["pages"]:
            lines.append(f"  pages = {{{article['pages']}}},")
        if article["doi"]:
            lines.append(f"  doi = {{{article['doi']}}},")

        lines.append(f"  pmid = {{{article['pmid']}}},")
        lines.append("}\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search PubMed for scientific literature",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "CRISPR gene editing"
  %(prog)s --query "cancer immunotherapy" --year 2024 --max-results 20
  %(prog)s --pmid 35648464 --format detailed
  %(prog)s --query "machine learning" --format bibtex
        """
    )

    parser.add_argument(
        "--query", "-q",
        help="Search query (supports PubMed syntax)"
    )
    parser.add_argument(
        "--pmid",
        help="Specific PubMed ID to fetch"
    )
    parser.add_argument(
        "--max-results", "-m",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)"
    )
    parser.add_argument(
        "--year", "-y",
        type=int,
        help="Filter by publication year"
    )
    parser.add_argument(
        "--year-start",
        type=int,
        help="Start year for date range"
    )
    parser.add_argument(
        "--year-end",
        type=int,
        help="End year for date range"
    )
    parser.add_argument(
        "--author", "-a",
        help="Filter by author name"
    )
    parser.add_argument(
        "--journal", "-j",
        help="Filter by journal name"
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "bibtex", "json"],
        help="Output format (default: summary)"
    )
    parser.add_argument(
        "--sort", "-s",
        default="relevance",
        choices=["relevance", "date", "first_author"],
        help="Sort order (default: relevance)"
    )

    args = parser.parse_args()

    if not args.query and not args.pmid:
        parser.error("Either --query or --pmid is required")

    try:
        if args.pmid:
            pmids = [args.pmid]
        else:
            pmids = search_pubmed(
                query=args.query,
                max_results=args.max_results,
                sort=args.sort,
                year=args.year,
                year_start=args.year_start,
                year_end=args.year_end,
                author=args.author,
                journal=args.journal
            )

        articles = fetch_articles(pmids)

        if args.format == "json":
            print(json.dumps(articles, indent=2))
        elif args.format == "bibtex":
            print(format_bibtex(articles))
        elif args.format == "detailed":
            print(format_detailed(articles))
        else:
            print(format_summary(articles))

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
