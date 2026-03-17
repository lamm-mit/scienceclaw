"""Lazy installer for ScienceClaw skill dependencies."""

import importlib.metadata
import logging
import subprocess
import sys

from .skill_deps import SKILL_DEPS

logger = logging.getLogger(__name__)


def _is_installed(package: str) -> bool:
    """Check if a pip package is installed, normalizing name variants."""
    # Normalize: hyphens and underscores are interchangeable in package names
    normalized = package.lower().replace("-", "_")
    try:
        importlib.metadata.distribution(package)
        return True
    except importlib.metadata.PackageNotFoundError:
        pass
    # Try underscore variant
    if normalized != package.lower():
        try:
            importlib.metadata.distribution(normalized)
            return True
        except importlib.metadata.PackageNotFoundError:
            pass
    # Try hyphen variant
    hyphenated = package.lower().replace("_", "-")
    if hyphenated != package.lower():
        try:
            importlib.metadata.distribution(hyphenated)
            return True
        except importlib.metadata.PackageNotFoundError:
            pass
    return False


def ensure_deps(skill_names: list) -> list:
    """
    Install pip packages needed for the given skill names.
    Returns list of packages that were installed.
    Skips already-installed packages.
    Catches per-package failures and logs warnings without aborting.
    """
    # Collect unique packages across all requested skills
    needed = []
    seen = set()
    for skill in skill_names:
        for pkg in SKILL_DEPS.get(skill, []):
            if pkg not in seen:
                seen.add(pkg)
                needed.append(pkg)

    installed = []
    for pkg in needed:
        if _is_installed(pkg):
            logger.debug("Already installed: %s", pkg)
            continue
        print(f"[deps] Installing {pkg}...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"[deps] Installed {pkg}")
                installed.append(pkg)
            else:
                logger.warning("Failed to install %s: %s", pkg, result.stderr.strip())
        except Exception as exc:
            logger.warning("Error installing %s: %s", pkg, exc)

    return installed


def install_for_profile(profile: dict) -> list:
    """
    Install deps for all tools listed in profile["preferences"]["tools"].
    Returns list of packages installed.
    """
    tools = []
    try:
        tools = profile["preferences"]["tools"]
    except (KeyError, TypeError):
        logger.warning("Could not read profile['preferences']['tools']; no deps installed.")
        return []

    return ensure_deps(tools)
