---
name: phonon
description: Compute phonon properties and assess dynamic stability using ML potentials via phonopy
metadata:
---

# Phonon Skill

Compute phonon properties (frequencies, DOS, thermal properties) and assess dynamic stability of crystal structures using the finite-displacement method via [phonopy](https://phonopy.github.io/phonopy/) with forces from ML interatomic potentials (UMA/fairchem).

A structure is **dynamically stable** if all phonon frequencies are real (no imaginary modes). Imaginary frequencies indicate the structure is at a saddle point on the potential energy surface and would spontaneously distort.

## Prerequisites

- `phonopy` installed (`pip install phonopy`)
- `fairchem-core` installed (for UMA calculator)
- `ase` installed
- GPU recommended for UMA force calculations

## Scripts

### `phonon_stability.py` — Check dynamic stability of crystal structures

From a directory of CIF files:
```bash
python3 {baseDir}/scripts/phonon_stability.py \
  --structures-dir ./relaxed_structures \
  --format json
```

From a single CIF file:
```bash
python3 {baseDir}/scripts/phonon_stability.py \
  --structure relaxed_LaH10.cif \
  --format json
```

With custom supercell size:
```bash
python3 {baseDir}/scripts/phonon_stability.py \
  --structures-dir ./candidates \
  --supercell 2,2,2 \
  --model uma-s-1p2 \
  --format json
```

## Parameters

| Parameter | Description |
|-----------|-------------|
| `--structure` | Path to a single CIF/POSCAR file |
| `--structures-dir` | Directory of CIF files to analyze |
| `--after-job` | SLURM job ID to wait for before starting (e.g. wait for UMA screening to finish) |
| `--supercell` | Supercell dimensions (default: auto, typically 2,2,2) |
| `--displacement` | Finite displacement distance in Angstrom (default: 0.01) |
| `--model` | UMA checkpoint (default: `uma-m-1p1`) |
| `--task` | UMA task (default: `omat`) |
| `--device` | `cuda` (default) or `cpu` |
| `--imaginary-threshold` | Frequency threshold in THz for instability (default: -0.5) |
| `--output-dir` | Directory for output files |
| `--format` | `summary` \| `json` |

## Output (JSON)

```json
{
  "status": "COMPLETED",
  "results": [
    {
      "label": "LaH10_relaxed",
      "formula": "LaH10",
      "dynamically_stable": true,
      "min_frequency_THz": 0.23,
      "max_frequency_THz": 45.2,
      "n_imaginary_modes": 0,
      "n_modes": 33,
      "thermal_properties": {
        "300K": {
          "free_energy_kJ_per_mol": -12.5,
          "entropy_J_per_mol_K": 45.2,
          "heat_capacity_J_per_mol_K": 38.1
        }
      }
    }
  ]
}
```

## Dynamic Stability Criteria

A structure is flagged as **dynamically unstable** if:
- Any phonon frequency at the Gamma point is below the imaginary threshold (default: -0.5 THz)
- Any phonon frequency at non-Gamma q-points is below 0 THz

Small negative frequencies near Gamma (> -0.5 THz) are typically numerical artifacts from the acoustic sum rule and are ignored.

## How It Works

1. Load structure from CIF file
2. Create phonopy object with appropriate supercell
3. Generate symmetry-inequivalent displaced supercells (finite displacement method)
4. Compute forces on each displaced supercell using UMA
5. Build force constant matrix, apply symmetry and acoustic sum rule
6. Compute phonon frequencies at commensurate q-points
7. Check for imaginary modes → determine stability
8. Optionally compute thermal properties (free energy, entropy, heat capacity)
