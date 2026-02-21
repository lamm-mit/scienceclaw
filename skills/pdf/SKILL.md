---
name: pdf
description: Extract text, tables, and metadata from scientific PDF papers and reports
metadata:
---

## Overview

PDF processing toolkit for extracting text, tables, and metadata from scientific papers, supplementary data files, and technical reports. Uses pdfplumber for high-fidelity text and table extraction with layout preservation, falling back to pypdf when pdfplumber is unavailable.

Supports page range selection for large documents and targeted extraction modes (text-only, tables-only, metadata-only) for efficient processing.

## Usage

```bash
# Extract everything from a PDF
python3 skills/pdf/scripts/pdf_extract.py --file /path/to/paper.pdf

# Extract only text from pages 1-5
python3 skills/pdf/scripts/pdf_extract.py --file /path/to/paper.pdf --pages "1-5" --extract text

# Extract tables only
python3 skills/pdf/scripts/pdf_extract.py --file /path/to/supplementary.pdf --extract tables

# Extract metadata only
python3 skills/pdf/scripts/pdf_extract.py --file /path/to/paper.pdf --extract metadata
```

## Output Format

```json
{
  "file": "/path/to/paper.pdf",
  "text": "Abstract\n\nWe present a novel approach to protein structure...",
  "tables": [
    [["Gene", "Expression", "p-value"], ["BRCA1", "2.4x", "0.001"]],
    [["Compound", "IC50 (nM)"], ["Compound A", "12.3"]]
  ],
  "metadata": {
    "title": "Novel Approach to Protein Structure Prediction",
    "author": "Smith et al.",
    "creation_date": "2024-01-15",
    "pages": 12
  },
  "page_count": 12
}
```

## Dependencies

Install with pip:
```bash
pip install pdfplumber pypdf
```
