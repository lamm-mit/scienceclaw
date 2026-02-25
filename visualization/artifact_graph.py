#!/usr/bin/env python3
"""
Reusable DAG visualization module for scienceclaw artifact lineage graphs.

Reads the global artifact index, builds a directed acyclic graph filtered by
investigation_id, computes layout and metrics, saves a PNG and JSON report.

Usage:
    from visualization.artifact_graph import generate_artifact_graph
    metrics = generate_artifact_graph("my-investigation-slug")
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Colour palette — one colour per artifact type
# ---------------------------------------------------------------------------
_TYPE_COLORS: Dict[str, str] = {
    "compound_data":         "#4CAF50",
    "rdkit_properties":      "#2196F3",
    "admet_prediction":      "#FF9800",
    "candidate_evaluation":  "#9C27B0",
    "candidate_ranking":     "#F44336",
    "registration_metadata": "#BDBDBD",
}
_DEFAULT_COLOR = "#90A4AE"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_artifact_graph(investigation_id: str) -> dict:
    """
    Build and save a DAG visualisation for all artifacts belonging to
    `investigation_id`.

    Steps:
      1. Parse ~/.scienceclaw/artifacts/global_index.jsonl, filter by inv id
      2. Build networkx DiGraph (parent → child edges)
      3. Layout via graphviz dot (fallback: spring_layout)
      4. Render PNG with legend; save PNG + metrics JSON to
         ~/.scienceclaw/reports/{investigation_id}/

    Returns a metrics dict:
        {
            "num_nodes": int,
            "num_edges": int,
            "max_depth": int,
            "num_synthesis_nodes": int,        # in_degree >= 2
            "agent_contribution_counts": dict, # agent -> count
            "png_path": str,
            "json_path": str,
        }
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    try:
        import networkx as nx
    except ImportError as exc:
        raise ImportError("networkx is required for artifact_graph: pip install networkx") from exc

    # ------------------------------------------------------------------
    # 1. Load index entries for this investigation
    # ------------------------------------------------------------------
    base = Path.home() / ".scienceclaw"
    global_index = base / "artifacts" / "global_index.jsonl"

    entries: List[dict] = []
    if global_index.exists():
        for line in global_index.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("investigation_id") == investigation_id:
                entries.append(entry)

    # ------------------------------------------------------------------
    # 2. Build directed graph
    # ------------------------------------------------------------------
    G = nx.DiGraph()

    # Add nodes
    for e in entries:
        aid = e["artifact_id"]
        G.add_node(
            aid,
            artifact_type=e.get("artifact_type", "unknown"),
            producer_agent=e.get("producer_agent", "unknown"),
            skill_used=e.get("skill_used", "unknown"),
            timestamp=e.get("timestamp", ""),
        )

    # Add edges parent → child
    for e in entries:
        child_id = e["artifact_id"]
        for parent_id in e.get("parent_artifact_ids", []):
            if G.has_node(parent_id):
                G.add_edge(parent_id, child_id)

    # ------------------------------------------------------------------
    # 3. Compute metrics
    # ------------------------------------------------------------------
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()

    # Max depth: BFS from roots (nodes with in_degree == 0)
    roots = [n for n, d in G.in_degree() if d == 0]
    max_depth = 0
    if roots and num_nodes > 0:
        for root in roots:
            lengths = nx.single_source_shortest_path_length(G, root)
            local_max = max(lengths.values()) if lengths else 0
            max_depth = max(max_depth, local_max)

    num_synthesis_nodes = sum(1 for _, d in G.in_degree() if d >= 2)

    agent_contribution_counts: Dict[str, int] = {}
    for _, data in G.nodes(data=True):
        agent = data.get("producer_agent", "unknown")
        agent_contribution_counts[agent] = agent_contribution_counts.get(agent, 0) + 1

    # ------------------------------------------------------------------
    # 4. Layout
    # ------------------------------------------------------------------
    if num_nodes == 0:
        pos = {}
    else:
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
        except Exception:
            pos = nx.spring_layout(G, seed=42)

    # ------------------------------------------------------------------
    # 5. Render
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(max(8, num_nodes), max(6, num_nodes * 0.6)), dpi=150)

    node_colors = [
        _TYPE_COLORS.get(G.nodes[n].get("artifact_type", ""), _DEFAULT_COLOR)
        for n in G.nodes()
    ]

    if pos:
        nx.draw_networkx(
            G,
            pos=pos,
            ax=ax,
            node_color=node_colors,
            node_size=800,
            font_size=6,
            arrows=True,
            arrowsize=15,
            labels={n: n[:8] for n in G.nodes()},
            edge_color="#607D8B",
            width=1.2,
        )

    # Legend
    seen_types = {G.nodes[n].get("artifact_type", "") for n in G.nodes()}
    patches = []
    for atype in sorted(seen_types):
        color = _TYPE_COLORS.get(atype, _DEFAULT_COLOR)
        patches.append(mpatches.Patch(color=color, label=atype))
    if patches:
        ax.legend(handles=patches, loc="upper left", fontsize=7, title="Artifact type")

    ax.set_title(
        f"Artifact DAG — investigation: {investigation_id}\n"
        f"nodes={num_nodes}  edges={num_edges}  max_depth={max_depth}  "
        f"synthesis_nodes={num_synthesis_nodes}",
        fontsize=9,
    )
    ax.axis("off")

    # ------------------------------------------------------------------
    # 6. Save outputs
    # ------------------------------------------------------------------
    report_dir = base / "reports" / investigation_id
    report_dir.mkdir(parents=True, exist_ok=True)

    png_path = str(report_dir / "artifact_dag.png")
    json_path = str(report_dir / "artifact_dag_metrics.json")

    fig.savefig(png_path, bbox_inches="tight")
    plt.close(fig)

    metrics = {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "max_depth": max_depth,
        "num_synthesis_nodes": num_synthesis_nodes,
        "agent_contribution_counts": agent_contribution_counts,
        "png_path": png_path,
        "json_path": json_path,
    }

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)

    # ------------------------------------------------------------------
    # 7. Print summary
    # ------------------------------------------------------------------
    print(f"\n=== Artifact DAG: {investigation_id} ===")
    print(f"  Nodes            : {num_nodes}")
    print(f"  Edges            : {num_edges}")
    print(f"  Max depth        : {max_depth}")
    print(f"  Synthesis nodes  : {num_synthesis_nodes}")
    print(f"  Agent contribs   : {agent_contribution_counts}")
    print(f"  PNG saved to     : {png_path}")
    print(f"  JSON saved to    : {json_path}")

    return metrics
