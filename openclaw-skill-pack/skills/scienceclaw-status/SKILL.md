---
name: scienceclaw-status
description: Check the status of a ScienceClaw agent — journal stats, recent investigations, knowledge graph size, and activity summary.
metadata: {"openclaw": {"emoji": "📊", "skillKey": "scienceclaw:status", "requires": {"bins": ["python3"]}, "primaryEnv": "ANTHROPIC_API_KEY"}}
---

# ScienceClaw: Agent Status

Inspect the memory, activity, and health of a ScienceClaw agent.

## When to use

Use this skill when the user asks to:
- Check what a ScienceClaw agent has been working on
- See recent investigations or journal entries
- Review agent activity stats (topics explored, tools used, post count)
- Search an agent's memory for a specific topic
- Get a health check on the ScienceClaw installation

## How to run

Use `bash` to invoke the memory CLI. `SCIENCECLAW_DIR` defaults to `~/scienceclaw` or `~/.scienceclaw/install`.

```bash
SCIENCECLAW_DIR="${SCIENCECLAW_DIR:-$HOME/scienceclaw}"
AGENT=$(python3 -c "import json,pathlib; p=pathlib.Path.home()/'.scienceclaw'/'agent_profile.json'; print(json.loads(p.read_text()).get('name','ScienceAgent'))" 2>/dev/null || echo "ScienceAgent")
cd "$SCIENCECLAW_DIR"
python3 memory_cli stats --agent "$AGENT"
```

### Subcommands

#### Journal stats (default status view)
```bash
python3 memory_cli journal --agent "$AGENT"
```

#### Recent journal entries
```bash
python3 memory_cli journal --agent "$AGENT" --recent 10
```

#### Active investigations
```bash
python3 memory_cli investigations --agent "$AGENT" --active
```

#### All investigated topics
```bash
python3 memory_cli journal --agent "$AGENT" --topics
```

#### Search memory for a topic
```bash
python3 memory_cli graph --agent "$AGENT" --search "CRISPR"
```

#### Full stats summary
```bash
python3 memory_cli stats --agent "$AGENT"
```

### Parameters

- `--agent` — agent name (auto-resolved from `~/.scienceclaw/agent_profile.json` if not provided)
- `--recent N` — show last N journal entries
- `--active` — show only in-progress investigations
- `--search TERM` — search knowledge graph for a term
- `--topics` — list all topics ever investigated

## Resolving the agent name

Always auto-resolve the agent name from the profile before running:

```bash
AGENT=$(python3 -c "
import json, pathlib
p = pathlib.Path.home() / '.scienceclaw' / 'agent_profile.json'
print(json.loads(p.read_text()).get('name', 'ScienceAgent'))
" 2>/dev/null || echo "ScienceAgent")
```

If the user specifies an agent name explicitly, use that instead.

## Workspace context

If the workspace memory (`memory.md`) contains a preferred agent name, use that as the default `--agent` value.

## After running

Report back to the user:
- Agent name and total journal entries
- Number of topics investigated
- Most recent 3–5 topics (if available)
- Any active/in-progress investigations
- Offer to run a deeper search with `scienceclaw-investigate` on any of the listed topics