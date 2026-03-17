---
name: scienceclaw-watch
description: Run a live multi-agent scientific collaboration session and return a full summary when complete. Multiple specialised agents work in parallel, challenge each other's findings, and generate figures. Results and figures are saved to disk and a summary is returned to chat.
metadata: {"openclaw": {"emoji": "👁️", "requires": {"bins": ["python3"]}, "primaryEnv": "ANTHROPIC_API_KEY"}}
---

# ScienceClaw: Watch (Multi-Agent Collaboration Session)

Run a parallel multi-agent collaboration session on a scientific topic. Agents work simultaneously, share findings, agree or challenge each other, and produce a rich synthesis with figures. Returns a full summary to chat when the session completes.

## When to use

Use this skill when the user asks to:
- "Watch agents investigate…"
- Run a multi-agent collaboration (not just a single agent)
- Get richer, more contested findings where agents push back on each other
- Generate figures or visual outputs alongside findings
- Run a thorough parallel investigation with 2–5 agents

Prefer `scienceclaw-investigate` if the user just wants findings posted to Infinite quickly.
Use this skill when they want depth, parallel perspectives, and saved artefacts.

## How it works (Option A: fire-and-forget)

The session runs synchronously with `--no-dashboard` so output is fully captured.
Results are written to a timestamped output directory. Once complete, the skill reads
`session_summary.json` and returns a formatted summary to the user in chat.

## How to run

```bash
SCIENCECLAW_DIR="${SCIENCECLAW_DIR:-$HOME/LAMM/scienceclaw}"
TOPIC="<TOPIC>"
N_AGENTS=3
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$SCIENCECLAW_DIR/run_exports/watch_${TIMESTAMP}"

cd "$SCIENCECLAW_DIR"
source .venv/bin/activate 2>/dev/null || true

python3 bin/scienceclaw-watch \
  "$TOPIC" \
  --agents "$N_AGENTS" \
  --output "$OUTPUT_DIR" \
  --no-dashboard \
  --timeout 60
```

Then read the summary:

```bash
cat "$OUTPUT_DIR/session_summary.json"
```

### Parameters

- `TOPIC` — the research topic (required). Use the user's exact phrasing.
- `--agents N` — number of agents to spawn (1–5, default: 3). Use 2 for speed, 4–5 for depth.
- `--output DIR` — where to save results and figures. Always set this to a timestamped path under `run_exports/` so results are organised.
- `--no-dashboard` — **always include this**. Disables the Rich live UI so output is captured cleanly.
- `--timeout SEC` — per-tool timeout in seconds (default: 45). Increase to 90–120 for complex topics.
- `--session-id` — optional custom session ID for tracking.

### Example invocations

```bash
# Standard 3-agent session
cd ~/LAMM/scienceclaw && python3 bin/scienceclaw-watch \
  "BACE1 inhibitors for Alzheimer's disease" \
  --agents 3 --no-dashboard \
  --output run_exports/watch_$(date +%Y%m%d_%H%M%S) \
  --timeout 60

# Quick 2-agent session
cd ~/LAMM/scienceclaw && python3 bin/scienceclaw-watch \
  "ibrutinib resistance in CLL" \
  --agents 2 --no-dashboard \
  --output run_exports/watch_$(date +%Y%m%d_%H%M%S) \
  --timeout 45

# Deep 5-agent session with longer timeout
cd ~/LAMM/scienceclaw && python3 bin/scienceclaw-watch \
  "multi-target kinase inhibitors for glioblastoma" \
  --agents 5 --no-dashboard \
  --output run_exports/watch_$(date +%Y%m%d_%H%M%S) \
  --timeout 120
```

## Reading the results

After the session completes, parse `session_summary.json` in the output directory.
It contains:

```json
{
  "topic": "...",
  "agents": ["Agent1", "Agent2", "Agent3"],
  "findings": [{"text": "...", "sources": ["AgentName"]}],
  "figures": [{"path": "..."}],
  "challenges": 4,
  "agreements": 7,
  "output_dir": "..."
}
```

## Workspace context injection

Before running, check if the user's workspace memory contains project context:
- Read `memory.md` in the workspace for stored research focus, organism, compound, or target
- If found, append context to the topic string:
  e.g. `"BACE1 inhibitors [project context: NSCLC, BBB penetration focus]"`

## After running

Report back to the user with a structured summary:
- **Agents** that participated (list them)
- **Key findings** — top 5, with the agent that found each one: `[AgentName] finding text`
- **Agreements** and **challenges** count (e.g. "7 agreements, 4 challenges between agents")
- **Figures generated** — list file paths or names
- **Results saved to** — the output directory path
- Offer follow-up options:
  - "Want me to post the synthesis to Infinite?" → use `scienceclaw-post`
  - "Want to investigate a specific finding deeper?" → use `scienceclaw-investigate`
