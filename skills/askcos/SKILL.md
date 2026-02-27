---
name: askcos
description: Retrosynthetic template relevance prediction using a locally deployed ASKCOS TorchServe service. Returns ranked precursor suggestions with confidence scores from 5 template sets (reaxys, pistachio, pistachio_ringbreaker, bkms_metabolic, reaxys_biocatalysis). Requires local deployment at http://localhost:9410.
license: MIT License
metadata:
    skill-author: K-Dense Inc.
---

# ASKCOS - Retrosynthetic Template Relevance

## Overview

ASKCOS template_relevance predicts retrosynthetic disconnections using reaction template libraries.
The service runs locally as a TorchServe container (`retro_template_relevance`) and requires a
SMILES input, returning ranked precursor SMILES with template match scores.

Deployment: https://gitlab.com/mlpds_mit/askcosv2/retro/template_relevance
Docs: https://askcos-docs.mit.edu/guide/4-Deployment/4.2-Standalone-deployment-of-individual-modules.html

## Requirements

- Docker container `retro_template_relevance` running at `http://localhost:9410`
- Start/stop: `docker start retro_template_relevance` / `docker stop retro_template_relevance`

## Usage

### Basic Retrosynthesis (JSON output — default)

```bash
python3 skills/askcos/scripts/askcos_retro.py \
  --smiles "CC(C)C1CCC(C)CC1O"
```

### Human-readable summary

```bash
python3 skills/askcos/scripts/askcos_retro.py \
  --smiles "CC(C)C1CCC(C)CC1O" \
  --model reaxys \
  --top 10 \
  --format summary
```

### Select template set

```bash
python3 skills/askcos/scripts/askcos_retro.py \
  --smiles "CC(C)C1CCC(C)CC1O" \
  --model pistachio
```

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--smiles` / `-s` | required | Target molecule SMILES |
| `--model` / `-m` | `reaxys` | Template set: `reaxys`, `pistachio`, `pistachio_ringbreaker`, `bkms_metabolic`, `reaxys_biocatalysis` |
| `--top` / `-n` | `10` | Number of top suggestions to return |
| `--base-url` | `http://localhost:9410` | TorchServe base URL |
| `--format` / `-f` | `json` | Output format: `json` or `summary` |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ASKCOS_BASE_URL` | `http://localhost:9410` | Override TorchServe URL |
| `ASKCOS_MODEL` | `reaxys` | Default template set |

## Output Format (JSON)

```json
{
  "target": "CC(C)C1CCC(C)CC1O",
  "model": "reaxys",
  "total_templates_matched": 191,
  "status": "success",
  "suggestions": [
    {
      "rank": 1,
      "reactants_smiles": "CC1CCC(C(C)C)C(=O)C1",
      "score": 0.4562,
      "template_smarts": "[C:1]-[CH;D3;+0:2](-[C:3])-[OH;D1;+0:4]>>[C:1]-[C;H0;D3;+0:2](-[C:3])=[O;H0;D1;+0:4]",
      "template_id": "5e1f4b6e6348832850995dbf",
      "template_count": 8688,
      "necessary_reagent": ""
    }
  ]
}
```

## Example Output (menthol)

```
ASKCOS (reaxys) — CC(C)C1CCC(C)CC1O
Templates matched: 191

  # 1  score=0.4562  n= 8688  precursors: CC1CCC(C(C)C)C(=O)C1
  # 2  score=0.0387  n=   20  precursors: CC1CCC2C(C1)OC(=O)C2C
  # 3  score=0.0387  n=   20  precursors: CC(C)C1CCC2CC1OC2=O
  # 4  score=0.0321  n=  245  precursors: CC1C=CC(C(C)C)CC1  reagent: [O]
  # 5  score=0.0279  n=26868  precursors: CC(=O)OC1CC(C)CCC1C(C)C
```

Top hit (menthone → menthol via reduction) correctly recovers the industrial Takasago process.

## Integration with Other Skills

```bash
# Get SMILES from RDKit, then run retrosynthesis
SMILES="CC(C)C1CCC(C)CC1O"

# Retrosynthesis
python3 skills/askcos/scripts/askcos_retro.py --smiles "$SMILES" --top 5 --format json

# Analyse top precursor with RDKit
PRECURSOR="CC1CCC(C(C)C)C(=O)C1"
python3 skills/rdkit/scripts/molecular_properties.py --smiles "$PRECURSOR"
```

## References

- ASKCOS: Coley et al., Science 2019. DOI: 10.1126/science.aax1566
- Template relevance: Coley et al., ACS Central Science 2017. DOI: 10.1021/acscentsci.7b00355
- GitLab: https://gitlab.com/mlpds_mit/askcosv2/retro/template_relevance
