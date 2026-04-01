---
name: hpc
description: SLURM HPC job management on Artemis — write submission scripts, submit jobs, monitor status, retrieve results
metadata:
---

# HPC Skill

Manage SLURM batch jobs on the Artemis HPC cluster. This skill teaches the agent how to write SLURM submission scripts, submit them, monitor status, and retrieve results using standard SLURM CLI tools.

There are no wrapper scripts — use SLURM commands directly via bash.

## Artemis Cluster Overview

33 nodes total: 25 CPU, 3 large-memory, 3 H100 GPU, 2 A100 GPU.

### Partitions

| Partition | Wall Time | Nodes | CPUs | RAM | GPUs | Notes |
|-----------|-----------|-------|------|-----|------|-------|
| `venkvis-cpu` | 48h | 25 | 96c (EPYC 9654) | 368 GB | — | Default for DFT |
| `venkvis-largemem` | 48h | 3 | 96c (EPYC 9654) | 768 GB | — | Large-memory jobs |
| `venkvis-a100` | 8h | 2 | 32c (EPYC 7513) | 512 GB | 4× A100 80GB | GPU compute |
| `venkvis-h100` | 8h | 3 | 96c (EPYC 9654) | 368 GB | 4× H100 80GB | GPU compute (fastest) |
| `debug` | 30m | 4 max | varies | varies | varies | Quick tests |

### Storage

| Tier | Path | Capacity | Notes |
|------|------|----------|-------|
| Turbo | `/nfs/turbo/coe-venkvis/` | 10 TB (500 GB fair share) | Persistent, backed up |
| Scratch | `/scratch/venkvis_root/venkvis/` | 10 TB (500 GB fair share) | **60-day auto-purge** |
| Home | `/home/<user>` | 80 GB | User home |
| Node Local | `/tmp` | 1.9 TB NVMe | Ephemeral, fast I/O |

## Writing a SLURM Submission Script

Create a bash script with `#SBATCH` directives. Example for a GPU job:

```bash
#!/bin/bash
#SBATCH --job-name=my-job
#SBATCH --partition=venkvis-h100
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:1
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

# Activate Python environment
source /path/to/venv/bin/activate

# Export any needed API keys
export HF_TOKEN="..."
export MP_API_KEY="..."

# Run your computation
python3 my_script.py --arg1 value1 --format json > results.json

echo "Done: $(date)"
```

For CPU jobs, remove `--gres=gpu:1` and use `--partition=venkvis-cpu`.

Key `#SBATCH` directives:
- `--partition=<name>` — which queue (see table above)
- `--gres=gpu:<N>` — request N GPUs (GPU partitions only)
- `--time=HH:MM:SS` — wall time limit
- `--mem=<N>G` — memory per node
- `--cpus-per-task=<N>` — CPU cores
- `--output=<path>` / `--error=<path>` — stdout/stderr files (`%j` = job ID)
- `--array=0-9` — submit a job array (10 tasks)

## Submitting Jobs

```bash
# Submit a script
sbatch submit.sh

# Submit with partition override
sbatch --partition=venkvis-h100 submit.sh

# Submit with dependency (run after job 12345 completes)
sbatch --dependency=afterok:12345 next_step.sh
```

Output: `Submitted batch job 12345`

## Checking Job Status

```bash
# Check your running/pending jobs
squeue -u $USER

# Check a specific job
squeue -j 12345

# Check a specific partition
squeue -p venkvis-h100

# Detailed job info (including completed jobs)
sacct -j 12345 --format=JobID,State,Elapsed,ExitCode,NodeList,MaxRSS

# Check estimated start time for pending job
squeue -j 12345 --start
```

Key job states: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `TIMEOUT`, `OUT_OF_MEMORY`.

## Retrieving Results

After a job completes, results are wherever your script wrote them:

```bash
# Check if job finished
sacct -j 12345 --format=JobID,State,Elapsed,ExitCode --noheader

# Read stdout/stderr
cat slurm-12345.out
cat slurm-12345.err

# Read structured results (if your script wrote JSON)
cat results.json | python3 -m json.tool
```

## Cancelling Jobs

```bash
# Cancel a specific job
scancel 12345

# Cancel all your jobs
scancel -u $USER

# Cancel all pending jobs
scancel -u $USER --state=PENDING
```

## Interactive GPU Sessions

For quick debugging or running `scienceclaw-post` with GPU access:

```bash
# Interactive shell with H100 GPU (up to 8 hours)
srun -N 1 -n 1 -p venkvis-h100 --gres=gpu:h100:1 --mem=32G -t 04:00:00 --pty bash

# Interactive shell with A100 GPU
srun -N 1 -n 1 -p venkvis-a100 --gres=gpu:a100:1 --mem=32G -t 04:00:00 --pty bash

# Quick debug session (30 min max, fastest scheduling)
srun --partition=debug --nodes=1 --gres=gpu:h100:1 --mem=2G --time=30 --pty bash
```

Once on the GPU node, activate the venv and run commands normally:
```bash
source /nfs/turbo/coe-venkvis/changwex/projects/scienceclaw/.venv/bin/activate
scienceclaw-post --agent MatSim --topic "..." --skills uma --dry-run
```

## Safety Rules

- **Never submit from inside a compute node** — check with `echo $SLURM_JOB_ID` (should be empty on login node)
- **Never install packages globally** — always use a virtualenv
- **Write large temporary data to `/scratch/`**, not `/nfs/turbo/` or `/home/`
- **Respect wall time limits** — GPU partitions have 8h max, CPU has 48h
- Jobs inherit environment variables from the submitting shell by default
