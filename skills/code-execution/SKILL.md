---
name: code-execution
description: Execute Python code for computational workflows — structure generation, simulation, analysis
metadata:
---

# Code Execution Skill

Execute arbitrary Python code for computational workflows that require multi-step logic beyond what single-purpose skills can handle. This enables the agent to write and run custom scripts for tasks like structure enumeration, batch simulations, data analysis, and result processing.

## Scripts

### `run_code.py` — Execute Python code

From inline code:
```bash
python3 {baseDir}/scripts/run_code.py \
  --code "from ase.build import bulk; atoms = bulk('Si'); print(atoms.get_chemical_formula())" \
  --format json
```

From a code file:
```bash
python3 {baseDir}/scripts/run_code.py \
  --file path/to/script.py \
  --format json
```

## Parameters

| Parameter | Description |
|-----------|-------------|
| `--code` | Inline Python code to execute (multi-line supported) |
| `--file` | Path to a Python script to execute |
| `--timeout` | Execution timeout in seconds (default: 300) |
| `--format` | `summary` \| `json` |

## Output (JSON)

```json
{
  "status": "success",
  "stdout": "...",
  "stderr": "...",
  "return_code": 0,
  "execution_time_s": 1.23
}
```

## Available Libraries

The following libraries are available in the Python environment:

- **pymatgen** — Crystal structure generation, spacegroup operations, phase diagrams, MP API
- **ase** — Atomic simulation environment, structure I/O, optimizers, filters
- **fairchem-core** — UMA model loading and inference (`pretrained_mlip`, `FAIRChemCalculator`)
- **mp-api** — Materials Project REST client
- **numpy**, **scipy** — Numerical computing
- **json**, **os**, **sys**, **pathlib** — Standard library

## Example Workflows

### Enumerate structures from a prototype
```python
from pymatgen.core import Structure, Lattice
from pymatgen.transformations.standard_transformations import SubstitutionTransformation

# Build LaH10 prototype (Fm-3m, SG 225)
proto = Structure.from_spacegroup(
    225, Lattice.cubic(5.1),
    ["La", "H", "H"],
    [[0,0,0], [0.25,0.25,0.25], [0.118,0.118,0.118]],
)

# Substitute La with other metals
import json
results = []
for metal in ["Y", "Ca", "Ce", "Sc"]:
    sub = SubstitutionTransformation({"La": metal})
    s = sub.apply_transformation(proto)
    s.to(f"{metal}H10.cif", fmt="cif")
    results.append({"metal": metal, "formula": s.composition.reduced_formula,
                     "n_atoms": len(s), "cif": f"{metal}H10.cif"})
print(json.dumps({"candidates": results}, indent=2))
```

### Relax a structure with UMA
```python
from fairchem.core import pretrained_mlip, FAIRChemCalculator
from ase.io import read
from ase.optimize import FIRE
from ase.filters import FrechetCellFilter
import json

predictor = pretrained_mlip.get_predict_unit("uma-m-1p1", device="cuda")
calc = FAIRChemCalculator(predictor, task_name="omat")

atoms = read("LaH10.cif")
atoms.calc = calc
opt = FIRE(FrechetCellFilter(atoms, scalar_pressure=150/160.21766208), logfile=None)
opt.run(fmax=0.05, steps=500)

print(json.dumps({
    "formula": atoms.get_chemical_formula(),
    "energy_per_atom_eV": round(atoms.get_potential_energy() / len(atoms), 6),
    "converged": opt.converged(),
    "volume_A3": round(atoms.get_volume(), 4),
}))
```

### Convex hull stability check
```python
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDEntry
from pymatgen.core import Composition
import os, json

with MPRester(os.environ["MP_API_KEY"]) as mpr:
    entries = mpr.get_entries_in_chemsys("La-H")

# Add a UMA-computed entry
my_entry = PDEntry(Composition("LaH10"), -155.0, name="UMA-LaH10")
pd = PhaseDiagram(list(entries) + [my_entry])
ehull = pd.get_e_above_hull(my_entry)
print(json.dumps({"e_above_hull_eV": round(ehull, 6)}))
```
