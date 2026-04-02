---
name: dft
description: Submit, monitor, and retrieve DFT calculations on Artemis/SLURM via DREAMS framework
metadata:
---

# DFT Skill

Submit and monitor density functional theory (DFT) calculations on the Artemis HPC cluster via the SLURM scheduler. Uses the [DREAMS](https://github.com/BattModels/material_agent) framework for structured DFT workflows ([paper](https://arxiv.org/pdf/2507.14267)).

## Status: IN DEVELOPMENT

## Prerequisites

- Access to Artemis HPC cluster (SLURM scheduler)
- Quantum Espresso installed on the cluster
- DREAMS framework configured (see `references/dreams_integration.md`)
- SSH key or credentials for job submission from a login node

## Scripts

### `dft_submit.py` — Submit a relaxation/SCF job
```bash
python3 {baseDir}/scripts/dft_submit.py \
  --structure path/to/structure.cif \
  --calc-type relax \
  --format json
```

### `dft_status.py` — Poll job status
```bash
python3 {baseDir}/scripts/dft_status.py \
  --job-id 12345 \
  --format json
```

### `dft_retrieve.py` — Retrieve and parse completed results
```bash
python3 {baseDir}/scripts/dft_retrieve.py \
  --job-id 12345 \
  --format json
```

## Parameters

| Parameter | Script | Description |
|-----------|--------|-------------|
| `--structure` | submit | Path to CIF or POSCAR file |
| `--calc-type` | submit | `relax` \| `scf` \| `vc-relax` \| `bands` |
| `--job-id` | status, retrieve | SLURM job ID |
| `--mp-id` | submit | Materials Project ID (fetches structure automatically) |
| `--format` | all | `summary` \| `json` |
| `--dry-run` | submit | Print SLURM script without submitting |
| `--queue` | submit | SLURM partition: `venkvis-cpu` (default), `venkvis-largemem`, `venkvis-a100`, `venkvis-h100`, `debug` |

## Output (JSON)

### Submit
```json
{"job_id": "12345", "calc_type": "relax", "structure": "LaH10", "status": "PENDING", "submit_time": "..."}
```

### Status
```json
{"job_id": "12345", "status": "RUNNING", "elapsed": "00:45:12", "node": "artemis-gpu-01"}
```

### Retrieve
```json
{"job_id": "12345", "status": "COMPLETED", "total_energy_eV": -142.38, "forces_converged": true, "relaxed_structure_cif": "...", "band_gap_eV": 0.0}
```

## Scheduler: SLURM (sbatch), NOT PBS

## Safety
- Never submit jobs from inside a compute node
- Never auto-generate input files without user confirmation
- Always validate structure file exists before submission