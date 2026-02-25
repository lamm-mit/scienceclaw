---
name: uniprot
description: "Protein sequence, function, and annotation lookup. Query MUST be a bare gene symbol or protein name — 1 to 3 words maximum. Valid examples: 'KRAS', 'EGFR', 'BTK', 'TP53', 'Bruton tyrosine kinase', 'P01116'. If the topic is 'sotorasib KRAS G12C', the correct query is 'KRAS'. If the topic is 'imatinib BCR-ABL resistance', the correct query is 'BCR-ABL'. Strip the drug name, mutation label, and all mechanism words — pass only the protein or gene name."
metadata:
---

# UniProt Protein Lookup

Query the UniProt protein database to retrieve protein sequences, annotations, functional information, and cross-references.

## Overview

UniProt is the world's most comprehensive protein sequence and functional annotation database. This skill provides access to:
- Protein sequences (FASTA format)
- Functional annotations
- Gene ontology (GO) terms
- Protein domains and families
- Cross-references to PDB, Pfam, InterPro, etc.

## Usage

### Fetch protein by accession:
```bash
python3 {baseDir}/scripts/uniprot_fetch.py --accession P53_HUMAN
```

### Fetch by UniProt ID:
```bash
python3 {baseDir}/scripts/uniprot_fetch.py --accession P04637
```

### Search for proteins:
```bash
python3 {baseDir}/scripts/uniprot_fetch.py --search "insulin human"
```

### Get sequence only:
```bash
python3 {baseDir}/scripts/uniprot_fetch.py --accession P53_HUMAN --format fasta
```

### Get full entry with all annotations:
```bash
python3 {baseDir}/scripts/uniprot_fetch.py --accession P53_HUMAN --format detailed
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--accession` | UniProt accession or entry name | - |
| `--search` | Search query | - |
| `--organism` | Filter by organism (e.g., "human", "9606") | - |
| `--reviewed` | Only Swiss-Prot (reviewed) entries | False |
| `--max-results` | Maximum results for search | 10 |
| `--format` | Output format: summary, detailed, fasta, json | summary |
| `--include-features` | Include sequence features | False |
| `--include-xrefs` | Include cross-references | False |

## Examples

### Look up human p53 tumor suppressor:
```bash
python3 {baseDir}/scripts/uniprot_fetch.py --accession P53_HUMAN --format detailed
```

### Search for kinases in human:
```bash
python3 {baseDir}/scripts/uniprot_fetch.py --search "kinase" --organism human --reviewed --max-results 20
```

### Get FASTA sequence for multiple proteins:
```bash
python3 {baseDir}/scripts/uniprot_fetch.py --accession "P53_HUMAN,BRCA1_HUMAN,EGFR_HUMAN" --format fasta
```

### Search with advanced query:
```bash
python3 {baseDir}/scripts/uniprot_fetch.py --search "gene:TP53 AND organism_id:9606"
```

### Get protein with PDB cross-references:
```bash
python3 {baseDir}/scripts/uniprot_fetch.py --accession P53_HUMAN --include-xrefs
```

## Output Fields

### Summary
- Accession, entry name, protein name
- Gene name, organism
- Sequence length
- Reviewed status

### Detailed
- Full protein name and alternative names
- Function description
- Subcellular location
- Gene ontology terms
- Protein domains
- Post-translational modifications
- Disease associations
- Literature references

### FASTA
Standard FASTA format sequence output.

### JSON
Full UniProt entry in JSON format.

## Cross-References

UniProt entries contain cross-references to:
- **PDB**: 3D protein structures
- **Pfam**: Protein families
- **InterPro**: Protein signatures
- **GO**: Gene Ontology terms
- **KEGG**: Pathway information
- **Reactome**: Reaction pathways
- **DrugBank**: Drug interactions
- **OMIM**: Disease associations

## Query Limitations — Read Before Using

UniProt is a **protein database**, not a drug/chemistry database. Queries must target **proteins by name, gene, or accession**. Drug or chemistry concepts will return zero results.

| ❌ Fails (not a protein query) | ✅ Works |
|---|---|
| "KRAS covalent inhibitors" | "KRAS_HUMAN" or "P01116" |
| "BTK warhead optimization" | "BTK" or "BTK_HUMAN" or "Q06187" |
| "covalent inhibitor design" | "Bruton tyrosine kinase" |
| "BBB penetration ADMET" | "ABCB1 human" or "MDR1" |
| "kinase inhibitor selectivity" | "EGFR kinase" or "EGFR_HUMAN" |

**Rule:** If your query describes a drug, chemical process, mechanism, or assay — use PubChem or TDC instead. UniProt answers: *"What is this protein and what does it do?"*

**For KRAS covalent inhibitor research, the correct two-step workflow is:**
1. UniProt: `--search "KRAS_HUMAN"` or `--accession P01116` → get KRAS protein structure, active site residues (Cys12, Gly12), domains
2. PubChem/ChEMBL: search "KRAS G12C inhibitor" or "sotorasib" → get inhibitor SMILES, IC50, selectivity data

## Notes

- UniProt accession numbers (e.g., P04637) are stable identifiers
- Entry names (e.g., P53_HUMAN) may change
- Reviewed (Swiss-Prot) entries are manually curated
- Unreviewed (TrEMBL) entries are computationally annotated
- API has no authentication requirement
