# gnomAD Database Skill Overview

The provided content documents a Claude agent skill for querying the **Genome Aggregation Database (gnomAD)**. This resource enables genetic variant interpretation through population frequency data and constraint metrics.

## Key Capabilities

The skill provides access to gnomAD v4, containing "exome sequences from 730,947 individuals and genome sequences from 76,215 individuals across diverse ancestries." Users can:

- **Query variant frequencies** by gene or specific genomic position via GraphQL API
- **Assess loss-of-function tolerance** using pLI and LOEUF scores
- **Analyze population-stratified data** across ancestries (African, East Asian, European, South Asian, etc.)
- **Apply ACMG classification criteria** for variant pathogenicity assessment

## Primary Use Cases

The documentation highlights three main workflows: variant pathogenicity assessment (filtering benign common variants), gene prioritization in rare disease research, and population genetics analysis.

## Technical Implementation

The skill leverages GraphQL queries against `https://gnomad.broadinstitute.org/api` with support for multiple datasets (gnomad_r4, gnomad_r3, gnomad_r2_1) and reference genomes (GRCh38, GRCh37).

**License**: CC0-1.0 (public domain)
