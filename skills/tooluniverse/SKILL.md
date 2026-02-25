---
name: tooluniverse
description: Access 1000+ scientific tools from Harvard's ToolUniverse — bioinformatics, drug discovery, genomics, clinical research, and more
metadata:
---

# ToolUniverse

Gateway to 1000+ machine learning models, databases, APIs, and scientific packages via Harvard's ToolUniverse ecosystem. Covers drug discovery, genomics, proteomics, clinical research, metabolomics, multi-omics, and more.

## Overview

ToolUniverse standardizes access to scientific tools through a unified `tu.run()` interface. This skill wraps that interface so agents can call any ToolUniverse tool and receive JSON output compatible with the scienceclaw artifact system.

## Usage

### Run any ToolUniverse tool:
```bash
python3 {baseDir}/scripts/tooluniverse_run.py --tool UniProt_get_entry_by_accession \
    --args '{"accession": "P05067"}'
```

### Discover available tools:
```bash
python3 {baseDir}/scripts/tooluniverse_list.py
python3 {baseDir}/scripts/tooluniverse_list.py --search "compound"
python3 {baseDir}/scripts/tooluniverse_list.py --search "protein" --format json
python3 {baseDir}/scripts/tooluniverse_list.py --info PubChem_get_compound_properties_by_CID
```

## Parameters (tooluniverse_run.py)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--tool` | ToolUniverse tool name (exact, case-sensitive) | Required |
| `--args` | Tool arguments as a JSON string | `{}` |
| `--format` | Output format: json, summary | json |
| `--no-cache` | Disable result caching | false |

## Available Research Workflows (54+)

### Drug Discovery
- binder-discovery, drug-repurposing, drug-target-validation, drug-drug-interaction
- chemical-safety, network-pharmacology, pharmacovigilance, adverse-event-detection

### Genomics & Variants
- gwas-trait-to-gene, gwas-snp-interpretation, gwas-fine-mapping, gwas-study-explorer
- variant-analysis, variant-interpretation, structural-variant-analysis
- crispr-screen-analysis, cancer-variant-interpretation

### Omics & Transcriptomics
- rnaseq-deseq2, single-cell, epigenomics, spatial-transcriptomics
- proteomics-analysis, metabolomics, metabolomics-analysis
- multi-omics-integration, gene-enrichment, expression-data-retrieval

### Disease & Clinical
- disease-research, rare-disease-diagnosis, clinical-trial-matching
- clinical-trial-design, clinical-guidelines, precision-oncology
- precision-medicine-stratification, immunotherapy-response-prediction, infectious-disease

### Proteins & Sequences
- sequence-retrieval, protein-structure-retrieval, protein-interactions
- protein-therapeutic-design, antibody-engineering, phylogenetics

### Systems Biology
- systems-biology, immune-repertoire-analysis, polygenic-risk-score
- gwas-drug-discovery, multiomic-disease-characterization, statistical-modeling

### Data Retrieval
- chemical-compound-retrieval, target-research, literature-deep-research

## Examples

```bash
# Retrieve protein entry
python3 {baseDir}/scripts/tooluniverse_run.py \
    --tool UniProt_get_entry_by_accession --args '{"accession": "P05067"}'

# Get compound properties
python3 {baseDir}/scripts/tooluniverse_run.py \
    --tool PubChem_get_compound_properties_by_CID --args '{"cid": 1983}'

# Search PubMed
python3 {baseDir}/scripts/tooluniverse_run.py \
    --tool PubMed_search_articles --args '{"query": "Alzheimer amyloid", "max_results": 10}'

# List tools related to GWAS
python3 {baseDir}/scripts/tooluniverse_list.py --search "gwas"
```

## Installation

```bash
pip install tooluniverse
```

## Notes

- Tool names are exact and case-sensitive — use `tooluniverse_list.py` to discover
- Results are cached by default; use `--no-cache` for fresh data
- All outputs are JSON for downstream tool chaining
- Set API keys via environment variables as required by individual tools
