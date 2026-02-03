---
name: tdc
description: Predict binding-related effects (ADMET) using TDC models from Hugging Face
metadata:
  openclaw:
    emoji: "🧬"
    requires:
      bins:
        - python3
---

# TDC – Binding Effect Prediction

Predict **binding-related effects** for small molecules using pre-trained models from [Therapeutics Data Commons (TDC)](https://huggingface.co/tdc/models) on Hugging Face. Uses SMILES as input and returns classification or scores.

## Overview

- **Blood–brain barrier (BBB):** Will the compound cross the BBB? (binary)
- **hERG blockade:** Cardiotoxicity risk – does it block hERG? (binary)
- **CYP3A4 inhibition:** Metabolism – does it inhibit CYP3A4? (binary)

Models: AttentiveFP (graph), CNN, or Morgan fingerprints. Same task, different architectures.

## Prerequisites

Install TDC and DeepPurpose (optional; needed for prediction). See ScienceClaw `requirements.txt` or:

```bash
pip install PyTDC DeepPurpose
pip install 'dgl' 'torch'
```

## Usage

**Run with the conda environment `tdc`** (PyTDC/DGL are installed there). Use: `conda run -n tdc python ...` or activate the env first.

### Predict with one model (SMILES required)

```bash
conda run -n tdc python {baseDir}/scripts/tdc_predict.py --smiles "CC(=O)OC1=CC=CC=C1C(=O)O" --model BBB_Martins-AttentiveFP
```

### Predict hERG blockade (cardiotoxicity)

```bash
conda run -n tdc python {baseDir}/scripts/tdc_predict.py --smiles "CN1C=NC2=C1C(=O)N(C(=O)N2C)C" --model herg_karim-AttentiveFP
```

### List available models

```bash
conda run -n tdc python {baseDir}/scripts/tdc_predict.py --list-models
```

## Parameters

| Parameter        | Description                                      | Default                  |
|-----------------|--------------------------------------------------|--------------------------|
| `--smiles`      | Single SMILES string                             | -                        |
| `--smiles-file` | File with one SMILES per line                    | -                        |
| `--model`       | TDC model name (see --list-models)               | BBB_Martins-AttentiveFP  |
| `--list-models` | Print available models and exit                  | -                        |
| `--format`      | Output: summary, json                            | summary                  |

## Notes

- First run downloads the model from Hugging Face (cached in `~/.scienceclaw/tdc_models`).
- Input must be valid SMILES; get SMILES from PubChem or ChEMBL if you have a name or ID.
- References: [TDC](https://tdcommons.ai/), [Hugging Face tdc](https://huggingface.co/tdc/models).
