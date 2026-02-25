# SolubleMPNN Solubility-Optimized Sequence Design

ProteinMPNN variant trained to design sequences with higher solubility in aqueous solution. Reduces aggregation propensity and improves expression yields in E. coli and cell-free systems.

## Installation

```bash
git clone https://github.com/dauparas/LigandMPNN
cd LigandMPNN
pip install -e .
bash get_model_params.sh
```

## When to Use SolubleMPNN vs ProteinMPNN

| Scenario | Use |
|----------|-----|
| E. coli expression optimization | SolubleMPNN |
| Reducing inclusion body formation | SolubleMPNN |
| High-yield cell-free synthesis | SolubleMPNN |
| Standard binder design (expression not bottleneck) | ProteinMPNN |
| Membrane proteins | LigandMPNN (membrane model) |
| Ligand-binding sites | LigandMPNN |

## Basic Usage

```bash
python3 LigandMPNN/run.py \
    --model_type "soluble_mpnn" \
    --checkpoint_path "model_params/solublempnn_v_48_002.pt" \
    --pdb_path structure.pdb \
    --out_folder output/ \
    --number_of_batches 8 \
    --batch_size 4 \
    --temperature 0.1
```

## Multi-Chain with Fixed Target

```bash
python3 LigandMPNN/run.py \
    --model_type "soluble_mpnn" \
    --checkpoint_path "model_params/solublempnn_v_48_002.pt" \
    --pdb_path complex.pdb \
    --out_folder output/ \
    --chains_to_design "B" \
    --fixed_chains "A" \
    --number_of_batches 16
```

## Python Wrapper

```python
import subprocess
from pathlib import Path

def design_soluble(pdb_path: str, out_folder: str, n_seqs: int = 64,
                   chains_to_design: list = None, fixed_chains: list = None,
                   temperature: float = 0.1) -> str:
    """Run SolubleMPNN and return output folder path."""
    cmd = [
        "python3", "LigandMPNN/run.py",
        "--model_type", "soluble_mpnn",
        "--checkpoint_path", "model_params/solublempnn_v_48_002.pt",
        "--pdb_path", pdb_path,
        "--out_folder", out_folder,
        "--number_of_batches", str(n_seqs // 4),
        "--batch_size", "4",
        "--temperature", str(temperature),
    ]
    if chains_to_design:
        cmd += ["--chains_to_design", " ".join(chains_to_design)]
    if fixed_chains:
        cmd += ["--fixed_chains", " ".join(fixed_chains)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"SolubleMPNN failed: {result.stderr}")
    return out_folder
```

## Post-Processing: Predict Solubility

Filter designed sequences using biophysical predictors:

```python
from Bio.SeqUtils.ProtParam import ProteinAnalysis

def analyze_sequence(seq: str) -> dict:
    analysis = ProteinAnalysis(seq)
    return {
        "instability_index": analysis.instability_index(),  # <40 = stable
        "gravy": analysis.gravy(),                           # <0 = hydrophilic
        "isoelectric_point": analysis.isoelectric_point(),
        "molecular_weight": analysis.molecular_weight(),
    }

# Flag likely insoluble sequences
def is_likely_soluble(seq: str) -> bool:
    props = analyze_sequence(seq)
    return (
        props["instability_index"] < 40 and
        props["gravy"] < 0.1 and  # not too hydrophobic
        not any(seq[i:i+5].count("C") >= 3 for i in range(len(seq)-4))  # no cysteine clusters
    )
```

## Sequence Liabilities to Check

```python
import re

def check_liabilities(seq: str) -> list:
    liabilities = []
    if re.search(r"N[^P][ST]", seq):
        liabilities.append("N-glycosylation site")
    if re.search(r"NG|DG", seq):
        liabilities.append("Deamidation motif")
    if re.search(r"[KR]{3,}", seq):
        liabilities.append("Polybasic cluster (proteolysis risk)")
    if seq.count("C") > 3 and seq.count("C") % 2 != 0:
        liabilities.append("Odd number of cysteines (unpaired disulfide)")
    if re.search(r"[FWYI]{4,}", seq):
        liabilities.append("Hydrophobic cluster (aggregation risk)")
    return liabilities
```

## Recommended Workflow for E. coli Expression

1. Generate backbone (RFdiffusion or BoltzGen)
2. Design sequences with SolubleMPNN (temperature 0.1, 64+ sequences)
3. Filter: GRAVY < 0, instability index < 40, no liabilities
4. Validate fold with ColabFold/Chai
5. Codon-optimize for E. coli (use online tools or `python-codon-tables`)
6. Order synthetic genes (200 bp–2 kb: IDT, Twist Bioscience)

## Benchmark: SolubleMPNN vs ProteinMPNN Expression

Published results (Dauparas et al., 2023):
- SolubleMPNN designs expressed solubly in E. coli at **72%** rate
- ProteinMPNN designs: **54%** rate
- ~18 percentage point improvement in soluble expression
