# GTEx Database Skill Summary

## Purpose
This skill enables querying the Genotype-Tissue Expression (GTEx) portal to investigate tissue-specific gene expression, expression quantitative trait loci (eQTLs), and splicing QTLs—critical for connecting GWAS variants to regulatory mechanisms.

## Primary Use Cases
The documentation identifies several key applications:
- Linking non-coding GWAS variants to regulated genes via eQTL analysis
- Comparing expression patterns across 54 human tissues
- Testing whether GWAS and eQTL signals share causal variants
- Identifying variants affecting RNA splicing ratios

## Core Technical Components

**API Foundation**: The GTEx REST API v2 (base: `https://gtexportal.org/api/v2/`) provides JSON responses without authentication and supports pagination.

**Key Endpoints**:
- Gene expression lookup returns median TPM values per tissue
- eQTL queries retrieve significant variant-gene associations with p-values and effect sizes
- Variant-based searches identify all genes regulated by a specific SNP
- Tissue lists provide available samples with metadata

**Data Format**: The skill uses GENCODE identifiers for genes and employs a standardized variant ID format: `chr{chrom}_{pos}_{ref}_{alt}_b38`.

## Practical Implementation
The documentation provides Python examples demonstrating pagination handling, DataFrame filtering, and multi-tissue aggregation. It emphasizes using GRCh38 coordinates and notes that FDR < 0.05 defines GTEx significance thresholds.

## License
The skill is distributed under CC-BY-4.0, authored by Kuan-lin Huang.
