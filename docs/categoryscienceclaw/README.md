# CategoryScienceClaw mechanics branch

This branch vendors the CategoryScienceClaw prototype and the manuscript extension used to discuss the mechanics discovery case study.

Included content:

- `categoryscienceclaw/`: flattened CategoryScienceClaw source package.
- `docs/categoryscienceclaw/discovery_endofunctor_categoryscienceclaw_mechanics.tex`: manuscript copy integrating the CategoryScienceClaw mechanics case study.
- `docs/categoryscienceclaw/discovery_endofunctor_categoryscienceclaw_mechanics.pdf`: compiled manuscript PDF.

Basic smoke checks from the repository root:

```bash
python3 -m py_compile categoryscienceclaw/*.py
python3 -m categoryscienceclaw --help
```

The bulky examples, run exports, and tests are intentionally omitted from this branch revision.
