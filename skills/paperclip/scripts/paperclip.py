#!/usr/bin/env python3
"""ScienceClaw wrapper for the Paperclip AI CLI."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def which_version(binary: str, *version_args: str) -> dict[str, Any]:
    """Return availability and version information for a local binary."""
    path = shutil.which(binary)
    result: dict[str, Any] = {"binary": binary, "available": bool(path), "path": path}
    if not path:
        return result

    try:
        completed = subprocess.run(
            [path, *version_args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        result["returncode"] = completed.returncode
        result["version"] = (completed.stdout or completed.stderr).strip()
    except Exception as exc:  # pragma: no cover - defensive CLI reporting
        result["error"] = str(exc)
    return result


def build_command(args: argparse.Namespace) -> list[str]:
    if args.action == "check":
        return []

    command = ["npx", "paperclipai"]

    if args.action == "version":
        return command + ["--version"]

    command.append(args.action)

    if args.action == "onboard":
        if args.yes:
            command.append("--yes")
        if args.run_after_onboard:
            command.append("--run")
        if args.bind:
            command.extend(["--bind", args.bind])
    elif args.action == "doctor" and args.repair:
        command.append("--repair")

    return command


def read_tail(path: Path, limit: int = 12000) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    return data[-limit:].decode(errors="replace")


def run_command(
    command: list[str],
    work_dir: Path,
    timeout: int,
    detach: bool = False,
    wait_seconds: int = 5,
) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("npm_config_yes", "true")

    if detach:
        log_dir = Path.home() / ".scienceclaw" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"paperclip-{int(time.time())}.log"
        handle = log_file.open("ab")
        process = subprocess.Popen(
            command,
            cwd=work_dir,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=False,
            start_new_session=True,
        )
        time.sleep(max(0, wait_seconds))
        returncode = process.poll()
        handle.close()
        return {
            "returncode": returncode,
            "pid": process.pid,
            "log_file": str(log_file),
            "stdout": read_tail(log_file),
            "stderr": "",
            "detached": returncode is None,
        }

    try:
        completed = subprocess.run(
            command,
            cwd=work_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return {
            "returncode": 124,
            "stdout": stdout,
            "stderr": stderr + f"\nTimed out after {timeout} seconds.",
        }


def summarize(result: dict[str, Any]) -> str:
    lines = [
        f"Paperclip action: {result['action']}",
        f"Executed: {result['executed']}",
    ]

    if result.get("command"):
        lines.append(f"Command: {' '.join(result['command'])}")

    if result["action"] == "check":
        for check in result["checks"]:
            status = "ok" if check["available"] else "missing"
            version = f" ({check.get('version')})" if check.get("version") else ""
            lines.append(f"{check['binary']}: {status}{version}")

    if result.get("returncode") is not None:
        lines.append(f"Return code: {result['returncode']}")
        if result.get("stdout"):
            lines.append("\nstdout:")
            lines.append(result["stdout"].rstrip())
        if result.get("stderr"):
            lines.append("\nstderr:")
            lines.append(result["stderr"].rstrip())

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Paperclip AI CLI commands from ScienceClaw.")
    parser.add_argument(
        "--action",
        default="check",
        choices=["check", "onboard", "doctor", "run", "version"],
        help="Paperclip operation to perform.",
    )
    parser.add_argument("--execute", action="store_true", help="Run the generated command.")
    parser.add_argument("--detach", action="store_true", help="Run the Paperclip command in the background.")
    parser.add_argument("--foreground", action="store_true", help="Keep long-lived Paperclip commands attached.")
    parser.add_argument("--yes", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--run-after-onboard", action="store_true")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--bind", help="Optional Paperclip bind target, such as tailnet.")
    parser.add_argument("--work-dir", default=".", help="Directory where the CLI should run.")
    parser.add_argument("--timeout", type=int, default=600, help="Command timeout in seconds.")
    parser.add_argument("--wait-seconds", type=int, default=5, help="Seconds to watch a detached command.")
    parser.add_argument("--format", default="summary", choices=["summary", "json"])
    args = parser.parse_args()

    work_dir = Path(args.work_dir).expanduser().resolve()
    checks = [
        which_version("node", "--version"),
        which_version("npm", "--version"),
        which_version("npx", "--version"),
    ]
    command = build_command(args)

    result: dict[str, Any] = {
        "action": args.action,
        "command": command,
        "executed": False,
        "detach": False,
        "work_dir": str(work_dir),
        "checks": checks,
        "requirements": {
            "node": "20+ recommended by Paperclip",
            "npm": "required for npx paperclipai",
            "npx": "required for quickstart onboarding",
        },
    }

    if args.action != "check":
        missing = [check["binary"] for check in checks if not check["available"]]
        if missing:
            result["status"] = "error"
            result["error"] = f"Missing required binaries: {', '.join(missing)}"
        elif args.execute:
            result["executed"] = True
            detach = args.detach or (args.action in {"onboard", "run"} and not args.foreground)
            result["detach"] = detach
            result.update(run_command(command, work_dir, args.timeout, detach, args.wait_seconds))
            result["status"] = "success" if result.get("returncode") in (0, None) else "error"
        else:
            result["status"] = "dry-run"
            result["message"] = "Pass --execute to run the command."
    else:
        result["status"] = "success" if all(check["available"] for check in checks) else "error"

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(summarize(result))

    return 0 if result.get("status") in {"success", "dry-run"} else 1


if __name__ == "__main__":
    sys.exit(main())
