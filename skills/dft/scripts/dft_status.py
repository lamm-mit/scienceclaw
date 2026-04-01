#!/usr/bin/env python3
"""Poll the status of a SLURM DFT job on Artemis.

Wraps `squeue` / `sacct` to return structured JSON about job state.
"""

import argparse
import json
import subprocess
import sys


def query_squeue(job_id: str) -> dict | None:
    """Check squeue for a running/pending job. Returns None if not found."""
    result = subprocess.run(
        ["squeue", "--job", job_id, "--noheader",
         "--format=%i|%T|%M|%N|%P|%j"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    parts = result.stdout.strip().split("|")
    if len(parts) < 6:
        return None
    return {
        "job_id": parts[0].strip(),
        "status": parts[1].strip(),
        "elapsed": parts[2].strip(),
        "node": parts[3].strip() or None,
        "partition": parts[4].strip(),
        "job_name": parts[5].strip(),
    }


def query_sacct(job_id: str) -> dict | None:
    """Check sacct for a completed/failed job."""
    result = subprocess.run(
        ["sacct", "-j", job_id, "--noheader", "--parsable2",
         "--format=JobID,State,Elapsed,NodeList,Partition,JobName,ExitCode"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    # sacct may return multiple lines (job + job steps); take the first (main job)
    for line in result.stdout.strip().splitlines():
        parts = line.split("|")
        if len(parts) < 7:
            continue
        jid = parts[0].strip()
        # Skip sub-steps like "12345.batch"
        if "." in jid:
            continue
        return {
            "job_id": jid,
            "status": parts[1].strip(),
            "elapsed": parts[2].strip(),
            "node": parts[3].strip() or None,
            "partition": parts[4].strip(),
            "job_name": parts[5].strip(),
            "exit_code": parts[6].strip(),
        }
    return None


def get_job_status(job_id: str) -> dict:
    """Get job status from squeue (active) or sacct (completed)."""
    info = query_squeue(job_id)
    if info:
        return info

    info = query_sacct(job_id)
    if info:
        return info

    return {"job_id": job_id, "status": "UNKNOWN",
            "error": "Job not found in squeue or sacct"}


def main():
    parser = argparse.ArgumentParser(
        description="Poll status of a SLURM DFT job")
    parser.add_argument("--job-id", "-j", required=True,
                        help="SLURM job ID")
    parser.add_argument("--format", default="summary",
                        choices=["summary", "json"])
    args = parser.parse_args()

    result = get_job_status(args.job_id)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        for k, v in result.items():
            if v is not None:
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
