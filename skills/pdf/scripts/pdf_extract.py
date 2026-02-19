#!/usr/bin/env python3
"""
PDF extraction tool - extract text, tables, and metadata from scientific
PDF papers and reports using pdfplumber or pypdf.
"""

import argparse
import json
import os
import sys


def parse_page_range(pages_str: str, total_pages: int) -> list:
    """Parse a page range string like '1-5' or '3' into a list of 0-indexed page numbers."""
    pages = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = max(1, int(start_s.strip()))
            end = min(total_pages, int(end_s.strip()))
            pages.extend(range(start - 1, end))
        else:
            p = int(part.strip())
            if 1 <= p <= total_pages:
                pages.append(p - 1)
    return pages


def extract_with_pdfplumber(file_path: str, page_indices: list, extract: str) -> dict:
    """Extract content using pdfplumber."""
    import pdfplumber

    text_parts = []
    all_tables = []
    metadata = {}
    page_count = 0

    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        metadata = {k: str(v) for k, v in (pdf.metadata or {}).items()}
        metadata["pages"] = page_count

        target_pages = [pdf.pages[i] for i in page_indices if i < len(pdf.pages)]

        for page in target_pages:
            if extract in ("text", "all"):
                t = page.extract_text()
                if t:
                    text_parts.append(t)

            if extract in ("tables", "all"):
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)

    return {
        "file": file_path,
        "text": "\n\n".join(text_parts) if extract in ("text", "all") else "",
        "tables": all_tables if extract in ("tables", "all") else [],
        "metadata": metadata if extract in ("metadata", "all") else {},
        "page_count": page_count,
        "extractor": "pdfplumber",
    }


def extract_with_pypdf(file_path: str, page_indices: list, extract: str) -> dict:
    """Extract content using pypdf as fallback."""
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader  # older name

    reader = PdfReader(file_path)
    page_count = len(reader.pages)

    info = reader.metadata or {}
    metadata = {
        "title": str(info.get("/Title", "")),
        "author": str(info.get("/Author", "")),
        "subject": str(info.get("/Subject", "")),
        "creator": str(info.get("/Creator", "")),
        "creation_date": str(info.get("/CreationDate", "")),
        "pages": page_count,
    }

    text_parts = []
    for i in page_indices:
        if i < page_count:
            t = reader.pages[i].extract_text()
            if t:
                text_parts.append(t)

    return {
        "file": file_path,
        "text": "\n\n".join(text_parts) if extract in ("text", "all") else "",
        "tables": [],  # pypdf does not support table extraction
        "metadata": metadata if extract in ("metadata", "all") else {},
        "page_count": page_count,
        "extractor": "pypdf",
        "note": "Table extraction not available with pypdf; install pdfplumber for tables.",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract text, tables, and metadata from scientific PDF files"
    )
    parser.add_argument("--file", required=True, help="Path to the PDF file")
    parser.add_argument(
        "--pages",
        default=None,
        help='Page range to extract, e.g. "1-5" or "2,4,6" (default: all pages)',
    )
    parser.add_argument(
        "--extract",
        choices=["text", "tables", "metadata", "all"],
        default="all",
        help="What to extract (default: all)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        result = {"error": f"File not found: {args.file}", "file": args.file}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    # Determine page count early for range parsing
    # We'll compute it inside the extractor; pass a large sentinel if pages_str not given
    page_indices_str = args.pages

    # Try pdfplumber first
    try:
        import pdfplumber

        with pdfplumber.open(args.file) as _pdf:
            total = len(_pdf.pages)

        if page_indices_str:
            page_indices = parse_page_range(page_indices_str, total)
        else:
            page_indices = list(range(total))

        result = extract_with_pdfplumber(args.file, page_indices, args.extract)

    except ImportError:
        # Fallback to pypdf
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader

            reader = PdfReader(args.file)
            total = len(reader.pages)

            if page_indices_str:
                page_indices = parse_page_range(page_indices_str, total)
            else:
                page_indices = list(range(total))

            result = extract_with_pypdf(args.file, page_indices, args.extract)

        except ImportError:
            result = {
                "error": (
                    "No PDF library available. "
                    "Install with: pip install pdfplumber pypdf"
                ),
                "file": args.file,
            }
            print(json.dumps(result, indent=2))
            sys.exit(1)

    except Exception as e:
        result = {"error": str(e), "file": args.file}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
