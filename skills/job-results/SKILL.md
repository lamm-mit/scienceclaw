---
name: job-results
description: Read and parse results from completed SLURM jobs — check status, retrieve output, filter candidates
metadata:
---

# Job Results Skill

Read results from completed SLURM jobs. Checks job status via `sacct`, reads output files (stdout JSON), and can filter results by criteria (e.g., thermodynamic stability, convergence).

This skill bridges the gap between job submission and subsequent analysis steps. When a screening job completes, use this skill to retrieve results and identify candidates for the next pipeline stage.

## Scripts

### `read_job_results.py` — Retrieve and parse job output

Check status and read results:
```bash
python3 {baseDir}/scripts/read_job_results.py \
  --job-id 27018190 \
  --output-dir ./uma_screen_output \
  --format json
```

Filter thermodynamically stable candidates:
```bash
python3 {baseDir}/scripts/read_job_results.py \
  --output-dir ./uma_screen_output \
  --filter-stable \
  --format json
```

Read the latest results from a directory:
```bash
python3 {baseDir}/scripts/read_job_results.py \
  --output-dir ./uma_screen_output \
  --format json
```

## Parameters

| Parameter | Description |
|-----------|-------------|
| `--job-id` | SLURM job ID to check status for |
| `--output-dir` | Directory containing SLURM output files (slurm-*.out) |
| `--results-file` | Direct path to a JSON results file |
| `--filter-stable` | Only return candidates with formation_energy < 0 or e_above_hull < 0.1 |
| `--filter-converged` | Only return converged calculations |
| `--list-cifs` | List relaxed CIF file paths for stable candidates |
| `--format` | `summary` \| `json` |

## Output (JSON)

```json
{
  "status": "COMPLETED",
  "job_id": "27018190",
  "results": { ... },
  "stable_candidates": [
    {
      "label": "YH10_from_LaH10",
      "formula": "YH10",
      "formation_energy_eV_per_atom": -0.18,
      "e_above_hull_eV": 0.0,
      "relaxed_cif": "/path/to/YH10_0GPa.cif"
    }
  ],
  "stable_cif_paths": ["/path/to/YH10_0GPa.cif", ...]
}
```
