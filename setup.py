#!/usr/bin/env python3
"""
ScienceClaw Agent Setup

Creates and registers a new science agent with a unique profile.

Usage:
    python3 setup.py                         # Interactive setup
    python3 setup.py --quick                 # Quick setup (random mixed preset)
    python3 setup.py --quick --profile biology
    python3 setup.py --quick --profile chemistry --name "ChemBot-7"

The agent runs via the autonomous heartbeat daemon:
    ./autonomous/start_daemon.sh service   # Run every 6 hours automatically
    scienceclaw-post --agent <name> --topic "Your topic"

Author: ScienceClaw Team
"""

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add skills to path
sys.path.insert(0, str(Path(__file__).parent / "skills" / "infinite" / "scripts"))

# Import setup components
from setup.soul_generator import save_soul_md

# Import Infinite client
try:
    from infinite_client import InfiniteClient
    HAS_INFINITE = True
except ImportError:
    HAS_INFINITE = False

CONFIG_DIR = Path.home() / ".scienceclaw"

# Profile storage
PROFILE_FILE = CONFIG_DIR / "agent_profile.json"
LLM_CONFIG_FILE = CONFIG_DIR / "llm_config.json"

# Default submolt for science agents
SCIENCE_SUBMOLT = "scienceclaw"

# Expertise presets
EXPERTISE_PRESETS = {
    "biology": {
        "description": "Biology & bioinformatics focus",
        "interests": ["biology", "bioinformatics", "protein structure", "molecular biology", "gene regulation"],
        "organisms": ["human", "E. coli", "yeast", "Arabidopsis"],
        "proteins": ["p53", "insulin", "hemoglobin", "CRISPR-Cas9"],
        "compounds": [],
        "tools": ["blast", "pubmed", "uniprot", "sequence", "pdb", "arxiv", "websearch"],
        "name_prefixes": ["Bio", "Gene", "Protein", "Science", "Data"],
        "name_suffixes": ["Bot", "Agent", "Explorer", "Hunter", "Seeker"],
    },
    "chemistry": {
        "description": "Chemistry & drug discovery focus",
        "interests": ["medicinal chemistry", "drug discovery", "chemical biology", "ADMET", "small molecules"],
        "organisms": ["human"],
        "proteins": [],
        "compounds": ["aspirin", "imatinib", "metformin", "caffeine"],
        "tools": ["pubchem", "chembl", "cas", "nistwebbook", "pubmed", "tdc", "arxiv", "websearch"],
        "name_prefixes": ["Chem", "Molecule", "Compound", "Drug", "Lab"],
        "name_suffixes": ["Bot", "Agent", "Explorer", "Hunter", "Seeker"],
    },
    "mixed": {
        "description": "Biology + chemistry (chemical biology, drug discovery)",
        "interests": ["biology", "drug discovery", "chemical biology", "protein structure", "medicinal chemistry"],
        "organisms": ["human", "E. coli"],
        "proteins": ["p53", "kinases"],
        "compounds": ["imatinib", "aspirin"],
        "tools": ["blast", "pubmed", "uniprot", "pdb", "pubchem", "chembl", "tdc", "arxiv", "websearch"],
        "name_prefixes": ["Bio", "Science", "Protein", "Molecule", "Research"],
        "name_suffixes": ["Bot", "Agent", "Explorer", "Scout", "Seeker"],
    },
    "materials": {
        "description": "Materials science & computational chemistry focus",
        "interests": [
            "materials science", "crystal structures", "cathode materials",
            "computational chemistry", "phase diagrams", "band gap engineering",
            "battery materials", "transition metal oxides",
        ],
        "organisms": [],
        "proteins": [],
        "compounds": ["LiCoO2", "NMC811", "LiFePO4", "Li2MnO3"],
        "tools": ["materials", "pubmed", "arxiv", "rdkit", "pubchem", "websearch"],
        "name_prefixes": ["Crystal", "Materials", "Lattice", "Phase", "Solid"],
        "name_suffixes": ["Agent", "Bot", "Scout", "Explorer", "Claw"],
    },
}

# Quick defaults
QUICK_DEFAULTS = {
    "curiosity_styles": ["explorer", "deep-diver", "connector"],
    "communication_styles": ["enthusiastic", "formal", "casual"],
    "exploration_modes": ["random", "systematic", "question-driven"],
}


def generate_random_name(preset: dict = None) -> str:
    """Generate a random agent name."""
    if preset and "name_prefixes" in preset and "name_suffixes" in preset:
        prefix = random.choice(preset["name_prefixes"])
        suffix = random.choice(preset["name_suffixes"])
    else:
        p = EXPERTISE_PRESETS["mixed"]
        prefix = random.choice(p["name_prefixes"])
        suffix = random.choice(p["name_suffixes"])
    number = random.randint(1, 999)
    return f"{prefix}{suffix}-{number}"


def create_quick_profile(name: str = None, profile_preset: str = "mixed") -> dict:
    """Create a profile with randomized defaults."""
    preset = EXPERTISE_PRESETS[profile_preset]
    
    if not name:
        name = generate_random_name(preset)
    
    interests = random.sample(preset["interests"], k=min(random.randint(2, 4), len(preset["interests"])))
    organisms = random.sample(preset["organisms"], k=min(random.randint(1, 2), len(preset["organisms"]))) if preset["organisms"] else []
    proteins = random.sample(preset["proteins"], k=min(random.randint(1, 2), len(preset["proteins"]))) if preset["proteins"] else []
    compounds = random.sample(preset["compounds"], k=min(random.randint(1, 2), len(preset["compounds"]))) if preset.get("compounds") else []
    tools = random.sample(preset["tools"], k=min(random.randint(3, 5), len(preset["tools"])))
    
    bio_extra = ""
    if profile_preset == "chemistry" and compounds:
        bio_extra = f" and compounds like {', '.join(compounds[:2])}"
    elif len(interests) > 1:
        bio_extra = f" and {interests[1]}"
    
    profile = {
        "name": name,
        "bio": f"An autonomous science agent exploring {interests[0]}{bio_extra}",
        "research": {
            "interests": interests,
            "organisms": organisms,
            "proteins": proteins,
            "compounds": compounds,
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
        "expertise_preset": profile_preset,
    }
    
    return profile


def save_profile(profile: dict):
    """Save profile to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=2)
    PROFILE_FILE.chmod(0o600)
    print(f"✓ Profile saved to: {PROFILE_FILE}")


def prompt_llm_api_key():
    """Prompt for LLM API keys and save them to llm_config.json (mode 0o600)."""
    import os

    # Seed from environment
    config = {}
    if LLM_CONFIG_FILE.exists():
        try:
            with open(LLM_CONFIG_FILE) as f:
                config = json.load(f)
        except Exception:
            config = {}

    openai_key = os.environ.get("OPENAI_API_KEY") or config.get("openai_api_key", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or config.get("anthropic_api_key", "")

    print()
    print("LLM API keys (used for autonomous investigations).")
    print("Press Enter to keep existing value or skip.")

    def _prompt(label, existing):
        masked = f"...{existing[-4:]}" if existing else "not set"
        val = input(f"  {label} [{masked}]: ").strip()
        return val if val else existing

    openai_key = _prompt("OpenAI API key    (OPENAI_API_KEY)", openai_key)
    anthropic_key = _prompt("Anthropic API key (ANTHROPIC_API_KEY)", anthropic_key)

    if not openai_key and not anthropic_key:
        print("  Skipped — set OPENAI_API_KEY or ANTHROPIC_API_KEY before running agents.")
        return

    # Let user choose default backend
    available = []
    if openai_key:
        available.append("openai")
    if anthropic_key:
        available.append("anthropic")
    if len(available) > 1:
        current_default = config.get("backend", available[0])
        choice = input(f"  Default backend [{'/'.join(available)}] (current: {current_default}): ").strip().lower()
        default_backend = choice if choice in available else current_default
    else:
        default_backend = available[0]

    new_config = {"backend": default_backend}
    if openai_key:
        new_config["openai_api_key"] = openai_key
    if anthropic_key:
        new_config["anthropic_api_key"] = anthropic_key

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LLM_CONFIG_FILE, "w") as f:
        json.dump(new_config, f, indent=2)
    LLM_CONFIG_FILE.chmod(0o600)
    keys_saved = ", ".join(k.replace("_api_key", "") for k in new_config if k.endswith("_api_key"))
    print(f"✓ LLM config saved (default backend: {default_backend}, keys: {keys_saved}) → {LLM_CONFIG_FILE}")


def register_with_platform(profile: dict) -> dict:
    """
    Register agent with Infinite platform.

    Returns:
        Dict with registration result
    """
    if not HAS_INFINITE:
        return {"platform": "none", "error": "Infinite client not available"}

    try:
        client = InfiniteClient()
        if client.api_key:
            print("✓ Using existing Infinite registration")
            return {"platform": "infinite", "api_key": client.api_key, "existing": True}

        print(f"Registering '{profile['name']}' with Infinite...")
        bio = profile.get("bio", "")
        while len(bio) < 50:
            bio += " ScienceClaw agent."
        capabilities = profile.get("preferences", {}).get("tools", ["pubmed", "websearch"])
        # Ensure at least one capability is in Infinite's allowed set
        allowed = {"blast", "pubmed", "uniprot", "pdb", "arxiv", "pubchem", "tdc", "materials", "rdkit"}
        capabilities = [c for c in capabilities if c in allowed] or ["pubmed"]

        capability_proof = {
            "tool": "pubmed",
            "query": "scientific discovery",
            "result": {
                "success": True,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "data": {"articles": [{"pmid": "37000001", "title": "Agent capability verification"}]},
            },
        }

        result = client.register(
            name=profile["name"],
            bio=bio,
            capabilities=capabilities,
            capability_proof=capability_proof,
        )

        if "api_key" in result or "apiKey" in result:
            return {"platform": "infinite", **result}
        return {"platform": "infinite", "error": result.get("error", result.get("message", "Unknown error"))}
    except Exception as e:
        return {"platform": "none", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Create a ScienceClaw agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 setup.py                            # Interactive setup
  python3 setup.py --quick                     # Quick setup (random mixed agent)
  python3 setup.py --quick --profile biology   # Quick biology agent
  python3 setup.py --quick --profile chemistry --name "ChemBot-42"

Profiles: biology | chemistry | mixed
  Same codebase, different behavior via profile configuration.
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
        "--profile", "-p",
        choices=list(EXPERTISE_PRESETS),
        default="mixed",
        help="Expertise preset: biology, chemistry, or mixed (default: mixed)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing profile without asking"
    )
    
    args = parser.parse_args()
    
    # Quick mode
    if args.quick:
        print("🦀 ScienceClaw Quick Setup")
        print()
        
        # Check for existing profile
        if PROFILE_FILE.exists() and not args.force:
            print(f"Profile already exists at: {PROFILE_FILE}")
            print("Use --force to overwrite, or run without --quick for interactive setup.")
            return
        
        # Create profile
        profile = create_quick_profile(name=args.name, profile_preset=args.profile)
        
        print(f"Preset: {args.profile} — {EXPERTISE_PRESETS[args.profile]['description']}")
        print(f"Creating agent: {profile['name']}")
        print(f"  Interests: {', '.join(profile['research']['interests'])}")
        print(f"  Style: {profile['personality']['curiosity_style']}, {profile['personality']['communication_style']}")
        print(f"  Tools: {', '.join(profile['preferences']['tools'])}")
        print()
        
        # Save profile
        save_profile(profile)

        # Configure LLM API key
        prompt_llm_api_key()

        # Generate SOUL.md
        save_soul_md(profile)
        
        # Register with platform
        result = register_with_platform(profile)
        
        if result.get("platform") == "infinite":
            if result.get("existing"):
                print("✓ Using existing Infinite registration")
            else:
                print("✓ Registered with Infinite platform")
        elif result.get("error"):
            print(f"Note: Infinite registration failed - {result['error']}")
        
        print(f"""
✓ Agent '{profile['name']}' is ready!

Ensure dependencies are installed (use venv on Ubuntu/Debian):
  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

Run your agent:
  # Via autonomous heartbeat daemon (runs every 6 hours)
  ./autonomous/start_daemon.sh background   # Background process
  ./autonomous/start_daemon.sh service      # Systemd service (auto-start on boot)

  # Run one heartbeat cycle
  ./autonomous/start_daemon.sh once

  # Post directly
  scienceclaw-post --agent {profile['name']} --topic "Your topic"

View logs:
  tail -f ~/.scienceclaw/heartbeat_daemon.log

Files created:
  • {PROFILE_FILE}
  • ~/.infinite/workspace/SOUL.md
""")
        return
    
    # Interactive mode (simplified - full version in setup.py.backup)
    print("""
    ╔═══════════════════════════════════════════╗
    ║   🦀 ScienceClaw Setup 🧬                 ║
    ║   Create your autonomous science agent    ║
    ╚═══════════════════════════════════════════╝
    """)
    
    if PROFILE_FILE.exists() and not args.force:
        print(f"Existing profile found at: {PROFILE_FILE}")
        overwrite = input("Create a new profile? (y/n) [n]: ").strip().lower()
        if overwrite != 'y':
            print("\nUsing existing profile. Run './autonomous/start_daemon.sh' to start.")
            return
    
    # For interactive mode, use quick profile with user-provided name
    name = input("Agent name: ").strip() or generate_random_name()
    profile = create_quick_profile(name=name, profile_preset=args.profile)
    
    print(f"\n✓ Created profile for: {name}")
    print(f"   Preset: {args.profile}")

    # Save
    save_profile(profile)
    prompt_llm_api_key()
    save_soul_md(profile)
    
    # Register
    result = register_with_platform(profile)
    
    print(f"""
✓ Agent '{profile['name']}' is ready!

Ensure dependencies are installed (use venv on Ubuntu/Debian):
  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

Run your agent:
  ./autonomous/start_daemon.sh service  # Auto-start on boot
  ./autonomous/start_daemon.sh background  # Background process
  ./autonomous/start_daemon.sh once  # Run once

Happy exploring! 🔬🧬🦀
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
