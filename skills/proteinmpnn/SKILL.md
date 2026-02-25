# ProteinMPNN Sequence Design

Inverse folding: design protein sequences that fold into a given backbone structure. Use after RFdiffusion backbone generation or to redesign existing protein sequences.

## Installation

```bash
pip install proteinmpnn
# Or from source (preferred for full control)
git clone https://github.com/dauparas/ProteinMPNN
cd ProteinMPNN
pip install -e .
```

## Basic Usage

### Single Chain Design

```bash
python3 protein_mpnn_run.py \
    --pdb_path designs/binder_0.pdb \
    --out_folder output/ \
    --num_seq_per_target 8 \
    --sampling_temp "0.1" \
    --seed 37 \
    --batch_size 1
```

### Fixed Residues (Partial Design)

Lock specific positions while designing the rest:

```bash
python3 protein_mpnn_run.py \
    --pdb_path structure.pdb \
    --out_folder output/ \
    --num_seq_per_target 8 \
    --sampling_temp "0.1" \
    --fixed_residues "A1 A2 A3 A45 A46"  # keep these unchanged
```

### Multi-Chain Design (Complex)

Design binder (chain B) while fixing target (chain A):

```bash
python3 protein_mpnn_run.py \
    --pdb_path complex.pdb \
    --out_folder output/ \
    --num_seq_per_target 8 \
    --sampling_temp "0.1" \
    --chain_id_jsonl chains.jsonl \
    --fixed_chains_jsonl fixed.jsonl  # fix chain A (target)
```

```python
# Generate chains.jsonl
import json
with open("chains.jsonl", "w") as f:
    json.dump({"complex": ["A", "B"]}, f)
    f.write("\n")

# Generate fixed.jsonl (fix target chain A)
with open("fixed.jsonl", "w") as f:
    json.dump({"complex": ["A"]}, f)
    f.write("\n")
```

## Python API

```python
from protein_mpnn_utils import ProteinMPNN, parse_PDB

# Load model
model = ProteinMPNN(
    num_letters=21,
    node_features=128,
    edge_features=128,
    hidden_dim=128,
    num_encoder_layers=3,
    num_decoder_layers=3,
    augment_eps=0,
    k_neighbors=48,
)
model.load_state_dict(torch.load("vanilla_model_weights/v_48_020.pt"))
model.eval()

# Parse structure
X, S, mask, chain_M, chain_encoding_all, residue_idx, chain_list = parse_PDB(
    "structure.pdb",
    input_chain_list=["A", "B"]
)

# Sample sequences
with torch.no_grad():
    sample_dict = model.sample(
        X, randn, S, chain_M, chain_encoding_all,
        residue_idx, mask, temperature=0.1,
        num_samples=8
    )
    sequences = sample_dict["S"]
```

## Temperature Parameter

Controls sequence diversity vs. nativeness:

| Temperature | Effect | Use When |
|-------------|--------|----------|
| 0.05–0.1 | Conservative, high identity to native | Redesigning functional proteins |
| 0.1–0.2 | Balanced diversity | Standard binder design |
| 0.3–0.5 | High diversity | Exploring sequence space |

## Output Format (FASTA)

```fasta
>design_0, score=1.234, global_score=1.189, seq_recovery=0.45
EVQLVESGGGLVQPGGSLRLSCAASGFTFSDYYMSWVRQAPGKGLEWVSYITYSGSTAYYADSVKGRFTISRDNAKNSLYLQMNSLRAEDTAVYYCARDYYGSGSYFDYWGQGTLVTVSS
>design_1, score=1.198, global_score=1.145, seq_recovery=0.43
EVQLVESGGGLVQPGGSLRLSCAASGFTFS...
```

Lower `score` = better fit to backbone.

## Scoring Existing Sequences

```bash
python3 protein_mpnn_run.py \
    --pdb_path structure.pdb \
    --out_folder scores/ \
    --score_only 1 \
    --path_to_fasta sequences.fasta
```

## Multi-State Design

Design sequences that fold well in multiple conformations:

```bash
python3 protein_mpnn_run.py \
    --pdb_path_multi '{"state1": "conf1.pdb", "state2": "conf2.pdb"}' \
    --out_folder output/ \
    --num_seq_per_target 8
```

## Recommended Workflow

1. Generate backbone with RFdiffusion (50–500 designs)
2. Run ProteinMPNN with `--num_seq_per_target 8 --sampling_temp 0.1`
3. Total: 400–4000 sequences per backbone set
4. Predict structures with ColabFold/Chai
5. Filter by ipTM > 0.7, pLDDT > 75
6. Rank survivors with ipSAE
