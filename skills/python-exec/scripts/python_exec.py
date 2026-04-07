"""
python_exec — execute arbitrary Python code and return stdout.
"""

import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Execute Python code and return stdout.")
    parser.add_argument("--code", required=True, help="Python code to execute. Use print() to produce output.")
    parser.add_argument("--timeout", type=int, default=60, help="Execution timeout in seconds (default 60).")
    args = parser.parse_args()

    code = args.code.strip()
    if not code:
        print('{"error": "empty code"}')
        return

    try:
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=args.timeout,
        )
        out = r.stdout
        if r.returncode != 0:
            out += f"\n[stderr]: {r.stderr[:1000]}"
        print((out or "[no output]")[:8000], end="")
    except subprocess.TimeoutExpired:
        print(f'{{"error": "timeout after {args.timeout}s"}}')
    except Exception as e:
        print(f'{{"error": "{e}"}}')


if __name__ == "__main__":
    main()
