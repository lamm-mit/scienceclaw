# NCBI E-utilities API Reference

This document provides reference information for the NCBI E-utilities API used by the BLAST and PubMed skills.

## Overview

NCBI E-utilities (Entrez Programming Utilities) is a set of server-side programs providing a stable interface into the Entrez query and database system at the National Center for Biotechnology Information (NCBI).

**Base URL:** `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`

## Authentication

- **No API key required** for basic usage
- **API key recommended** for heavy usage (more than 3 requests/second)
- Register for an API key at: https://www.ncbi.nlm.nih.gov/account/

### Rate Limits

| Access Type | Rate Limit |
|-------------|------------|
| Without API key | 3 requests/second |
| With API key | 10 requests/second |
| With API key (registered tool) | Higher limits available |

## E-utilities Endpoints

### ESearch - Text Search

Search and retrieve UIDs from a database.

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
```

**Parameters:**
- `db` - Database name (pubmed, nucleotide, protein, etc.)
- `term` - Search query
- `retmax` - Maximum number of UIDs returned
- `retstart` - Index of first UID to retrieve
- `sort` - Sort order (relevance, pub_date, etc.)
- `datetype` - Date type for range (pdat, mdat, edat)
- `mindate` / `maxdate` - Date range

**Example:**
```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=cancer+immunotherapy&retmax=10&retmode=json"
```

### EFetch - Data Retrieval

Retrieve data for UIDs.

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
```

**Parameters:**
- `db` - Database name
- `id` - Comma-separated UIDs
- `rettype` - Return type (abstract, fasta, gb, xml, etc.)
- `retmode` - Return mode (text, xml, json)

**Example:**
```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=35648464&rettype=abstract&retmode=xml"
```

### ESummary - Document Summaries

Retrieve document summaries for UIDs.

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi
```

**Parameters:**
- `db` - Database name
- `id` - Comma-separated UIDs
- `retmode` - Return mode (json, xml)

### EInfo - Database Information

Get information about NCBI databases.

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi
```

## NCBI BLAST API

### QBlast Interface

Submit and retrieve BLAST searches.

**Submit URL:**
```
https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi
```

**Parameters for submission:**
- `CMD=Put` - Submit a search
- `PROGRAM` - blastn, blastp, blastx, tblastn, tblastx
- `DATABASE` - nr, nt, refseq_protein, swissprot, pdb, etc.
- `QUERY` - Sequence to search
- `EXPECT` - E-value threshold
- `HITLIST_SIZE` - Maximum hits to return
- `FORMAT_TYPE` - Output format (HTML, Text, XML, JSON2)

**Parameters for retrieval:**
- `CMD=Get` - Retrieve results
- `RID` - Request ID from submission
- `FORMAT_TYPE` - Output format

### BLAST Workflow

1. Submit search (CMD=Put)
2. Receive RID (Request ID)
3. Poll for status (CMD=Get with RID)
4. Retrieve results when ready

**Example with Biopython:**
```python
from Bio.Blast import NCBIWWW, NCBIXML

# Submit search
result_handle = NCBIWWW.qblast(
    "blastp",           # program
    "nr",               # database
    "MTEYKLVVVGAGGVGKSALTIQLIQ",  # sequence
    expect=10.0,
    hitlist_size=10
)

# Parse results
blast_records = NCBIXML.parse(result_handle)
for record in blast_records:
    for alignment in record.alignments:
        print(f"{alignment.title}: E={alignment.hsps[0].expect}")
```

## Databases

### PubMed
- **ID:** `pubmed`
- **Description:** Biomedical literature
- **UID Type:** PMID (PubMed ID)

### Nucleotide
- **ID:** `nucleotide`
- **Description:** Nucleotide sequences
- **UID Type:** GI number or accession

### Protein
- **ID:** `protein`
- **Description:** Protein sequences
- **UID Type:** GI number or accession

### Gene
- **ID:** `gene`
- **Description:** Gene records
- **UID Type:** Gene ID

### Structure
- **ID:** `structure`
- **Description:** 3D structures
- **UID Type:** MMDB ID

## Search Syntax

### Boolean Operators
- `AND` - Both terms required
- `OR` - Either term
- `NOT` - Exclude term

### Field Tags
- `[Title]` - Search in title only
- `[Author]` - Author name
- `[Journal]` - Journal name
- `[MeSH Terms]` - MeSH vocabulary
- `[Date - Publication]` - Publication date

### Examples
```
cancer[Title] AND therapy[Title]
"machine learning"[Title/Abstract]
Smith J[Author] AND 2024[Date - Publication]
BRCA1[Gene Name]
```

## Response Formats

### XML
Default format, most complete data.

### JSON
Use `retmode=json` for JSON output.

### Text
Simple text format for sequences.

## Error Handling

| HTTP Code | Description |
|-----------|-------------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 429 | Rate limit exceeded |
| 500 | Server error |
| 502 | Bad gateway (retry) |
| 503 | Service unavailable (retry) |

## Best Practices

1. **Use API key** for better rate limits
2. **Set email** (`tool` and `email` parameters)
3. **Handle rate limits** with exponential backoff
4. **Cache results** when appropriate
5. **Use batch requests** for multiple IDs
6. **Respect NCBI usage policies**

## Resources

- [E-utilities Documentation](https://www.ncbi.nlm.nih.gov/books/NBK25497/)
- [BLAST Help](https://blast.ncbi.nlm.nih.gov/Blast.cgi?CMD=Web&PAGE_TYPE=BlastDocs)
- [Entrez Direct (EDirect)](https://www.ncbi.nlm.nih.gov/books/NBK179288/)
- [Biopython Tutorial](https://biopython.org/DIST/docs/tutorial/Tutorial.html)
