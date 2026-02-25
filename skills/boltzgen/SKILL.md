# BoltzGen All-Atom Protein Design

All-atom diffusion-based protein design using BoltzGen. Generates protein backbones and sequences simultaneously with side-chain awareness. Recommended for binder design when precise binding geometry matters.

## Requirements

- Python 3.10+
- 24 GB GPU VRAM minimum
- `boltz` package (BoltzGen is included)

## Installation

```bash
pip install boltz
```

## Design Protocols

BoltzGen supports three entity-based protocols via YAML:

### protein-anything (Standard Binder Design)

Design a protein that binds a fixed target:

```yaml
# binder_design.yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: EVQLVESGGGLVQPGGSLRLSCAASGFTFS...  # target protein (fixed)
  - protein:
      id: B
      length: 80  # binder length to design (no sequence = design this)
      design: true

constraints:
  hotspots:
    - chain: A
      residue: [45, 67, 89, 102]  # target residues to contact
```

### peptide-anything (Peptide Binder)

```yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: MTEYKLVVVGAGGVGKS...  # target
  - peptide:
      id: B
      length: 15  # design 15-residue peptide
      design: true
```

### nanobody-anything (Nanobody Design)

```yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: MTEYKLVVVGAGGVGKS...  # target
  - nanobody:
      id: B
      design: true  # design full nanobody CDRs
      scaffold: VHH  # use nanobody scaffold
```

## Running BoltzGen

```bash
# Generate 50 designs
boltzgen design binder_design.yaml \
    --out_dir designs/ \
    --num_designs 50 \
    --accelerator gpu \
    --devices 1

# With increased sampling steps (better quality, slower)
boltzgen design binder_design.yaml \
    --out_dir designs/ \
    --num_designs 100 \
    --diffusion_steps 200
```

## Python API

```python
from boltz.design import run_design

results = run_design(
    config="binder_design.yaml",
    out_dir="designs/",
    num_designs=50,
    accelerator="gpu",
    diffusion_steps=100,
)

for i, design in enumerate(results):
    print(f"Design {i}: ipTM={design.iptm:.3f}, pLDDT={design.plddt:.1f}")
```

## Output Structure

```
designs/
  design_001/
    structure.cif              # All-atom structure (backbone + side chains)
    confidence.json            # pLDDT, pTM, ipTM scores
    sequence.fasta             # Designed sequence
  design_002/
    ...
  summary.csv                  # All designs ranked by ipTM
```

## Filtering Designs

```python
import pandas as pd

df = pd.read_csv("designs/summary.csv")

# Apply quality filters
passing = df[
    (df["iptm"] > 0.7) &
    (df["plddt"] > 75) &
    (df["pde"] < 15)
].sort_values("iptm", ascending=False)

print(f"{len(passing)} designs pass QC")
print(passing[["design_id", "iptm", "plddt", "sequence"]].head(10))
```

## vs. RFdiffusion + ProteinMPNN

| Feature | BoltzGen | RFdiffusion + MPNN |
|---------|----------|-------------------|
| Side chains | Designed jointly | Separate step |
| Speed (50 designs) | ~2h A100 | ~30min + 10min |
| Accuracy | Higher | Good baseline |
| Ligand-aware | ✓ | Limited |
| Customization | YAML | Extensive flags |
| Best for | Precision interfaces | High-throughput screening |

## Recommended Workflow

1. Generate 100–500 designs with BoltzGen
2. Filter by `iptm > 0.7` and `plddt > 75`
3. Validate top 50 with independent Boltz or ColabFold prediction
4. Rank by ipSAE score (see `ipsae` skill)
5. Order top 10–20 for experimental validation
