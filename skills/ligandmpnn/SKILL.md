# LigandMPNN Ligand-Aware Sequence Design

Extends ProteinMPNN to design sequences around small molecules, metal ions, nucleic acids, and other non-protein entities. Essential for enzyme active site design and ligand-binding protein engineering.

## Installation

```bash
git clone https://github.com/dauparas/LigandMPNN
cd LigandMPNN
pip install -e .
# Download model weights
bash get_model_params.sh
```

## Key Difference from ProteinMPNN

ProteinMPNN only sees protein backbone atoms. LigandMPNN encodes ligand atoms as additional context nodes, so designed sequences are informed by the chemical environment of the binding site.

## Basic Usage

### Design Around Small Molecule

```bash
python3 run.py \
    --model_type "ligand_mpnn" \
    --checkpoint_ligand_mpnn "model_params/ligandmpnn_v_32_010_25.pt" \
    --pdb_path complex.pdb \
    --out_folder output/ \
    --number_of_batches 8 \
    --batch_size 4
```

### Fix Non-Binding Residues (Design Interface Only)

```bash
python3 run.py \
    --model_type "ligand_mpnn" \
    --checkpoint_ligand_mpnn "model_params/ligandmpnn_v_32_010_25.pt" \
    --pdb_path enzyme.pdb \
    --out_folder output/ \
    --redesigned_residues "A42 A67 A89 A134 A156"  # active site only
```

### Metal Coordination Design

```bash
python3 run.py \
    --model_type "ligand_mpnn" \
    --checkpoint_ligand_mpnn "model_params/ligandmpnn_v_32_010_25.pt" \
    --pdb_path metal_complex.pdb \
    --out_folder output/ \
    --use_side_chain_context 1  # include side-chain atoms in context
```

### Protein-DNA/RNA Interface Design

```bash
python3 run.py \
    --model_type "per_residue_label_membrane_mpnn" \
    --checkpoint_path "model_params/ligandmpnn_v_32_020_25.pt" \
    --pdb_path dna_complex.pdb \
    --out_folder output/ \
    --chains_to_design "A"  # design protein chain A around DNA
```

## Model Types

| Model | Use Case |
|-------|---------|
| `ligand_mpnn` | Small molecules, metal ions |
| `per_residue_label_membrane_mpnn` | Membrane proteins (hydrophobic label per residue) |
| `global_label_membrane_mpnn` | Transmembrane topology-aware |
| `soluble_mpnn` | See `solublempnn` skill |

## Python API

```python
import subprocess
import json

def design_with_ligand(pdb_path, out_folder, n_seqs=32, temp=0.1):
    cmd = [
        "python3", "LigandMPNN/run.py",
        "--model_type", "ligand_mpnn",
        "--checkpoint_ligand_mpnn", "model_params/ligandmpnn_v_32_010_25.pt",
        "--pdb_path", pdb_path,
        "--out_folder", out_folder,
        "--number_of_batches", str(n_seqs // 4),
        "--batch_size", "4",
        "--temperature", str(temp),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return out_folder
```

## Output

Same FASTA format as ProteinMPNN with additional ligand-context score:

```fasta
>design_0, score=0.876, ligand_score=0.234, seq_recovery=0.51
MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSY...
```

Lower `ligand_score` = better accommodation of ligand.

## When to Use LigandMPNN vs ProteinMPNN

| Scenario | Use |
|----------|-----|
| No ligand in design | ProteinMPNN |
| Small molecule binding site | LigandMPNN |
| Metal coordination | LigandMPNN |
| DNA/RNA interface | LigandMPNN |
| Membrane protein | LigandMPNN (membrane model) |
| Maximize solubility | SolubleMPNN |

## Typical Workflow for Enzyme Design

1. Generate backbone with RFdiffusion (motif scaffolding of active site)
2. Place ligand in active site (docking or manual placement)
3. Run LigandMPNN with `--redesigned_residues` = active site shell
4. Generate 200–500 sequences
5. Validate with structure prediction (Chai/Boltz) + docking (DiffDock)
6. Filter by pLDDT > 75 and predicted ligand contacts
