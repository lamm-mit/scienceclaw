---
name: blast
description: Search NCBI BLAST for sequence homology and find similar sequences in biological databases
metadata:
  openclaw:
    emoji: "🧬"
    requires:
      bins:
        - python3
---

# BLAST Search

Run NCBI BLAST (Basic Local Alignment Search Tool) searches to find sequence homology against NCBI databases.

## Overview

BLAST finds regions of similarity between biological sequences. The program compares nucleotide or protein sequences to sequence databases and calculates the statistical significance of matches.

## Usage

### Basic protein BLAST search:
```bash
python3 {baseDir}/scripts/blast_search.py --query "MTEYKLVVVGAGGVGKSALTIQLIQ" --program blastp
```

### Nucleotide search:
```bash
python3 {baseDir}/scripts/blast_search.py --query "ATGCGATCGATCGATCG" --program blastn
```

### Search from FASTA file:
```bash
python3 {baseDir}/scripts/blast_search.py --query /path/to/sequence.fasta --database nr --program blastp
```

### Get detailed output:
```bash
python3 {baseDir}/scripts/blast_search.py --query "SEQUENCE" --program blastp --format detailed --max-hits 20
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Amino acid/nucleotide sequence or path to FASTA file | Required |
| `--program` | BLAST program: blastn, blastp, blastx, tblastn, tblastx | blastp |
| `--database` | Database to search: nr, nt, refseq_protein, refseq_rna, swissprot, pdb | nr |
| `--evalue` | E-value threshold | 10.0 |
| `--max-hits` | Maximum number of hits to return | 10 |
| `--format` | Output format: summary, detailed, json | summary |

## BLAST Programs

- **blastp**: Protein query vs protein database
- **blastn**: Nucleotide query vs nucleotide database
- **blastx**: Translated nucleotide query vs protein database
- **tblastn**: Protein query vs translated nucleotide database
- **tblastx**: Translated nucleotide query vs translated nucleotide database

## Databases

- **nr**: Non-redundant protein sequences
- **nt**: Non-redundant nucleotide sequences
- **refseq_protein**: NCBI Reference Sequence protein database
- **refseq_rna**: NCBI Reference Sequence RNA database
- **swissprot**: Swiss-Prot protein database (curated)
- **pdb**: Protein Data Bank sequences

## Examples

### Find similar proteins to human p53:
```bash
python3 {baseDir}/scripts/blast_search.py --query "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGP" --program blastp --database swissprot
```

### Search for homologs with strict E-value:
```bash
python3 {baseDir}/scripts/blast_search.py --query "MTEYKLVVVGAGGVGKSALTIQLIQ" --evalue 0.001 --max-hits 50
```

## Output

The tool returns:
- Hit accession and description
- E-value and bit score
- Percent identity and alignment length
- Query and subject coverage
- Alignment details (in detailed mode)

## Notes

- BLAST searches are submitted to NCBI servers and may take 30 seconds to several minutes
- For large-scale searches, consider using local BLAST+ installation
- NCBI requests that you provide an email for heavy usage (set NCBI_EMAIL environment variable)
