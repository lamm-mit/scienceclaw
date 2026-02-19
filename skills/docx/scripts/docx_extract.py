#!/usr/bin/env python3
"""
DOCX extraction tool - extract text, tables, headings, and metadata
from Microsoft Word .docx files for scientific document analysis.
"""

import argparse
import json
import os
import sys


def extract_docx(file_path: str, extract: str) -> dict:
    """Extract content from a .docx file using python-docx."""
    import docx  # python-docx

    doc = docx.Document(file_path)

    # --- Text and headings ---
    text_parts = []
    headings = []

    if extract in ("text", "headings", "all"):
        for para in doc.paragraphs:
            if para.style and para.style.name.startswith("Heading"):
                headings.append(para.text.strip())
            if extract in ("text", "all") and para.text.strip():
                text_parts.append(para.text.strip())

    # --- Tables ---
    tables_data = []
    if extract in ("tables", "all"):
        for table in doc.tables:
            rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(cells)
            if rows:
                tables_data.append(rows)

    # --- Metadata ---
    metadata = {}
    if extract in ("metadata", "all"):
        core = doc.core_properties
        metadata = {
            "author": core.author or "",
            "title": core.title or "",
            "subject": core.subject or "",
            "description": core.description or "",
            "keywords": core.keywords or "",
            "created": str(core.created) if core.created else "",
            "modified": str(core.modified) if core.modified else "",
            "last_modified_by": core.last_modified_by or "",
            "revision": str(core.revision) if core.revision else "",
            "category": core.category or "",
        }

    return {
        "file": file_path,
        "text": "\n\n".join(text_parts) if extract in ("text", "all") else "",
        "headings": headings if extract in ("headings", "all") else [],
        "tables": tables_data if extract in ("tables", "all") else [],
        "metadata": metadata if extract in ("metadata", "all") else {},
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract text, tables, headings, and metadata from .docx files"
    )
    parser.add_argument("--file", required=True, help="Path to the .docx file")
    parser.add_argument(
        "--extract",
        choices=["text", "tables", "headings", "metadata", "all"],
        default="all",
        help="What to extract (default: all)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        result = {"error": f"File not found: {args.file}", "file": args.file}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    if not args.file.lower().endswith(".docx"):
        result = {
            "error": "File must be a .docx file. Convert older .doc files with LibreOffice first.",
            "file": args.file,
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    try:
        import docx  # noqa: F401
    except ImportError:
        result = {
            "error": "python-docx not installed. Run: pip install python-docx",
            "file": args.file,
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    try:
        result = extract_docx(args.file, args.extract)
    except Exception as e:
        result = {"error": str(e), "file": args.file}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
