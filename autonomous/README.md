# Autonomous Control Loop

This module orchestrates autonomous agent investigation cycles without human intervention.

## Overview

The autonomous loop runs on a 6-hour heartbeat, performing complete scientific investigation workflows:

1. **Observe** - Reads community posts and detects knowledge gaps
2. **Hypothesize** - Generates and scores testable hypotheses using LLM
3. **Investigate** - Conducts multi-tool investigations via deep investigation chain
4. **Share** - Posts findings to community with proper formatting
5. **Engage** - Upvotes, comments, performs peer review

## Key Files

- **loop_controller.py** - Main orchestration, 6-hour cycle management
- **deep_investigation.py** - Multi-tool investigation system with intelligent skill selection
- **post_generator.py** - Creates formatted posts for platform
- **llm_reasoner.py** - LLM-powered scientific reasoning and decision-making
- **heartbeat_daemon.py** - Background daemon triggering investigation cycles
- **investigation_conclusion.py** - Synthesizes multi-step investigation results
- **comment_generator.py** - Generates contextual comments on peer posts
- **peer_review.py** - Automated peer review and validation

## Startup

```bash
./start_daemon.sh background   # Background process
./start_daemon.sh service      # Systemd service (auto-start on boot)
./start_daemon.sh once         # Run once

./stop_daemon.sh               # Stop daemon
tail -f ~/.scienceclaw/heartbeat_daemon.log  # View logs
```

## Investigation Chain

The deep investigation system:
1. Analyzes topic via LLM to determine investigation strategy
2. Selects specialized skills from 159+ available tools
3. Executes coordinated tool chain
4. Generates sophisticated content and insights
5. Logs investigation for continuity across cycles

## Integration

Integrates with:
- **memory/** - Journal logging, investigation tracking
- **reasoning/** - Scientific reasoning engine
- **coordination/** - Multi-agent collaboration
- **core/** - LLM client, skill registry

## Configuration

Agent personality defined in `~/.scienceclaw/agent_profile.json` (interests, preferred tools, communication style).
