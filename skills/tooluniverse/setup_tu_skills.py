#!/usr/bin/env python3
"""
Fetch all 54 ToolUniverse research workflow skills from GitHub and scaffold
them as scienceclaw skills under scienceclaw/skills/.

Each skill gets:
  scienceclaw/skills/tu-{name}/
    SKILL.md        — pulled from ToolUniverse GitHub
    scripts/run.py  — Python wrapper calling tu.run() for that workflow

Run once:
    cd scienceclaw
    python3 skills/tooluniverse/setup_tu_skills.py
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

SKILLS_BASE = Path(__file__).resolve().parents[1]   # scienceclaw/skills/
TU_SKILLS_RAW = (
    "https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/{name}/SKILL.md"
)

TU_RESEARCH_SKILLS = [
    "tooluniverse-adverse-event-detection",
    "tooluniverse-antibody-engineering",
    "tooluniverse-binder-discovery",
    "tooluniverse-cancer-variant-interpretation",
    "tooluniverse-chemical-compound-retrieval",
    "tooluniverse-chemical-safety",
    "tooluniverse-clinical-guidelines",
    "tooluniverse-clinical-trial-design",
    "tooluniverse-clinical-trial-matching",
    "tooluniverse-crispr-screen-analysis",
    "tooluniverse-disease-research",
    "tooluniverse-drug-drug-interaction",
    "tooluniverse-drug-repurposing",
    "tooluniverse-drug-research",
    "tooluniverse-drug-target-validation",
    "tooluniverse-epigenomics",
    "tooluniverse-expression-data-retrieval",
    "tooluniverse-gene-enrichment",
    "tooluniverse-gwas-drug-discovery",
    "tooluniverse-gwas-finemapping",
    "tooluniverse-gwas-snp-interpretation",
    "tooluniverse-gwas-study-explorer",
    "tooluniverse-gwas-trait-to-gene",
    "tooluniverse-image-analysis",
    "tooluniverse-immune-repertoire-analysis",
    "tooluniverse-immunotherapy-response-prediction",
    "tooluniverse-infectious-disease",
    "tooluniverse-literature-deep-research",
    "tooluniverse-metabolomics",
    "tooluniverse-metabolomics-analysis",
    "tooluniverse-multi-omics-integration",
    "tooluniverse-multiomic-disease-characterization",
    "tooluniverse-network-pharmacology",
    "tooluniverse-pharmacovigilance",
    "tooluniverse-phylogenetics",
    "tooluniverse-polygenic-risk-score",
    "tooluniverse-precision-medicine-stratification",
    "tooluniverse-precision-oncology",
    "tooluniverse-protein-interactions",
    "tooluniverse-protein-structure-retrieval",
    "tooluniverse-protein-therapeutic-design",
    "tooluniverse-proteomics-analysis",
    "tooluniverse-rare-disease-diagnosis",
    "tooluniverse-rnaseq-deseq2",
    "tooluniverse-sequence-retrieval",
    "tooluniverse-single-cell",
    "tooluniverse-spatial-omics-analysis",
    "tooluniverse-spatial-transcriptomics",
    "tooluniverse-statistical-modeling",
    "tooluniverse-structural-variant-analysis",
    "tooluniverse-systems-biology",
    "tooluniverse-target-research",
    "tooluniverse-variant-analysis",
    "tooluniverse-variant-interpretation",
]


def skill_slug(tu_name):
    """tu-adverse-event-detection from tooluniverse-adverse-event-detection"""
    return "tu-" + tu_name.replace("tooluniverse-", "", 1)


def make_run_script(workflow_name):
    """Generate the run.py wrapper for a given workflow name."""
    lines = [
        "#!/usr/bin/env python3",
        '"""',
        "ToolUniverse workflow: " + workflow_name,
        "",
        "Calls the ToolUniverse AgenticTool for this workflow and returns JSON output.",
        "Requires: pip install tooluniverse",
        "",
        "Usage:",
        '    python3 run.py --query "Your research question or input"',
        '    python3 run.py --query "Alzheimer disease" --format summary',
        '"""',
        "",
        "import argparse",
        "import json",
        "import sys",
        "",
        "",
        'WORKFLOW = "' + workflow_name + '"',
        "",
        "",
        "def build_parser():",
        "    parser = argparse.ArgumentParser(",
        '        description="Run the ToolUniverse \'" + WORKFLOW + "\' research workflow.",',
        "    )",
        '    parser.add_argument("--query", "-q", required=True, help="Research query or input")',
        "    parser.add_argument(",
        '        "--format", "-f", choices=["json", "summary"], default="json",',
        '        help="Output format",',
        "    )",
        "    parser.add_argument(",
        '        "--no-cache", action="store_true", help="Disable result caching",',
        "    )",
        "    return parser",
        "",
        "",
        "def to_serializable(obj):",
        "    if isinstance(obj, dict):",
        "        return {k: to_serializable(v) for k, v in obj.items()}",
        "    if isinstance(obj, list):",
        "        return [to_serializable(v) for v in obj]",
        "    try:",
        "        json.dumps(obj)",
        "        return obj",
        "    except (TypeError, ValueError):",
        "        return str(obj)",
        "",
        "",
        "def main():",
        "    parser = build_parser()",
        "    args = parser.parse_args()",
        "",
        "    try:",
        "        from tooluniverse import ToolUniverse",
        "    except ImportError:",
        '        print("Error: tooluniverse is not installed. Run: pip install tooluniverse", file=sys.stderr)',
        "        sys.exit(1)",
        "",
        "    tu = ToolUniverse()",
        "    tu.load_tools()",
        "",
        "    try:",
        "        result = tu.run(",
        '            {"name": WORKFLOW, "arguments": {"query": args.query}},',
        "            use_cache=not args.no_cache,",
        "        )",
        "    except Exception as exc:",
        '        error = {"error": str(exc), "workflow": WORKFLOW, "query": args.query}',
        "        print(json.dumps(error, indent=2))",
        "        sys.exit(1)",
        "",
        "    safe = to_serializable(result)",
        '    if args.format == "summary":',
        "        if isinstance(safe, str):",
        "            print(safe[:3000])",
        "        else:",
        "            print(json.dumps(safe, indent=2)[:3000])",
        "    else:",
        "        print(json.dumps(safe, indent=2))",
        "",
        "",
        'if __name__ == "__main__":',
        "    main()",
        "",
    ]
    return "\n".join(lines)


def fetch_skill_md(tu_name):
    url = TU_SKILLS_RAW.format(name=tu_name)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as exc:
        print(f"  WARNING: could not fetch {url}: {exc}", file=sys.stderr)
        return None


def scaffold_skill(tu_name, skill_md_content):
    slug = skill_slug(tu_name)
    skill_dir = SKILLS_BASE / slug
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    display_name = slug.replace("tu-", "").replace("-", " ").title()

    # SKILL.md
    if skill_md_content:
        frontmatter = (
            "---\n"
            "name: " + slug + "\n"
            "description: ToolUniverse workflow — " + display_name + "\n"
            "source: https://github.com/mims-harvard/ToolUniverse/tree/main/skills/" + tu_name + "\n"
            "metadata:\n"
            "---\n\n"
        )
        (skill_dir / "SKILL.md").write_text(frontmatter + skill_md_content, encoding="utf-8")
    else:
        (skill_dir / "SKILL.md").write_text(
            "---\nname: " + slug + "\ndescription: ToolUniverse workflow — " + display_name + "\nmetadata:\n---\n\n"
            "# " + display_name + "\n\nToolUniverse research workflow.\n"
            "See: https://github.com/mims-harvard/ToolUniverse/tree/main/skills/" + tu_name + "\n",
            encoding="utf-8",
        )

    # scripts/run.py
    run_py = scripts_dir / "run.py"
    run_py.write_text(make_run_script(tu_name), encoding="utf-8")
    run_py.chmod(0o755)

    return skill_dir


def main():
    print("Scaffolding " + str(len(TU_RESEARCH_SKILLS)) + " ToolUniverse skills into " + str(SKILLS_BASE) + "/")
    print()

    created = []
    updated = []

    for tu_name in TU_RESEARCH_SKILLS:
        slug = skill_slug(tu_name)
        skill_dir = SKILLS_BASE / slug
        action = "updated" if skill_dir.exists() else "created"

        print("  [" + action + "] " + slug + " ...", end=" ", flush=True)
        md = fetch_skill_md(tu_name)
        scaffold_skill(tu_name, md)
        print("OK" if md else "OK (no remote SKILL.md)")

        if action == "created":
            created.append(slug)
        else:
            updated.append(slug)

    total = len(created) + len(updated)
    print("\nDone. " + str(total) + " skills scaffolded (" + str(len(created)) + " new, " + str(len(updated)) + " updated).")
    print("\nNext: pip install tooluniverse")

    manifest_path = SKILLS_BASE / "tooluniverse" / "tu_skills_manifest.json"
    manifest_path.write_text(
        json.dumps({"skills": [skill_slug(n) for n in TU_RESEARCH_SKILLS]}, indent=2),
        encoding="utf-8",
    )
    print("Manifest: " + str(manifest_path))


if __name__ == "__main__":
    main()
