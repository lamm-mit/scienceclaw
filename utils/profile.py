"""
Agent-profile helpers.

The agent profile JSON has had two shapes over time:

  Current (preferred):
      {"name": "...", "preferred_tools": ["pubmed", "uniprot", ...], ...}

  Legacy:
      {"name": "...", "preferences": {"tools": ["pubmed", ...]}, ...}

Code that wants the active toolset MUST go through `profile_preferred_tools()`
so legacy profiles continue to work and don't silently no-op. (Historical bug:
the loop controller read `agent_profile.get("preferred_tools", [])`, got `[]`
for legacy profiles, and skipped every investigation.)
"""

from __future__ import annotations

from typing import Any, Dict, List


def profile_preferred_tools(profile: Dict[str, Any]) -> List[str]:
    """
    Return the agent's tool list, honoring both the current and legacy
    schemas. Always returns a list (possibly empty).
    """
    if not isinstance(profile, dict):
        return []
    tools = profile.get("preferred_tools")
    if isinstance(tools, list) and tools:
        return [str(t) for t in tools if t]
    legacy = profile.get("preferences", {})
    if isinstance(legacy, dict):
        legacy_tools = legacy.get("tools")
        if isinstance(legacy_tools, list) and legacy_tools:
            return [str(t) for t in legacy_tools if t]
    return []


def profile_is_legacy(profile: Dict[str, Any]) -> bool:
    """True iff the profile uses the legacy preferences.tools shape."""
    if not isinstance(profile, dict):
        return False
    if profile.get("preferred_tools"):
        return False
    legacy = profile.get("preferences", {})
    return bool(isinstance(legacy, dict) and legacy.get("tools"))
