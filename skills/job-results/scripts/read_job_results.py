#!/usr/bin/env python3
"""Read and parse results from completed SLURM jobs.

Checks job status via sacct, reads JSON output from slurm-*.out files,
and can filter candidates by stability criteria.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def check_job_status(job_id: str) -> dict:
    """Query SLURM for job status."""
    try:
        result = subprocess.run(
            ["sacct", "-j", job_id,
             "--format=JobID,State,Elapsed,ExitCode,NodeList",
             "--noheader", "--parsable2"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return {"job_id": job_id, "status": "UNKNOWN"}

        for line in result.stdout.strip().splitlines():
            parts = line.split("|")
            if len(parts) >= 5 and parts[0] == job_id:
                return {
                    "job_id": job_id,
                    "status": parts[1],
                    "elapsed": parts[2],
                    "exit_code": parts[3],
                    "node": parts[4],
                }
        return {"job_id": job_id, "status": "NOT_FOUND"}
    except Exception as e:
        return {"job_id": job_id, "status": "UNKNOWN", "error": str(e)}


def find_latest_results(output_dir: Path) -> dict | None:
    """Find and parse the latest slurm-*.out file containing JSON."""
    out_files = sorted(output_dir.glob("slurm-*.out"), reverse=True)
    for out_file in out_files:
        content = out_file.read_text().strip()
        # Try to parse as JSON (may have non-JSON prefix/suffix)
        # Find the outermost { ... }
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(content[start:end + 1])
                # Skip error results — keep looking for successful ones
                if data.get("status") in ("ERROR", "error", "FAILED"):
                    continue
                data["_source_file"] = str(out_file)
                return data
            except json.JSONDecodeError:
                continue
    return None


def find_results_file(output_dir: Path) -> dict | None:
    """Find screening_results.json or similar in the output dir."""
    for name in ["screening_results.json", "results.json", "phonon_results.json"]:
        path = output_dir / name
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
    return None


def extract_stable_candidates(data: dict, filter_stable: bool,
                               filter_converged: bool) -> list:
    """Extract candidate entries from screening results, optionally filtering."""
    candidates = []

    # Handle different result formats
    if "ranking" in data:
        for entry in data["ranking"]:
            cand = {**entry}
            # Find corresponding CIF paths
            if "candidates" in data:
                for c in data["candidates"]:
                    if c.get("label") == entry.get("label"):
                        # Get CIF path from pressure data
                        for p_key, p_data in c.get("pressures", {}).items():
                            if isinstance(p_data, dict) and "cif_path" in p_data:
                                cand.setdefault("relaxed_cifs", {})[p_key] = p_data["cif_path"]
            candidates.append(cand)

    elif "results" in data and isinstance(data["results"], list):
        # Phonon or flat results format
        for entry in data["results"]:
            candidates.append(entry)

    elif "candidates" in data:
        for c in data["candidates"]:
            cand = {"label": c.get("label"), "formula": c.get("formula")}
            for p_key, p_data in c.get("pressures", {}).items():
                if isinstance(p_data, dict):
                    cand[f"ef_{p_key}GPa"] = p_data.get("formation_energy_eV_per_atom")
                    cand[f"converged_{p_key}GPa"] = p_data.get("converged")
                    if "cif_path" in p_data:
                        cand.setdefault("relaxed_cifs", {})[p_key] = p_data["cif_path"]
                    if "e_above_hull_eV" in p_data:
                        cand["e_above_hull_eV"] = p_data["e_above_hull_eV"]
            candidates.append(cand)

    if filter_stable:
        filtered = []
        for c in candidates:
            ef = c.get("formation_energy_eV_per_atom")
            ehull = c.get("e_above_hull_eV_0GPa", c.get("e_above_hull_eV"))
            # Keep if formation energy < 0 or on/near hull
            is_stable = (ef is not None and ef < 0) or \
                        (ehull is not None and ehull < 0.1)
            # For phonon results
            if "dynamically_stable" in c:
                is_stable = c["dynamically_stable"]
            if is_stable:
                filtered.append(c)
        candidates = filtered

    if filter_converged:
        candidates = [c for c in candidates if c.get("converged", True)]

    return candidates


def collect_cif_paths(candidates: list, output_dir: Path) -> list:
    """Collect all relaxed CIF file paths for the given candidates."""
    cif_paths = []
    for c in candidates:
        # From explicit paths in results
        if "relaxed_cifs" in c:
            cif_paths.extend(c["relaxed_cifs"].values())
        elif "cif_path" in c:
            cif_paths.append(c["cif_path"])

    # Also check output_dir for CIFs matching candidate labels
    if output_dir.exists():
        for c in candidates:
            label = c.get("label", "")
            for cif in output_dir.glob(f"{label}*.cif"):
                if str(cif) not in cif_paths:
                    cif_paths.append(str(cif))

    return sorted(set(cif_paths))


def main():
    parser = argparse.ArgumentParser(
        description="Read and parse results from completed SLURM jobs")
    parser.add_argument("--job-id", help="SLURM job ID to check")
    parser.add_argument("--output-dir", help="Directory with SLURM output files")
    parser.add_argument("--results-file", help="Direct path to JSON results file")
    parser.add_argument("--filter-stable", action="store_true",
                        help="Only return stable candidates")
    parser.add_argument("--filter-converged", action="store_true",
                        help="Only return converged calculations")
    parser.add_argument("--list-cifs", action="store_true",
                        help="Include relaxed CIF file paths")
    parser.add_argument("--format", default="json",
                        choices=["summary", "json"])
    args = parser.parse_args()

    if not args.job_id and not args.output_dir and not args.results_file:
        print("Error: provide --job-id, --output-dir, or --results-file",
              file=sys.stderr)
        sys.exit(1)

    output = {}

    # Check job status
    if args.job_id:
        output["job_status"] = check_job_status(args.job_id)

    # Read results
    data = None
    output_dir = Path(args.output_dir) if args.output_dir else Path(".")

    if args.results_file:
        path = Path(args.results_file)
        if path.exists():
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError:
                output["error"] = f"Could not parse {path}"

    if data is None and args.output_dir:
        # Try dedicated results files first
        data = find_results_file(output_dir)
        # Fall back to SLURM output
        if data is None:
            data = find_latest_results(output_dir)

    if data is None and args.job_id and args.output_dir:
        # Try specific slurm-JOBID.out
        slurm_out = output_dir / f"slurm-{args.job_id}.out"
        if slurm_out.exists():
            content = slurm_out.read_text()
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                try:
                    data = json.loads(content[start:end + 1])
                except json.JSONDecodeError:
                    pass

    if data is None:
        output["status"] = "NO_RESULTS"
        output["error"] = "No results found. Job may still be running."
        print(json.dumps(output, indent=2))
        return

    output["status"] = data.get("status", "COMPLETED")

    # Extract candidates
    candidates = extract_stable_candidates(
        data, args.filter_stable, args.filter_converged)
    output["n_candidates"] = len(candidates)
    output["candidates"] = candidates

    if args.list_cifs:
        output["cif_paths"] = collect_cif_paths(candidates, output_dir)

    if args.format == "json":
        print(json.dumps(output, indent=2))
    else:
        print(f"Status: {output['status']}")
        if "job_status" in output:
            js = output["job_status"]
            print(f"Job {js.get('job_id')}: {js.get('status')} ({js.get('elapsed', 'N/A')})")
        print(f"Candidates: {len(candidates)}")
        for c in candidates:
            label = c.get("label", "?")
            ef = c.get("formation_energy_eV_per_atom", "N/A")
            ehull = c.get("e_above_hull_eV_0GPa", c.get("e_above_hull_eV", "N/A"))
            print(f"  {label:<30s} Ef={ef}  Ehull={ehull}")


if __name__ == "__main__":
    main()
