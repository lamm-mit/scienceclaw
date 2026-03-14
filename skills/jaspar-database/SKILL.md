# JASPAR Database Skill - Complete Content

**Name:** jaspar-database

**Description:** "Query JASPAR for transcription factor binding site (TFBS) profiles (PWMs/PFMs). Search by TF name, species, or class; scan DNA sequences for TF binding sites; compare matrices; essential for regulatory genomics, motif analysis, and GWAS regulatory variant interpretation."

**License:** CC0-1.0

**Skill Author:** Kuan-lin Huang

## Overview

JASPAR (https://jaspar.elixir.no/) serves as the authoritative open-access repository of curated transcription factor binding profiles represented as position frequency matrices. The 2024 version contains approximately 1,210 non-redundant profiles across 164 eukaryotic species, with each profile derived from experimental validation methods.

## Core Capabilities

The skill provides REST API access and Python implementations for:

1. **Profile searching** by transcription factor name, species, family, or classification
2. **Matrix retrieval** with PFM/PWM conversion and scoring
3. **Sequence scanning** across forward and reverse complement strands
4. **Variant impact assessment** comparing reference versus alternative allele binding affinity
5. **Multi-TF workflow automation** for promoter and regulatory element analysis

## Key Workflows

- Finding all binding sites in promoter regions
- Assessing regulatory variant effects on transcription factor recognition
- Motif enrichment analysis from ChIP-seq and ATAC-seq data

## Best Practices

The resource recommends using the CORE collection for most analyses, setting thresholds at 80% of maximum score for general prediction, always scanning both DNA strands, and validating predictions against experimental ChIP-seq datasets.
