# Binding Characterization: SPR and BLI

Computational and experimental planning guide for Surface Plasmon Resonance (SPR) and Biolayer Interferometry (BLI) binding kinetics. Covers assay design, troubleshooting, and data interpretation for designed proteins.

## SPR vs. BLI Selection

| Feature | SPR | BLI |
|---------|-----|-----|
| Throughput | Low–medium | High (96/384-well) |
| Sensitivity | Higher | Lower |
| Reference subtraction | Flow cell | Reference well |
| Sample consumption | More | Less |
| Regeneration | Critical | More forgiving |
| Best for | High-quality kinetics | Screening many variants |
| Instruments | Biacore (Cytiva), ProteOn | Octet (Sartorius) |

## Assay Design Principles

### Ligand vs. Analyte Choice

```
Ligand (immobilized on chip/tip):
  - Use the molecule you have abundant, stable supply of
  - Typically: target protein (larger, more stable)
  - Avoid: multivalent molecules on surface (avidity artifacts)

Analyte (flows in solution):
  - Typically: designed binder/antibody
  - Monovalent preferred for clean 1:1 kinetics
```

### Immobilization Strategies (SPR)

| Method | Use When |
|--------|---------|
| Amine coupling (NHS/EDC) | Any protein, permanent |
| Streptavidin capture | Biotinylated ligand, reversible |
| His-tag capture | His-tagged ligand, regenerable |
| Protein A/G | Antibody Fc capture |

```python
# Target immobilization levels (Biacore)
# RMax = Rligand × (MW_analyte / MW_ligand) × stoichiometry
# Target: RMax = 50–200 RU for kinetics (avoid mass transport)

def calc_immobilization_target(
    mw_ligand: float,    # kDa
    mw_analyte: float,   # kDa
    target_rmax: float = 100,   # RU
    stoichiometry: float = 1.0
) -> float:
    """Calculate required ligand immobilization level (RU)."""
    return target_rmax * (mw_ligand / mw_analyte) / stoichiometry
```

## Kinetic Experiment Design

```python
# Analyte concentration series for kinetics
# Span at least 10x above and below Kd
# Use 6–8 concentrations in 2–3x dilution series

def design_concentration_series(
    estimated_kd: float,   # M, rough estimate
    n_points: int = 7,
    dilution_factor: float = 3.0
) -> list:
    """Design analyte concentration series spanning Kd."""
    import numpy as np
    # Center series around Kd
    top = estimated_kd * 30
    bottom = estimated_kd / 30
    concs = [top / (dilution_factor**i) for i in range(n_points)]
    return concs

# Example: estimated Kd = 10 nM
concs = design_concentration_series(10e-9)
# → [300nM, 100nM, 33nM, 11nM, 3.7nM, 1.2nM, 0.4nM]
```

## Data Analysis

```python
import numpy as np
from scipy.optimize import curve_fit

def fit_1to1_kinetics(time: np.ndarray, response: np.ndarray,
                      conc: float) -> dict:
    """
    Fit simple 1:1 Langmuir binding model to SPR/BLI data.
    Returns ka, kd, Rmax.
    """
    def binding_model(t, ka, kd, rmax):
        kobs = ka * conc + kd
        return rmax * (ka * conc / kobs) * (1 - np.exp(-kobs * t))

    popt, pcov = curve_fit(
        binding_model, time, response,
        p0=[1e5, 1e-3, 100],
        bounds=([0, 0, 0], [1e8, 1, 1000])
    )
    ka, kd, rmax = popt
    kd_eq = kd / ka  # Equilibrium Kd = kd/ka

    return {
        "ka": ka,          # M⁻¹s⁻¹ (association rate)
        "kd": kd,          # s⁻¹ (dissociation rate)
        "Kd": kd_eq,       # M (equilibrium dissociation constant)
        "Rmax": rmax,      # RU
        "t_half_dissoc": np.log(2) / kd  # seconds
    }
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| No binding signal | Wrong orientation/inactivation | Switch ligand/analyte; check activity |
| Biphasic association | Heterogeneous ligand or two-state | Use fresh surface; check protein homogeneity |
| Incomplete dissociation | Very slow kd or non-specific | Extend dissociation time; add 0.05% Tween-20 |
| Bulk refractive index shift | Buffer mismatch | Match buffer exactly; increase reference subtraction |
| High non-specific binding | Charge interactions | Add 0.5 M NaCl; block with BSA/ethanolamine |
| Hook effect | Too high analyte conc | Reduce top concentration 10x |
| Mass transport limitation | Too much ligand | Reduce immobilization level; increase flow rate |
| Poor regeneration | Harsh conditions | Test HCl 10mM; glycine pH 2.0; NaOH 10mM |

## Interpreting Results

```python
def interpret_binding(ka: float, kd: float, kd_eq: float) -> dict:
    """Classify binding kinetics."""
    return {
        "Kd_nM": kd_eq * 1e9,
        "affinity_class": (
            "picomolar" if kd_eq < 1e-10 else
            "nanomolar" if kd_eq < 1e-7 else
            "micromolar" if kd_eq < 1e-4 else
            "weak/non-specific"
        ),
        "kinetic_class": (
            "fast_on_fast_off" if ka > 1e6 and kd > 1e-2 else
            "fast_on_slow_off" if ka > 1e6 and kd < 1e-3 else
            "slow_on_slow_off" if ka < 1e5 else "moderate"
        ),
        "t_half_hours": (np.log(2) / kd) / 3600,
        "diffusion_limited": ka > 1e7,  # Possible mass transport if True
    }
```

## Typical Results for Designed Proteins

| Design method | Typical Kd range | Notes |
|--------------|-----------------|-------|
| RFdiffusion + MPNN (first round) | 10–100 µM | Needs optimization |
| BoltzGen (first round) | 1–10 µM | Better starting point |
| After affinity maturation | 1–100 nM | Target for therapeutic proteins |
| Antibodies (CDR design) | 0.1–10 nM | Mature |
