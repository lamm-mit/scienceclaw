# Protein Design Workflow

End-to-end pipeline guidance for protein design projects. Covers target preparation, design strategy selection, computational pipeline execution, and quality control.

## Workflow Overview

```
1. Target Preparation
   └── PDB structure → clean → define binding site → identify hotspots

2. Design Generation
   └── RFdiffusion / BoltzGen / BindCraft → backbone + sequence

3. Sequence Optimization
   └── ProteinMPNN / LigandMPNN / SolubleMPNN → diverse sequences

4. Rapid Screening
   └── ESMFold / ESM PLL → filter ~50% by fold quality

5. High-Quality Validation
   └── ColabFold / Chai / Boltz → ipTM, pLDDT, interface PAE

6. Final Ranking
   └── ipSAE → rank survivors → select top 10–20 for ordering

7. QC Checks
   └── Sequence liabilities, biophysical properties, diversity

8. Experimental Validation (wet-lab)
   └── CFPS → SPR/BLI → cellular assay
```

## Step 1: Target Preparation

```python
from Bio.PDB import PDBParser, PDBIO, Select

class CleanedSelect(Select):
    """Keep only standard protein residues."""
    def accept_residue(self, residue):
        return residue.id[0] == " "  # Exclude HETATM (ligands, water)

def prepare_target(pdb_path: str, chains: list = None,
                   out_path: str = "target_clean.pdb"):
    """Clean PDB: remove waters, select chains, renumber."""
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("target", pdb_path)

    io = PDBIO()
    io.set_structure(structure)
    io.save(out_path, CleanedSelect())
    return out_path
```

## Step 2: Choose Design Strategy

See `binder-design` skill for full decision tree. Quick guide:

| Scenario | Pipeline |
|----------|---------|
| Standard protein binder | RFdiffusion → ProteinMPNN |
| Need side-chain precision | BoltzGen |
| High hit rate priority | BindCraft |
| Enzyme / ligand binding | RFdiffusion → LigandMPNN |
| Maximize solubility | Any backbone → SolubleMPNN |

## Step 3: Full Pipeline Script

```python
import subprocess
import os
from pathlib import Path

def run_binder_pipeline(
    target_pdb: str,
    hotspot_residues: list,       # e.g. ["A45", "A67", "A102"]
    binder_length: tuple = (70, 100),
    n_backbones: int = 100,
    n_seqs_per_backbone: int = 8,
    output_dir: str = "pipeline_out/",
    gpu: int = 0
):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    hotspots = ",".join(hotspot_residues)

    # Step 1: RFdiffusion
    backbone_dir = f"{output_dir}/backbones/"
    subprocess.run([
        "python3", "RFdiffusion/scripts/run_inference.py",
        f"inference.output_prefix={backbone_dir}/binder",
        f"inference.input_pdb={target_pdb}",
        f"ppi.hotspot_res=[{hotspots}]",
        f"contigmap.contigs=[A1-999/0 {binder_length[0]}-{binder_length[1]}]",
        f"inference.num_designs={n_backbones}",
    ], check=True)

    # Step 2: ProteinMPNN
    seq_dir = f"{output_dir}/sequences/"
    subprocess.run([
        "python3", "ProteinMPNN/protein_mpnn_run.py",
        "--pdb_path", backbone_dir,
        "--out_folder", seq_dir,
        "--num_seq_per_target", str(n_seqs_per_backbone),
        "--sampling_temp", "0.1",
    ], check=True)

    # Step 3: ESMFold pre-filter
    esm_dir = f"{output_dir}/esmfold/"
    # (run ESMFold on all sequences, keep pLDDT > 70)

    # Step 4: ColabFold
    af2_dir = f"{output_dir}/af2_predictions/"
    subprocess.run([
        "colabfold_batch",
        f"{seq_dir}/seqs.fasta", af2_dir,
        "--model-type", "alphafold2_multimer_v3",
        "--num-recycles", "3",
        "--num-models", "1",
    ], check=True)

    return af2_dir
```

## Step 4–6: Filtering & Ranking

```python
import pandas as pd
from protein_qc import rank_designs  # see protein-qc skill
from ipsae import compute_ipsae      # see ipsae skill

def filter_and_rank(
    predictions_dir: str,
    chain_lengths: list,
    iptm_min: float = 0.6,
    plddt_min: float = 75.0,
    top_n: int = 20
) -> pd.DataFrame:

    results = []
    for f in Path(predictions_dir).glob("*.json"):
        import json, numpy as np
        with open(f) as fp:
            r = json.load(fp)

        pae = np.array(r["pae"])
        ipsae = compute_ipsae(pae, chain_lengths)
        results.append({
            "file": f.stem,
            "iptm": r.get("iptm", 0),
            "plddt": np.array(r["plddt"]).mean(),
            "ipsae": ipsae,
        })

    df = pd.DataFrame(results)
    passing = df[(df.iptm >= iptm_min) & (df.plddt >= plddt_min)]
    return passing.nlargest(top_n, "ipsae")
```

## Step 7: Sequence QC

```python
from protein_qc import biophysical_screen  # see protein-qc skill

def final_sequence_check(sequences: list) -> list:
    approved = []
    for seq in sequences:
        props = biophysical_screen(seq)
        if props["pass_basic_qc"] and len(props["liabilities"]) == 0:
            approved.append({
                "sequence": seq,
                "length": len(seq),
                "mw_kda": props["molecular_weight"] / 1000,
                "pI": props["isoelectric_point"],
                "instability": props["instability_index"],
            })
    return approved
```

## Compute Resources & Time Estimates

| Step | Tool | GPU VRAM | Time (100 designs) |
|------|------|----------|-------------------|
| Backbone generation | RFdiffusion | 16 GB | ~30 min |
| Sequence design | ProteinMPNN | CPU | ~5 min |
| ESMFold screening | ESMFold | 16 GB | ~20 min |
| AF2 validation | ColabFold | 24 GB | ~4 hours |
| ipSAE ranking | CPU | — | <1 min |
| **Total** | | **24 GB recommended** | **~5 hours** |

## Common Failure Modes

| Failure | Diagnosis | Fix |
|---------|-----------|-----|
| No designs pass ipTM > 0.6 | Hotspots inaccessible or too constrained | Relax hotspot list; increase binder length |
| Designs all identical | Too little diversity from RFdiffusion | Increase `diffuser.T`; use partial diffusion |
| Good AF2 ipTM but no experimental binding | Sequence not expressed | Use SolubleMPNN; check CFPS yield first |
| Expression but no binding | Wrong binding mode | Run Boltz with design; inspect interface |
