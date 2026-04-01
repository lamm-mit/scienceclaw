---
name: uma
description: Run structure relaxation and phonon calculations using Meta's UMA (Universal Materials Accelerator) via fairchem
metadata:
---

# UMA Skill

Run structure relaxation, single-point energy calculations, and phonon property calculations using [UMA](https://huggingface.co/facebook/UMA) (Universal Materials Accelerator), a machine-learned interatomic potential from Meta FAIR. UMA is a fast alternative to DFT, achieving near-DFT accuracy at a fraction of the cost.

Built on the [fairchem](https://github.com/facebookresearch/fairchem) framework.

## Prerequisites

- `fairchem-core` installed (`pip install fairchem-core`)
- `phonopy` installed (`pip install phonopy`) — for phonon calculations
- `HF_TOKEN` environment variable set (gated model on HuggingFace)
- GPU recommended (CUDA); CPU works but is much slower

## Scripts

### `uma_relax.py` — Relax a crystal structure (CLI)

```bash
python3 {baseDir}/scripts/uma_relax.py \
  --structure path/to/structure.cif \
  --relax-cell --pressure 150 \
  --format json
```

| Parameter | Description |
|-----------|-------------|
| `--structure` | Path to CIF, POSCAR, or XYZ structure file |
| `--mp-id` | Materials Project ID (fetches structure automatically) |
| `--model` | `uma-s-1p1`, `uma-s-1p2`, `uma-m-1p1` (default: `uma-m-1p1`) |
| `--task` | `omat` (default), `omol`, `omc`, `oc20`, `odac` |
| `--device` | `cuda` (default) or `cpu` |
| `--relax-cell` | Enable full cell relaxation |
| `--pressure` | External pressure in GPa (default: 0). Implies `--relax-cell` |
| `--fmax` | Force convergence threshold in eV/A (default: 0.05) |
| `--steps` | Max optimizer steps (default: 200) |
| `--output-cif` | Path to save relaxed structure as CIF |
| `--format` | `summary` \| `json` |

## Python API

For batch workflows (screening, phonon), use the Python API directly:

### Loading the model (do once, reuse for all calculations)

```python
from fairchem.core import pretrained_mlip, FAIRChemCalculator

predictor = pretrained_mlip.get_predict_unit("uma-m-1p1", device="cuda")
calc = FAIRChemCalculator(predictor, task_name="omat")
```

### Structure relaxation

```python
from ase.build import bulk
from ase.optimize import FIRE
from ase.filters import FrechetCellFilter

atoms = bulk("Si")  # or: ase.io.read("structure.cif")
atoms.calc = calc

# Relax with external pressure (1 GPa = 1/160.21766208 eV/A^3)
pressure_gpa = 150.0
pressure_ev_per_A3 = pressure_gpa / 160.21766208
opt = FIRE(FrechetCellFilter(atoms, scalar_pressure=pressure_ev_per_A3))
opt.run(fmax=0.05, steps=500)

energy = atoms.get_potential_energy()  # eV
volume = atoms.get_volume()            # A^3
```

### Phonon calculation (finite displacement method)

```python
import phonopy
from phonopy.structure.atoms import PhonopyAtoms
import numpy as np

# Convert ASE Atoms to PhonopyAtoms
ph_atoms = PhonopyAtoms(
    symbols=atoms.get_chemical_symbols(),
    cell=atoms.get_cell(),
    scaled_positions=atoms.get_scaled_positions(),
)

# Create phonopy object with supercell
ph = phonopy.Phonopy(ph_atoms, supercell_matrix=np.diag([2, 2, 2]))
ph.generate_displacements(distance=0.01, is_diagonal=False)

# Compute forces on each displaced supercell using UMA
force_sets = []
for scell in ph.supercells_with_displacements:
    from ase import Atoms as ASEAtoms
    ase_scell = ASEAtoms(
        symbols=scell.symbols, positions=scell.positions,
        cell=scell.cell, pbc=True,
    )
    ase_scell.calc = FAIRChemCalculator(predictor, task_name="omat")
    forces = ase_scell.get_forces()
    forces -= forces.mean(axis=0)  # acoustic sum rule
    force_sets.append(forces)

ph.forces = force_sets
ph.produce_force_constants()
ph.symmetrize_force_constants()

# Get phonon frequencies
ph.run_mesh([8, 8, 8])
frequencies = ph.get_mesh_dict()["frequencies"]  # (n_qpoints, n_bands) in THz

# Check dynamic stability (no imaginary modes)
min_freq = frequencies.min()
dynamically_stable = min_freq > -0.5  # THz threshold

# Thermal properties
ph.run_thermal_properties(t_min=0, t_max=600, t_step=100)
tp = ph.get_thermal_properties_dict()
# tp["temperatures"], tp["free_energy"], tp["entropy"], tp["heat_capacity"]
```

### Auto supercell size

```python
def auto_supercell(n_atoms):
    if n_atoms <= 4: return [3, 3, 3]
    elif n_atoms <= 16: return [2, 2, 2]
    elif n_atoms <= 48: return [2, 2, 1]
    else: return [1, 1, 1]
```

## Structure Generation with pymatgen

### Build from spacegroup + Wyckoff positions

```python
from pymatgen.core import Structure, Lattice

# LaH10 clathrate (Fm-3m, SG 225)
structure = Structure.from_spacegroup(
    225, Lattice.cubic(5.1),
    ["La", "H", "H"],
    [[0, 0, 0], [0.25, 0.25, 0.25], [0.118, 0.118, 0.118]],
)

# CaH6 sodalite (Im-3m, SG 229)
structure = Structure.from_spacegroup(
    229, Lattice.cubic(3.54),
    ["Ca", "H"],
    [[0, 0, 0], [0.25, 0, 0.5]],
)
```

### Element substitution

```python
from pymatgen.transformations.standard_transformations import SubstitutionTransformation
sub = SubstitutionTransformation({"La": "Y"})
new_structure = sub.apply_transformation(structure)
```

### Convert pymatgen ↔ ASE

```python
from pymatgen.io.ase import AseAtomsAdaptor
atoms = AseAtomsAdaptor.get_atoms(structure)      # pymatgen → ASE
structure = AseAtomsAdaptor.get_structure(atoms)   # ASE → pymatgen
```

## Convex Hull Stability

```python
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDEntry
from pymatgen.core import Composition
import os

with MPRester(os.environ["MP_API_KEY"]) as mpr:
    entries = mpr.get_entries_in_chemsys("La-H")

my_entry = PDEntry(Composition("LaH10"), total_energy_eV, name="UMA-LaH10")
pd = PhaseDiagram(list(entries) + [my_entry])
e_above_hull = pd.get_e_above_hull(my_entry)  # eV/atom; 0 = on hull
```

## GPU and SLURM

UMA requires a GPU. Structure your code with a GPU check at the top. When no GPU
is available, write a SLURM script that re-runs the SAME script on a GPU node.
The script file is at `agent_scripts/agent_code.py` relative to the project root.

```python
import torch, subprocess, os, sys, json

# GPU check — must be at the TOP of the script, before any UMA imports
if not torch.cuda.is_available():
    print("No GPU — submitting to SLURM", file=sys.stderr)
    venv = os.environ.get("VIRTUAL_ENV", "")
    script_path = os.path.abspath(sys.argv[0])  # path to this script
    slurm = f"""#!/bin/bash
#SBATCH --partition=venkvis-h100
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err
source {venv}/bin/activate
export HF_TOKEN="{os.environ.get('HF_TOKEN', '')}"
export MP_API_KEY="{os.environ.get('MP_API_KEY', '')}"
cd {os.getcwd()}
{sys.executable} {script_path}
"""
    with open("submit.sh", "w") as f:
        f.write(slurm)
    result = subprocess.run(["sbatch", "submit.sh"], capture_output=True, text=True)
    job_id = result.stdout.strip().split()[-1] if result.returncode == 0 else None
    print(json.dumps({"status": "SUBMITTED_TO_SLURM", "job_id": job_id}))
    sys.exit(0)

# === GPU code below (only runs on GPU node) ===
from fairchem.core import pretrained_mlip, FAIRChemCalculator
# ... rest of computation
```

For job dependency (ensure job B runs after job A):
```bash
sbatch --dependency=afterok:<job_A_id> submit_B.sh
```

## Verification Checklist

Before submitting or executing code that uses UMA, verify:

- [ ] Model loaded with `pretrained_mlip.get_predict_unit("uma-m-1p1", device="cuda")` — NOT `pretrained_mlip("UMA")` or `pretrained_mlip.load()`
- [ ] Calculator created with `FAIRChemCalculator(predictor, task_name="omat")` — NOT `FAIRChemCalculator(model)`
- [ ] Cell filter is `FrechetCellFilter` from `ase.filters` — NOT `ExpCellFilter` from `ase.constraints`
- [ ] Pressure conversion: `pressure_gpa / 160.21766208` — NOT `* 0.0006242` or other approximations
- [ ] SLURM partition is `venkvis-h100` or `venkvis-a100` — NOT `gpu` or `standard`
- [ ] Environment activation: `source <venv>/bin/activate` — NOT `conda activate` or `module load`
- [ ] Venv path from `os.environ.get("VIRTUAL_ENV", "")` — NOT hardcoded
- [ ] API keys from `os.environ.get("HF_TOKEN")` and `os.environ.get("MP_API_KEY")`
- [ ] Output printed as JSON to stdout, progress/errors to stderr

## Models

| Model | Parameters | Speed | Accuracy |
|-------|-----------|-------|----------|
| `uma-s-1p1` | 6.6M active / 150M total | Fast | Good |
| `uma-s-1p2` | 6.6M active / 290M total | Fast | Better |
| `uma-m-1p1` | 50M active / 1.4B total | Slower | Best |

### `uma_screen.py` — Batch structure relaxation and stability screening

Relax all CIF files in a directory with UMA at multiple pressures, compute
formation energies, and check 0 GPa stability against the Materials Project
convex hull. **No hardcoded prototypes** — structures come from the
`structure-enumeration` skill or any other source.

**Typical workflow:**
1. Use `materials` skill to find prototype structures from MP
2. Use `structure-enumeration` skill to generate candidates by metal substitution
3. Use `uma_screen.py` to relax all candidates and assess stability

```bash
# Relax all CIFs in the default enumeration directory
python3 {baseDir}/scripts/uma_screen.py --format json

# From a custom directory
python3 {baseDir}/scripts/uma_screen.py \
  --structures-dir ./my_candidates \
  --pressures 0,150 \
  --format json
```

If no GPU is available, the script auto-submits to SLURM (`venkvis-h100`).

#### Screening Parameters

| Parameter | Description |
|-----------|-------------|
| `--structures-dir` | Directory of CIF files to relax (default: `~/.scienceclaw/enumerated_structures`) |
| `--pressures` | Pressures in GPa (default: `0,150`) |
| `--after-job` | SLURM job ID to wait for before starting (ensures prior job completes first) |
| `--model` | UMA checkpoint (default: `uma-m-1p1`) |
| `--device` | `cuda` (default) or `cpu` |
| `--fmax` | Force convergence threshold (default: `0.05`) |
| `--steps` | Max optimizer steps (default: `200`) |
| `--output-dir` | Directory for relaxed CIFs (default: `./uma_screen_output`) |
| `--format` | `json` or `summary` |
| `--dry-run` | Show plan without running |

#### Pipeline Steps

1. Scan `--structures-dir` for CIF files
2. Identify metal elements in each structure
3. Relax elemental references + H2 at 0 GPa
4. Relax each structure at each pressure
5. Compute formation energy per atom
6. At 0 GPa, query MP convex hull for energy above hull
7. Rank by formation energy, save relaxed CIFs

#### Output (JSON)

```json
{
  "status": "COMPLETED",
  "model": "uma-m-1p1",
  "ranking": [
    {
      "rank": 1,
      "formula": "LaH10",
      "prototype": "LaH10-type",
      "formation_energy_eV_per_atom": -0.1234,
      "converged": true,
      "e_above_hull_eV_per_atom_0GPa": 0.045
    }
  ],
  "candidates": [ ... ],
  "reference_energies": { ... }
}
```

---

## Python API (for scripting)

You can also use UMA directly in Python without the CLI script:

```python
from fairchem.core import pretrained_mlip, FAIRChemCalculator
from ase.build import bulk
from ase.optimize import FIRE
from ase.filters import FrechetCellFilter

# Load model (do this once, reuse for many structures)
predictor = pretrained_mlip.get_predict_unit("uma-m-1p1", device="cuda")
calc = FAIRChemCalculator(predictor, task_name="omat")

# Build or load structure
atoms = bulk("Si")  # or: ase.io.read("structure.cif")
atoms.calc = calc

# Relax with optional external pressure
pressure_gpa = 150.0
pressure_ev_per_A3 = pressure_gpa / 160.21766208
filtered = FrechetCellFilter(atoms, scalar_pressure=pressure_ev_per_A3)
opt = FIRE(filtered)
opt.run(fmax=0.05, steps=500)

# Read results
energy = atoms.get_potential_energy()        # eV
forces = atoms.get_forces()                   # eV/A
volume = atoms.get_volume()                   # A^3
```

## Typical Workflow with HPC

Since UMA requires a GPU, a typical workflow on Artemis is:

1. Prepare your structure files (CIF/POSCAR) on the login node
2. Write a SLURM script that runs `uma_relax.py` (see `hpc` skill for script format)
3. Submit with `sbatch` to `venkvis-h100` or `venkvis-a100`
4. Check status with `squeue -j <job_id>`
5. Read results from the output JSON after completion

## Structure Generation with pymatgen

To enumerate candidate structures for screening, use pymatgen directly:

```python
from pymatgen.core import Structure, Lattice

# Build a structure from spacegroup + Wyckoff positions
structure = Structure.from_spacegroup(
    225,                              # Fm-3m
    Lattice.cubic(5.1),               # lattice parameter
    ["La", "H", "H"],                 # species at each site
    [[0, 0, 0],                       # 4a: metal
     [0.25, 0.25, 0.25],             # 8c: H
     [0.118, 0.118, 0.118]],         # 32f: H (clathrate cage)
)
structure.to("LaH10.cif", fmt="cif")
```

To substitute metals in a prototype:
```python
from pymatgen.transformations.standard_transformations import SubstitutionTransformation

# Replace La with Y in a prototype
sub = SubstitutionTransformation({"La": "Y"})
new_structure = sub.apply_transformation(structure)
```

## Convex Hull Stability Analysis

To check thermodynamic stability at 0 GPa, compare against the Materials Project convex hull:

```python
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDEntry
from pymatgen.core import Composition

with MPRester("YOUR_MP_API_KEY") as mpr:
    # Fetch all known phases in the La-H system
    entries = mpr.get_entries_in_chemsys("La-H")

# Add your UMA-computed entry
my_entry = PDEntry(Composition("LaH10"), total_energy_eV, name="UMA-LaH10")
all_entries = list(entries) + [my_entry]

# Build phase diagram and check stability
pd = PhaseDiagram(all_entries)
e_above_hull = pd.get_e_above_hull(my_entry)  # eV/atom; 0 = on hull (stable)
```
