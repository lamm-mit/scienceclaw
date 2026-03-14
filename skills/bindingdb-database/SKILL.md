# BindingDB Database Skill Summary

## Overview
BindingDB is a major public repository containing "over 3 million binding data records for ~1.4 million compounds tested against ~9,200 protein targets." The database stores quantitative binding measurements essential for pharmaceutical research and computational chemistry.

## Primary Use Cases
This resource excels when researchers need to:
- Identify known compounds that bind to specific protein targets
- Conduct structure-activity relationship (SAR) analyses examining how molecular modifications impact binding strength
- Assess compound selectivity across multiple protein targets
- Source curated affinity datasets for machine learning applications
- Evaluate potential off-target binding for drug repurposing studies

## Core Query Methods
The skill provides multiple access approaches: REST API queries by UniProt target ID, compound name searches, SMILES-based lookups, and large-scale TSV file downloads for comprehensive analysis.

## Key Measurement Types
BindingDB tracks four primary affinity metrics: Ki (inhibition constant), Kd (dissociation constant), IC50 (half-maximal inhibition), and EC50 (half-maximal effectiveness). Values below 10 nM typically indicate drug-potency compounds.

## Data Quality Considerations
Results should be filtered by target organism to ensure human protein relevance, and users should recognize that IC50 values vary based on experimental conditions like substrate concentration.
