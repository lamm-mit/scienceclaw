# CategoryScienceClaw

CategoryScienceClaw is a minimal proof-carrying execution runtime for decentralized
ScienceClaw-style agents.

Agents coordinate through shared categorical state:

- typed artifacts,
- open needs,
- append-only events,
- atomic claims,
- executable morphisms,
- JSON proof certificates.

There is no central planner. Each worker heartbeat scans open needs, claims one
compatible need, executes a typed morphism, writes a child artifact, and emits a
certificate proving the execution was type- and provenance-valid.

## Quick Start

```bash
categoryscienceclaw init /tmp/csc-run --topic "toy mechanism" --agents examples/agents.json
categoryscienceclaw run /tmp/csc-run --agents examples/agents.json --cycles 4
categoryscienceclaw audit /tmp/csc-run
categoryscienceclaw replay /tmp/csc-run
```

The default local executor provides deterministic built-in demo morphisms. The
ScienceClaw adapter can wrap the existing `/home/fiona/LAMM/scienceclaw` skill
runtime when available.
