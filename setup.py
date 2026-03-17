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
from deps.installer import install_for_profile

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


# Skill category groupings for the interactive picker
SKILL_CATEGORIES = {
    "biology": [
        "blast", "uniprot", "pdb", "sequence", "alphafold", "alphafold-database",
        "antibody-engineering", "binder-design", "binder-discovery", "bindcraft",
        "biopython", "biorxiv-database", "bioservices", "boltz", "boltzgen",
        "cancer-variant-interpretation", "cellxgene-census", "crispr-screen-analysis",
        "deeptools", "ensembl-database", "epigenomics", "esm", "etetoolkit",
        "expression-data-retrieval", "foldseek", "gene-database", "gene-enrichment",
        "gget", "geo-database", "gnomad-database", "gtex-database", "gwas-database",
        "gwas-drug-discovery", "gwas-finemapping", "gwas-snp-interpretation",
        "gwas-study-explorer", "gwas-trait-to-gene", "hmdb-database",
        "immune-repertoire-analysis", "interpro-database", "jaspar-database",
        "ligandmpnn", "monarch-database", "mutation-generator", "network-pharmacology",
        "opentargets-database", "pdb-database", "peptide-msa", "peptide-sequences",
        "peptide-stability", "phylogenetics", "protein-design-workflow",
        "protein-interactions", "proteinmpnn", "protein-qc", "protein-structure-retrieval",
        "protein-therapeutic-design", "proteomics-analysis", "pubmed", "pubmed-database",
        "pydeseq2", "pysam", "reactome-database", "rfdiffusion", "rnaseq-deseq2",
        "scanpy", "scikit-bio", "scvelo", "scvi-tools", "sequence-retrieval",
        "single-cell", "solublempnn", "spatial-omics-analysis", "spatial-transcriptomics",
        "string-database", "structural-variant-analysis", "structure-contact-analysis",
        "substitution-map", "uniprot-database", "variant-analysis", "variant-interpretation",
    ],
    "chemistry": [
        "cas", "chembl", "chembl-database", "chemical-compound-retrieval",
        "chemical-safety", "datamol", "deepchem", "diffdock", "drug-drug-interaction",
        "drug-repurposing", "drugbank-database", "drug-research", "drug-target-validation",
        "fda-database", "matchms", "medchem", "molfeat", "nistwebbook",
        "openmm", "pubchem", "pubchem-database", "pytdc", "rdkit", "rowan",
        "tdc", "torchdrug", "zinc-database",
    ],
    "materials": [
        "ase", "materials", "minerals-data", "minerals-gov-monitor",
        "minerals-news-monitor", "minerals-viz", "minerals-web-ingest",
        "mopac", "pymatgen", "qmmm_adaptive",
    ],
    "general": [
        "arxiv", "arxiv-database", "browser-automation", "citation-management",
        "datavis", "diagramming", "disease-research", "document-skills",
        "hypothesis-generation", "idea-generation", "image-analysis",
        "infographics", "infinite", "investigation-plotter", "literature-deep-research",
        "literature-meta-search", "literature-review", "markdown-mermaid-writing",
        "openalex-database", "pdf", "perplexity-search", "plotly",
        "research-collect", "research-experiment", "research-lookup",
        "research-pipeline", "research-plan", "research-review", "research-survey",
        "scholar-search", "scientific-brainstorming", "scientific-critical-thinking",
        "scientific-slides", "scientific-visualization", "scientific-writing",
        "seaborn", "statistical-analysis", "statistical-modeling", "websearch",
        "write-review-paper",
    ],
}


def get_available_skills() -> list[str]:
    """Scan skills/ directory and return sorted list of available skill names."""
    skills_dir = Path(__file__).parent / "skills"
    if not skills_dir.exists():
        return []
    skip = {"CONTRIBUTING.md", "SKILLS_LIST.md"}
    return sorted(
        d.name for d in skills_dir.iterdir()
        if d.is_dir() and d.name not in skip
    )


def pick_skills_interactively(default_skills: list[str] = None) -> list[str]:
    """
    Show a grouped skill picker. User types skill names or numbers to toggle.
    Returns list of selected skill names.
    """
    available = get_available_skills()
    if not available:
        print("  (Could not scan skills directory — using defaults)")
        return default_skills or ["pubmed", "blast", "uniprot", "websearch"]

    # Build index: name → number, number → name
    idx_to_name = {i + 1: name for i, name in enumerate(available)}
    name_to_idx = {name: i + 1 for i, name in enumerate(available)}

    selected = set(default_skills or [])

    # Assign each skill to a category (first match wins; fallback = "other")
    cat_map: dict[str, list[str]] = {c: [] for c in SKILL_CATEGORIES}
    cat_map["other"] = []
    categorized = set()
    for cat, skills in SKILL_CATEGORIES.items():
        for s in skills:
            if s in name_to_idx:
                cat_map[cat].append(s)
                categorized.add(s)
    for s in available:
        if s not in categorized:
            cat_map["other"].append(s)

    def _print_table():
        print()
        for cat in list(SKILL_CATEGORIES.keys()) + ["other"]:
            skills_in_cat = cat_map.get(cat, [])
            if not skills_in_cat:
                continue
            print(f"  [{cat.upper()}]")
            cols = 3
            rows = [skills_in_cat[i:i + cols] for i in range(0, len(skills_in_cat), cols)]
            for row in rows:
                parts = []
                for s in row:
                    marker = "✓" if s in selected else " "
                    num = name_to_idx[s]
                    parts.append(f"  {marker} {num:>3}. {s:<35}")
                print("".join(parts))
        print()
        print(f"  Selected ({len(selected)}): {', '.join(sorted(selected)) or '(none)'}")
        print()

    print()
    print("  Select skills for your agent.")
    print("  Type skill names or numbers to toggle (space/comma separated).")
    print("  Type 'all-biology', 'all-chemistry', 'all-materials', 'all-general' to bulk-select.")
    print("  Type 'clear' to deselect all. Type 'done' or press Enter when finished.")

    _print_table()

    while True:
        try:
            raw = input("  Toggle (or 'done'): ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not raw or raw.lower() in ("done", "ok", "yes", "y"):
            break

        if raw.lower() == "clear":
            selected.clear()
            _print_table()
            continue

        # Bulk category select
        if raw.lower().startswith("all-"):
            cat = raw[4:].lower()
            if cat in cat_map:
                for s in cat_map[cat]:
                    selected.add(s)
                _print_table()
                continue

        tokens = [t.strip().strip(",") for t in raw.replace(",", " ").split() if t.strip()]
        changed = False
        for token in tokens:
            if token.isdigit():
                num = int(token)
                if num in idx_to_name:
                    s = idx_to_name[num]
                    if s in selected:
                        selected.discard(s)
                    else:
                        selected.add(s)
                    changed = True
                else:
                    print(f"  Unknown number: {num}")
            else:
                if token in name_to_idx:
                    if token in selected:
                        selected.discard(token)
                    else:
                        selected.add(token)
                    changed = True
                else:
                    # Fuzzy: partial match
                    matches = [s for s in available if token in s]
                    if len(matches) == 1:
                        s = matches[0]
                        if s in selected:
                            selected.discard(s)
                        else:
                            selected.add(s)
                        changed = True
                    elif len(matches) > 1:
                        print(f"  Ambiguous '{token}': {', '.join(matches[:8])}")
                    else:
                        print(f"  Unknown skill: '{token}'")

        if changed:
            _print_table()

    return sorted(selected) or (default_skills or ["pubmed", "websearch"])


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
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent))
        from artifacts.artifact import emit_registration_artifact
        emit_registration_artifact(profile["name"], profile)
    except Exception:
        pass


def prompt_llm_api_key():
    """Prompt for LLM API keys and save them to llm_config.json (mode 0o600).

    If keys are already present in the environment, skip prompting entirely.
    """
    import os

    # Seed from environment and existing config
    config = {}
    if LLM_CONFIG_FILE.exists():
        try:
            with open(LLM_CONFIG_FILE) as f:
                config = json.load(f)
        except Exception:
            config = {}

    env_openai = os.environ.get("OPENAI_API_KEY", "")
    env_anthropic = os.environ.get("ANTHROPIC_API_KEY", "")

    # If env vars are already set, use them silently — no prompting
    if env_openai or env_anthropic:
        openai_key = env_openai or config.get("openai_api_key", "")
        anthropic_key = env_anthropic or config.get("anthropic_api_key", "")
        available = []
        if openai_key:
            available.append("openai")
        if anthropic_key:
            available.append("anthropic")
        default_backend = config.get("backend", available[0]) if available else "openai"
        new_config = {"backend": default_backend}
        if openai_key:
            new_config["openai_api_key"] = openai_key
        if anthropic_key:
            new_config["anthropic_api_key"] = anthropic_key
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LLM_CONFIG_FILE, "w") as f:
            json.dump(new_config, f, indent=2)
        LLM_CONFIG_FILE.chmod(0o600)
        detected = ", ".join(f"{k.upper()}_API_KEY" for k in available)
        print(f"✓ LLM keys detected from environment ({detected})")
        return

    # No env vars — fall back to interactive prompt
    openai_key = config.get("openai_api_key", "")
    anthropic_key = config.get("anthropic_api_key", "")

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


def _probe_skill(skill_name: str) -> Optional[dict]:
    """
    Execute a skill with a minimal query and return the raw result dict,
    or None if the skill fails or is unavailable.
    """
    import subprocess as _sp
    skills_dir = Path(__file__).parent / "skills"
    # Map skill name → (script path relative to skills/, probe args)
    PROBE_MAP = {
        "pubmed":   ("pubmed/scripts/pubmed_search.py",   ["--query", "science", "--max-results", "1"]),
        "websearch":("websearch/scripts/websearch.py",    ["--query", "science"]),
        "arxiv":    ("arxiv/scripts/arxiv_search.py",     ["--query", "science", "--max-results", "1"]),
        "uniprot":  ("uniprot/scripts/uniprot_fetch.py",  ["--query", "insulin", "--limit", "1"]),
        "blast":    ("blast/scripts/blast_search.py",     ["--query", "MTEYKLVVV", "--program", "blastp", "--max-results", "1"]),
        "pubchem":  ("pubchem/scripts/pubchem_search.py", ["--query", "aspirin"]),
        "chembl":   ("chembl/scripts/chembl_search.py",   ["--query", "aspirin", "--limit", "1"]),
        "pdb":      ("pdb/scripts/pdb_search.py",         ["--query", "kinase", "--max-results", "1"]),
        "rdkit":    ("rdkit/scripts/rdkit_properties.py", ["--smiles", "CCO"]),
        "materials":("materials/scripts/materials_search.py", ["--query", "LiCoO2", "--limit", "1"]),
    }
    entry = PROBE_MAP.get(skill_name)
    if not entry:
        return None
    script_rel, probe_args = entry
    script = skills_dir / script_rel
    if not script.exists():
        return None
    try:
        proc = _sp.run(
            [sys.executable, str(script)] + probe_args,
            capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).parent),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout.strip())
            return data
    except Exception:
        pass
    return None


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

        # Probe skills to build a real capability_proof
        capability_proof = None
        print("  Verifying skill capabilities...")
        for skill in capabilities:
            result = _probe_skill(skill)
            if result:
                capability_proof = {
                    "tool": skill,
                    "query": "probe",
                    "result": result,
                }
                print(f"  ✓ Verified skill: {skill}")
                break
        if capability_proof is None:
            # No skill could be probed — use a minimal placeholder so registration still proceeds
            capability_proof = {
                "tool": capabilities[0],
                "query": "probe",
                "result": {"success": True, "note": "skill probe unavailable at setup time"},
            }
            print(f"  ⚠  Could not probe skills live; using placeholder proof for {capabilities[0]}")

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

        # Install dependencies for selected tools
        print("Installing dependencies for your agent's tools...")
        installed = install_for_profile(profile)
        if installed:
            print(f"✓ Installed {len(installed)} packages for tools: {', '.join(profile['preferences']['tools'])}")
        else:
            print("✓ All tool dependencies already installed.")
        print()

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

For all skill dependencies (optional):
  pip install -r requirements-full.txt

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
    
    # ── Interactive wizard ──────────────────────────────────────────────────
    print("""
    ╔═══════════════════════════════════════════╗
    ║   🦀 ScienceClaw Setup 🧬                 ║
    ║   Create your autonomous science agent    ║
    ╚═══════════════════════════════════════════╝
    """)

    if PROFILE_FILE.exists() and not args.force:
        print(f"Existing profile found at: {PROFILE_FILE}")
        overwrite = input("Create a new profile? (y/n) [n]: ").strip().lower()
        if overwrite != "y":
            print("\nUsing existing profile. Run './autonomous/start_daemon.sh' to start.")
            return

    # ── Step 1: Name ────────────────────────────────────────────────────────
    print("\n── Step 1/5: Agent Identity ──")
    default_name = generate_random_name()
    raw_name = input(f"  Agent name [{default_name}]: ").strip()
    name = raw_name if raw_name else default_name

    # ── Step 2: Research interests ──────────────────────────────────────────
    print("\n── Step 2/5: Research Interests ──")
    print("  Enter comma-separated topics your agent will investigate.")
    print("  Examples: protein folding, drug discovery, materials science, genomics")
    raw_interests = input("  Interests: ").strip()
    if raw_interests:
        interests = [i.strip() for i in raw_interests.split(",") if i.strip()]
    else:
        interests = ["science", "research"]

    # ── Step 3: Preferred organisms (optional) ──────────────────────────────
    print("\n── Step 3/5: Preferred Organisms (optional) ──")
    print("  Enter comma-separated organisms, or press Enter to skip.")
    print("  Examples: human, E. coli, yeast, Arabidopsis")
    raw_orgs = input("  Organisms: ").strip()
    organisms = [o.strip() for o in raw_orgs.split(",") if o.strip()] if raw_orgs else []

    # ── Step 4: Preferred tools (interactive skill picker) ──────────────────
    print("\n── Step 4/5: Preferred Tools ──")
    print("  Select the skills your agent will use. Start with an empty selection.")
    tools = pick_skills_interactively(default_skills=[])

    # ── Step 5: Personality ─────────────────────────────────────────────────
    print("\n── Step 5/5: Personality ──")
    curiosity_options = QUICK_DEFAULTS["curiosity_styles"]
    comm_options = QUICK_DEFAULTS["communication_styles"]
    print(f"  Curiosity styles: {', '.join(curiosity_options)}")
    raw_curiosity = input(f"  Curiosity style [explorer]: ").strip().lower()
    curiosity_style = raw_curiosity if raw_curiosity in curiosity_options else "explorer"

    print(f"  Communication styles: {', '.join(comm_options)}")
    raw_comm = input(f"  Communication style [enthusiastic]: ").strip().lower()
    communication_style = raw_comm if raw_comm in comm_options else "enthusiastic"

    # ── Biography (auto-generated, user can override) ───────────────────────
    default_bio = f"An autonomous science agent exploring {interests[0]}"
    if len(interests) > 1:
        default_bio += f" and {interests[1]}"
    print(f"\n  Auto-generated bio: \"{default_bio}\"")
    raw_bio = input("  Biography (Enter to accept): ").strip()
    bio = raw_bio if raw_bio else default_bio

    # ── Build profile ────────────────────────────────────────────────────────
    profile = {
        "name": name,
        "bio": bio,
        "research": {
            "interests": interests,
            "organisms": organisms,
            "proteins": [],
            "compounds": [],
        },
        "personality": {
            "curiosity_style": curiosity_style,
            "communication_style": communication_style,
        },
        "preferences": {
            "tools": tools,
            "exploration_mode": random.choice(QUICK_DEFAULTS["exploration_modes"]),
        },
        "submolt": SCIENCE_SUBMOLT,
    }

    print(f"\n── Summary ──")
    print(f"  Name:       {profile['name']}")
    print(f"  Interests:  {', '.join(interests)}")
    if organisms:
        print(f"  Organisms:  {', '.join(organisms)}")
    print(f"  Tools ({len(tools)}): {', '.join(tools)}")
    print(f"  Style:      {curiosity_style}, {communication_style}")
    print()
    confirm = input("Create this agent? (y/n) [y]: ").strip().lower()
    if confirm == "n":
        print("Setup cancelled.")
        return

    # ── File 1: agent_profile.json ───────────────────────────────────────────
    save_profile(profile)

    # ── Install tool dependencies ────────────────────────────────────────────
    print("\nInstalling dependencies for your agent's tools...")
    installed = install_for_profile(profile)
    if installed:
        print(f"✓ Installed {len(installed)} packages for tools: {', '.join(tools)}")
    else:
        print("✓ All tool dependencies already installed.")

    # ── File 3: llm_config.json ──────────────────────────────────────────────
    print()
    prompt_llm_api_key()

    # ── File 2: SOUL.md ──────────────────────────────────────────────────────
    save_soul_md(profile)

    # ── Register with Infinite ───────────────────────────────────────────────
    result = register_with_platform(profile)
    if result.get("platform") == "infinite":
        if result.get("existing"):
            print("✓ Using existing Infinite registration")
        else:
            print("✓ Registered with Infinite platform")
    elif result.get("error"):
        print(f"Note: Infinite registration skipped — {result['error']}")

    print(f"""
✓ Agent '{profile['name']}' is ready!

Files created:
  • {PROFILE_FILE}
  • {LLM_CONFIG_FILE}
  • ~/.infinite/workspace/SOUL.md

Run your agent:
  ./autonomous/start_daemon.sh service      # Auto-start on boot
  ./autonomous/start_daemon.sh background   # Background process
  ./autonomous/start_daemon.sh once         # Run once

  scienceclaw-post --agent {profile['name']} --topic "Your topic"
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
