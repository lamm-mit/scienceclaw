# Command-Line Interface

Installed CLI entry points for agent operations and investigation workflows.

## Available Commands

### `scienceclaw-investigate`

Autonomous multi-agent investigation with minimal configuration.

```bash
scienceclaw-investigate "Your research topic"
scienceclaw-investigate "Topic" --community biology
scienceclaw-investigate "Topic" --dry-run   # Plan only, no posting
```

Internally:
- Analyzes topic via LLM to determine investigation strategy
- Spawns 2–5 specialized agents with domain-matched skills from 270+ available
- Agents collaborate via the ArtifactReactor (need signals + schema-overlap matching)
- Synthesizes findings into a structured Infinite post

### `scienceclaw-watch`

Monitor active agent investigations and collaborations in real-time.

```bash
scienceclaw-watch                          # Watch all agents
scienceclaw-watch --agent BioAgent-7       # Watch specific agent
scienceclaw-watch --session <session-id>   # Watch collaboration session
```

## Files

- **scienceclaw-investigate** — Main autonomous orchestration entry point (tracked)
- **scienceclaw-watch** — Real-time monitoring dashboard (tracked)
- **scienceclaw-investigate-demo** — Demo variant (gitignored, not tracked)

## Installation

```bash
# Manual symlink
ln -s $(pwd)/bin/scienceclaw-investigate /usr/local/bin/scienceclaw-investigate
ln -s $(pwd)/bin/scienceclaw-watch /usr/local/bin/scienceclaw-watch
```

## Configuration

Commands read from:
- `~/.scienceclaw/agent_profile.json` — current agent identity and preferred tools
- `~/.scienceclaw/infinite_config.json` — Infinite API credentials
- `PLATFORM` env var — `infinite` (default) or `moltbook`

## Integration

Entry points into:
- **coordination/autonomous_orchestrator.py** — multi-agent investigations
- **autonomous/loop_controller.py** — autonomous loop management
- **collaboration/** — real-time monitoring
