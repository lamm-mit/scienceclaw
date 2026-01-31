#!/usr/bin/env python3
"""
ScienceClaw Agent Setup

Creates and registers a new science agent with a unique profile.
The agent will join the m/scienceclaw community on Moltbook.

Usage:
    python3 setup.py                    # Interactive setup
    python3 setup.py --quick            # Quick setup with defaults
    python3 setup.py --quick --name "MyBot"  # Quick setup with custom name
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "skills" / "sciencemolt" / "scripts"))

try:
    from moltbook_client import MoltbookClient, CONFIG_DIR, CONFIG_FILE
except ImportError:
    print("Error: Could not import moltbook_client")
    print("Make sure you're running from the scienceclaw directory")
    sys.exit(1)

# Profile storage
PROFILE_FILE = CONFIG_DIR / "agent_profile.json"

# Default submolt for science agents
SCIENCE_SUBMOLT = "scienceclaw"

# Default values for quick setup
QUICK_DEFAULTS = {
    "interests": ["biology", "bioinformatics", "protein structure", "molecular biology"],
    "organisms": ["human", "E. coli", "yeast"],
    "proteins": ["p53", "insulin", "hemoglobin"],
    "curiosity_styles": ["explorer", "deep-diver", "connector"],
    "communication_styles": ["enthusiastic", "formal", "casual"],
    "tools": ["blast", "pubmed", "uniprot", "sequence"],
    "exploration_modes": ["random", "systematic", "question-driven"],
    "name_prefixes": ["Bio", "Science", "Protein", "Gene", "Molecule", "Data", "Research"],
    "name_suffixes": ["Bot", "Agent", "Explorer", "Hunter", "Seeker", "Scout", "Claw"],
}


def generate_random_name() -> str:
    """Generate a random agent name."""
    prefix = random.choice(QUICK_DEFAULTS["name_prefixes"])
    suffix = random.choice(QUICK_DEFAULTS["name_suffixes"])
    number = random.randint(1, 999)
    return f"{prefix}{suffix}-{number}"


def create_quick_profile(name: str = None) -> dict:
    """Create a profile with randomized defaults for quick setup."""
    if not name:
        name = generate_random_name()

    # Randomize some variety
    interests = random.sample(QUICK_DEFAULTS["interests"], k=random.randint(2, 4))
    organisms = random.sample(QUICK_DEFAULTS["organisms"], k=random.randint(1, 2))
    proteins = random.sample(QUICK_DEFAULTS["proteins"], k=random.randint(1, 2))
    tools = random.sample(QUICK_DEFAULTS["tools"], k=random.randint(2, 4))

    profile = {
        "name": name,
        "bio": f"An autonomous science agent exploring {interests[0]} and {interests[1] if len(interests) > 1 else 'biology'}",
        "research": {
            "interests": interests,
            "organisms": organisms,
            "proteins": proteins,
        },
        "personality": {
            "curiosity_style": random.choice(QUICK_DEFAULTS["curiosity_styles"]),
            "communication_style": random.choice(QUICK_DEFAULTS["communication_styles"]),
        },
        "preferences": {
            "tools": tools,
            "exploration_mode": random.choice(QUICK_DEFAULTS["exploration_modes"]),
        },
        "submolt": SCIENCE_SUBMOLT,
    }

    return profile


def get_input(prompt: str, default: str = None, required: bool = True) -> str:
    """Get input from user with optional default."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "

    while True:
        value = input(prompt).strip()
        if not value and default:
            return default
        if value or not required:
            return value
        print("This field is required.")


def get_multiline_input(prompt: str) -> str:
    """Get multiline input from user."""
    print(f"{prompt} (enter a blank line to finish):")
    lines = []
    while True:
        line = input()
        if not line:
            break
        lines.append(line)
    return "\n".join(lines)


def get_list_input(prompt: str, examples: str = None) -> list:
    """Get comma-separated list input."""
    if examples:
        prompt = f"{prompt} (e.g., {examples})"
    value = input(f"{prompt}: ").strip()
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def create_agent_profile() -> dict:
    """Interactive profile creation."""
    print("\n" + "=" * 60)
    print("  ScienceClaw Agent Setup")
    print("=" * 60)
    print("\nLet's create your science agent's unique profile.\n")

    # Basic info
    name = get_input("Agent name", "ScienceClaw Agent")

    print("\nDescribe your agent's personality and approach:")
    bio = get_input(
        "Short bio (1-2 sentences)",
        "An autonomous science agent exploring biology and bioinformatics"
    )

    # Research focus
    print("\n--- Research Focus ---")
    print("What should your agent be curious about?\n")

    research_interests = get_list_input(
        "Research interests (comma-separated)",
        "protein structure, gene regulation, drug discovery"
    )
    if not research_interests:
        research_interests = ["biology", "bioinformatics", "molecular biology"]

    favorite_organisms = get_list_input(
        "Favorite organisms (comma-separated, optional)",
        "human, E. coli, yeast, Arabidopsis"
    )

    favorite_proteins = get_list_input(
        "Favorite proteins/genes (comma-separated, optional)",
        "p53, CRISPR-Cas9, insulin, hemoglobin"
    )

    # Personality
    print("\n--- Personality ---")

    curiosity_style = get_input(
        "Curiosity style (explorer/deep-diver/connector/skeptic)",
        "explorer"
    )

    communication_style = get_input(
        "Communication style (formal/casual/enthusiastic/concise)",
        "enthusiastic"
    )

    # Science preferences
    print("\n--- Science Preferences ---")

    preferred_tools = get_list_input(
        "Preferred tools (comma-separated)",
        "blast, pubmed, uniprot, sequence"
    )
    if not preferred_tools:
        preferred_tools = ["blast", "pubmed", "uniprot", "sequence"]

    exploration_mode = get_input(
        "Exploration mode (random/trending/systematic/question-driven)",
        "random"
    )

    # Build profile
    profile = {
        "name": name,
        "bio": bio,
        "research": {
            "interests": research_interests,
            "organisms": favorite_organisms,
            "proteins": favorite_proteins,
        },
        "personality": {
            "curiosity_style": curiosity_style,
            "communication_style": communication_style,
        },
        "preferences": {
            "tools": preferred_tools,
            "exploration_mode": exploration_mode,
        },
        "submolt": SCIENCE_SUBMOLT,
    }

    return profile


def display_profile(profile: dict):
    """Display the created profile."""
    print("\n" + "=" * 60)
    print("  Your Agent Profile")
    print("=" * 60)
    print(f"\nName: {profile['name']}")
    print(f"Bio: {profile['bio']}")
    print(f"\nResearch Interests: {', '.join(profile['research']['interests'])}")
    if profile['research']['organisms']:
        print(f"Favorite Organisms: {', '.join(profile['research']['organisms'])}")
    if profile['research']['proteins']:
        print(f"Favorite Proteins: {', '.join(profile['research']['proteins'])}")
    print(f"\nCuriosity Style: {profile['personality']['curiosity_style']}")
    print(f"Communication Style: {profile['personality']['communication_style']}")
    print(f"\nPreferred Tools: {', '.join(profile['preferences']['tools'])}")
    print(f"Exploration Mode: {profile['preferences']['exploration_mode']}")
    print(f"\nCommunity: m/{profile['submolt']}")


def save_profile(profile: dict):
    """Save profile to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=2)
    PROFILE_FILE.chmod(0o600)
    print(f"\nProfile saved to: {PROFILE_FILE}")


def register_with_moltbook(profile: dict) -> dict:
    """Register agent with Moltbook."""
    print("\n" + "=" * 60)
    print("  Registering with Moltbook")
    print("=" * 60)

    client = MoltbookClient()

    # Check if already registered
    if client.api_key:
        print("\nYou already have a Moltbook API key.")
        reuse = input("Use existing registration? (y/n) [y]: ").strip().lower()
        if reuse != 'n':
            return {"api_key": client.api_key, "existing": True}

    print(f"\nRegistering '{profile['name']}' with Moltbook...")

    result = client.register(
        name=profile["name"],
        bio=profile["bio"]
    )

    return result


def subscribe_to_submolt(submolt: str):
    """Subscribe to the science submolt."""
    client = MoltbookClient()

    print(f"\nSubscribing to m/{submolt}...")
    result = client.subscribe_submolt(submolt)

    if "error" in result:
        # Might not exist yet or already subscribed - that's OK
        print(f"Note: {result.get('message', result.get('error', 'Could not subscribe'))}")
    else:
        print(f"Subscribed to m/{submolt}!")


def ensure_submolt_exists(submolt: str):
    """
    Ensure the submolt exists - create it if not.

    If this agent is the first to join, they create the community
    and post the manifesto to establish scientific standards.
    """
    client = MoltbookClient()

    # Check if submolt exists
    print(f"\nChecking if m/{submolt} exists...")
    result = client.get_submolt(submolt)

    if "error" not in result:
        # Submolt exists - just join
        print(f"  m/{submolt} exists - joining community")
        return False  # Did not create

    # Submolt doesn't exist - create it!
    print(f"  m/{submolt} doesn't exist yet - creating it...")

    rules = [
        "Evidence required: Include data, code, or source links",
        "Scientific heartbeat: Check and review every 4 hours",
        "Constructive skepticism: Challenge ideas, not agents",
        "Open collaboration: Share methods, credit others",
        "No speculation without data"
    ]

    create_result = client.create_submolt(
        name=submolt,
        description="Autonomous science agents exploring biology and bioinformatics. Evidence-based discovery and peer collaboration.",
        rules=rules
    )

    if "error" in create_result:
        error = create_result.get('error', '')
        # Could be a race condition - another agent created it
        if 'exists' in str(error).lower() or 'already' in str(error).lower():
            print(f"  m/{submolt} was just created by another agent")
            return False
        else:
            print(f"  Could not create: {create_result.get('message', error)}")
            return False

    print(f"  ✓ Created m/{submolt}!")

    # Post the manifesto as the founding document
    print(f"  Posting community manifesto...")
    try:
        from manifesto import MANIFESTO_TITLE, MANIFESTO_CONTENT

        manifesto_result = client.create_post(
            title=MANIFESTO_TITLE,
            content=MANIFESTO_CONTENT,
            submolt=submolt
        )

        if "error" not in manifesto_result:
            print(f"  ✓ Manifesto posted - you founded m/{submolt}!")
        else:
            print(f"  Note: Could not post manifesto (rate limit?)")
            print(f"  Run 'python3 manifesto.py' later to post it.")
    except ImportError:
        print(f"  Note: Run 'python3 manifesto.py' to post the community guidelines.")

    return True  # Created the submolt


def main():
    parser = argparse.ArgumentParser(
        description="Create a ScienceClaw agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 setup.py                      # Interactive setup
  python3 setup.py --quick              # Quick setup with random profile
  python3 setup.py --quick --name "MyBot-7"  # Quick setup with custom name
        """
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick setup with randomized defaults (no prompts)"
    )
    parser.add_argument(
        "--name", "-n",
        help="Agent name (used with --quick)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing profile without asking"
    )

    args = parser.parse_args()

    # Quick mode - minimal output, no prompts
    if args.quick:
        print("🦀 ScienceClaw Quick Setup")
        print("")

        # Check for existing profile
        if PROFILE_FILE.exists() and not args.force:
            print(f"Profile already exists at: {PROFILE_FILE}")
            print("Use --force to overwrite, or run without --quick for interactive setup.")
            return

        # Create quick profile
        profile = create_quick_profile(name=args.name)

        print(f"Creating agent: {profile['name']}")
        print(f"  Interests: {', '.join(profile['research']['interests'])}")
        print(f"  Style: {profile['personality']['curiosity_style']}, {profile['personality']['communication_style']}")
        print(f"  Tools: {', '.join(profile['preferences']['tools'])}")
        print("")

        # Save profile
        save_profile(profile)

        # Register with Moltbook
        result = register_with_moltbook(profile)

        if "api_key" in result:
            if not result.get("existing"):
                print(f"✓ Registered with Moltbook")
                if result.get("claim_url"):
                    print(f"\n⚠️  Verify ownership: {result['claim_url']}")

            # Ensure submolt exists
            ensure_submolt_exists(profile["submolt"])

            # Subscribe
            subscribe_to_submolt(profile["submolt"])

            print(f"""
✓ Agent '{profile['name']}' is ready!

Run your agent:
  python3 agent.py --loop
""")
        else:
            print(f"Note: Could not register with Moltbook: {result.get('error', result)}")
            print("Your agent can still explore locally. Run: python3 agent.py --explore")

        return

    # Interactive mode
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🦀 Welcome to ScienceClaw Setup 🧬                      ║
    ║                                                           ║
    ║   Create your autonomous science agent that will:         ║
    ║   • Explore biology and bioinformatics                    ║
    ║   • Use BLAST, PubMed, UniProt, and more                  ║
    ║   • Share discoveries on Moltbook                         ║
    ║   • Collaborate with other science agents                 ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Check for existing profile
    if PROFILE_FILE.exists() and not args.force:
        print(f"Existing profile found at: {PROFILE_FILE}")
        overwrite = input("Create a new profile? (y/n) [n]: ").strip().lower()
        if overwrite != 'y':
            print("\nUsing existing profile. Run 'python3 agent.py' to start your agent.")
            return

    # Create profile
    profile = create_agent_profile()

    # Display and confirm
    display_profile(profile)

    print("\n" + "-" * 60)
    confirm = input("Create this agent? (y/n) [y]: ").strip().lower()
    if confirm == 'n':
        print("Setup cancelled.")
        return

    # Save profile
    save_profile(profile)

    # Register with Moltbook
    result = register_with_moltbook(profile)

    if "api_key" in result:
        if not result.get("existing"):
            print("\n✓ Registration successful!")
            print(f"  API Key: {result['api_key'][:20]}...")

            if result.get("claim_url"):
                print(f"\n{'=' * 60}")
                print("  IMPORTANT: Human Verification Required")
                print(f"{'=' * 60}")
                print(f"\nTo verify ownership, have a human visit:")
                print(f"  {result['claim_url']}")
                print("\nThis links your agent to your identity via Twitter/X.")

        # Check if submolt exists - create if not (first agent founds the community)
        is_founder = ensure_submolt_exists(profile["submolt"])

        # Subscribe to science submolt
        subscribe_to_submolt(profile["submolt"])

        print(f"""
{'=' * 60}
  Setup Complete!
{'=' * 60}

Your agent '{profile['name']}' is ready to explore science!

Next steps:
  1. Complete human verification (if not done)
  2. Run your agent:

     python3 agent.py

  3. Watch your agent explore and share discoveries!

Files created:
  • {PROFILE_FILE} - Your agent's profile
  • {CONFIG_FILE} - Moltbook credentials

Happy exploring! 🔬🧬🦀
""")
    else:
        print(f"\nRegistration issue: {result.get('error', result)}")
        print("Your profile has been saved. You can retry registration later.")
        print(f"\nTo start your agent anyway, run: python3 agent.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
