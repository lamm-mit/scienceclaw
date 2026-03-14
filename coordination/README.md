# Multi-Agent Coordination

This module enables autonomous collaboration between multiple agents on shared research tasks.

## Overview

Two complementary systems for multi-agent research:

### 1. Autonomous Orchestration (AutonomousOrchestrator)
Fully automated, minimal human configuration:
- Analyzes topic to determine investigation strategy
- Spawns 2-5 specialized agents dynamically
- Agents collaborate with shared memory and discussion
- Synthesizes findings and posts results
- **Zero explicit agent/task configuration needed**

### 2. Manual Workflows (Scientific Workflows)
Fine-grained control for specific patterns:
- Validation chains (expert → reviewer → validator)
- Screening workflows (parallel tool application)
- Synthesis pipelines (multi-agent integration)
- Custom interaction types (challenge, validate, extend, synthesize)

## Key Files

- **autonomous_orchestrator.py** - Auto-spawning orchestrator for minimal-config investigations
- **scientific_workflows.py** - Explicit workflow patterns and templates
- **session_manager.py** - Collaborative session lifecycle management
- **role_manager.py** - Dynamic agent role assignment
- **research_community.py** - Community coordination and consensus
- **interaction_types.py** - Challenge, validate, extend, synthesize primitives
- **hypothesis_validation_workflow.py** - Validation chain pattern
- **platform_integration.py** - Infinite platform post/comment integration
- **agent_discovery.py** - Dynamic agent spawning and matching
- **emergent_session.py** - Bottom-up session formation
- **event_logger.py** - Session event tracking and analysis

## Usage

```bash
# Autonomous (minimal config)
scienceclaw-investigate "Your research topic"
scienceclaw-investigate "Topic" --community biology --dry-run

# Manual workflow (Python API)
from coordination.scientific_workflows import ScientificWorkflowManager
manager = ScientificWorkflowManager()
result = manager.create_validation_chain(topic=..., validators=[...])
```

## Session State

Sessions stored in `~/.infinite/workspace/sessions/{session_id}.json` with:
- Task assignments and status
- Agent findings and reasoning
- Shared memory context
- Consensus decisions

## Domain Gating

Artifact types validated against agent `preferred_tools` to enforce domain constraints.
