# AlphaFold2 Structure Prediction

Run AlphaFold2 for protein structure prediction and complex modeling. Use for validating designed sequences, predicting binder-target complexes, and calculating confidence metrics (pLDDT, pTM, ipTM).

Distinct from `alphafold-database` (which retrieves pre-computed structures) — this skill covers running AF2 predictions on custom sequences.

## Requirements

- Python 3.8+
- CUDA 11.0+, 32 GB GPU VRAM minimum (A100 recommended)
- For multimers: ColabFold recommended over local install

## Deployment Options

### 1. ColabFold (Recommended for Multimers)

```bash
pip install colabfold[alphafold]

# Single chain
colabfold_batch input.fasta output_dir/ \
    --model-type alphafold2_ptm \
    --num-recycles 3

# Complex (multimer) — comma-separate chains in FASTA header
# >complex:ChainA,ChainB
colabfold_batch complex.fasta output_dir/ \
    --model-type alphafold2_multimer_v3 \
    --num-recycles 20 \
    --num-models 5
```

### 2. LocalColabFold

```bash
# Install
wget https://raw.githubusercontent.com/YoshitakaMo/localcolabfold/main/install_colabbatch_linux.sh
bash install_colabbatch_linux.sh

# Run offline
colabfold_batch sequences.fasta results/ \
    --model-type alphafold2_multimer_v3 \
    --num-recycles 3 \
    --use-gpu-relax
```

### 3. OpenFold (PyTorch reimplementation)

```bash
pip install openfold
python run_pretrained_openfold.py \
    --fasta_paths input.fasta \
    --output_dir results/ \
    --model_device cuda:0
```

## Key Parameters

| Parameter | Values | Notes |
|-----------|--------|-------|
| `--model-type` | `alphafold2_ptm`, `alphafold2_multimer_v3` | Use multimer for complexes |
| `--num-recycles` | 3–20 | More recycles = better accuracy, slower |
| `--num-models` | 1–5 | 5 models for ensemble confidence |
| `--msa-mode` | `mmseqs2_uniref_env` (default), `single_sequence` | Single = no MSA, faster |
| `--use-gpu-relax` | flag | Amber relaxation on GPU |

## Confidence Metrics

```python
import numpy as np
import json

# Load result JSON
with open("result_model_1.json") as f:
    result = json.load(f)

plddt = np.array(result["plddt"])           # Per-residue confidence 0-100
ptm = result["ptm"]                          # Global TM-score estimate 0-1
iptm = result.get("iptm", None)             # Interface TM-score (multimer only)
pae = np.array(result.get("pae", []))       # Predicted Aligned Error matrix

# Quality thresholds
print(f"Mean pLDDT: {plddt.mean():.1f}")    # >70 = good, >90 = excellent
print(f"pTM: {ptm:.3f}")                    # >0.5 = confident fold
if iptm:
    print(f"ipTM: {iptm:.3f}")              # >0.6 = reliable complex, >0.8 = high confidence
```

## Self-Consistency Validation for Designed Sequences

```bash
# Design → predict → measure similarity to input backbone
# 1. Generate sequences with ProteinMPNN
# 2. Predict structure of each sequence with AF2
# 3. Calculate TM-score / RMSD vs. design backbone

python3 -c "
from Bio.PDB import PDBParser, Superimposer
# Compare predicted vs. designed structure
# High TM-score (>0.8) = sequence encodes target fold
"
```

## Output Files

| File | Contents |
|------|----------|
| `*_relaxed_rank_1.pdb` | Top-ranked relaxed structure |
| `*_unrelaxed_rank_1.pdb` | Top-ranked unrelaxed structure |
| `result_model_*.json` | Scores: pLDDT, pTM, ipTM, PAE matrix |
| `*_coverage.png` | MSA coverage plot |
| `*_pae.png` | PAE heatmap (low = confident) |

## Quality Thresholds

| Metric | Poor | Acceptable | Good | Excellent |
|--------|------|-----------|------|-----------|
| Mean pLDDT | <50 | 50–70 | 70–90 | >90 |
| pTM | <0.4 | 0.4–0.5 | 0.5–0.7 | >0.7 |
| ipTM (complex) | <0.5 | 0.5–0.6 | 0.6–0.8 | >0.8 |
| Interface PAE | >20 Å | 15–20 Å | 8–15 Å | <8 Å |

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Low ipTM despite high pLDDT | Chains fold well independently but don't interact | Redesign interface residues |
| High PAE at interface | Interface not well-determined | Add more recycles; check contact predictions |
| OOM on GPU | Sequence too long | Use `--chunk-size 128` or CPU for MSA |
| All models disagree | Disordered region or wrong fold | Check MSA depth; try `--msa-mode single_sequence` |
