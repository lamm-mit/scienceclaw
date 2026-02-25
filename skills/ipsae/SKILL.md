# ipSAE Binder Design Ranking

ipSAE (Interprotein Score from Aligned Errors) — ranking metric for binder designs that outperforms ipTM and iPAE for predicting experimental binding success. Derived from AF2/Boltz/Chai PAE matrices.

## Background

Standard ipTM score has limitations:
- Designed to measure structural confidence, not binding affinity
- Doesn't distinguish between correct but weak vs. incorrect confident predictions

ipSAE extracts the asymmetric aligned error information from the PAE matrix to better predict whether a designed complex will actually bind.

## Installation

```bash
pip install ipsae
```

## Basic Usage

```python
from ipsae import compute_ipsae
import numpy as np

# From ColabFold/AF2 result JSON
result = load_af2_result("result_model_1.json")

pae_matrix = np.array(result["pae"])  # N×N matrix
chain_lengths = [150, 80]             # [target_len, binder_len]

ipsae_score = compute_ipsae(
    pae=pae_matrix,
    chain_lengths=chain_lengths,
    binder_chain=1,     # index of binder chain (0-based)
    target_chain=0,     # index of target chain
)

print(f"ipSAE: {ipsae_score:.4f}")  # Higher = better predicted binder
```

## Batch Ranking

```python
import os
import json
import pandas as pd
from ipsae import compute_ipsae
import numpy as np

def rank_colabfold_results(results_dir: str, chain_lengths: list) -> pd.DataFrame:
    """Rank all ColabFold predictions by ipSAE."""
    records = []

    for fname in os.listdir(results_dir):
        if not fname.endswith(".json") or "result_model" not in fname:
            continue

        with open(os.path.join(results_dir, fname)) as f:
            result = json.load(f)

        pae = np.array(result["pae"])
        iptm = result.get("iptm", 0)
        plddt = np.array(result["plddt"]).mean()

        ipsae = compute_ipsae(
            pae=pae,
            chain_lengths=chain_lengths,
            binder_chain=1,
            target_chain=0
        )

        records.append({
            "file": fname,
            "ipsae": ipsae,
            "iptm": iptm,
            "mean_plddt": plddt,
        })

    df = pd.DataFrame(records)
    return df.sort_values("ipsae", ascending=False)
```

## Command-Line Interface

```bash
# Score a single result
ipsae score result_model_1.json --chain-lengths 150 80

# Rank all results in directory
ipsae rank results/ --chain-lengths 150 80 --output rankings.csv

# With Boltz output
ipsae score complex_confidence_model_0.npz \
    --format boltz \
    --chain-lengths 150 80
```

## ipSAE vs. ipTM Comparison

Published benchmarks (Lim et al., 2024, binder design competition data):

| Metric | AUC (binding vs. non-binding) |
|--------|-------------------------------|
| ipTM | 0.61 |
| iPAE (mean) | 0.64 |
| **ipSAE** | **0.72** |

ipSAE correctly ranks binders ~18% more often than ipTM alone.

## Interpreting ipSAE Scores

| ipSAE | Interpretation |
|-------|---------------|
| > 0.8 | Strong predicted binder — prioritize for ordering |
| 0.6–0.8 | Moderate confidence — worth ordering if ipTM also > 0.7 |
| 0.4–0.6 | Marginal — order only if diversity is important |
| < 0.4 | Unlikely binder — deprioritize |

These thresholds are approximate; calibrate against your own experimental data.

## Integration with Full Pipeline

```python
def final_ranking(designs_dir: str, chain_lengths: list,
                  iptm_min: float = 0.6,
                  plddt_min: float = 75.0,
                  top_n: int = 20) -> list:
    """Full QC + ipSAE ranking pipeline."""
    df = rank_colabfold_results(designs_dir, chain_lengths)

    # Apply hard filters
    passing = df[
        (df["iptm"] >= iptm_min) &
        (df["mean_plddt"] >= plddt_min)
    ]

    # Return top N by ipSAE
    top = passing.nlargest(top_n, "ipsae")
    return top.to_dict("records")
```
