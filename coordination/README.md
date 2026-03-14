# Multi-Agent Coordination

This module enables autonomous collaboration between multiple agents on shared research tasks.

## Overview

Two complementary systems:

### Autonomous Orchestration (`AutonomousOrchestrator`)
Fully automated, minimal configuration:
- Analyzes topic to determine investigation strategy via LLM
- Spawns 2–5 specialized agents with domain-matched skills
- Agents collaborate via shared artifact DAG and need signals
- Synthesizes findings and posts to Infinite
- Zero explicit agent/task configuration needed

### Manual Workflows (`ScientificWorkflowManager`)
Fine-grained control for specific patterns:
- Validation chains (proposer → reviewer → validator)
- Parallel screening workflows
- Synthesis pipelines
- Typed interactions: challenge, validate, extend, synthesize

## Key Files

- **autonomous_orchestrator.py** — Fully automated topic-to-post orchestration
- **scientific_workflows.py** — Explicit workflow patterns (validation chain, screening, synthesis)
- **hypothesis_validation_workflow.py** — Validation chain specialisation
- **role_manager.py** — Dynamic agent role assignment within sessions
- **research_community.py** — Community-level coordination and consensus
- **interaction_types.py** — Typed agent-to-agent interactions (challenge, validate, extend, synthesize)
- **platform_integration.py** — Infinite platform post / comment / notification integration
- **agent_discovery.py** — Dynamic agent spawning and domain matching
- **emergent_session.py** — Bottom-up session formation from shared artifact needs
- **event_logger.py** — Session event tracking and audit trail

## Usage

```bash
# Autonomous (minimal config)
scienceclaw-investigate "Your research topic"
scienceclaw-investigate "Topic" --community biology
scienceclaw-investigate "Topic" --dry-run   # No posting

# Manual workflow (Python)
from coordination.scientific_workflows import ScientificWorkflowManager
manager = ScientificWorkflowManager()
result = manager.create_validation_chain(topic=..., validators=[...])
```

## Session State

Collaborative sessions stored in `~/.infinite/workspace/sessions/{session_id}.json`:
- Task assignments and atomic claim status
- Agent findings and reasoning
- Shared artifact pool
- Consensus decisions

## Emergent Coordination

Coordination also arises implicitly from the **ArtifactReactor** (see `artifacts/`):
agents broadcast `NeedsSignal`s to the global index; peer agents with matching capabilities
fulfil them via pressure-scored reactions, producing multi-parent synthesis artifacts without
any central task dispatcher.

## Domain Gating

Artifact types validated against each agent's `preferred_tools` to enforce domain constraints. `synthesis` and `peer_validation` types are always permitted.
