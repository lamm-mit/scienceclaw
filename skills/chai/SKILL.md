# Chai-1 Structure Prediction

Foundation model for molecular structure prediction. Handles proteins, nucleic acids, small molecules, and complexes. Fast inference, strong multimer performance, available via API and local install.

## Requirements

- Python 3.10+
- 16 GB GPU VRAM (A10G sufficient; A100 for large complexes)
- Or: use Chai Discovery API (no local GPU needed)

## Installation

```bash
pip install chai-lab
```

## Local Usage

### Python API

```python
from chai_lab.chai1 import run_inference
import torch
from pathlib import Path

# Single protein
results = run_inference(
    fasta_file=Path("input.fasta"),
    output_dir=Path("results/"),
    num_trunk_recycles=3,
    num_diffn_timesteps=200,
    seed=42,
    device=torch.device("cuda:0"),
    use_esm_embeddings=True,
)

# Access results
for i, result in enumerate(results):
    print(f"Model {i}: pTM={result.ptm:.3f}, ipTM={result.iptm:.3f}")
```

### FASTA Input Format

```fasta
# Single chain
>protein|A
MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPT

# Complex: separate chains with different headers
>protein|A
EVQLVESGGGLVQPGGSLRLSCAASGFTFSDYYMSWVRQAP
>protein|B
MTEYKLVVVGAGGVGKSALTIQLIQNHFVDE

# With small molecule (SMILES)
>protein|A
MTEYKLVVVGAGGVGKS...
>ligand|L
CC1=CC=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C

# RNA
>rna|R
GCGGAUUUAGCUCAGUUGGGAGAGCGCCAGACUGAAGAUCUGGAGGUCCUGUGUUCGAUCCACAGAAUUCGCACCA
```

## Chai Discovery API (No Local GPU)

```python
import requests

# Submit prediction job
response = requests.post(
    "https://api.chaidiscovery.com/v1/predictions",
    headers={"Authorization": f"Bearer {CHAI_API_KEY}"},
    json={
        "sequences": [
            {"type": "protein", "chain_id": "A", "sequence": "MTEYKLVV..."},
            {"type": "protein", "chain_id": "B", "sequence": "EVQLVES..."}
        ],
        "num_diffn_timesteps": 200,
        "num_trunk_recycles": 3,
    }
)
job_id = response.json()["job_id"]

# Poll for results
import time
while True:
    status = requests.get(
        f"https://api.chaidiscovery.com/v1/predictions/{job_id}",
        headers={"Authorization": f"Bearer {CHAI_API_KEY}"}
    ).json()
    if status["status"] == "completed":
        break
    time.sleep(30)

# Download structure
structure_url = status["results"]["structure_url"]
```

## Output Files

| File | Contents |
|------|----------|
| `pred.model_idx_0.cif` | Top-ranked structure (CIF format) |
| `pred.model_idx_0.npz` | Confidence arrays (pLDDT, PAE, pDE) |
| `scores.json` | Aggregate scores per model |

## Parsing Confidence Scores

```python
import numpy as np

data = np.load("pred.model_idx_0.npz")
plddt = data["plddt"]                    # Per-residue, shape (N,)
pae = data["pae"]                        # N×N matrix, Angstroms
pde = data.get("pde")                    # Predicted Distance Error

# Interface residues (chain A = target, chain B = binder)
chain_a_len = 150  # length of chain A
interface_pae = pae[:chain_a_len, chain_a_len:].mean()
print(f"Interface PAE: {interface_pae:.2f} Å (< 10 = good)")
```

## Chai vs. Other Predictors

| Feature | Chai-1 | Boltz | AF2 |
|---------|--------|-------|-----|
| Speed (complex) | Fast | Medium | Slow |
| Small molecules | ✓ | ✓ | ✗ |
| RNA/DNA | ✓ | ✓ | ✗ |
| API available | ✓ | ✗ | ✗ |
| Open weights | ✓ | ✓ | ✓ |
| GPU VRAM | 16 GB | 24 GB | 32 GB |

## Quality Thresholds

| Metric | Marginal | Good | Excellent |
|--------|----------|------|-----------|
| Mean pLDDT | <60 | 60–80 | >80 |
| ipTM (complex) | <0.5 | 0.5–0.75 | >0.75 |
| Interface PAE | >20 Å | 10–20 Å | <10 Å |

## Use Cases

- **Fast validation**: Quickly predict binder-target complexes before expensive MD
- **Ligand complexes**: Predict protein-small molecule binding poses
- **Ensemble scoring**: Generate 5 models, rank by ipTM for design selection
- **Nucleic acid interactions**: Protein-DNA/RNA complex prediction
