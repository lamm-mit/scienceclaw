#!/usr/bin/env python3
"""Retrieve and parse results from a completed DFT job on Artemis.

Looks for Quantum Espresso output in the SLURM working directory,
extracts total energy, forces convergence, relaxed structure, and
band gap (if applicable).

TODO: Wire DREAMS result parser once integrated.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCIENCECLAW_DIR = Path.home() / ".scienceclaw"


def find_job_workdir(job_id: str) -> Path | None:
    """Locate the working directory of a completed SLURM job via sacct."""
    result = subprocess.run(
        ["sacct", "-j", job_id, "--noheader", "--parsable2",
         "--format=JobID,WorkDir,State"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.strip().splitlines():
        parts = line.split("|")
        if len(parts) >= 3 and "." not in parts[0]:
            workdir = Path(parts[1].strip())
            if workdir.exists():
                return workdir
    return None


def parse_qe_output(output_path: Path) -> dict:
    """Parse a Quantum Espresso pw.x output file for key results.

    TODO: This is a minimal parser. Replace with DREAMS result parser or
    a more robust QE output parser (e.g., from ASE or pymatgen) for
    production use.
    """
    results: dict = {
        "total_energy_eV": None,
        "forces_converged": None,
        "band_gap_eV": None,
        "n_scf_steps": None,
        "wall_time": None,
    }

    try:
        text = output_path.read_text()
    except Exception as e:
        return {"error": f"Cannot read output file: {e}"}

    # Total energy (Ry → eV: 1 Ry = 13.6057 eV)
    energy_matches = re.findall(r"!\s+total energy\s+=\s+([-\d.]+)\s+Ry", text)
    if energy_matches:
        ry = float(energy_matches[-1])
        results["total_energy_eV"] = round(ry * 13.6057, 6)

    # Forces convergence
    if "Forces acting on atoms" in text:
        results["forces_converged"] = "convergence achieved" in text.lower()

    # SCF steps
    scf_steps = re.findall(r"iteration #\s*(\d+)", text)
    if scf_steps:
        results["n_scf_steps"] = int(scf_steps[-1])

    # Wall time
    wall_match = re.search(r"PWSCF\s+:\s+(.+?)\s+CPU", text)
    if wall_match:
        results["wall_time"] = wall_match.group(1).strip()

    return results


def find_qe_output(workdir: Path) -> Path | None:
    """Find the QE output file in the working directory."""
    # Common patterns: *.out, *.pw.out, pw.out, relax.out, scf.out
    for pattern in ["*.pw.out", "pw.out", "relax.out", "scf.out", "*.out"]:
        matches = sorted(workdir.glob(pattern))
        if matches:
            return matches[-1]  # most recent
    return None


def find_relaxed_structure(workdir: Path) -> str | None:
    """Find a relaxed structure file (CIF or POSCAR) in the working directory.

    TODO: Replace with DREAMS output parser that extracts the final
    optimized structure from QE output.
    """
    for pattern in ["*.cif", "CONTCAR", "*.poscar", "relaxed.*"]:
        matches = list(workdir.glob(pattern))
        if matches:
            try:
                return matches[0].read_text()
            except Exception:
                return str(matches[0])
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve and parse results from a completed DFT job")
    parser.add_argument("--job-id", "-j", required=True,
                        help="SLURM job ID")
    parser.add_argument("--workdir", "-w", default=None,
                        help="Override working directory (default: auto-detect via sacct)")
    parser.add_argument("--format", default="summary",
                        choices=["summary", "json"])
    args = parser.parse_args()

    if args.workdir:
        workdir = Path(args.workdir)
    else:
        workdir = find_job_workdir(args.job_id)

    if not workdir or not workdir.exists():
        err = {"job_id": args.job_id, "status": "ERROR",
               "error": "Could not locate job working directory"}
        if args.format == "json":
            print(json.dumps(err, indent=2))
        else:
            print(f"Error: {err['error']}", file=sys.stderr)
        sys.exit(1)

    qe_output = find_qe_output(workdir)
    if not qe_output:
        err = {"job_id": args.job_id, "status": "ERROR",
               "error": f"No QE output file found in {workdir}"}
        if args.format == "json":
            print(json.dumps(err, indent=2))
        else:
            print(f"Error: {err['error']}", file=sys.stderr)
        sys.exit(1)

    parsed = parse_qe_output(qe_output)
    relaxed_cif = find_relaxed_structure(workdir)

    result = {
        "job_id": args.job_id,
        "status": "COMPLETED",
        "workdir": str(workdir),
        "output_file": str(qe_output),
        **parsed,
    }
    if relaxed_cif:
        result["relaxed_structure_cif"] = relaxed_cif

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        for k, v in result.items():
            if v is not None and k != "relaxed_structure_cif":
                print(f"  {k}: {v}")
        if relaxed_cif:
            print(f"  relaxed_structure: (available, {len(relaxed_cif)} chars)")


if __name__ == "__main__":
    main()
