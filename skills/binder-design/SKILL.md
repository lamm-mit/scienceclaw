# Binder Design Tool Selection

Decision framework for choosing between BoltzGen, RFdiffusion, BindCraft, and other tools for protein binder design campaigns.

## Decision Tree

```
What do you need?
│
├── All-atom output with side-chain awareness?
│   └── YES → BoltzGen (recommended default)
│
├── Backbone-only + sequence design separately?
│   └── YES → RFdiffusion → ProteinMPNN/LigandMPNN
│
├── End-to-end with built-in AF2 validation per design?
│   └── YES → BindCraft (slower but higher hit rate)
│
├── Ligand/small molecule in binding site?
│   └── YES → BoltzGen or RFdiffusion + LigandMPNN
│
├── Peptide binder (< 30 residues)?
│   └── YES → BoltzGen (peptide-anything protocol)
│
├── Symmetric oligomer scaffold?
│   └── YES → RFdiffusion (symmetry support)
│
└── Very large target (> 500 residues)?
    └── YES → RFdiffusion (better memory efficiency)
```

## Tool Comparison

| Feature | BoltzGen | RFdiffusion | BindCraft |
|---------|----------|-------------|-----------|
| Side chains | Joint design | Backbone only | Joint (via AF2 hallucination) |
| Speed (50 designs) | ~2h A100 | ~30 min | ~8h A100 |
| Hit rate (exp. binding) | ~15–25% | ~10–20% | ~25–40% |
| Built-in validation | ipTM from diffusion | None | AF2 ipTM per design |
| Ligand-aware | ✓ | Limited | ✗ |
| Symmetric designs | ✗ | ✓ | ✗ |
| Ease of use | YAML config | CLI flags | Config JSON |
| GPU VRAM | 24 GB | 16 GB | 32 GB |

## Campaign Scale Guide

| Goal | Recommended Tool | Designs to Generate | Expected Binders to Order |
|------|-----------------|--------------------|-----------------------------|
| Proof of concept | BoltzGen | 50–100 | 5–10 |
| Standard campaign | RFdiffusion + MPNN | 200–500 | 10–20 |
| High-quality hits | BindCraft | 100–200 | 5–15 |
| Ligand-binding enzyme | RFdiffusion + LigandMPNN | 200–1000 | 10–20 |
| Rapid screen | BoltzGen | 100 | 10 |

## Pipeline Templates

### Standard Binder Campaign

```bash
# 1. Generate backbones
python3 RFdiffusion/scripts/run_inference.py \
    inference.output_prefix=designs/binder \
    inference.input_pdb=target.pdb \
    'ppi.hotspot_res=[A45,A67,A102]' \
    'contigmap.contigs=[A1-200/0 60-100]' \
    inference.num_designs=200

# 2. Design sequences
python3 LigandMPNN/run.py \
    --model_type proteinmpnn \
    --pdb_path designs/ \
    --out_folder seqs/ \
    --number_of_batches 8

# 3. Predict structures (ColabFold batch)
colabfold_batch seqs/all_sequences.fasta predictions/ \
    --model-type alphafold2_multimer_v3 \
    --num-recycles 3 \
    --num-models 1

# 4. Rank by ipSAE
ipsae rank predictions/ --chain-lengths 200 80 --output rankings.csv
```

### BoltzGen All-in-One

```yaml
# binder.yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: MTEYKLVVVGAGGVGKS...  # target
  - protein:
      id: B
      length: 80
      design: true
constraints:
  hotspots:
    - chain: A
      residue: [45, 67, 102]
```

```bash
boltzgen design binder.yaml --out_dir designs/ --num_designs 100
```

### BindCraft High-Quality

```json
{
  "target_pdb": "target.pdb",
  "hotspot_residues": "A45,A67,A102",
  "binder_length": [60, 100],
  "num_designs": 100,
  "protocol": "default",
  "af2_validation": true,
  "output_dir": "bindcraft_out/"
}
```

```bash
python3 bindcraft.py --config binder_config.json
```

## Hotspot Identification

```python
from Bio.PDB import PDBParser
import numpy as np

def identify_hotspots(pdb_path: str, chain: str = "A",
                      binding_site_center: tuple = None,
                      radius: float = 10.0) -> list:
    """Find surface residues near a binding site for hotspot specification."""
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("target", pdb_path)
    model = structure[0]

    hotspots = []
    for residue in model[chain]:
        if residue.id[0] != " ":  # Skip HET
            continue
        # Use CA atom as representative
        if "CA" not in residue:
            continue
        ca = residue["CA"].get_vector()

        if binding_site_center:
            center = np.array(binding_site_center)
            dist = np.linalg.norm(ca.get_array() - center)
            if dist < radius:
                hotspots.append(f"{chain}{residue.id[1]}")

    return hotspots
```

## Avoiding Common Failures

| Problem | Prevention |
|---------|-----------|
| Designs don't contact hotspots | Verify hotspot accessibility; reduce binder length range |
| All designs converge to same solution | Use partial diffusion for diversity; vary hotspot sets |
| Poor AF2 validation scores | Use BindCraft (built-in AF2 during design) |
| Low expression yield | Switch to SolubleMPNN; check GRAVY/instability |
| Target flexibility issues | Use ensemble of target conformations |
