# Visualization

This module provides graph-based visualization of artifacts and their relationships.

## Overview

Transforms scientific artifacts into interactive knowledge graphs:
- **Artifact Graph** - Node-link visualization of artifacts and dependencies
- **Relationship Extraction** - Identifies connections between findings
- **Hierarchical Layout** - Groups artifacts by type and temporal order

## Key Files

- **artifact_graph.py** - Creates and renders artifact graphs
- **__init__.py** - Package exports

## Graph Visualization

```python
from visualization.artifact_graph import ArtifactGraph

graph = ArtifactGraph(agent_name="CrazyChem")

# Add artifacts as nodes
graph.add_artifact(artifact)

# Build relationships
graph.build_edges()

# Export to various formats
graph.export_json("graph.json")
graph.export_graphml("graph.graphml")
graph.render_html("graph.html")
```

## Integration

Works with:
- **artifacts/** - Consumes artifact data
- **collaboration/dashboard.py** - Embedded visualization in web UI
- **memory/** - Knowledge graph integration

## Output Formats

- **JSON** - For programmatic analysis
- **GraphML** - For Gephi/Cytoscape
- **HTML** - Interactive visualization with D3.js
- **SVG** - Static publication quality

## Artifact Node Types

Nodes represent: pubmed_results, protein_data, admet_prediction, compound_data, sequence_alignment, synthesis, peer_validation
