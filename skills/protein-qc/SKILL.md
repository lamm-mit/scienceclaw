# Protein Design QC

Quality control metrics and filtering thresholds for protein designs. Use to evaluate binders, enzymes, and de novo proteins across structure quality, interface metrics, sequence liabilities, and biophysical properties.

## Structure Quality Metrics

```python
import numpy as np
import json

def evaluate_af2_result(result_json_path: str) -> dict:
    with open(result_json_path) as f:
        result = json.load(f)

    plddt = np.array(result["plddt"])
    iptm = result.get("iptm")
    ptm = result.get("ptm")
    pae = np.array(result.get("pae", [[]]))

    qc = {
        "mean_plddt": float(plddt.mean()),
        "min_plddt": float(plddt.min()),
        "ptm": ptm,
        "iptm": iptm,
    }

    if pae.size > 0:
        # Assumes chain A is rows/cols 0:n_a, chain B is n_a:
        # Estimate interface PAE from off-diagonal block
        n = pae.shape[0]
        n_a = n // 2  # rough split; use actual chain lengths if known
        qc["interface_pae"] = float(pae[:n_a, n_a:].mean())

    return qc
```

## Thresholds (Research-Backed)

### Structure Confidence

| Metric | Reject | Marginal | Accept | Excellent |
|--------|--------|---------|--------|-----------|
| Mean pLDDT | <60 | 60–70 | 70–85 | >85 |
| ipTM (complex) | <0.5 | 0.5–0.6 | 0.6–0.8 | >0.8 |
| pTM | <0.4 | 0.4–0.5 | 0.5–0.7 | >0.7 |
| Interface PAE | >25 Å | 15–25 Å | 8–15 Å | <8 Å |

### Interface Metrics (PyRosetta)

```python
def compute_rosetta_interface_metrics(pdb_path: str) -> dict:
    import pyrosetta
    pyrosetta.init("-mute all")
    from pyrosetta import pose_from_pdb
    from pyrosetta.rosetta.protocols.scoring import Interface

    pose = pose_from_pdb(pdb_path)

    # Interface score (dG_separated)
    sfxn = pyrosetta.get_fa_scorefxn()
    score_full = sfxn(pose)

    # Separate chains
    chains = pose.split_by_chain()
    score_sep = sum(sfxn(c) for c in chains)
    dG = score_full - score_sep

    return {"dG_separated": dG}
```

| Metric | Reject | Good | Excellent |
|--------|--------|------|-----------|
| dG_separated (REU) | >-10 | -10 to -30 | <-30 |
| Interface SC | <0.5 | 0.5–0.65 | >0.65 |
| dSASA (Å²) | <400 | 400–800 | >800 |

## Sequence Liability Screening

```python
import re
from Bio.SeqUtils.ProtParam import ProteinAnalysis

def screen_liabilities(seq: str) -> list:
    """Return list of potential problems in sequence."""
    issues = []

    # Aggregation-prone regions
    if re.search(r"[FWYL]{4,}", seq):
        issues.append("hydrophobic_cluster")

    # Deamidation hotspots
    if re.search(r"N[^P][ST]", seq):
        issues.append("deamidation_NxS/T")
    if re.search(r"NG|DG", seq):
        issues.append("deamidation_NG/DG")

    # Proteolytic sites
    if re.search(r"[KR][KR]", seq):
        issues.append("dibasic_site")
    if re.search(r"DP", seq):
        issues.append("DP_cleavage")

    # Cysteines
    n_cys = seq.count("C")
    if n_cys % 2 != 0 and n_cys > 0:
        issues.append("unpaired_cysteine")
    if n_cys > 4:
        issues.append("high_cysteine_count")

    # N-glycosylation
    if re.search(r"N[^P][ST]", seq):
        issues.append("n_glycosylation_site")

    return issues

def biophysical_screen(seq: str) -> dict:
    analysis = ProteinAnalysis(seq)
    return {
        "molecular_weight": analysis.molecular_weight(),
        "isoelectric_point": analysis.isoelectric_point(),
        "instability_index": analysis.instability_index(),
        "gravy": analysis.gravy(),           # < 0 = hydrophilic
        "length": len(seq),
        "liabilities": screen_liabilities(seq),
        "pass_basic_qc": (
            analysis.instability_index() < 40 and
            analysis.gravy() < 0.3
        )
    }
```

## Composite Scoring Pipeline

```python
def rank_designs(designs: list) -> list:
    """
    designs: list of dicts with keys: sequence, plddt, iptm, ptm, interface_pae
    Returns sorted list with composite score.
    """
    scored = []
    for d in designs:
        bio = biophysical_screen(d["sequence"])

        # Composite score (higher = better)
        score = (
            0.4 * d.get("iptm", 0) +
            0.3 * (d.get("mean_plddt", 0) / 100) +
            0.2 * d.get("ptm", 0) +
            0.1 * max(0, 1 - d.get("interface_pae", 20) / 20)
        )

        # Hard filters
        passes = (
            d.get("mean_plddt", 0) > 70 and
            d.get("iptm", 0) > 0.6 and
            bio["instability_index"] < 40 and
            len(bio["liabilities"]) == 0
        )

        scored.append({**d, "composite_score": score, "passes_qc": passes})

    return sorted(scored, key=lambda x: -x["composite_score"])
```

## Multi-Stage Filtering Funnel

Typical binder campaign (starting from 500 RFdiffusion designs):

| Stage | Tool | Filter | Typical pass rate |
|-------|------|--------|-------------------|
| 1. Sequence design | ProteinMPNN | 8 seqs/backbone | 4000 sequences |
| 2. Biophysical screen | BioPython | instability < 40, no liabilities | ~60% pass → 2400 |
| 3. ESMFold screen | ESMFold | pLDDT > 70 | ~70% pass → 1680 |
| 4. AF2 validation | ColabFold | ipTM > 0.6, pLDDT > 75 | ~30% pass → 500 |
| 5. ipSAE ranking | ipSAE | top 50 | 50 candidates |
| 6. Experimental order | — | — | 10–20 |
