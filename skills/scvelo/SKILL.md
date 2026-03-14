---
name: scvelo
description: RNA velocity analysis with scVelo. Estimate cell state transitions from unspliced/spliced mRNA dynamics, infer trajectory directions, compute latent time, and identify driver genes in single-cell RNA-seq data. Complements Scanpy/scVI-tools for trajectory inference.
license: BSD-3-Clause
metadata:
    skill-author: Kuan-lin Huang
---

# scVelo — RNA Velocity Analysis

## Overview

scVelo is the leading Python package for RNA velocity analysis in single-cell RNA-seq data. It infers cell state transitions by modeling the kinetics of mRNA splicing — using the ratio of unspliced (pre-mRNA) to spliced (mature mRNA) abundances to determine whether a gene is being upregulated or downregulated in each cell. This allows reconstruction of developmental trajectories and identification of cell fate decisions without requiring time-course data.

**Installation:** `pip install scvelo`

**Key resources:**
- Documentation: https://scvelo.readthedocs.io/
- GitHub: https://github.com/theislab/scvelo
- Paper: Bergen et al. (2020) Nature Biotechnology. PMID: 32747759

## Core Capabilities

1. **Velocity estimation** - Compute RNA velocity vectors for each cell
2. **Trajectory inference** - Reconstruct developmental paths and cell fate transitions
3. **Latent time assignment** - Order cells along developmental/differentiation timelines
4. **Driver gene identification** - Detect genes driving state transitions
5. **Gene dynamics modeling** - Model transcriptional kinetics (unspliced/spliced ratios)

## Key Workflows

- Developmental trajectory reconstruction from time-series scRNA-seq
- Cell fate decision point identification
- Pseudo-temporal ordering of cells without explicit timing
- Key gene discovery in differentiation processes
- Validation of developmental hypotheses

## Best Practices

The resource recommends ensuring quality QC of spliced/unspliced counts, using stochastic models for high-noise datasets, validating velocity vectors with known developmental markers, and integrating trajectory inference with spatial transcriptomics for context.
