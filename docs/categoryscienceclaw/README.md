# CategoryScienceClaw mechanics branch

This branch vendors the CategoryScienceClaw prototype and the mechanics discovery outputs used to extend the discovery-endofunctor manuscript.

Included content:

- `categoryscienceclaw/`: source package, tests, examples, and formal mechanics run exports.
- `categoryscienceclaw/run_exports/formal_mechanics_runs/`: four mechanics investigations, categorical discovery graphs, presentable reports, and generated figures.
- `docs/categoryscienceclaw/discovery_endofunctor_categoryscienceclaw_mechanics.tex`: manuscript copy integrating the CategoryScienceClaw mechanics case study.
- `docs/categoryscienceclaw/discovery_endofunctor_categoryscienceclaw_mechanics.pdf`: compiled manuscript PDF.

Useful checks from the repository root:

```bash
cd categoryscienceclaw
python3 -m pytest -q
python3 -m categoryscienceclaw audit run_exports/formal_mechanics_runs/7t10_formal_extension
python3 -m categoryscienceclaw audit run_exports/formal_mechanics_runs/biomechanics_fiber_network
python3 -m categoryscienceclaw audit run_exports/formal_mechanics_runs/mechanobiology_force_paths
python3 -m categoryscienceclaw audit run_exports/formal_mechanics_runs/membrane_biophysics
```

The mechanics reports distinguish imported, computational surrogate, and synthetic computational evidence. Synthetic computational inputs are not labeled as experimental measurements.
