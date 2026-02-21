---
name: tooluniverse
description: Semantic search across 600+ computational biology and chemistry tools
metadata:
---

## Overview

Scientific tool ecosystem providing access to 600+ computational biology and chemistry tools (AlphaFold, PubChem, UniProt, ChEMBL, KEGG, DESeq2) via semantic search and standardized API. Find and invoke the right scientific tool for any task.

Query the ToolUniverse index to discover tools by natural language description, filter by category (biology, chemistry, genomics, proteomics, materials), and retrieve API endpoint information for programmatic access.

## Usage

```bash
# Search for tools related to protein structure prediction
python3 skills/tooluniverse/scripts/tooluniverse_search.py --query "protein structure prediction"

# Filter by category with more results
python3 skills/tooluniverse/scripts/tooluniverse_search.py --query "drug ADMET" --category chemistry --max-results 20

# Find genomics tools
python3 skills/tooluniverse/scripts/tooluniverse_search.py --query "RNA-seq differential expression" --category genomics
```

## Output Format

```json
{
  "tools": [
    {
      "name": "AlphaFold",
      "description": "Deep learning protein structure prediction from amino acid sequence",
      "api_endpoint": "https://alphafold.ebi.ac.uk/api"
    }
  ],
  "query": "protein structure prediction",
  "total": 5
}
```
