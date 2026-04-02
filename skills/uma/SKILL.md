---
name: uma
description: Run structure relaxation using Meta's UMA (Universal Materials Accelerator) via fairchem
metadata:
---

# UMA Skill

Run structure relaxation and single-point energy calculations using [UMA](https://huggingface.co/facebook/UMA) (Universal Materials Accelerator), a machine-learned interatomic potential from Meta FAIR. UMA is a fast alternative to DFT for structure relaxation, achieving near-DFT accuracy at a fraction of the cost.

Built on the [fairchem](https://github.com/facebookresearch/fairchem) framework.

## Prerequisites

- Python 3.12+
- `fairchem-core` installed (`pip install fairchem-core`)
- HuggingFace token with access to `facebook/UMA` (gated model)
  - Set `HF_TOKEN` environment variable or run `huggingface-cli login`
- GPU recommended (CUDA); CPU works but is much slower

## Scripts

### `uma_relax.py` — Relax a crystal structure

From a local structure file:
```bash
python3 {baseDir}/scripts/uma_relax.py \
  --structure path/to/structure.cif \
  --relax-cell \
  --format json
```

From a Materials Project ID:
```bash
python3 {baseDir}/scripts/uma_relax.py \
  --mp-id mp-149 \
  --relax-cell \
  --format json
```

With external pressure (e.g. 150 GPa):
```bash
python3 {baseDir}/scripts/uma_relax.py \
  --structure LaH10.cif \
  --pressure 150 \
  --fmax 0.01 \
  --steps 500 \
  --format json
```

## Parameters

| Parameter | Description |
|-----------|-------------|
| `--structure` | Path to CIF, POSCAR, or XYZ structure file |
| `--mp-id` | Materials Project ID (e.g. `mp-149`); fetches structure automatically |
| `--model` | UMA checkpoint: `uma-s-1p1`, `uma-s-1p2`, `uma-m-1p1` (default: `uma-m-1p1`) |
| `--task` | Task/DFT level: `omat`, `omol`, `omc`, `oc20`, `odac` (default: `omat`) |
| `--device` | `cuda` (default) or `cpu` |
| `--relax-cell` | Enable full cell relaxation (shape + volume + positions) |
| `--pressure` | External pressure in GPa (default: 0). Implies `--relax-cell` |
| `--fmax` | Force convergence threshold in eV/A (default: 0.05) |
| `--steps` | Max optimizer steps (default: 200) |
| `--optimizer` | ASE optimizer: `FIRE` (default) or `LBFGS` |
| `--output-traj` | Path to save ASE trajectory file |
| `--output-cif` | Path to save relaxed structure as CIF |
| `--format` | `summary` \| `json` |
| `--dry-run` | Validate inputs without running relaxation |

## Output (JSON)

```json
{
  "status": "COMPLETED",
  "model": "uma-m-1p1",
  "task": "omat",
  "formula": "LaH10",
  "n_atoms": 44,
  "initial_energy_eV": -45.23,
  "final_energy_eV": -48.71,
  "energy_per_atom_eV": -4.43,
  "converged": true,
  "steps_taken": 87,
  "fmax_achieved": 0.032,
  "pressure_GPa": 150.0,
  "cell_relaxed": true,
  "lattice_a": 5.12,
  "lattice_b": 5.12,
  "lattice_c": 5.12,
  "volume_A3": 134.2,
  "relaxed_structure_cif": "data_LaH10\n..."
}
```

## Tasks and DFT Levels

| Task | Dataset | DFT Level | Use For |
|------|---------|-----------|---------|
| `omat` | OMat24 | PBE/PBE+U (VASP) | Inorganic materials, photovoltaics |
| `omol` | OMol25 | wB97M-V/def2-TZVPD | Organics, pharmaceuticals |
| `omc` | OMC25 | PBE+D3 (VASP) | Molecular crystals |
| `oc20` | OC20 | RPBE (VASP) | Heterogeneous catalysis |
| `odac` | ODAC23 | PBE+D3 (VASP) | Direct air capture, MOFs |

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
