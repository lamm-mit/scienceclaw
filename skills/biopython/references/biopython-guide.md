# Biopython Quick Reference Guide

This document provides a quick reference for Biopython features used in ScienceClaw.

## Installation

```bash
pip install biopython
```

## Core Modules

### Seq - Sequence Objects

```python
from Bio.Seq import Seq

# Create sequence
seq = Seq("ATGCGATCGATCG")

# Basic operations
len(seq)                    # Length
seq[0:10]                   # Slicing
seq.complement()            # Complement
seq.reverse_complement()    # Reverse complement

# Transcription and translation
rna = seq.transcribe()      # DNA -> RNA
protein = seq.translate()   # DNA -> Protein
protein = seq.translate(table=1, to_stop=True)
```

### SeqRecord - Annotated Sequences

```python
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq

record = SeqRecord(
    Seq("ATGCGATCG"),
    id="gene1",
    name="Example",
    description="An example sequence"
)

# Access attributes
record.seq          # Sequence
record.id           # ID
record.name         # Name
record.description  # Description
record.features     # List of features
record.annotations  # Dictionary of annotations
```

### SeqIO - Sequence File I/O

```python
from Bio import SeqIO

# Read single sequence
record = SeqIO.read("sequence.fasta", "fasta")

# Read multiple sequences
for record in SeqIO.parse("sequences.fasta", "fasta"):
    print(record.id, len(record.seq))

# Write sequences
SeqIO.write(records, "output.fasta", "fasta")

# Supported formats
# fasta, genbank, embl, fastq, clustal, phylip, etc.
```

### SeqUtils - Sequence Utilities

```python
from Bio.SeqUtils import gc_fraction, molecular_weight

seq = Seq("ATGCGATCG")

# GC content
gc = gc_fraction(seq)  # Returns 0.0-1.0

# Molecular weight
mw = molecular_weight(seq, seq_type="DNA")
```

### ProtParam - Protein Analysis

```python
from Bio.SeqUtils.ProtParam import ProteinAnalysis

protein_seq = "MTEYKLVVVGAGGVGKSALTIQLIQ"
analysis = ProteinAnalysis(protein_seq)

# Properties
analysis.molecular_weight()      # Molecular weight
analysis.isoelectric_point()     # pI
analysis.instability_index()     # Stability
analysis.gravy()                 # Hydrophobicity (GRAVY)
analysis.count_amino_acids()     # AA composition
analysis.get_amino_acids_percent()  # AA percentages
analysis.secondary_structure_fraction()  # Helix, turn, sheet
```

## BLAST Interface

### NCBIWWW - Remote BLAST

```python
from Bio.Blast import NCBIWWW, NCBIXML

# Run BLAST search
result_handle = NCBIWWW.qblast(
    program="blastp",       # blastn, blastp, blastx, tblastn
    database="nr",          # nr, nt, swissprot, pdb
    sequence="MTEYKLVVVGAGGVGKSALTIQLIQ",
    expect=10.0,            # E-value threshold
    hitlist_size=50         # Max hits
)

# Parse results
blast_records = NCBIXML.parse(result_handle)

for record in blast_records:
    for alignment in record.alignments:
        for hsp in alignment.hsps:
            print(f"Hit: {alignment.title}")
            print(f"E-value: {hsp.expect}")
            print(f"Score: {hsp.score}")
            print(f"Identity: {hsp.identities}/{hsp.align_length}")
```

## Entrez - NCBI Database Access

### Configuration

```python
from Bio import Entrez

Entrez.email = "your.email@example.com"  # Required
Entrez.api_key = "your_api_key"          # Optional but recommended
```

### ESearch - Search

```python
handle = Entrez.esearch(
    db="pubmed",
    term="CRISPR",
    retmax=10,
    sort="relevance"
)
record = Entrez.read(handle)
pmids = record["IdList"]
```

### EFetch - Retrieve

```python
handle = Entrez.efetch(
    db="pubmed",
    id=",".join(pmids),
    rettype="xml",
    retmode="xml"
)
records = Entrez.read(handle)
```

### ESummary - Summaries

```python
handle = Entrez.esummary(db="pubmed", id="35648464")
record = Entrez.read(handle)
```

## Codon Tables

```python
from Bio.Data import CodonTable

# Standard table
table = CodonTable.unambiguous_dna_by_id[1]

# Mitochondrial table
mito_table = CodonTable.unambiguous_dna_by_id[2]

# Table properties
table.start_codons    # ['TTG', 'CTG', 'ATG']
table.stop_codons     # ['TAA', 'TAG', 'TGA']
table.forward_table   # Codon -> AA mapping
```

### Codon Table IDs

| ID | Name |
|----|------|
| 1 | Standard |
| 2 | Vertebrate Mitochondrial |
| 3 | Yeast Mitochondrial |
| 4 | Mold/Protozoan Mitochondrial |
| 5 | Invertebrate Mitochondrial |
| 6 | Ciliate Nuclear |
| 11 | Bacterial/Archaeal/Plant Plastid |

## Alignment

### Pairwise Alignment

```python
from Bio import pairwise2
from Bio.pairwise2 import format_alignment

# Global alignment
alignments = pairwise2.align.globalxx(seq1, seq2)

# Local alignment
alignments = pairwise2.align.localxx(seq1, seq2)

# Format output
for alignment in alignments:
    print(format_alignment(*alignment))
```

### AlignIO - Alignment Files

```python
from Bio import AlignIO

# Read alignment
alignment = AlignIO.read("alignment.clustal", "clustal")

# Iterate over sequences
for record in alignment:
    print(record.id, record.seq)

# Alignment properties
alignment.get_alignment_length()
```

## File Formats

| Format | Extension | Read | Write |
|--------|-----------|------|-------|
| FASTA | .fasta, .fa | Yes | Yes |
| GenBank | .gb, .gbk | Yes | Yes |
| EMBL | .embl | Yes | Yes |
| FASTQ | .fastq | Yes | Yes |
| Clustal | .aln | Yes | Yes |
| Phylip | .phy | Yes | Yes |
| Stockholm | .sto | Yes | Yes |

## IUPAC Codes

### Nucleotide Ambiguity Codes

| Code | Bases | Description |
|------|-------|-------------|
| R | A, G | puRine |
| Y | C, T | pYrimidine |
| S | G, C | Strong |
| W | A, T | Weak |
| K | G, T | Keto |
| M | A, C | aMino |
| B | C, G, T | not A |
| D | A, G, T | not C |
| H | A, C, T | not G |
| V | A, C, G | not T |
| N | A, C, G, T | aNy |

### Amino Acid Codes

| Code | Amino Acid |
|------|------------|
| A | Alanine |
| C | Cysteine |
| D | Aspartic acid |
| E | Glutamic acid |
| F | Phenylalanine |
| G | Glycine |
| H | Histidine |
| I | Isoleucine |
| K | Lysine |
| L | Leucine |
| M | Methionine |
| N | Asparagine |
| P | Proline |
| Q | Glutamine |
| R | Arginine |
| S | Serine |
| T | Threonine |
| V | Valine |
| W | Tryptophan |
| Y | Tyrosine |
| X | Any |
| * | Stop |

## Resources

- [Biopython Tutorial](https://biopython.org/DIST/docs/tutorial/Tutorial.html)
- [Biopython API Documentation](https://biopython.org/docs/latest/api/)
- [Biopython Cookbook](https://biopython.org/wiki/Category:Cookbook)
- [GitHub Repository](https://github.com/biopython/biopython)
