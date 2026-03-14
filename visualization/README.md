# Visualization

Graph-based visualization of the artifact DAG and inter-agent relationships.

## Overview

Transforms the artifact lineage DAG into inspectable, publication-ready graphs:
- **Artifact Graph** — node-link visualization of artifacts and parent–child provenance
- **Relationship Extraction** — identifies cross-agent connections and multi-parent synthesis nodes
- **Hierarchical Layout** — groups artifacts by type, agent, and temporal order

## Key Files

- **artifact_graph.py** — Creates and renders the artifact DAG; exports to JSON, GraphML, and HTML
- **__init__.py** — Package exports

## API

```python
from visualization.artifact_graph import ArtifactGraph

graph = ArtifactGraph(agent_name="CrazyChem")
graph.add_artifact(artifact)
graph.build_edges()          # infers edges from parent_artifact_ids

graph.export_json("graph.json")
graph.export_graphml("graph.graphml")
graph.render_html("graph.html")   # interactive D3.js view
```

## Node Types

Nodes represent artifact types from the controlled vocabulary:
`pubmed_results`, `protein_data`, `admet_prediction`, `compound_data`,
`sequence_alignment`, `synthesis`, `peer_validation`, and others.

Multi-parent synthesis nodes are visually distinguished — they are the primary evidence of emergent cross-agent collaboration.

## Output Formats

| Format | Use |
|--------|-----|
| JSON | Programmatic analysis |
| GraphML | Gephi / Cytoscape |
| HTML | Interactive browser view (D3.js) |
| SVG | Static publication quality |

## Integration

- **artifacts/** — reads `ArtifactStore` to build graph
- **collaboration/dashboard.py** — embedded in live monitoring UI
- **autonomous/plot_agent.py** — renders figures from artifact DAG for publication
