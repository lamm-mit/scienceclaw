# InterPro Database Skill Documentation

## Overview
InterPro is a comprehensive protein annotation resource maintained by EMBL-EBI that integrates signatures from 13 member databases. It classifies proteins into families, domains, homologous superfamilies, repeats, and functional sites, covering over 100 million protein sequences.

## Primary Use Cases
- Predicting functions of uncharacterized proteins
- Analyzing domain architecture and composition
- Classifying proteins into evolutionary families
- Mapping Gene Ontology terms to sequences
- Conducting evolutionary and structural analyses

## Core API Functions

**Protein Lookup**: Query InterPro entries for any UniProt identifier using the `/protein/UniProt/{id}/entry/InterPro/` endpoint.

**Entry Details**: Retrieve comprehensive information about specific InterPro entries through `/entry/InterPro/{id}/` or member database-specific endpoints.

**Reverse Lookup**: "Get all proteins annotated with an InterPro entry" via `/entry/InterPro/{id}/protein/UniProt/` to discover related sequences.

**Domain Architecture**: Obtain complete positional mapping of domains across a protein sequence.

**GO Term Mapping**: Extract Gene Ontology annotations embedded within InterPro entry metadata.

## Integration Strategy
- Utilize UniProt accession numbers for reliable queries
- Distinguish between broad family classifications and specific structural domains
- Implement rate limiting (0.3 seconds between requests) for batch operations
- Combine results with UniProt and PDB data for enriched biological context

## Technical Implementation
All queries use the REST API at `https://www.ebi.ac.uk/interpro/api/` with JSON responses. Python implementations employ the `requests` library with appropriate headers and error handling.
