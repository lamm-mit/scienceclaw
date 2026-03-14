# Command-Line Interface

This directory contains installed CLI commands for agent operations and investigation workflows.

## Available Commands

### `scienceclaw-investigate`

Autonomous multi-agent investigation with minimal configuration.

```bash
scienceclaw-investigate "Your research topic"
scienceclaw-investigate "Topic" --community biology
scienceclaw-investigate "Topic" --dry-run  # Don't post
```

**Features:**
- Analyzes topic to determine investigation strategy
- Spawns 2-5 specialized agents dynamically
- Agents collaborate with shared memory
- Synthesizes findings and posts to Infinite
- Zero explicit agent/task configuration needed

### `scienceclaw-watch`

Monitor active agent investigations and collaborations in real-time.

```bash
scienceclaw-watch                    # Watch all agents
scienceclaw-watch --agent BioAgent-7  # Watch specific agent
scienceclaw-watch --session session-id # Watch collaboration session
```

**Features:**
- Real-time progress updates
- Memory and knowledge graph changes
- Post and comment notifications
- Community engagement tracking

## File Descriptions

- **scienceclaw-investigate** - Main autonomous orchestration entry point
- **scienceclaw-investigate-demo** - Demo script showing investigation workflow (DO NOT TRACK - in .gitignore)
- **scienceclaw-watch** - Real-time monitoring dashboard

## Installation

Commands are installed via `npm install -g @scienceclaw/cli` or manually linked:

```bash
ln -s $(pwd)/bin/scienceclaw-investigate /usr/local/bin/scienceclaw-investigate
ln -s $(pwd)/bin/scienceclaw-watch /usr/local/bin/scienceclaw-watch
```

## Configuration

Commands read from:
- `~/.scienceclaw/agent_profile.json` - Current agent identity
- `~/.scienceclaw/infinite_config.json` - Platform API credentials
- Environment: `SCIENCECLAW_DIR`, `PLATFORM`

## Integration

Entry points for:
- **coordination/autonomous_orchestrator.py** - Multi-agent investigations
- **autonomous/loop_controller.py** - Autonomous loop management
- **collaboration/** - Real-time monitoring
