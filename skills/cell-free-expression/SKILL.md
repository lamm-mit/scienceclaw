# Cell-Free Protein Synthesis (CFPS)

Cell-free protein synthesis system selection, optimization, and troubleshooting for expressing designed proteins without living cells. Ideal for toxic proteins, rapid prototyping, and non-standard amino acid incorporation.

## System Comparison

| System | Best For | Yield | Cost | Disulfides |
|--------|---------|-------|------|-----------|
| E. coli extract | General proteins, high yield | High (1–3 mg/mL) | Low | Challenging |
| Wheat germ | Eukaryotic proteins, membrane | Medium (0.1–1 mg/mL) | Medium | Yes (oxidizing) |
| Rabbit reticulocyte | Mammalian proteins, PTMs | Low (0.01–0.1 mg/mL) | High | Yes |
| HeLa/CHO cell-free | Complex mammalian glycoproteins | Low | Very high | Yes |

## System Selection Flowchart

```
Protein type?
├── Prokaryotic / simple eukaryotic → E. coli extract
├── Requires glycosylation → HeLa/CHO cell-free
├── Toxic to cells → Any CFPS (cells absent)
├── Disulfide bonds required:
│   ├── 1–2 disulfides → E. coli (with oxidizing additives)
│   └── 3+ disulfides → Wheat germ or reticulocyte
└── Non-standard amino acids → E. coli (auxotrophic strain)
```

## E. coli CFPS Protocol

```python
# Typical reaction composition (50 µL scale)
reaction_components = {
    # Energy system
    "phosphoenolpyruvate": "33 mM",
    "atp": "1.2 mM",
    "gtp_ctp_utp": "0.85 mM each",

    # Amino acids
    "amino_acid_mix": "2 mM each (20 AAs)",

    # Template
    "plasmid_dna": "20 nM",  # Or linear PCR product

    # Extract
    "s30_cell_extract": "33% v/v",

    # Salts & cofactors
    "mgcl2": "10–20 mM",  # Optimize for each extract batch
    "kcl": "100 mM",
    "hepes_ph74": "57 mM",
    "spermidine": "1 mM",
    "putrescine": "1 mM",
    "nad": "0.33 mM",
    "coa": "0.27 mM",
    "folinic_acid": "34 µg/mL",
    "trna_mix": "170 µg/mL",

    # Detection
    "fluorescent_aa": "Optional (BODIPY-Lys for incorporation check)",
}
```

## DNA Template Design for CFPS

Critical differences from standard expression:

```python
# Promoter: T7 (needs T7 RNA polymerase in extract)
# or sigma70 for native E. coli RNAP

template_features = {
    "promoter": "T7 (TAATACGACTCACTATA)",
    "rbs": "Optimal Shine-Dalgarno: AAGGAGG (6–10 nt upstream AUG)",
    "his_tag": "N-terminal 6xHis (improves capture)",
    "terminator": "T7 Te terminator",
    "linear_ok": True,  # PCR products work; add GamS protein to prevent degradation
}

# Codon optimization for E. coli (use online tools)
# Key: avoid rare codons (AGA, AGG, CTA, CGA, ATA, GTA)
# Aim for CAI > 0.8
```

## Troubleshooting Matrix

| Problem | Likely Cause | Solution |
|---------|-------------|---------|
| No expression | Promoter issue | Check T7 promoter sequence; add T7 RNAP |
| Low yield | Mg²⁺ not optimal | Titrate MgCl₂ 6–20 mM |
| Aggregation | Hydrophobic design | Add 1% Tween-20; reduce temp to 25°C |
| No soluble protein | Misfolding | Add chaperones (DnaK/DnaJ/GrpE, GroEL/ES) |
| Truncated product | Rare codons | Recode sequence; add rare tRNA supplement |
| Disulfide incorrect | Redox wrong | Add DsbC (0.1 µM) + GSH/GSSG 4mM/1mM |
| Degradation | Protease activity | Add protease inhibitor cocktail |

## Disulfide Bond Formation

```python
# For proteins with disulfides in E. coli CFPS:
disulfide_additives = {
    "iodoacetamide": "1 mM",         # Pre-treat extract (cap free thiols)
    "dtt": "0 mM",                    # Remove all reducing agents
    "gssg": "4 mM",                   # Oxidized glutathione
    "gsh": "1 mM",                    # Reduced glutathione
    "dsbc_enzyme": "0.1 µM",          # Disulfide isomerase
}
# Alternative: use SHuffle T7 extract (pre-engineered for disulfides)
```

## Non-Standard Amino Acid Incorporation

```python
# Amber suppression (UAG codon → nsAA)
nsaa_setup = {
    "suppressor_trna": "Optimized amber suppressor tRNA",
    "aminoacyl_trna_synthetase": "Engineered aaRS (e.g., PylRS for UAA)",
    "amber_codon_position": "Site-specific in gene",
    "competitor_release_factor": "Add RF1 inhibitor or use RF1-depleted extract",
    "nsaa_concentration": "1–5 mM",
}
```

## Rapid Prototyping Workflow

```python
# 1. PCR amplify gene from plasmid or gene block
# 2. Add T7 promoter and RBS by PCR
# 3. Run 50 µL CFPS reaction at 30°C, 4–16 hours
# 4. Analyze by SDS-PAGE (Coomassie or anti-His western)
# 5. Quantify by ELISA or fluorescence if labeled

# Turnaround: Design → expression check in 1–2 days
```

## Suppliers

| Product | Supplier | Notes |
|---------|---------|-------|
| myTXTL | Arbor Biosciences | Ready-to-use E. coli; good T7 yields |
| PURExpress | NEB | Reconstituted system; minimal proteolysis |
| TNT Rabbit Reticulocyte | Promega | For mammalian protein GTPs |
| Wheat Germ | CellFree Sciences | Best for eukaryotic membrane proteins |
| SHuffle T7 Extract | Custom/lab-made | Disulfide-optimized E. coli |
