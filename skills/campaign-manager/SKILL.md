# Campaign Manager

Goal-oriented protein design campaign planning. Converts abstract objectives into concrete computational pipelines with cost/time estimates, health monitoring, and adaptive decision-making.

## Campaign Types

| Goal | Pipeline | Expected Timeline |
|------|---------|-----------------|
| Proof-of-concept binder | BoltzGen → Chai → ipSAE | 1–2 weeks compute |
| High-throughput screen | RFdiffusion → MPNN → ESMFold → AF2 | 2–4 weeks compute |
| High-quality therapeutic | BindCraft → ipSAE → affinity maturation | 4–8 weeks compute |
| Enzyme design | RFdiffusion + LigandMPNN → Boltz | 3–6 weeks compute |
| Quick exploration | BoltzGen 50 designs → Chai | 3–5 days compute |

## Campaign Planning

```python
from dataclasses import dataclass, field
from typing import List, Optional
import json

@dataclass
class DesignCampaign:
    name: str
    target_pdb: str
    goal: str                          # "binder", "enzyme", "scaffold"
    hotspot_residues: List[str]
    binder_length_range: tuple = (60, 100)

    # Pipeline config
    n_backbone_designs: int = 200
    n_seqs_per_backbone: int = 8
    structure_prediction_tool: str = "colabfold"  # or "chai", "boltz"
    sequence_design_tool: str = "proteinmpnn"     # or "ligandmpnn", "solublempnn"

    # Quality thresholds
    iptm_threshold: float = 0.6
    plddt_threshold: float = 75.0
    ipsae_top_n: int = 20

    # Budget
    gpu_hours_budget: Optional[float] = None
    designs_to_order: int = 10

    def estimate_pipeline(self) -> dict:
        """Estimate compute requirements and expected yields."""
        total_seqs = self.n_backbone_designs * self.n_seqs_per_backbone

        # Empirical pass rates
        esm_pass_rate = 0.65
        af2_pass_rate = 0.25
        ipsae_final = self.ipsae_top_n

        esm_survivors = int(total_seqs * esm_pass_rate)
        af2_survivors = int(esm_survivors * af2_pass_rate)
        final_candidates = min(af2_survivors, ipsae_final)

        # GPU time estimates (A100)
        rfdiffusion_hours = self.n_backbone_designs * 0.1 / 60
        mpnn_hours = 0.1  # fast
        esm_hours = esm_survivors * 0.01 / 60
        af2_hours = esm_survivors * 2.5 / 60  # ~2.5 min per pair

        return {
            "total_sequences_designed": total_seqs,
            "esm_survivors": esm_survivors,
            "af2_survivors": af2_survivors,
            "expected_final_candidates": final_candidates,
            "gpu_hours": {
                "rfdiffusion": round(rfdiffusion_hours, 1),
                "mpnn": round(mpnn_hours, 1),
                "esmfold": round(esm_hours, 1),
                "af2_validation": round(af2_hours, 1),
                "total": round(rfdiffusion_hours + esm_hours + af2_hours, 1),
            },
            "wall_time_days": round(
                (rfdiffusion_hours + esm_hours + af2_hours) / 24, 1
            ),
            "meets_budget": (
                self.gpu_hours_budget is None or
                (rfdiffusion_hours + af2_hours) <= self.gpu_hours_budget
            )
        }
```

## Campaign Health Assessment

```python
def assess_campaign_health(campaign_dir: str, stage: str) -> dict:
    """
    Check campaign progress and flag issues.
    stage: "post_rfdiffusion" | "post_mpnn" | "post_esm" | "post_af2"
    """
    import os, glob, json
    import numpy as np

    health = {"stage": stage, "issues": [], "recommendations": []}

    if stage == "post_af2":
        json_files = glob.glob(f"{campaign_dir}/af2/**/*.json", recursive=True)
        iptm_vals = []
        plddt_vals = []

        for f in json_files:
            with open(f) as fp:
                r = json.load(fp)
            iptm_vals.append(r.get("iptm", 0))
            plddt_vals.append(np.array(r.get("plddt", [0])).mean())

        if not iptm_vals:
            health["issues"].append("No AF2 results found")
            return health

        pass_rate = sum(1 for x in iptm_vals if x > 0.6) / len(iptm_vals)
        health["metrics"] = {
            "n_predictions": len(iptm_vals),
            "mean_iptm": np.mean(iptm_vals),
            "pass_rate_iptm06": pass_rate,
            "mean_plddt": np.mean(plddt_vals),
        }

        if pass_rate < 0.05:
            health["issues"].append("Very low pass rate (<5%) — redesign needed")
            health["recommendations"].extend([
                "Check hotspot accessibility in target structure",
                "Try BoltzGen instead of RFdiffusion",
                "Reduce binder length constraints",
                "Verify target PDB quality",
            ])
        elif pass_rate < 0.15:
            health["issues"].append("Low pass rate (<15%) — consider adjustments")
            health["recommendations"].append("Try partial diffusion for diversity")

    return health
```

## Adaptive Pipeline Decisions

```python
def decide_next_step(health: dict) -> str:
    """
    Given campaign health assessment, recommend next action.
    """
    issues = health.get("issues", [])
    metrics = health.get("metrics", {})

    pass_rate = metrics.get("pass_rate_iptm06", 0)

    if pass_rate == 0:
        return "ABORT: Zero passing designs. Review target preparation and hotspot selection."

    elif pass_rate < 0.05:
        return (
            "REDESIGN: Switch to BindCraft for built-in AF2 validation during design, "
            "or verify hotspot residues are solvent-exposed."
        )

    elif pass_rate < 0.10:
        return (
            "EXPAND: Generate 2x more backbones with partial diffusion from best current designs. "
            "Also try SolubleMPNN for better expression."
        )

    elif metrics.get("mean_iptm", 0) > 0.75:
        return (
            "ADVANCE: Strong campaign. Run ipSAE ranking on top designs, "
            "run biophysical QC, and prepare ordering list."
        )

    else:
        return (
            "CONTINUE: Moderate progress. Apply ipSAE ranking, "
            "consider affinity maturation on top 5 designs via partial diffusion."
        )
```

## Cost Estimation

```python
def estimate_costs(campaign: DesignCampaign,
                   gpu_cost_per_hour: float = 2.50,  # USD, A100 on-demand
                   gene_synthesis_per_seq: float = 150.0,
                   expression_per_sample: float = 80.0) -> dict:

    estimates = campaign.estimate_pipeline()
    gpu_hours = estimates["gpu_hours"]["total"]

    return {
        "compute_cost_usd": round(gpu_hours * gpu_cost_per_hour, 0),
        "gene_synthesis_usd": round(campaign.designs_to_order * gene_synthesis_per_seq, 0),
        "expression_screening_usd": round(campaign.designs_to_order * expression_per_sample, 0),
        "total_estimated_usd": round(
            gpu_hours * gpu_cost_per_hour +
            campaign.designs_to_order * (gene_synthesis_per_seq + expression_per_sample),
            0
        ),
    }
```

## Affinity Maturation (Second Round)

After identifying binders, improve affinity via computational iteration:

```bash
# Partial diffusion on best designs
python3 RFdiffusion/scripts/run_inference.py \
    inference.input_pdb=best_binder.pdb \
    'contigmap.contigs=[A1-999/0 B1-80]' \
    diffuser.partial_T=20 \
    inference.num_designs=50 \
    inference.output_prefix=matured/binder

# Then: ProteinMPNN → AF2 → ipSAE (same pipeline)
```
