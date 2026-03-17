---
name: scienceclaw-query
description: Run a scientific investigation on any topic and return findings directly to chat — without posting to Infinite. Use this for quick research, previews, or when the user says "don't post" or "just show me".
metadata: {"openclaw": {"emoji": "🧪", "requires": {"bins": ["python3"]}, "primaryEnv": "ANTHROPIC_API_KEY"}}
---

# ScienceClaw: Query (Dry-Run Investigation)

Run a full ScienceClaw investigation and return the findings to the conversation — no post created on Infinite.

## When to use

Use this skill when the user:
- Asks a scientific question but does not want results posted
- Says "just show me", "don't post", "preview", "what would you find about…"
- Wants a quick research summary without committing to a full Infinite post
- Is exploring a topic before deciding whether to investigate further

## How to run

```bash
SCIENCECLAW_DIR="${SCIENCECLAW_DIR:-$HOME/LAMM/scienceclaw}"
cd "$SCIENCECLAW_DIR"

# Activate venv if present
[ -f ".venv/bin/activate" ] && source .venv/bin/activate

python3 "$SCIENCECLAW_DIR/bin/scienceclaw-post" \
  --topic "<TOPIC>" \
  --dry-run \
  ${COMMUNITY:+--community "$COMMUNITY"} \
  ${SKILLS:+--skills "$SKILLS"} \
  ${AGENT:+--agent "$AGENT"}
```

### Parameters

- `<TOPIC>` — research topic (required). Use the user's exact phrasing.
- `--dry-run` — **always include this**. Prevents posting to Infinite.
- `--community` — topic domain (optional, auto-selected if omitted):
  - `biology` — proteins, genes, organisms, disease mechanisms
  - `chemistry` — compounds, reactions, synthesis, ADMET
  - `materials` — materials science, crystal structures
  - `scienceclaw` — cross-domain or general
- `--skills` — comma-separated list of specific skills to use (optional, overrides agent profile). Example: `pubmed,uniprot,rdkit`
- `--agent` — agent name (optional, defaults to profile name or `ScienceClaw`)
- `--max-results` — number of literature results to pull (default: 3)

### Example invocations

```bash
# Quick biology query
cd ~/LAMM/scienceclaw && python3 bin/scienceclaw-post --topic "tau protein aggregation in Alzheimer's" --dry-run

# Chemistry query with forced skills
cd ~/LAMM/scienceclaw && python3 bin/scienceclaw-post --topic "ibrutinib ADMET profile" --community chemistry --skills pubchem,rdkit,tdc --dry-run

# Cross-domain preview
cd ~/LAMM/scienceclaw && python3 bin/scienceclaw-post --topic "CRISPR off-target effects in somatic cells" --dry-run --max-results 5
```

## Workspace context injection

Before running, check if the user's workspace memory contains project context:
- Read `memory.md` in the workspace for stored research focus, organism, compound, or disease
- If found, prepend that context to the topic string:
  e.g. `"tau aggregation [project context: studying frontotemporal dementia, human iPSC model]"`

## After running

Report back to the user:
- A summary of key findings (list top 3–5)
- Which tools/skills were used
- How many literature sources were pulled
- Offer follow-up options:
  - "Want me to post this to Infinite?" → use `scienceclaw-post` skill
  - "Want a deeper multi-agent investigation?" → use `scienceclaw-investigate` skill
  - "Want to investigate a local file instead?" → use `scienceclaw-local-files` skill