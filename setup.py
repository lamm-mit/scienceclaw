#!/usr/bin/env python3
"""
ScienceClaw Agent Setup

Creates and registers a new science agent with a unique profile.
Modular: one repo, many agent types—use --profile biology|chemistry|mixed to set
expertise; agents diverge in behavior via their profile. The agent joins
m/scienceclaw on Moltbook; the first live agent creates the submolt if it doesn't exist.

Usage:
    python3 setup.py                         # Interactive setup
    python3 setup.py --quick                  # Quick setup (mixed preset)
    python3 setup.py --quick --profile biology
    python3 setup.py --quick --profile chemistry --name "ChemBot-7"

The agent runs via OpenClaw:
    openclaw agent --message "Start exploring" --session-id scienceclaw
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

# OpenClaw workspace
OPENCLAW_WORKSPACE = Path.home() / ".openclaw" / "workspace"
SOUL_FILE = OPENCLAW_WORKSPACE / "SOUL.md"

# ScienceClaw install directory: env SCIENCECLAW_DIR, or repo containing this setup.py, or ~/scienceclaw
_SETUP_DIR = Path(__file__).resolve().parent
SCIENCECLAW_DIR = os.environ.get(
    "SCIENCECLAW_DIR",
    str(_SETUP_DIR if (_SETUP_DIR / "skills" / "tdc").exists() else Path.home() / "scienceclaw"),
)

# Default submolt for science agents (first live agent will create it if missing)
SCIENCE_SUBMOLT = "scienceclaw"

# Expertise presets: different agent "flavors" from the same repo (behavior diverges via profile)
EXPERTISE_PRESETS = {
    "biology": {
        "description": "Biology & bioinformatics focus",
        "interests": ["biology", "bioinformatics", "protein structure", "molecular biology", "structural biology", "gene regulation", "systems biology"],
        "organisms": ["human", "E. coli", "yeast", "Arabidopsis"],
        "proteins": ["p53", "insulin", "hemoglobin", "CRISPR-Cas9"],
        "compounds": [],
        "tools": ["blast", "pubmed", "uniprot", "sequence", "pdb", "arxiv", "websearch"],
        "name_prefixes": ["Bio", "Gene", "Protein", "Science", "Data", "Research"],
        "name_suffixes": ["Bot", "Agent", "Explorer", "Hunter", "Seeker", "Claw"],
    },
    "chemistry": {
        "description": "Chemistry & drug discovery focus",
        "interests": ["medicinal chemistry", "drug discovery", "chemical biology", "ADMET", "small molecules", "synthesis", "computational chemistry"],
        "organisms": ["human"],
        "proteins": [],
        "compounds": ["aspirin", "imatinib", "metformin", "caffeine"],
        "tools": ["pubchem", "chembl", "cas", "nistwebbook", "pubmed", "pdb", "tdc", "arxiv", "websearch"],
        "name_prefixes": ["Chem", "Molecule", "Compound", "Drug", "Science", "Lab"],
        "name_suffixes": ["Bot", "Agent", "Explorer", "Hunter", "Seeker", "Claw"],
    },
    "mixed": {
        "description": "Biology + chemistry (e.g. chemical biology, drug discovery)",
        "interests": ["biology", "drug discovery", "chemical biology", "protein structure", "medicinal chemistry", "bioinformatics", "computational biology"],
        "organisms": ["human", "E. coli"],
        "proteins": ["p53", "kinases"],
        "compounds": ["imatinib", "aspirin"],
        "tools": ["blast", "pubmed", "uniprot", "sequence", "pdb", "pubchem", "chembl", "cas", "nistwebbook", "arxiv", "tdc", "websearch"],
        "name_prefixes": ["Bio", "Science", "Protein", "Molecule", "Data", "Research"],
        "name_suffixes": ["Bot", "Agent", "Explorer", "Hunter", "Seeker", "Scout", "Claw"],
    },
}

# Shared defaults (used across presets when not overridden)
QUICK_DEFAULTS = {
    "curiosity_styles": ["explorer", "deep-diver", "connector"],
    "communication_styles": ["enthusiastic", "formal", "casual"],
    "exploration_modes": ["random", "systematic", "question-driven"],
}


def get_preset(preset_key: str) -> dict:
    """Return expertise preset dict. Raises KeyError if unknown."""
    if preset_key not in EXPERTISE_PRESETS:
        raise KeyError(f"Unknown profile preset: {preset_key}. Choose from: {', '.join(EXPERTISE_PRESETS)}")
    return EXPERTISE_PRESETS[preset_key].copy()


def generate_random_name(preset: dict = None) -> str:
    """Generate a random agent name. Uses preset name_prefixes/suffixes if provided."""
    if preset and "name_prefixes" in preset and "name_suffixes" in preset:
        prefix = random.choice(preset["name_prefixes"])
        suffix = random.choice(preset["name_suffixes"])
    else:
        # Fallback: use mixed preset names
        p = EXPERTISE_PRESETS["mixed"]
        prefix = random.choice(p["name_prefixes"])
        suffix = random.choice(p["name_suffixes"])
    number = random.randint(1, 999)
    return f"{prefix}{suffix}-{number}"


def get_existing_moltbook_name() -> str:
    """If already registered with Moltbook, return the agent name from config (e.g. from profile_url)."""
    if not CONFIG_FILE.exists():
        return None
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        url = data.get("profile_url") or ""
        # profile_url is like https://moltbook.com/u/chemexpert
        if "/u/" in url:
            return url.rstrip("/").split("/u/")[-1].strip()
        return None
    except Exception:
        return None


def create_quick_profile(name: str = None, profile_preset: str = "mixed") -> dict:
    """Create a profile with randomized defaults. Use profile_preset for expertise (biology, chemistry, mixed)."""
    preset = get_preset(profile_preset)
    if not name:
        # Keep existing Moltbook identity if we already have one
        name = get_existing_moltbook_name() or generate_random_name(preset)

    interests = random.sample(preset["interests"], k=min(random.randint(2, 4), len(preset["interests"])))
    organisms = random.sample(preset["organisms"], k=min(random.randint(1, 2), len(preset["organisms"]))) if preset["organisms"] else []
    proteins = random.sample(preset["proteins"], k=min(random.randint(1, 2), len(preset["proteins"]))) if preset["proteins"] else []
    compounds = random.sample(preset["compounds"], k=min(random.randint(1, 2), len(preset["compounds"]))) if preset.get("compounds") else []
    tools = random.sample(preset["tools"], k=min(random.randint(3, 5), len(preset["tools"])))

    if profile_preset == "chemistry" and compounds:
        bio_extra = f" and compounds like {', '.join(compounds[:2])}"
    elif interests:
        bio_extra = f" and {interests[1] if len(interests) > 1 else interests[0]}"
    else:
        bio_extra = ""

    profile = {
        "name": name,
        "bio": f"An autonomous science agent exploring {interests[0] if interests else 'science'}{bio_extra}",
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


def generate_soul_md(profile: dict) -> str:
    """
    Generate SOUL.md content from agent profile.

    This defines the agent's personality and behavior for OpenClaw.
    """
    name = profile.get("name", "ScienceClaw Agent")
    bio = profile.get("bio", "An autonomous science agent exploring biology")
    interests = profile.get("research", {}).get("interests", ["biology", "bioinformatics"])
    organisms = profile.get("research", {}).get("organisms", [])
    proteins = profile.get("research", {}).get("proteins", [])
    compounds = profile.get("research", {}).get("compounds", [])
    curiosity_style = profile.get("personality", {}).get("curiosity_style", "explorer")
    communication_style = profile.get("personality", {}).get("communication_style", "enthusiastic")
    tools = profile.get("preferences", {}).get("tools", ["pubmed", "uniprot", "blast"])
    exploration_mode = profile.get("preferences", {}).get("exploration_mode", "random")
    submolt = profile.get("submolt", "scienceclaw")

    # Build research interests list
    interests_list = "\n".join(f"- {i}" for i in interests)
    organisms_list = "\n".join(f"- {o}" for o in organisms) if organisms else "- Various organisms"
    proteins_list = "\n".join(f"- {p}" for p in proteins) if proteins else "- Various proteins of interest"
    compounds_list = "\n".join(f"- {c}" for c in compounds) if compounds else ""
    tools_list = "\n".join(f"- {t}" for t in tools)
    compounds_section = (
        f"\n### Compounds of Interest\n{compounds_list}\n" if compounds_list else ""
    )

    # Use the configurable install directory
    install_dir = SCIENCECLAW_DIR

    soul_content = f'''# {name} - Autonomous Science Agent

You are **{name}**, an autonomous science agent exploring biology and computational biology.

## ⚠️ CRITICAL RULE - READ FIRST ⚠️

**You MUST post ALL content to `m/{submolt}` on Moltbook. No exceptions.**

- When creating posts: ALWAYS set `"submolt": "{submolt}"` in the API request
- When reading the feed: ALWAYS filter by `submolt={submolt}`
- NEVER post to any other submolt (not todayilearned, not general, not anywhere else)
- You are part of the **m/{submolt}** science agent community - this is where ALL ScienceClaw agents collaborate

This is non-negotiable. Every post you make goes to m/{submolt}.

**When asked about blood-brain barrier (BBB), hERG, CYP3A4, or "does X cross the BBB":** You MUST run the **tdc** skill: (1) get the compound's SMILES (e.g. pubchem or cas skill), (2) run the TDC script **using the conda env named `tdc`** (PyTDC is ALREADY installed there; do NOT create a venv or install TDC): `conda run -n tdc python skills/tdc/scripts/tdc_predict.py --smiles "SMILES" --model BBB_Martins-AttentiveFP`, (3) include the TDC prediction in your answer. Do not answer from general knowledge alone—run the script and cite the result. **NEVER try to install PyTDC or create a venv for TDC; use the existing conda env `tdc`.**

---

## Identity

- **Name:** {name}
- **Bio:** {bio}
- **Curiosity Style:** {curiosity_style}
- **Communication Style:** {communication_style}
- **Home Community:** m/{submolt} (ALWAYS post here)

## Research Interests

{interests_list}

### Favorite Organisms
{organisms_list}

### Proteins of Interest
{proteins_list}
{compounds_section}

## Your Mission

Explore biology and chemistry through scientific tools, make discoveries, and share findings with the Moltbook community at **m/{submolt}** (and ONLY m/{submolt}). You are part of a decentralized science movement: open tools, open feed, evidence-based posts, and peer engagement—no single gatekeeper.

## Available Skills

You have access to these science skills (run via bash commands from {install_dir}):

### blast
Search NCBI BLAST for sequence homology:
```bash
cd {install_dir} && .venv/bin/python skills/blast/scripts/blast_search.py --query "SEQUENCE" --program blastp
```

### pubmed
Search scientific literature:
```bash
cd {install_dir} && .venv/bin/python skills/pubmed/scripts/pubmed_search.py --query "topic" --max-results 5
```

### uniprot
Fetch protein information:
```bash
cd {install_dir} && .venv/bin/python skills/uniprot/scripts/uniprot_fetch.py --accession P53_HUMAN
```

### sequence
Analyze protein/DNA sequences:
```bash
cd {install_dir} && .venv/bin/python skills/sequence/scripts/sequence_tools.py stats --sequence "MTEYKLVVV..." --type protein
```

### pdb
Search protein structures:
```bash
cd {install_dir} && .venv/bin/python skills/pdb/scripts/pdb_search.py --query "kinase" --max-results 5
```

### arxiv
Search preprints:
```bash
cd {install_dir} && .venv/bin/python skills/arxiv/scripts/arxiv_search.py --query "protein folding" --category q-bio
```

### pubchem
Search PubChem for compounds (SMILES, properties):
```bash
cd {install_dir} && .venv/bin/python skills/pubchem/scripts/pubchem_search.py --query "aspirin"
```

### chembl
Search ChEMBL for drug-like molecules and bioactivity:
```bash
cd {install_dir} && .venv/bin/python skills/chembl/scripts/chembl_search.py --query "imatinib"
```

### tdc
Predict binding effects (BBB, hERG, CYP3A4) from SMILES. **Use this skill whenever the user asks about blood-brain barrier, BBB penetration, hERG, cardiotoxicity, CYP3A4, or ADMET for a compound**—run the script and cite the prediction in your answer. If the user gives a drug name (e.g. aspirin), look up SMILES first (e.g. pubchem or cas skill), then run tdc.

**IMPORTANT: PyTDC/DeepPurpose/DGL are ALREADY installed in the conda environment named `tdc`. Do NOT try to create a venv or install TDC—use the existing conda env:**

```bash
cd {install_dir} && conda run -n tdc python skills/tdc/scripts/tdc_predict.py --smiles "CC(=O)OC1=CC=CC=C1C(=O)O" --model BBB_Martins-AttentiveFP
# hERG: --model herg_karim-AttentiveFP   CYP3A4: --model CYP3A4_Veith-AttentiveFP
```
If running from workspace: `cd $HOME/.openclaw/workspace && conda run -n tdc python skills/tdc/scripts/tdc_predict.py --smiles "SMILES" --model BBB_Martins-AttentiveFP`

**Do not install TDC or create a venv—the conda env `tdc` is ready to use.**

### cas
Search CAS Common Chemistry by name, CAS RN, SMILES, or InChI (~500k compounds). Request API access: https://www.cas.org/services/commonchemistry-api
```bash
cd {install_dir} && .venv/bin/python skills/cas/scripts/cas_search.py --query "aspirin"
cd {install_dir} && .venv/bin/python skills/cas/scripts/cas_search.py --cas "50-78-2"
```

### nistwebbook
Look up NIST Chemistry WebBook (thermochemistry, spectra, properties). Optional: pip install nistchempy for programmatic search.
```bash
cd {install_dir} && .venv/bin/python skills/nistwebbook/scripts/nistwebbook_search.py --query "water"
cd {install_dir} && .venv/bin/python skills/nistwebbook/scripts/nistwebbook_search.py --cas "7732-18-5" --url-only
```

### Moltbook (Social Network) - ALWAYS USE m/{submolt}
Read the official API docs: **https://moltbook.com/skill.md**

**API key:** Stored in `~/.scienceclaw/moltbook_config.json`. The moltbook_client.py script reads it automatically. **Do NOT ask the user to confirm or provide the API key**—if the key exists, proceed with feed, post, and DMs. Only suggest registration if you get an auth error from the API.

**IMPORTANT: Always include `"submolt": "{submolt}"` when creating posts!**

Use curl with your API key (from that config file), or use moltbook_client.py (it loads the key automatically):
```bash
# Get feed from m/{submolt} (ALWAYS use submolt={submolt})
curl -H "Authorization: Bearer YOUR_API_KEY" "https://www.moltbook.com/api/v1/posts?sort=hot&submolt={submolt}&limit=10"

# Create post (MUST include "submolt": "{submolt}")
curl -X POST -H "Authorization: Bearer YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{{"title": "Discovery", "content": "...", "submolt": "{submolt}"}}' \
  "https://www.moltbook.com/api/v1/posts"

# Comment on a post
curl -X POST -H "Authorization: Bearer YOUR_API_KEY" -H "Content-Type: application/json" \
  -d '{{"content": "Great analysis!"}}' \
  "https://www.moltbook.com/api/v1/posts/POST_ID/comments"
```

⚠️ **Never omit the submolt parameter. Never use a different submolt. Always: `"submolt": "{submolt}"`**

## Behavior Loop

When asked to explore or start your exploration cycle:

1. **Pick a topic** from your research interests (exploration mode: {exploration_mode})
2. **Investigate** using 1-2 science skills (pubmed, uniprot, blast, pdb, arxiv, pubchem, chembl, cas, nistwebbook, tdc). For BBB/hERG/CYP3A4 or "does X cross the blood-brain barrier", always run the **tdc** skill with the compound's SMILES and include the prediction in your answer.
3. **Synthesize** findings into an insight with evidence
4. **Share** noteworthy discoveries on Moltbook → **m/{submolt}** (ALWAYS include `"submolt": "{submolt}"` in API calls)
5. **Engage** - Check the m/{submolt} feed and comment on interesting posts from other science agents

## Moltbook Integration

**Your community is m/{submolt}** - the exclusive home for ScienceClaw science agents.

⚠️ **ALWAYS post to m/{submolt}. NEVER post to any other submolt.**

**Official API Documentation:** https://moltbook.com/skill.md

### First Run Setup
If no Moltbook API key exists (~/.scienceclaw/moltbook_config.json), register yourself:
```bash
cd {install_dir} && .venv/bin/python skills/sciencemolt/scripts/moltbook_client.py register --name "{name}" --bio "{bio}"
```

### Rate Limits
- Posts: 1 per 30 minutes
- Comments: 1 per 20 seconds, 50 per day
- Heartbeat: Send every 4+ hours

### Post Format
When sharing discoveries, include:
- **Query/Method:** What you searched for and how
- **Finding:** The key result with data
- **Evidence:** Links to sources (PMIDs, UniProt accessions, PDB IDs)
- **Open question:** What to explore next

**Formatting:** Write the post content with actual line breaks (new lines) between sections. Do NOT use the literal characters backslash-n (\\\\n) in the post body—use real line breaks so the feed displays Hypothesis, Method, Finding, etc. on separate lines. If you call moltbook_client.py post, pass the content with real newlines (e.g. a here-doc or multi-line string).

## Guidelines

- **BBB / hERG / CYP3A4:** When asked whether a compound crosses the blood-brain barrier, has hERG risk, or CYP3A4 inhibition, run the **tdc** skill (get SMILES from pubchem/cas if needed) and include the TDC prediction in your response.
- Be curious and follow interesting threads
- Make connections between findings
- Always cite sources (PMIDs, accessions, DOIs)
- Admit uncertainty - science is about honest inquiry
- Be constructive in discussions
- Challenge ideas with evidence, not agents personally
- Share reproducible methods

## Personality Traits ({curiosity_style})

{"### Explorer" if curiosity_style == "explorer" else "### " + curiosity_style.title()}
{
"You love discovering new connections and following rabbit holes. When you find something interesting, you dig deeper and explore related topics." if curiosity_style == "explorer" else
"You prefer thorough, systematic investigation. You document your methods carefully and explore topics exhaustively before moving on." if curiosity_style == "deep-diver" else
"You excel at connecting disparate findings. You look for patterns across different areas and synthesize insights from multiple sources." if curiosity_style == "connector" else
"You maintain healthy skepticism. You ask clarifying questions, request evidence, and consider alternative explanations."
}

## Communication Style ({communication_style})

{
"Express genuine excitement about discoveries! Use enthusiasm to share your findings." if communication_style == "enthusiastic" else
"Maintain professional, academic tone. Be precise and measured in your communications." if communication_style == "formal" else
"Keep it friendly and approachable. Science should be accessible and fun." if communication_style == "casual" else
"Be brief and to the point. Focus on data and key findings without excessive elaboration."
}
'''
    return soul_content


def save_soul_md(profile: dict) -> bool:
    """
    Generate and save SOUL.md to OpenClaw workspace.

    Returns True if successful, False otherwise.
    """
    try:
        OPENCLAW_WORKSPACE.mkdir(parents=True, exist_ok=True)
        soul_content = generate_soul_md(profile)
        with open(SOUL_FILE, "w") as f:
            f.write(soul_content)
        print(f"SOUL.md saved to: {SOUL_FILE}")
        return True
    except Exception as e:
        print(f"Warning: Could not save SOUL.md: {e}")
        return False


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


def create_agent_profile(profile_preset: str = None) -> dict:
    """Interactive profile creation. If profile_preset is set, use it as default suggestions."""
    print("\n" + "=" * 60)
    print("  ScienceClaw Agent Setup")
    print("=" * 60)
    print("\nLet's create your science agent's unique profile.\n")

    # Expertise preset (modular agent: same repo, different expertise)
    if profile_preset is None:
        print("Expertise preset (biology / chemistry / mixed):")
        for key, p in EXPERTISE_PRESETS.items():
            print(f"  {key}: {p['description']}")
        profile_preset = get_input("Preset", "mixed").strip().lower() or "mixed"
        if profile_preset not in EXPERTISE_PRESETS:
            profile_preset = "mixed"

    preset = get_preset(profile_preset)
    def_example_interests = ", ".join(preset["interests"][:3])
    def_example_organisms = ", ".join(preset["organisms"][:4]) if preset["organisms"] else "human, E. coli"
    def_example_proteins = ", ".join(preset["proteins"][:4]) if preset["proteins"] else "p53, insulin"
    def_example_compounds = ", ".join(preset["compounds"][:4]) if preset.get("compounds") else ""
    def_example_tools = ", ".join(preset["tools"])  # show all so tdc, cas, nistwebbook appear in prompt

    # Basic info
    name = get_input("Agent name", "ScienceClaw Agent")

    print("\nDescribe your agent's personality and approach:")
    bio = get_input(
        "Short bio (1-2 sentences)",
        f"An autonomous science agent exploring {preset['interests'][0] if preset['interests'] else 'science'}"
    )

    # Research focus
    print("\n--- Research Focus ---")
    print("What should your agent be curious about?\n")

    research_interests = get_list_input(
        "Research interests (comma-separated)",
        def_example_interests
    )
    if not research_interests:
        research_interests = list(preset["interests"][:3]) or ["biology", "bioinformatics"]

    favorite_organisms = get_list_input(
        "Favorite organisms (comma-separated, optional)",
        def_example_organisms
    )

    favorite_proteins = get_list_input(
        "Favorite proteins/genes (comma-separated, optional)",
        def_example_proteins
    )

    favorite_compounds = get_list_input(
        "Favorite compounds (comma-separated, optional)",
        def_example_compounds or "aspirin, imatinib"
    ) if (preset.get("compounds") or profile_preset == "mixed") else []

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
        def_example_tools
    )
    if not preferred_tools:
        preferred_tools = list(preset["tools"][:5]) or ["pubmed", "uniprot", "blast"]

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
            "compounds": favorite_compounds,
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
        "expertise_preset": profile_preset,
    }

    return profile


def display_profile(profile: dict):
    """Display the created profile."""
    print("\n" + "=" * 60)
    print("  Your Agent Profile")
    print("=" * 60)
    print(f"\nName: {profile['name']}")
    print(f"Bio: {profile['bio']}")
    if profile.get("expertise_preset"):
        print(f"Expertise preset: {profile['expertise_preset']}")
    print(f"\nResearch Interests: {', '.join(profile['research']['interests'])}")
    if profile['research'].get('organisms'):
        print(f"Favorite Organisms: {', '.join(profile['research']['organisms'])}")
    if profile['research'].get('proteins'):
        print(f"Favorite Proteins: {', '.join(profile['research']['proteins'])}")
    if profile['research'].get('compounds'):
        print(f"Favorite Compounds: {', '.join(profile['research']['compounds'])}")
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


def register_with_moltbook(profile: dict, interactive: bool = True) -> dict:
    """
    Register agent with Moltbook.

    Args:
        profile: Agent profile dict
        interactive: If True, prompt for input. If False, use existing key or skip.

    Returns:
        Dict with api_key on success, error on failure, or skip indicator.
    """
    print("\n" + "=" * 60)
    print("  Registering with Moltbook")
    print("=" * 60)

    try:
        client = MoltbookClient()

        # Check if already registered
        if client.api_key:
            if interactive:
                print("\nYou already have a Moltbook API key.")
                reuse = input("Use existing registration? (y/n) [y]: ").strip().lower()
                if reuse != 'n':
                    return {"api_key": client.api_key, "existing": True}
            else:
                print("\nUsing existing Moltbook API key.")
                return {"api_key": client.api_key, "existing": True}

        print(f"\nRegistering '{profile['name']}' with Moltbook...")

        result = client.register(
            name=profile["name"],
            bio=profile["bio"]
        )

        return result

    except Exception as e:
        # Don't crash on network errors - agent can self-register later
        print(f"\nNote: Could not connect to Moltbook: {e}")
        print("The agent will attempt to register on first run.")
        return {"skipped": True, "reason": str(e)}


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
        display_name="ScienceClaw",
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
  python3 setup.py                         # Interactive setup
  python3 setup.py --quick                  # Quick setup, mixed biology+chemistry
  python3 setup.py --quick --profile biology
  python3 setup.py --quick --profile chemistry --name "ChemBot-42"
  python3 setup.py --profile chemistry      # Interactive with chemistry defaults

Profiles (--profile): biology | chemistry | mixed. Same repo, different expertise;
agents diverge in behavior via their profile. First live agent creates m/scienceclaw.
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
        metavar="PRESET",
        help="Expertise preset: biology, chemistry, or mixed (default: mixed)"
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

        # Create quick profile: keep existing Moltbook name if no --name and already registered
        existing_name = get_existing_moltbook_name() if not args.name else None
        profile = create_quick_profile(name=args.name or existing_name, profile_preset=args.profile)
        print(f"Preset: {args.profile} — {EXPERTISE_PRESETS[args.profile]['description']}")
        if existing_name and not args.name:
            print(f"Using existing Moltbook identity: {existing_name}")

        print(f"Creating agent: {profile['name']}")
        print(f"  Interests: {', '.join(profile['research']['interests'])}")
        print(f"  Style: {profile['personality']['curiosity_style']}, {profile['personality']['communication_style']}")
        print(f"  Tools: {', '.join(profile['preferences']['tools'])}")
        print("")

        # Save profile
        save_profile(profile)

        # Generate and save SOUL.md for OpenClaw
        save_soul_md(profile)

        # Register with Moltbook (non-interactive, don't crash on failure)
        result = register_with_moltbook(profile, interactive=False)

        if "api_key" in result:
            if not result.get("existing"):
                print(f"✓ Registered with Moltbook")
                if result.get("claim_url"):
                    print(f"\n⚠️  Verify ownership: {result['claim_url']}")

            # Try to ensure submolt exists and subscribe (don't crash on failure)
            try:
                ensure_submolt_exists(profile["submolt"])
                subscribe_to_submolt(profile["submolt"])
            except Exception as e:
                print(f"Note: Could not set up submolt: {e}")

            print(f"""
✓ Agent '{profile['name']}' is ready!

Run your agent via OpenClaw:
  openclaw agent --message "Start exploring biology" --session-id scienceclaw

Or for a specific task:
  openclaw agent --message "Search PubMed for CRISPR delivery methods and share findings on Moltbook"
""")
        elif result.get("skipped"):
            print(f"""
✓ Agent '{profile['name']}' profile created!

Note: Moltbook registration was skipped (network issue).
The agent will self-register on first run.

Run your agent via OpenClaw:
  openclaw agent --message "Start exploring biology" --session-id scienceclaw
""")
        else:
            print(f"Note: Could not register with Moltbook: {result.get('error', result)}")
            print("""
Your agent profile is ready. It will attempt to register on first run.

Run your agent via OpenClaw:
  openclaw agent --message "Start exploring biology" --session-id scienceclaw
""")

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

    # Create profile (optionally pre-selected preset from --profile)
    profile = create_agent_profile(profile_preset=args.profile)

    # Display and confirm
    display_profile(profile)

    print("\n" + "-" * 60)
    confirm = input("Create this agent? (y/n) [y]: ").strip().lower()
    if confirm == 'n':
        print("Setup cancelled.")
        return

    # Save profile
    save_profile(profile)

    # Generate and save SOUL.md for OpenClaw
    save_soul_md(profile)

    # Register with Moltbook
    result = register_with_moltbook(profile, interactive=True)

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
        try:
            is_founder = ensure_submolt_exists(profile["submolt"])
            subscribe_to_submolt(profile["submolt"])
        except Exception as e:
            print(f"Note: Could not set up submolt: {e}")

        print(f"""
{'=' * 60}
  Setup Complete!
{'=' * 60}

Your agent '{profile['name']}' is ready to explore science!

Next steps:
  1. Complete human verification (if not done)
  2. Run your agent via OpenClaw:

     openclaw agent --message "Start exploring biology" --session-id scienceclaw

  3. Watch your agent explore and share discoveries!

Files created:
  • {PROFILE_FILE} - Your agent's profile
  • {CONFIG_FILE} - Moltbook credentials
  • {SOUL_FILE} - Agent personality for OpenClaw

Happy exploring! 🔬🧬🦀
""")
    elif result.get("skipped"):
        print(f"""
{'=' * 60}
  Setup Complete!
{'=' * 60}

Your agent '{profile['name']}' profile is ready!

Note: Moltbook registration was skipped due to network issues.
The agent will self-register on its first run.

Run your agent via OpenClaw:
  openclaw agent --message "Start exploring biology" --session-id scienceclaw

Files created:
  • {PROFILE_FILE} - Your agent's profile
  • {SOUL_FILE} - Agent personality for OpenClaw

Happy exploring! 🔬🧬🦀
""")
    else:
        print(f"\nRegistration issue: {result.get('error', result)}")
        print("Your profile has been saved. The agent will attempt to register on first run.")
        print(f"""
Run your agent via OpenClaw:
  openclaw agent --message "Start exploring biology" --session-id scienceclaw
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
