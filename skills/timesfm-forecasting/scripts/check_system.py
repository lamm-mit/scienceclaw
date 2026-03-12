#!/usr/bin/env python3
"""
TimesFM System Preflight Checker

Verifies RAM, GPU/VRAM, disk space, Python version, and package availability
before attempting to load the TimesFM model.

Usage:
    python3 check_system.py
    python3 check_system.py --model v2.5
    python3 check_system.py --json          # Machine-readable output
    python3 check_system.py --model v1.0 --json

Exit codes:
    0 - System meets requirements
    1 - System does NOT meet minimum requirements
"""

import argparse
import json
import platform
import shutil
import sys


MODEL_PROFILES = {
    "v1.0": {
        "ram_gb": 1.5,
        "vram_gb": 1.5,
        "disk_gb": 0.8,
        "python_min": (3, 9),
        "huggingface_id": "google/timesfm-1.0-200m-pytorch"
    },
    "v2.0": {
        "ram_gb": 1.5,
        "vram_gb": 2.0,
        "disk_gb": 0.8,
        "python_min": (3, 10),
        "huggingface_id": "google/timesfm-2.0-200m-pytorch"
    },
    "v2.5": {
        "ram_gb": 2.0,
        "vram_gb": 3.0,
        "disk_gb": 2.0,
        "python_min": (3, 10),
        "huggingface_id": "google/timesfm-2.5-500m-pytorch"
    }
}

REQUIRED_PACKAGES = ["timesfm", "torch", "numpy", "pandas", "psutil"]


def check_python(min_version: tuple) -> dict:
    current = sys.version_info[:2]
    ok = current >= min_version
    return {
        "check": "python_version",
        "required": f">= {min_version[0]}.{min_version[1]}",
        "found": f"{current[0]}.{current[1]}",
        "ok": ok
    }


def check_ram(required_gb: float) -> dict:
    try:
        import psutil
        vm = psutil.virtual_memory()
        available_gb = vm.available / (1024 ** 3)
        total_gb = vm.total / (1024 ** 3)
        ok = available_gb >= required_gb
        return {
            "check": "ram_available",
            "required_gb": required_gb,
            "available_gb": round(available_gb, 2),
            "total_gb": round(total_gb, 2),
            "ok": ok
        }
    except ImportError:
        return {
            "check": "ram_available",
            "required_gb": required_gb,
            "available_gb": None,
            "ok": None,
            "warning": "psutil not installed; cannot check RAM"
        }


def check_gpu(required_vram_gb: float) -> dict:
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
            vram_total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            vram_free_approx = vram_total * 0.85  # rough estimate
            return {
                "check": "gpu",
                "device": device,
                "gpu_name": torch.cuda.get_device_name(0),
                "vram_total_gb": round(vram_total, 2),
                "vram_estimated_free_gb": round(vram_free_approx, 2),
                "required_vram_gb": required_vram_gb,
                "ok": vram_free_approx >= required_vram_gb
            }
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return {
                "check": "gpu",
                "device": "mps",
                "gpu_name": "Apple Silicon MPS",
                "vram_total_gb": None,
                "ok": True,
                "note": "MPS available; uses shared system RAM"
            }
        else:
            return {
                "check": "gpu",
                "device": "cpu",
                "gpu_name": None,
                "ok": True,  # CPU is always acceptable fallback
                "note": "No GPU found; will use CPU (slower)"
            }
    except ImportError:
        return {
            "check": "gpu",
            "device": "unknown",
            "ok": None,
            "warning": "torch not installed; cannot check GPU"
        }


def check_disk(required_gb: float, path: str = ".") -> dict:
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024 ** 3)
    total_gb = usage.total / (1024 ** 3)
    ok = free_gb >= required_gb
    return {
        "check": "disk_space",
        "path": path,
        "required_gb": required_gb,
        "free_gb": round(free_gb, 2),
        "total_gb": round(total_gb, 2),
        "ok": ok
    }


def check_packages(packages: list) -> list:
    import importlib
    results = []
    for pkg in packages:
        try:
            mod = importlib.import_module(pkg.replace("-", "_"))
            version = getattr(mod, "__version__", "unknown")
            results.append({
                "check": f"package_{pkg}",
                "package": pkg,
                "version": version,
                "ok": True
            })
        except ImportError:
            results.append({
                "check": f"package_{pkg}",
                "package": pkg,
                "version": None,
                "ok": False,
                "fix": f"pip install {pkg}"
            })
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Preflight system check for TimesFM model loading"
    )
    parser.add_argument("--model", default="v2.5",
                        choices=list(MODEL_PROFILES.keys()),
                        help="TimesFM model version to check for (default: v2.5)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON for machine-readable parsing")

    args = parser.parse_args()
    profile = MODEL_PROFILES[args.model]

    results = {
        "model": args.model,
        "huggingface_id": profile["huggingface_id"],
        "platform": platform.platform(),
        "checks": []
    }

    # Run checks
    results["checks"].append(check_python(profile["python_min"]))
    results["checks"].append(check_ram(profile["ram_gb"]))
    results["checks"].append(check_gpu(profile["vram_gb"]))
    results["checks"].append(check_disk(profile["disk_gb"]))
    results["checks"].extend(check_packages(REQUIRED_PACKAGES))

    # Determine overall pass/fail
    # None means uncertain (missing dep to check); treat as warning not failure
    critical_failures = [c for c in results["checks"]
                         if c.get("ok") is False
                         and c["check"] not in ["gpu"]]  # GPU failure = CPU fallback
    results["passed"] = len(critical_failures) == 0
    results["critical_failures"] = [c["check"] for c in critical_failures]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\n=== TimesFM {args.model} System Check ===\n")
        for check in results["checks"]:
            status = "✓" if check.get("ok") else ("?" if check.get("ok") is None else "✗")
            name = check["check"].replace("_", " ").title()
            if check.get("ok") is False:
                detail = check.get("fix") or check.get("warning") or "Does not meet requirement"
                print(f"  {status} {name}: FAIL — {detail}")
            elif check.get("note"):
                print(f"  {status} {name}: {check.get('found') or ''} ({check['note']})")
            else:
                found = check.get("found") or check.get("version") or check.get("available_gb") or check.get("free_gb")
                print(f"  {status} {name}: {found}")

        print()
        if results["passed"]:
            print("✓ System is ready to run TimesFM")
            print(f"  Model: {profile['huggingface_id']}")
        else:
            print("✗ System does NOT meet requirements")
            print(f"  Failed: {', '.join(results['critical_failures'])}")

    sys.exit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
