# Boltz Structure Prediction

Open-source biomolecular structure prediction using diffusion models. MSA-optional, handles proteins, RNA, DNA, small molecules, ions, and covalent modifications in a single model. Strong alternative to AlphaFold3.

## Requirements

- Python 3.10+
- 24 GB GPU VRAM minimum (A10G/A100 recommended)
- ~10 GB disk for model weights

## Installation

```bash
pip install boltz
```

## Input Format (YAML)

Boltz uses YAML for flexible entity specification:

```yaml
# complex.yaml — protein + ligand
version: 1
sequences:
  - protein:
      id: A
      sequence: MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSY...
  - ligand:
      id: B
      smiles: "CC1=CC=C(C=C1)S(=O)(=O)N"  # or CCD code
      ccd: ATP  # alternative: use CCD code

# binder-target complex
version: 1
sequences:
  - protein:
      id: [A, B]  # homodimer
      sequence: MTEYKLVVVGAGGVGKS...
      count: 2
  - protein:
      id: C
      sequence: EVQLVESGGGLVQPGG...  # binder
```

## Running Predictions

```bash
# Single prediction
boltz predict complex.yaml \
    --out_dir results/ \
    --accelerator gpu \
    --devices 1 \
    --num_workers 4

# Batch prediction (multiple YAML files)
boltz predict inputs/ \
    --out_dir results/ \
    --accelerator gpu

# Without MSA (faster, slightly lower accuracy for monomers)
boltz predict complex.yaml \
    --out_dir results/ \
    --use_msa_server false
```

## Python API

```python
from boltz.main import predict

predict(
    data="complex.yaml",
    out_dir="results/",
    accelerator="gpu",
    devices=1,
    num_predictions=1,  # ensemble size
    recycling_steps=3,
    diffusion_samples=1
)
```

## Output Files

```
results/
  boltz_results_complex/
    predictions/
      complex/
        complex_model_0.cif          # Predicted structure (CIF format)
        complex_confidence_model_0.json  # Confidence scores
    lightning_logs/                  # Training logs (ignore)
```

## Confidence Metrics

```python
import json

with open("complex_confidence_model_0.json") as f:
    conf = json.load(f)

# Key metrics
plddt = conf["plddt"]                    # Per-residue confidence (0-100)
ptm = conf["ptm"]                        # Global fold confidence (0-1)
iptm = conf["iptm"]                      # Interface confidence (0-1)
ligand_iptm = conf.get("ligand_iptm")    # Ligand interface confidence
pde = conf.get("pde")                    # Predicted Distance Error

print(f"pTM={ptm:.3f}, ipTM={iptm:.3f}")
```

## Quality Thresholds

| Metric | Marginal | Acceptable | Good |
|--------|----------|-----------|------|
| pLDDT (mean) | <60 | 60–80 | >80 |
| ipTM | <0.5 | 0.5–0.7 | >0.7 |
| pTM | <0.4 | 0.4–0.6 | >0.6 |

## vs. AlphaFold2/3

| Feature | Boltz | AF2 | AF3 |
|---------|-------|-----|-----|
| Open source | ✓ | ✓ (weights) | ✗ |
| Ligands | ✓ | ✗ | ✓ |
| RNA/DNA | ✓ | ✗ | ✓ |
| MSA required | Optional | Yes | Optional |
| Local run | ✓ | ✓ | Limited |
| CIF output | ✓ | PDB | CIF |

## Convert CIF to PDB

```bash
# Using BioPython
python3 -c "
from Bio.PDB import MMCIFParser, PDBIO
parser = MMCIFParser()
structure = parser.get_structure('pred', 'complex_model_0.cif')
io = PDBIO()
io.set_structure(structure)
io.save('complex_model_0.pdb')
"
```
