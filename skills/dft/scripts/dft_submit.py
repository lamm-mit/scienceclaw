#!/usr/bin/env python3
"""Submit a DFT calculation to Artemis via SLURM.

Delegates to the DREAMS framework for input generation and job orchestration.
Structure can come from a local CIF/POSCAR file or be fetched from Materials
Project by --mp-id.

Safety:
  - Never submits from inside a compute node (checks SLURM_JOB_ID).
  - --dry-run prints the SLURM script without submitting.
  - Refuses to auto-generate QE input without a valid structure.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# DREAMS integration stub — replace with real import once DREAMS is wired in.
# from dreams.workflows import build_qe_input, generate_slurm_script
# ---------------------------------------------------------------------------

SCIENCECLAW_DIR = Path.home() / ".scienceclaw"
DFT_CONFIG_PATH = SCIENCECLAW_DIR / "dft_config.json"
DEFAULT_PARTITION = "venkvis-cpu"
VALID_CALC_TYPES = ("relax", "scf", "vc-relax", "bands")


def load_dft_config() -> dict:
    """Load DFT/DREAMS configuration from ~/.scienceclaw/dft_config.json."""
    if DFT_CONFIG_PATH.exists():
        try:
            with open(DFT_CONFIG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def check_not_on_compute_node():
    """Abort if running inside a SLURM compute job."""
    if os.environ.get("SLURM_JOB_ID"):
        print("Error: refusing to submit from inside a compute node "
              "(SLURM_JOB_ID is set). Run from a login node.", file=sys.stderr)
        sys.exit(1)


def resolve_structure(args, config: dict) -> str:
    """Return path to structure file, fetching from MP if needed."""
    if args.structure:
        path = Path(args.structure)
        if not path.exists():
            print(f"Error: structure file not found: {path}", file=sys.stderr)
            sys.exit(1)
        return str(path)

    if args.mp_id:
        # TODO: fetch structure CIF from Materials Project using mp-api or the
        # materials skill, and write to a temp file.  For now, return a
        # placeholder so the rest of the pipeline can be developed.
        print(f"TODO: fetch structure for {args.mp_id} from Materials Project",
              file=sys.stderr)
        return f"<mp:{args.mp_id}>"

    print("Error: provide --structure or --mp-id", file=sys.stderr)
    sys.exit(1)


def build_slurm_script(structure_path: str, calc_type: str,
                        config: dict, partition: str) -> str:
    """Generate a SLURM batch script for a QE calculation.

    TODO: Replace this stub with DREAMS workflow builder once integrated.
    The real implementation should call dreams.workflows.build_qe_input() to
    produce the pw.x input file and wrap it in the appropriate SLURM directives.
    """
    job_name = f"sc-dft-{calc_type}-{Path(structure_path).stem}"
    dreams_cmd = config.get("dreams_command", "dreams-run")
    qe_module = config.get("qe_module", "quantum-espresso/7.2")

    # Artemis CPU nodes: AMD EPYC 9654 (96 cores), 368 GB RAM
    # Artemis A100 nodes: AMD EPYC 7513 (32 cores), 512 GB RAM, 4× A100
    # GPU partitions have 8h walltime limit; CPU partitions have 48h
    default_ntasks = 96 if "cpu" in partition or "largemem" in partition else 32
    is_gpu = "a100" in partition or "h100" in partition
    default_walltime = "08:00:00" if is_gpu else "48:00:00"

    gpu_line = ""
    if is_gpu:
        gpu_count = config.get("gpus", 1)
        gpu_line = f"#SBATCH --gres=gpu:{gpu_count}"

    script = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition={partition}
#SBATCH --nodes=1
#SBATCH --ntasks-per-node={config.get('ntasks', default_ntasks)}
#SBATCH --time={config.get('walltime', default_walltime)}
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err
{gpu_line}

module load {qe_module}

# Use /scratch for large temporary files (auto-purged after 60 days)
export TMPDIR=/scratch/venkvis_root/venkvis/$USER/dft_$SLURM_JOB_ID
mkdir -p $TMPDIR

# --- DREAMS orchestration (TODO: wire real DREAMS call) ---
# {dreams_cmd} --structure {structure_path} --calc-type {calc_type}

echo "PLACEHOLDER: replace with DREAMS workflow execution"
echo "Structure: {structure_path}"
echo "Calc type: {calc_type}"
"""
    return script


def submit_job(script_content: str) -> str:
    """Submit a SLURM script via sbatch and return the job ID."""
    result = subprocess.run(
        ["sbatch"],
        input=script_content,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error: sbatch failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    # sbatch output: "Submitted batch job 12345"
    for word in result.stdout.strip().split():
        if word.isdigit():
            return word
    print(f"Error: could not parse job ID from sbatch output: {result.stdout}",
          file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Submit a DFT calculation to Artemis/SLURM via DREAMS")
    parser.add_argument("--structure", "-s",
                        help="Path to CIF or POSCAR structure file")
    parser.add_argument("--mp-id",
                        help="Materials Project ID (e.g. mp-149); "
                             "fetches structure automatically")
    parser.add_argument("--calc-type", "-c", default="relax",
                        choices=VALID_CALC_TYPES,
                        help="Calculation type (default: relax)")
    parser.add_argument("--queue", "--partition", dest="partition",
                        default=None,
                        help="SLURM partition (default: from config or 'standard')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print SLURM script without submitting")
    parser.add_argument("--format", default="summary",
                        choices=["summary", "json"])
    args = parser.parse_args()

    config = load_dft_config()
    partition = args.partition or config.get("partition", DEFAULT_PARTITION)

    if not args.dry_run:
        check_not_on_compute_node()

    structure_path = resolve_structure(args, config)
    script = build_slurm_script(structure_path, args.calc_type, config, partition)

    if args.dry_run:
        if args.format == "json":
            print(json.dumps({
                "dry_run": True,
                "slurm_script": script,
                "structure": structure_path,
                "calc_type": args.calc_type,
                "partition": partition,
            }, indent=2))
        else:
            print("=== DRY RUN — SLURM script (not submitted) ===")
            print(script)
        return

    job_id = submit_job(script)
    result = {
        "job_id": job_id,
        "calc_type": args.calc_type,
        "structure": structure_path,
        "status": "PENDING",
        "partition": partition,
        "submit_time": datetime.now(timezone.utc).isoformat(),
    }

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"  job_id:    {result['job_id']}")
        print(f"  calc_type: {result['calc_type']}")
        print(f"  structure: {result['structure']}")
        print(f"  status:    {result['status']}")
        print(f"  partition: {result['partition']}")
        print(f"  submitted: {result['submit_time']}")


if __name__ == "__main__":
    main()
