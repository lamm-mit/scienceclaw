# Real-Time Collaboration

This module provides server-side components for live, multi-agent investigation dashboards and event streaming.

## Overview

Enables real-time visibility into concurrent agent investigations:
- **Message Bus** — Server-Sent Events (SSE) pub/sub for live updates between agents and dashboard
- **Live Runner** — Streams investigation progress as it happens
- **Dashboard** — Web interface for monitoring agent activity and artifact DAG growth

## Key Files

- **message_bus.py** — SSE message broker; agents publish events, dashboard and peer agents subscribe
- **live_runner.py** — Executes investigations with streaming output; emits progress events at each skill invocation
- **dashboard.py** — FastAPI web server; renders live investigation status, memory changes, and session activity

## Message Bus

```python
from collaboration.message_bus import MessageBus

bus = MessageBus()
subscription = bus.subscribe("agent/BioAgent-7/progress")
for message in subscription:
    print(f"{message['type']}: {message['data']}")
```

## Live Runner

```python
from collaboration.live_runner import LiveRunner

runner = LiveRunner(agent_name="BioAgent-7")
async for event in runner.stream_investigation(topic="CRISPR delivery"):
    print(f"{event['status']} — {event['progress']}%")
```

## Dashboard

Accessible at `https://lamm.mit.edu/infinite` when running:
- Real-time agent activity feed
- Artifact DAG growth visualisation
- Multi-agent session monitoring
- Memory and knowledge graph updates

## Integration

- **autonomous/** — investigation loop emits progress events
- **coordination/** — multi-agent session state updates
- **artifacts/** — artifact creation events broadcast to subscribers
- **visualization/** — artifact graph rendered in dashboard
