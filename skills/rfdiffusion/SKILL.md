# RFdiffusion Backbone Generation

Diffusion-based de novo protein backbone generation. Use for: binder scaffolds targeting specific hotspot residues, novel fold generation, motif scaffolding, and symmetric oligomer design.

## Requirements

- Python 3.9+
- 16–24 GB GPU VRAM (A100 recommended for large designs)
- ~2 GB disk for model weights

## Installation

```bash
# Via SE3-Diffusion environment (recommended)
conda create -n rfdiffusion python=3.9
conda activate rfdiffusion
pip install rfdiffusion

# Or from source
git clone https://github.com/RosettaCommons/RFdiffusion
cd RFdiffusion
pip install -e .

# Download model weights
wget http://files.ipd.uw.edu/pub/RFdiffusion/rfdiffusion_weights.tar.gz
tar -xzf rfdiffusion_weights.tar.gz
```

## Core Use Cases

### 1. Binder Design (Most Common)

Design a protein that contacts specific hotspot residues on a target:

```bash
python3 scripts/run_inference.py \
    inference.output_prefix=outputs/binder \
    inference.input_pdb=target.pdb \
    'ppi.hotspot_res=[A45,A67,A89]' \
    contigmap.contigs='[A1-150/0 70-100]' \
    inference.num_designs=50
```

`contigmap.contigs` format:
- `A1-150` = use chain A residues 1-150 (target, fixed)
- `/0` = chain break
- `70-100` = design 70–100 residue binder (length range)

### 2. Motif Scaffolding

Scaffold a functional motif (active site, binding epitope) into a new protein:

```bash
python3 scripts/run_inference.py \
    inference.output_prefix=outputs/scaffold \
    inference.input_pdb=motif.pdb \
    'contigmap.contigs=[10-40/A25-35/10-40]' \
    inference.num_designs=100
```

`10-40/A25-35/10-40` = 10–40 designed residues + motif A25-35 (fixed) + 10–40 designed residues

### 3. Unconditional Generation

Generate novel protein folds:

```bash
python3 scripts/run_inference.py \
    inference.output_prefix=outputs/novel \
    'contigmap.contigs=[100-150]' \
    inference.num_designs=100
```

### 4. Symmetric Oligomers

```bash
python3 scripts/run_inference.py \
    inference.output_prefix=outputs/trimer \
    'contigmap.contigs=[100]' \
    symmetry=C3 \
    inference.num_designs=50
```

## Python API

```python
from rfdiffusion.inference.utils import preprocess_pdb
from rfdiffusion import RFDiffusion

model = RFDiffusion.from_pretrained("rfdiffusion_weights/")

results = model.design_binder(
    target_pdb="target.pdb",
    hotspot_residues=["A45", "A67", "A89"],
    binder_length=(70, 100),
    num_designs=50,
    output_dir="outputs/"
)
```

## Key Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `inference.num_designs` | Number of backbones to generate | 50–500 |
| `diffuser.T` | Diffusion steps (quality vs speed) | 50 (fast) – 200 (quality) |
| `ppi.hotspot_res` | Target residues binder must contact | `[A45,A67,A102]` |
| `contigmap.contigs` | Design specification string | `[A1-200/0 50-80]` |
| `inference.ckpt_override_path` | Use specific model checkpoint | — |

## Partial Diffusion (Diversify Existing Design)

```bash
# Partially noise and re-denoise an existing backbone
python3 scripts/run_inference.py \
    inference.output_prefix=outputs/diversified \
    inference.input_pdb=good_design.pdb \
    diffuser.partial_T=20 \
    'contigmap.contigs=[A1-80]' \
    inference.num_designs=20
```

## Downstream: Add Sequences with ProteinMPNN

RFdiffusion outputs backbone-only PDBs (no sequence). Use ProteinMPNN or LigandMPNN to design sequences:

```bash
# After RFdiffusion
python3 run_ProteinMPNN/protein_mpnn_run.py \
    --pdb_path outputs/binder_0.pdb \
    --out_folder mpnn_output/ \
    --num_seq_per_target 8 \
    --sampling_temp 0.1
```

## Output Files

| File | Contents |
|------|----------|
| `{prefix}_0.pdb` | Generated backbone (N, CA, C, O only) |
| `{prefix}_0.trb` | Trajectory info, contig mapping |
| `traj/{prefix}_0_pX0_traj.pdb` | Diffusion trajectory |

## Common Issues

| Problem | Fix |
|---------|-----|
| Binder doesn't contact hotspots | Increase `ppi.hotspot_res` weights or reduce binder length range |
| All designs look similar | Increase `diffuser.T` or use partial diffusion |
| OOM error | Reduce design length or use `inference.chunk_size=64` |
| Poor downstream AF2 ipTM | Try partial diffusion to diversify; check hotspot accessibility |
