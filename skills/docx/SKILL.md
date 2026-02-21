---
name: docx
description: Extract text, tables, headings, and metadata from Microsoft Word .docx files
metadata:
---

## Overview

Microsoft Word document processing toolkit for extracting text, tables, headings, and metadata from .docx files. Useful for analyzing scientific manuscripts, grant applications, protocols, and supplementary documents shared in Word format.

Uses python-docx for structured extraction, preserving document hierarchy (headings, paragraphs, tables) to enable downstream semantic analysis.

## Usage

```bash
# Extract everything from a .docx file
python3 skills/docx/scripts/docx_extract.py --file /path/to/manuscript.docx

# Extract only headings (document structure)
python3 skills/docx/scripts/docx_extract.py --file /path/to/protocol.docx --extract headings

# Extract tables only (supplementary data)
python3 skills/docx/scripts/docx_extract.py --file /path/to/supplementary.docx --extract tables

# Extract metadata (author, date, revision)
python3 skills/docx/scripts/docx_extract.py --file /path/to/grant.docx --extract metadata
```

## Output Format

```json
{
  "file": "/path/to/manuscript.docx",
  "text": "Introduction\n\nProtein aggregation is a hallmark...",
  "headings": [
    "Abstract",
    "Introduction",
    "Methods",
    "Results",
    "Discussion",
    "References"
  ],
  "tables": [
    [["Sample", "Concentration", "Activity"], ["WT", "1 uM", "100%"]]
  ],
  "metadata": {
    "author": "Jane Smith",
    "title": "Novel Drug Discovery Approach",
    "created": "2024-01-10T09:30:00",
    "modified": "2024-02-01T14:22:00",
    "revision": "5"
  }
}
```

## Dependencies

```bash
pip install python-docx
```
