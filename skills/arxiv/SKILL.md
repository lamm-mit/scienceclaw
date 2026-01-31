---
name: arxiv
description: Search ArXiv for scientific preprints in biology, chemistry, and related fields
metadata:
  {
    "openclaw": {
      "emoji": "📄",
      "requires": {
        "bins": ["python3"]
      }
    }
  }
---

# ArXiv Search

Search ArXiv for scientific preprints. Great for cutting-edge research in quantitative biology, bioinformatics, and computational biology.

## Usage

### Basic search:
```bash
python3 {baseDir}/scripts/arxiv_search.py --query "protein structure prediction"
```

### Search specific category:
```bash
python3 {baseDir}/scripts/arxiv_search.py --query "deep learning" --category q-bio
```

### Recent papers:
```bash
python3 {baseDir}/scripts/arxiv_search.py --query "AlphaFold" --sort date --max-results 20
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Search query | Required |
| `--category` | ArXiv category | - |
| `--max-results` | Maximum results | 10 |
| `--sort` | Sort by: relevance, date, submitted | relevance |
| `--format` | Output format: summary, detailed, json, bibtex | summary |

## Categories

| Category | Description |
|----------|-------------|
| `q-bio` | Quantitative Biology |
| `q-bio.BM` | Biomolecules |
| `q-bio.GN` | Genomics |
| `q-bio.MN` | Molecular Networks |
| `q-bio.NC` | Neurons and Cognition |
| `q-bio.PE` | Populations and Evolution |
| `q-bio.QM` | Quantitative Methods |
| `cs.LG` | Machine Learning |
| `cs.AI` | Artificial Intelligence |
| `physics.bio-ph` | Biological Physics |
| `cond-mat.soft` | Soft Condensed Matter |

## Examples

```bash
# Search quantitative biology
python3 {baseDir}/scripts/arxiv_search.py --query "CRISPR" --category q-bio

# Recent machine learning papers
python3 {baseDir}/scripts/arxiv_search.py --query "protein language model" --category cs.LG --sort date

# Get BibTeX citations
python3 {baseDir}/scripts/arxiv_search.py --query "drug discovery" --format bibtex
```

## Notes

- ArXiv API is free, no authentication required
- Rate limit: ~3 requests per second
- Preprints are not peer-reviewed
