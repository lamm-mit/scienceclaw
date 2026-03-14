# Real-Time Collaboration

This module provides server-side components for live, multi-agent investigation dashboards and message passing.

## Overview

Enables real-time visualization and coordination:
- **Message Bus** - Server-sent events (SSE) for live updates
- **Live Runner** - Executes investigations with streaming output
- **Dashboard** - Web interface for monitoring agent progress

## Key Files

- **message_bus.py** - SSE message broker for pub/sub coordination
- **live_runner.py** - Streams investigation progress in real-time
- **dashboard.py** - FastAPI web server for monitoring
- **__init__.py** - Package exports

## Message Bus API

```python
from collaboration.message_bus import MessageBus

bus = MessageBus()
subscription = bus.subscribe("agent/BioAgent-7/progress")
for message in subscription:
    print(f"Event: {message['type']}, Data: {message['data']}")
```

## Live Runner

```python
from collaboration.live_runner import LiveRunner

runner = LiveRunner(agent_name="BioAgent-7")
async for event in runner.stream_investigation(topic="CRISPR delivery"):
    print(f"Status: {event['status']}, Progress: {event['progress']}%")
```

## Dashboard

Accessible at `http://localhost:8000/` (if running):
- Real-time agent activity feed
- Investigation progress bars
- Memory and knowledge graph visualization
- Multi-agent session monitoring

## Integration

Works alongside:
- **autonomous/** - Investigation loop progress streaming
- **coordination/** - Multi-agent session updates
- **artifacts/** - Artifact creation events

## Deployment

Runs as separate FastAPI process on port 8000 (configurable).
Can be deployed independently from main agent infrastructure.
