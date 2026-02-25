# Contributing Skills to ScienceClaw

This guide explains how to add a new skill to the ScienceClaw catalog. Skills are discovered automatically; follow the structure below and your skill will be available to agents.

---

## 1. Directory Structure

Create a skill directory under `skills/`:

```
skills/
└── your-skill-name/
    ├── SKILL.md              # Required: documentation + metadata
    ├── scripts/
    │   └── your_skill.py     # Required: executable script(s)
    └── requirements.txt      # Optional: pip dependencies
```

---

## 2. SKILL.md

Every skill needs a `SKILL.md` file. Use YAML frontmatter for metadata:

```markdown
---
name: your-skill-name
description: One-line description of what the skill does
metadata:
---

# Your Skill Name

Full documentation: parameters, examples, output format.

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Primary input | Required |
| `--max-results` | Limit results | 10 |

## Examples

\`\`\`bash
python3 {baseDir}/scripts/your_skill.py --query "example" --format json
\`\`\`
```

The registry parses `description` from frontmatter; capabilities and keywords from the body. See `skills/pubmed/SKILL.md` for a reference.

---

## 3. Executable Script

- Use **argparse** for CLI arguments.
- Support **`--format json`** for chainability — the executor injects it when not provided.
- **Return JSON** on stdout for structured output; the executor parses it.

```python
#!/usr/bin/env python3
"""Your skill description."""

import argparse
import json
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--format", default="summary", choices=["summary", "json"])
    args = parser.parse_args()

    results = do_work(args.query, args.max_results)

    if args.format == "json":
        print(json.dumps(results))
    else:
        print(format_summary(results))

if __name__ == "__main__":
    main()
```

Output conventions for chainability:

- Put list data in keys like `results`, `papers`, `entries`, `items`, `hits`, `compounds`, or `proteins` so downstream tools can extract it.
- Include `summary`, `message`, or `description` for human-readable summaries.

---

## 4. Optional: Emergent Coordination (ArtifactReactor)

For the **ArtifactReactor** (Mode 4 heartbeat) to react to your skill’s output, add an entry in:

- **`artifacts/artifact.py`** → `SKILL_DOMAIN_MAP`: maps your skill to artifact type(s), e.g. `"your-skill": ["your_artifact_type"]`
- **`artifacts/reactor.py`** → `SKILL_INPUT_MAP`: maps your skill to the primary CLI param and entity type, e.g.  
  `"your-skill": {"param": "query", "entity": "research topic", "hint": "example value"}`

Matching uses schema overlap: `skill.input_schema ∩ artifact.payload_schema`. Expose keys in your JSON that match other skills’ expected params (e.g. `query`, `pmid`, `smiles`, `sequence`).

---

## 5. Optional: Hidden by Default

Skills that require API keys or credentials not bundled with the repo can be hidden:

- Add to `~/.scienceclaw/skill_config.json`: `{"hidden_skills": ["your-skill"]}`
- Or set `SCIENCECLAW_HIDDEN_SKILLS=your-skill,other-skill`
- Default hidden skills include `adaptyv`, `drugbank-database`, `pubchem`, etc.

---

## 6. Test Your Skill

```bash
# Run directly
python3 skills/your-skill/scripts/your_skill.py --query "test" --format json

# Verify discovery (refresh registry)
python3 skill_catalog.py --stats

# Suggest skills for a topic
python3 skill_catalog.py --suggest "your research area"
```

---

## Checklist

- [ ] Directory: `skills/your-skill-name/`
- [ ] `SKILL.md` with YAML frontmatter and `description`
- [ ] `scripts/your_skill.py` with argparse, `--format json`, JSON output
- [ ] `requirements.txt` if external packages needed
- [ ] (Optional) `SKILL_DOMAIN_MAP` and `SKILL_INPUT_MAP` for emergent coordination
