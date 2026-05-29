# Formal mechanics heartbeat examples

These examples run CategoryScienceClaw agents through decentralized heartbeat cycles.

Core semantics:

- `needs.index.jsonl` is the live need frontier.
- `ArtifactReactor` advances heartbeat cycles.
- Workers rank needs with ScienceClaw-style pressure: novelty, centrality, depth, and age.
- Agents fulfill only compatible needs.
- Produced artifacts may emit second-order needs.
- Claims are formal/provisional unless backed by real input data.

Run all high-complexity examples:

```bash
categoryscienceclaw run-examples-a-to-d \
  --complexity high \
  --cycles 30 \
  --out-root run_exports/formal_mechanics_runs/high_complexity
```

Run one example:

```bash
categoryscienceclaw run-example biomechanics-fiber-network \
  --scienceclaw \
  --complexity high \
  --cycles 30 \
  --out run_exports/formal_mechanics_runs/biomechanics_fiber_network
```

Example A extends the existing 7T10 run with formal descriptors. It does not repeat the original contact-hotspot or force-extension workflow.

Examples B-D are formal mechanics demonstrations. They must not invent real mechanical values. Missing empirical inputs become blocked real-data needs.

ScienceClaw-backed mode records the executed ScienceClaw skill in each heartbeat-produced artifact under `payload.scienceclaw.skill_name`. The formal wrapper still enforces CategoryScienceClaw certificates, child needs, and symbolic data-honesty labels.
