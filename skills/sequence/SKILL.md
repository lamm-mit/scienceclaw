---
name: sequence
description: Analyze biological sequences using Biopython - translate, align, parse FASTA/GenBank
metadata:
  {
    "openclaw": {
      "emoji": "🧪",
      "requires": {
        "bins": ["python3"]
      }
    }
  }
---

# Sequence Analysis

Analyze biological sequences using Biopython. Translate DNA, compute statistics, parse sequence files, and perform basic alignments.

## Overview

This skill provides sequence analysis capabilities including:
- DNA/RNA translation to protein
- Sequence statistics (GC content, molecular weight, etc.)
- Reverse complement
- FASTA/GenBank file parsing
- Sequence alignment
- Motif searching

## Usage

### Translate DNA to protein:
```bash
python3 {baseDir}/scripts/sequence_tools.py translate --sequence "ATGCGATCGATCGATCG"
```

### Compute sequence statistics:
```bash
python3 {baseDir}/scripts/sequence_tools.py stats --sequence "ATGCGATCGATCGATCG"
```

### Get reverse complement:
```bash
python3 {baseDir}/scripts/sequence_tools.py revcomp --sequence "ATGCGATCGATCG"
```

### Parse FASTA file:
```bash
python3 {baseDir}/scripts/sequence_tools.py parse --file sequences.fasta --format fasta
```

### Find ORFs:
```bash
python3 {baseDir}/scripts/sequence_tools.py orfs --sequence "ATGCGATCGATCGATCGTAG"
```

### Search for motif:
```bash
python3 {baseDir}/scripts/sequence_tools.py motif --sequence "ATGCGATCGATCG" --pattern "GATC"
```

## Commands

### translate
Translate DNA/RNA sequence to protein.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--sequence` | DNA/RNA sequence or file | Required |
| `--table` | Codon table (1=standard, 2=mitochondrial, etc.) | 1 |
| `--frame` | Reading frame (1, 2, 3, -1, -2, -3) | 1 |
| `--all-frames` | Translate all 6 reading frames | False |
| `--to-stop` | Translate until first stop codon | False |

### stats
Compute sequence statistics.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--sequence` | Sequence or file | Required |
| `--type` | Sequence type: dna, rna, protein, auto | auto |

Output includes:
- Length
- GC content (nucleotide)
- Molecular weight
- Base/amino acid composition

### revcomp
Get reverse complement of DNA sequence.

| Parameter | Description |
|-----------|-------------|
| `--sequence` | DNA sequence or file |

### parse
Parse sequence files (FASTA, GenBank, etc.).

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--file` | Input file path | Required |
| `--format` | File format: fasta, genbank, embl | auto |
| `--output` | Output format: summary, fasta, json | summary |

### orfs
Find Open Reading Frames.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--sequence` | DNA sequence or file | Required |
| `--min-length` | Minimum ORF length (codons) | 30 |
| `--table` | Codon table | 1 |

### motif
Search for sequence motifs/patterns.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--sequence` | Sequence to search | Required |
| `--pattern` | Pattern to find (supports IUPAC codes) | Required |

## Examples

### Translate with specific codon table:
```bash
python3 {baseDir}/scripts/sequence_tools.py translate --sequence "ATGCGATCG" --table 2
```

### Get stats for protein sequence:
```bash
python3 {baseDir}/scripts/sequence_tools.py stats --sequence "MTEYKLVVVGAGGVGKSALTIQLIQ" --type protein
```

### Parse GenBank file and extract sequences:
```bash
python3 {baseDir}/scripts/sequence_tools.py parse --file gene.gb --format genbank --output fasta
```

### Find all ORFs with minimum 50 codons:
```bash
python3 {baseDir}/scripts/sequence_tools.py orfs --file genome.fasta --min-length 50
```

### Translate all 6 reading frames:
```bash
python3 {baseDir}/scripts/sequence_tools.py translate --sequence "ATGCGATCGATCGATCG" --all-frames
```

## Codon Tables

| ID | Description |
|----|-------------|
| 1 | Standard |
| 2 | Vertebrate Mitochondrial |
| 3 | Yeast Mitochondrial |
| 4 | Mold/Protozoan Mitochondrial |
| 5 | Invertebrate Mitochondrial |
| 6 | Ciliate Nuclear |
| 11 | Bacterial/Archaeal/Plant Plastid |

## IUPAC Codes

### Nucleotides
- R = A or G (purine)
- Y = C or T (pyrimidine)
- S = G or C
- W = A or T
- K = G or T
- M = A or C
- N = any nucleotide

### Amino Acids
- X = any amino acid
- B = D or N
- Z = E or Q

## Notes

- Sequences can be provided directly or as file paths
- Auto-detection identifies DNA/RNA/protein sequences
- Large files are processed efficiently with streaming
