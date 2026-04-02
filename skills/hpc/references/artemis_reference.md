# Artemis HPC Reference

## Cluster Info
- URL: https://eeg.engin.umich.edu/ArtemisUsers/
- Scheduler: SLURM
- Available software: Quantum Espresso, VASP (check `module avail`)

## Node Types

| Node Type | Count | CPU | GPU | RAM | Local NVMe |
|-----------|-------|-----|-----|-----|------------|
| H100 GPU | 3 | AMD EPYC 9654 (96c/192t, Zen4) | 4× NVIDIA H100 SXM 80GB | 768 GB | 1.9 TB |
| A100 GPU | 2 | AMD EPYC 7513 (32c/64t, Zen3) | 4× NVIDIA A100 SXM 80GB | 512 GB | 1.6 TB |
| Large Memory | 3 | AMD EPYC 9654 (96c/192t, Zen4) | None | 768 GB | 1.9 TB |
| CPU | 25 | AMD EPYC 9654 (96c/192t, Zen4) | None | 368 GB | 1.9 TB |

## GPU Specs

| GPU | VRAM | Memory BW | FP64 | FP32 Tensor |
|-----|------|-----------|------|-------------|
| H100 SXM | 80 GB | 3.34 TB/s | 34 TFLOPS | 989 TFLOPS |
| A100 SXM | 80 GB | 2.039 TB/s | 9.7 TFLOPS | 156 TFLOPS |

## Partitions

| Partition | Wall Time Limit | Notes |
|-----------|-----------------|-------|
| `venkvis-cpu` | 48 hours | 25 CPU nodes (96 cores each) |
| `venkvis-largemem` | 48 hours | 3 large-memory nodes (768 GB RAM) |
| `venkvis-a100` | 8 hours | 2 nodes, 4× A100 each |
| `venkvis-h100` | 8 hours | 3 nodes, 4× H100 each |
| `debug` | 30 minutes | Priority 100, max 1 job, 4 nodes |

## Storage (4-Tier)

| Storage | Path | Capacity | Fair Share | Notes |
|---------|------|----------|------------|-------|
| Node Local | `/tmp` | 1.9 TB | — | Fast NVMe, ephemeral per job |
| Turbo | `/nfs/turbo/coe-venkvis/` | 10 TB | 500 GB | Persistent, backed up; code and venvs live here |
| Scratch | `/scratch/venkvis_root/venkvis/` | 10 TB | 500 GB | Active datasets; **60-day auto-purge** |
| DataDen | Via Globus | 100 TB | 5 TB | Tape archival for large datasets |
| Home | `/home/<user>` | 80 GB | — | User home directory |

## Common SLURM Commands
```bash
sbatch job.sh                        # submit
squeue -u $USER                      # check your queue
sacct -j <jobid>                     # completed job details
scancel <jobid>                      # cancel
sinfo -p venkvis-cpu                 # partition info
```

## Job Submission Rules
- Submit only from login nodes (never from compute nodes)
- Respect walltime limits: 48h for CPU/largemem, 8h for GPU, 30m for debug
- Use `module load` for software dependencies in batch scripts
- Write large scratch data to `/scratch/`, not `/nfs/turbo/` or `/home/`
- Default partition for DFT jobs is configurable in `~/.scienceclaw/dft_config.json`
