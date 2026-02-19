#!/usr/bin/env python3
"""
Profile Manager - Multi-agent profile management for ScienceClaw.

Allows switching between multiple agent profiles, each with:
- agent_profile.json (agent details, interests, tools)
- infinite_config.json (API credentials)
- moltbook_config.json (optional platform credentials)
"""

import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class ProfileManager:
    """Manage multiple agent profiles."""

    CONFIG_DIR = Path.home() / ".scienceclaw"
    PROFILES_DIR = CONFIG_DIR / "profiles"
    CURRENT_PROFILE_FILE = CONFIG_DIR / "current_profile.json"

    def __init__(self):
        """Initialize profile manager."""
        self.PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    def get_active_profile_name(self) -> str:
        """Get name of currently active profile."""
        if self.CURRENT_PROFILE_FILE.exists():
            try:
                with open(self.CURRENT_PROFILE_FILE) as f:
                    data = json.load(f)
                    return data.get("active_profile", "CRISPRBio")
            except Exception:
                pass
        return "CRISPRBio"  # Default

    def set_active_profile(self, profile_name: str) -> bool:
        """Switch to a different profile."""
        profile_dir = self.PROFILES_DIR / profile_name
        if not profile_dir.exists():
            print(f"❌ Profile '{profile_name}' not found")
            return False

        if not (profile_dir / "agent_profile.json").exists():
            print(f"❌ Profile '{profile_name}' missing agent_profile.json")
            return False

        # Update current profile pointer
        current = {
            "active_profile": profile_name,
            "last_switched": datetime.now().isoformat()
        }

        with open(self.CURRENT_PROFILE_FILE, "w") as f:
            json.dump(current, f, indent=2)

        print(f"✅ Switched to profile: {profile_name}")
        return True

    def get_agent_profile(self, profile_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load agent profile for a specific profile or active one."""
        if not profile_name:
            profile_name = self.get_active_profile_name()

        profile_file = self.PROFILES_DIR / profile_name / "agent_profile.json"
        if not profile_file.exists():
            return None

        try:
            with open(profile_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading profile {profile_name}: {e}")
            return None

    def get_infinite_config(self, profile_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load Infinite API config for a profile."""
        if not profile_name:
            profile_name = self.get_active_profile_name()

        config_file = self.PROFILES_DIR / profile_name / "infinite_config.json"
        if not config_file.exists():
            return None

        try:
            with open(config_file) as f:
                return json.load(f)
        except Exception:
            return None

    def list_profiles(self) -> List[str]:
        """List all available profiles."""
        if not self.PROFILES_DIR.exists():
            return []

        profiles = [
            d.name for d in self.PROFILES_DIR.iterdir()
            if d.is_dir() and (d / "agent_profile.json").exists()
        ]
        return sorted(profiles)

    def create_profile(self, name: str, agent_profile: Dict[str, Any],
                      infinite_config: Dict[str, Any]) -> bool:
        """Create a new profile."""
        profile_dir = self.PROFILES_DIR / name

        if profile_dir.exists():
            print(f"❌ Profile '{name}' already exists")
            return False

        profile_dir.mkdir(parents=True, exist_ok=True)

        # Save agent profile
        with open(profile_dir / "agent_profile.json", "w") as f:
            json.dump(agent_profile, f, indent=2)

        # Save Infinite config if provided
        if infinite_config:
            with open(profile_dir / "infinite_config.json", "w") as f:
                json.dump(infinite_config, f, indent=2)
            (profile_dir / "infinite_config.json").chmod(0o600)

        print(f"✅ Created profile: {name}")
        return True

    def delete_profile(self, name: str) -> bool:
        """Delete a profile."""
        if name == self.get_active_profile_name():
            print(f"❌ Cannot delete active profile '{name}'")
            return False

        profile_dir = self.PROFILES_DIR / name
        if not profile_dir.exists():
            print(f"❌ Profile '{name}' not found")
            return False

        import shutil
        try:
            shutil.rmtree(profile_dir)
            print(f"✅ Deleted profile: {name}")
            return True
        except Exception as e:
            print(f"❌ Error deleting profile: {e}")
            return False

    def show_profile_info(self, profile_name: Optional[str] = None) -> None:
        """Display info about a profile."""
        if not profile_name:
            profile_name = self.get_active_profile_name()

        profile = self.get_agent_profile(profile_name)
        if not profile:
            print(f"❌ Profile '{profile_name}' not found")
            return

        print(f"\n📋 Profile: {profile_name}")
        print(f"   Agent: {profile.get('name', 'Unknown')}")
        print(f"   Bio: {profile.get('bio', 'N/A')[:80]}")
        print(f"   Expertise: {profile.get('expertise_preset', 'mixed')}")

        interests = profile.get('research', {}).get('interests', [])
        if interests:
            print(f"   Interests: {', '.join(interests)}")

        infinite_cfg = self.get_infinite_config(profile_name)
        if infinite_cfg:
            print(f"   Platform: Infinite (registered)")
        else:
            print(f"   Platform: Not configured for Infinite")

        print()


def main():
    """CLI for profile management."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage ScienceClaw agent profiles")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List profiles
    subparsers.add_parser("list", help="List all profiles")

    # Show current profile
    subparsers.add_parser("current", help="Show active profile")

    # Switch profile
    switch_parser = subparsers.add_parser("switch", help="Switch to a profile")
    switch_parser.add_argument("profile", help="Profile name")

    # Show profile info
    info_parser = subparsers.add_parser("info", help="Show profile details")
    info_parser.add_argument("--profile", help="Profile name (default: active)")

    # Delete profile
    delete_parser = subparsers.add_parser("delete", help="Delete a profile")
    delete_parser.add_argument("profile", help="Profile name")

    args = parser.parse_args()

    manager = ProfileManager()

    if args.command == "list":
        profiles = manager.list_profiles()
        active = manager.get_active_profile_name()
        print("\n📊 Available profiles:")
        for p in profiles:
            marker = "✓" if p == active else " "
            print(f"  [{marker}] {p}")
        if not profiles:
            print("  (no profiles)")
        print()

    elif args.command == "current":
        active = manager.get_active_profile_name()
        print(f"Active profile: {active}\n")
        manager.show_profile_info(active)

    elif args.command == "switch":
        manager.set_active_profile(args.profile)

    elif args.command == "info":
        manager.show_profile_info(args.profile)

    elif args.command == "delete":
        manager.delete_profile(args.profile)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
