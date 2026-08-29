"""Smoke tests for skill CLI scripts.

Every skill script must at least start up and reach its own argument
parsing without raising a NameError / SyntaxError at import or in the
default output path. This guards against undefined names in the
human-readable (``--format summary``) branch, which is the default and
is exercised whenever the executor calls a skill without an explicit
``format`` parameter.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"


def discover_skill_scripts():
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(
        p for p in SKILLS_DIR.glob("*/scripts/*.py")
        if not p.name.startswith("_")
    )


SCRIPTS = discover_skill_scripts()


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: f"{p.parents[1].name}/{p.name}")
def test_help_does_not_raise_name_error(script):
    """``--help`` must not blow up on an undefined name."""
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True, text=True, timeout=60,
    )
    combined = result.stdout + result.stderr
    assert "'skill_name' is not defined" not in combined, combined[-500:]


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: f"{p.parents[1].name}/{p.name}")
def test_summary_path_has_no_undefined_names(script):
    """The default (summary) output path must not reference undefined names.

    Scripts that need network access, credentials or optional third-party
    packages are allowed to fail for those reasons; only NameError is fatal.
    """
    source = script.read_text(encoding="utf-8", errors="replace")
    if "skill_name" not in source and "SKILL_NAME" not in source:
        pytest.skip("script does not emit a skill name banner")
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=60,
    )
    combined = result.stdout + result.stderr
    assert "'skill_name' is not defined" not in combined, combined[-500:]
