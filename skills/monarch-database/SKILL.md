---
name: monarch-database
description: Query the Monarch Initiative knowledge graph for disease-gene-phenotype associations across species. Integrates OMIM, ORPHANET, HPO, ClinVar, and model organism databases. Use for rare disease gene discovery, phenotype-to-gene mapping, cross-species disease modeling, and HPO term lookup.
license: CC0-1.0
metadata:
    skill-author: Kuan-lin Huang
---

# Monarch Initiative Database

## Overview

The Monarch Initiative (https://monarchinitiative.org/) is a multi-species integrated knowledgebase that links genes, diseases, and phenotypes across humans and model organisms. It integrates data from over 40 sources including OMIM, ORPHANET, HPO (Human Phenotype Ontology), ClinVar, MGI (Mouse Genome Informatics), ZFIN (Zebrafish), RGD (Rat), FlyBase, and WormBase.

## Core Capabilities

The skill provides REST API v3 access for:

1. **Phenotype-to-gene mapping** - Find genes associated with human phenotype terms
2. **Disease-to-gene associations** - Discover disease-causing genes using MONDO disease identifiers
3. **Cross-species ortholog discovery** - Identify model organism orthologs for human genes
4. **HPO semantic similarity** - Compare phenotype profiles between individuals/organisms
5. **Automated disease diagnosis** - Build diagnostic algorithms from phenotype to gene lists

## Key Workflows

- Rare disease gene discovery using patient phenotypes (HP terms)
- Model organism selection for disease research
- Phenotype-based patient stratification
- Cross-species disease mechanism studies
- Regulatory variant functional consequence prediction

## Best Practices

Use standardized identifiers: MONDO for diseases, HP for phenotypes, HGNC for human genes. Leverage the integrated data from multiple curated sources for robust evidence accumulation.
