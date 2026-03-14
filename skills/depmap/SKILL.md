# DepMap — Cancer Dependency Map Skill Summary

## Overview
This skill enables querying the Cancer Dependency Map project from the Broad Institute to analyze genetic dependencies across cancer cell lines using CRISPR screens, RNAi, and compound sensitivity data.

## Primary Use Cases
The skill supports identifying cancer-selective gene dependencies, validating oncology drug targets, discovering synthetic lethal interactions, and uncovering biomarkers that predict treatment sensitivity.

## Core Data Types

**Dependency Scores:**
- Chronos (CRISPR): ranges ~-3 to 0+, where more negative indicates higher essentiality
- Standard thresholds: ≤-0.5 suggests dependence; ≤-1 indicates strong dependence
- Gene Effect: normalized version where -1 represents median effect of common essential genes

**Cell Line Information:**
Each line includes unique DepMap ID, name, primary disease classification, tissue lineage, and lineage subtype.

## Technical Implementation

The skill provides Python-based access through:
1. RESTful API endpoints at https://depmap.org/portal/api/
2. Direct data downloads from https://depmap.org/portal/download/all/
3. Local analysis of CSV files including gene effect matrices, mutation data, copy number, and expression

## Key Analytical Workflows

**Target Validation:** Filter cell lines by cancer type and compute selective dependency patterns for candidate genes.

**Synthetic Lethality:** Compare gene effect scores between mutant and wild-type cell lines to identify selective dependencies.

**Biomarker Discovery:** Correlate genomic features (mutations, expression) with dependency scores using statistical testing.

**Co-Essentiality:** Identify genes with correlated dependency profiles suggesting shared pathways or complexes.

## Critical Best Practices

- Prioritize current Chronos scores over legacy DEMETER2 data
- Distinguish broadly essential genes (poor drug targets) from cancer-selective dependencies
- Validate findings against expression data since unexpressed genes appear non-essential
- Account for copy number artifacts in essential gene calls
- Apply multiple-testing correction for genome-wide analyses