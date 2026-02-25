#!/usr/bin/env python3
"""
Graph Snapshot Tool — Artifact DAG visualization and policy drift analysis.

Reads global_index + per-agent store, exports DAG as JSON, renders PNG via
networkx + matplotlib, and plots mutation policy drift over generations.

Usage:
    # Export JSON snapshot
    python3 -m artifacts.graph_snapshot --investigation inv_test --out /tmp/snap.json

    # Render DAG to PNG
    python3 -m artifacts.graph_snapshot --investigation inv_test --render /tmp/dag.png

    # Plot policy drift
    python3 -m artifacts.graph_snapshot --investigation inv_test --policy /tmp/policy.png

    # All three at once
    python3 -m artifacts.graph_snapshot --investigation inv_test \\
        --out /tmp/snap.json --render /tmp/dag.png --policy /tmp/policy.png
"""

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Node color map by mutation type
# ---------------------------------------------------------------------------
NODE_COLORS = {
    None:             "#4C72B0",  # normal reaction — blue
    "fork":           "#DD8452",  # orange
    "prune":          "#55A868",  # green
    "graft":          "#C44E52",  # red
    "merge_conflict": "#8172B3",  # purple
    "mutation_policy": "#937860", # brown (policy nodes)
}


# ---------------------------------------------------------------------------
# GraphSnapshot
# ---------------------------------------------------------------------------

class GraphSnapshot:
    """
    Snapshot of the artifact DAG for a given investigation_id.

    Reads from:
      ~/.scienceclaw/artifacts/global_index.jsonl  — node metadata + edges
      ~/.scienceclaw/artifacts/{agent}/store.jsonl — full payloads (for mutation_type)
    """

    def __init__(
        self,
        investigation_id: str,
        agents: Optional[List[str]] = None,
        base_dir: Optional[Path] = None,
    ):
        self.investigation_id = investigation_id
        self._base = base_dir or (Path.home() / ".scienceclaw" / "artifacts")
        self._global_index_path = self._base / "global_index.jsonl"
        self._agents = agents  # None = all agents

        # Loaded lazily
        self._nodes: Optional[List[dict]] = None
        self._edges: Optional[List[dict]] = None
        self._policy_timeline: Optional[List[dict]] = None

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load nodes + edges from global index and per-agent stores."""
        if self._nodes is not None:
            return  # already loaded

        index_entries: List[dict] = []
        if self._global_index_path.exists():
            for line in self._global_index_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("investigation_id") == self.investigation_id:
                    if self._agents is None or entry.get("producer_agent") in self._agents:
                        index_entries.append(entry)

        # Load payloads to extract mutation_type
        payload_cache: Dict[str, dict] = self._load_payloads(index_entries)

        # Build depth map
        depth_map = self._compute_depths(index_entries)

        nodes = []
        edges = []
        policy_timeline = []

        for entry in index_entries:
            aid = entry.get("artifact_id", "")
            atype = entry.get("artifact_type", "")
            payload = payload_cache.get(aid, {})
            prov = payload.get("mutation_provenance", {})
            mutation_type = prov.get("mutation_type") if prov else None

            # Special handling for mutation_policy nodes
            if atype == "mutation_policy":
                mutation_type = "mutation_policy"
                policy_timeline.append({
                    "generation":            payload.get("policy_generation", 0),
                    "redundancy_threshold":  payload.get("redundancy_threshold", 0.7),
                    "stagnation_cycles":     payload.get("stagnation_cycles", 3),
                    "timestamp":             entry.get("timestamp", ""),
                    "artifact_id":           aid,
                })

            node = {
                "id":             aid,
                "artifact_type":  atype,
                "producer_agent": entry.get("producer_agent", ""),
                "skill_used":     entry.get("skill_used", ""),
                "mutation_type":  mutation_type,
                "payload_keys":   list(payload.keys()) if payload else [],
                "depth":          depth_map.get(aid, 0),
                "timestamp":      entry.get("timestamp", ""),
            }
            nodes.append(node)

            for parent_id in entry.get("parent_artifact_ids", []):
                edges.append({"source": parent_id, "target": aid})

        # Sort policy timeline by generation
        policy_timeline.sort(key=lambda p: p["generation"])

        self._nodes = nodes
        self._edges = edges
        self._policy_timeline = policy_timeline

    def _load_payloads(self, index_entries: List[dict]) -> Dict[str, dict]:
        """Load payloads for all entries from per-agent store files."""
        # Group by producer_agent for efficiency
        agent_to_ids: Dict[str, List[str]] = {}
        for entry in index_entries:
            agent = entry.get("producer_agent", "")
            aid = entry.get("artifact_id", "")
            if agent and aid:
                agent_to_ids.setdefault(agent, []).append(aid)

        payloads: Dict[str, dict] = {}
        for agent, ids in agent_to_ids.items():
            store_path = self._base / agent / "store.jsonl"
            if not store_path.exists():
                continue
            id_set = set(ids)
            try:
                for line in store_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    aid = d.get("artifact_id", "")
                    if aid in id_set:
                        payloads[aid] = d.get("payload", {})
            except OSError:
                pass

        return payloads

    def _compute_depths(self, index_entries: List[dict]) -> Dict[str, int]:
        """BFS depth computation from roots (no parents)."""
        parent_map: Dict[str, List[str]] = {}
        for entry in index_entries:
            aid = entry.get("artifact_id", "")
            parent_map[aid] = entry.get("parent_artifact_ids", [])

        depths: Dict[str, int] = {}
        # Topological order: process nodes whose parents are already resolved
        remaining = list(parent_map.keys())
        max_iters = len(remaining) + 1
        iters = 0
        while remaining and iters < max_iters:
            iters += 1
            still_remaining = []
            for aid in remaining:
                parents = parent_map[aid]
                if not parents or all(p in depths or p not in parent_map for p in parents):
                    parent_depths = [depths.get(p, 0) for p in parents if p in depths]
                    depths[aid] = (max(parent_depths) + 1) if parent_depths else 0
                else:
                    still_remaining.append(aid)
            remaining = still_remaining

        # Unresolved nodes (cycles) get depth 0
        for aid in remaining:
            depths[aid] = 0

        return depths

    # ------------------------------------------------------------------
    # JSON export
    # ------------------------------------------------------------------

    def export_json(self, output_path: str) -> dict:
        """Export DAG as JSON: nodes + edges + policy timeline."""
        self._load()
        data = {
            "investigation_id": self.investigation_id,
            "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
            "nodes": self._nodes,
            "edges": self._edges,
            "policy_timeline": self._policy_timeline,
        }
        Path(output_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Exported JSON snapshot: {output_path} "
              f"({len(self._nodes)} nodes, {len(self._edges)} edges)")
        return data

    # ------------------------------------------------------------------
    # DAG PNG render
    # ------------------------------------------------------------------

    def render_png(self, output_path: str, color_by: str = "mutation_type") -> None:
        """Render DAG to PNG using networkx + matplotlib."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx

        self._load()

        G = nx.DiGraph()
        color_map = []
        labels = {}

        for node in self._nodes:
            aid = node["id"]
            G.add_node(aid)
            mutation_type = node.get("mutation_type")
            color = NODE_COLORS.get(mutation_type, NODE_COLORS[None])
            color_map.append(color)
            short_type = node.get("artifact_type", "")[:8]
            short_id = aid[:6]
            labels[aid] = f"{short_type}\n{short_id}"

        for edge in self._edges:
            src = edge["source"]
            tgt = edge["target"]
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt)

        fig, ax = plt.subplots(figsize=(14, 10))
        ax.set_title(
            f"Artifact DAG — investigation: {self.investigation_id}\n"
            f"{len(self._nodes)} nodes, {len(self._edges)} edges",
            fontsize=11,
        )

        # Layout: graphviz if available, else spring
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
        except Exception:
            pos = nx.spring_layout(G, seed=42, k=2.0)

        # Reorder colors to match G.nodes() order (networkx may reorder)
        node_order = list(G.nodes())
        node_id_to_color = {node["id"]: NODE_COLORS.get(node.get("mutation_type"), NODE_COLORS[None])
                            for node in self._nodes}
        ordered_colors = [node_id_to_color.get(n, NODE_COLORS[None]) for n in node_order]

        nx.draw_networkx_nodes(G, pos, node_color=ordered_colors, node_size=600, ax=ax)
        nx.draw_networkx_edges(G, pos, ax=ax, arrows=True,
                               arrowstyle="-|>", arrowsize=15,
                               edge_color="black", width=1.0)
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=6, ax=ax)

        # Legend
        from matplotlib.patches import Patch
        legend_items = [
            Patch(color=NODE_COLORS[None], label="normal"),
            Patch(color=NODE_COLORS["fork"], label="fork"),
            Patch(color=NODE_COLORS["prune"], label="prune"),
            Patch(color=NODE_COLORS["graft"], label="graft"),
            Patch(color=NODE_COLORS["merge_conflict"], label="merge_conflict"),
            Patch(color=NODE_COLORS["mutation_policy"], label="mutation_policy"),
        ]
        ax.legend(handles=legend_items, loc="upper left", fontsize=8)
        ax.axis("off")

        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"Rendered DAG PNG: {output_path}")

    # ------------------------------------------------------------------
    # Policy drift plot
    # ------------------------------------------------------------------

    def plot_policy_drift(self, output_path: str) -> None:
        """
        Three-panel plot showing mutation policy threshold drift and structural entropy.

        Top panel:    redundancy_threshold vs. policy generation (line + scatter)
        Middle panel: stagnation_cycles vs. policy generation (step plot)
        Bottom panel: structural_entropy vs. node insertion order (computed on-the-fly)

        If thresholds drift meaningfully, adaptive topology pressure is present.
        If they stay flat, the pressure signal is weak.
        Structural entropy shows whether mutation is diversifying the artifact graph.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        self._load()

        # --- Compute structural entropy series from _nodes ---
        nodes_sorted = sorted(self._nodes, key=lambda n: n["timestamp"])
        entropy_series = []
        for i in range(1, len(nodes_sorted) + 1):
            prefix = nodes_sorted[:i]
            combo_counts: dict = {}
            for n in prefix:
                combo = frozenset(
                    k for k in n["payload_keys"] if k != "mutation_provenance"
                )
                combo_counts[combo] = combo_counts.get(combo, 0) + 1
            n_total = len(prefix)
            h = -sum(
                (c / n_total) * math.log(c / n_total)
                for c in combo_counts.values()
                if c > 0
            )
            entropy_series.append(h)
        x_entropy = list(range(1, len(entropy_series) + 1))

        timeline = self._policy_timeline

        if not timeline:
            # Create a 3-panel placeholder figure
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 10))
            for ax, msg in [
                (ax1, "No mutation_policy artifacts found.\nRun mutation cycles with investigation_id."),
                (ax2, "No stagnation_cycles data."),
            ]:
                ax.text(0.5, 0.5, msg, ha="center", va="center",
                        transform=ax.transAxes, fontsize=11, wrap=True)
                ax.axis("off")
            # Entropy panel may have real data
            if entropy_series:
                ax3.plot(x_entropy, entropy_series, color="#2CA02C", linewidth=2)
                ax3.scatter(x_entropy, entropy_series, color="#2CA02C", s=40, zorder=5)
                ax3.set_ylabel("structural_entropy (nats)", fontsize=9)
                ax3.set_xlabel("node index (insertion order)", fontsize=9)
                ax3.grid(True, alpha=0.3)
                ax3.annotate(
                    f"final entropy: {entropy_series[-1]:.4f} nats",
                    xy=(0.98, 0.85), xycoords="axes fraction",
                    fontsize=8, ha="right", color="#333333",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8),
                )
            else:
                ax3.text(0.5, 0.5, "No nodes found.", ha="center", va="center",
                         transform=ax3.transAxes, fontsize=11)
                ax3.axis("off")
            fig.suptitle(f"Policy Drift — {self.investigation_id}\n(no policy data)", fontsize=11)
            fig.tight_layout()
            fig.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"Policy drift plot (no policy data): {output_path}")
            return

        generations = [p["generation"] for p in timeline]
        redundancy_thresholds = [p["redundancy_threshold"] for p in timeline]
        stagnation_cycles = [p["stagnation_cycles"] for p in timeline]

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 10), sharex=False)
        fig.suptitle(
            f"Mutation Policy Drift — investigation: {self.investigation_id}\n"
            f"{len(timeline)} policy generation(s)",
            fontsize=11,
        )

        # --- Top: redundancy_threshold ---
        ax1.plot(generations, redundancy_thresholds, color="#4C72B0", linewidth=2, label="redundancy_threshold")
        ax1.scatter(generations, redundancy_thresholds, color="#4C72B0", s=50, zorder=5)
        ax1.axhline(y=0.3, color="gray", linestyle="--", linewidth=1, alpha=0.7, label="lower bound (0.3)")
        ax1.axhline(y=0.95, color="gray", linestyle=":", linewidth=1, alpha=0.7, label="upper bound (0.95)")
        ax1.set_ylabel("redundancy_threshold", fontsize=9)
        ax1.set_ylim(0.0, 1.05)
        ax1.legend(fontsize=8, loc="upper right")
        ax1.grid(True, alpha=0.3)

        if len(redundancy_thresholds) > 1:
            drift = max(redundancy_thresholds) - min(redundancy_thresholds)
            ax1.annotate(
                f"drift range: {drift:.3f}",
                xy=(0.02, 0.85), xycoords="axes fraction",
                fontsize=8, color="#333333",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8),
            )

        # --- Middle: stagnation_cycles ---
        ax2.step(generations, stagnation_cycles, color="#DD8452", linewidth=2,
                 where="post", label="stagnation_cycles")
        ax2.scatter(generations, stagnation_cycles, color="#DD8452", s=50, zorder=5)
        ax2.axhline(y=3, color="gray", linestyle="--", linewidth=1, alpha=0.7, label="default (3)")
        ax2.axhline(y=8, color="gray", linestyle=":", linewidth=1, alpha=0.7, label="max (8)")
        ax2.set_ylabel("stagnation_cycles", fontsize=9)
        ax2.set_xlabel("policy generation", fontsize=9)
        ax2.set_ylim(0, 10)
        ax2.legend(fontsize=8, loc="upper right")
        ax2.grid(True, alpha=0.3)

        if len(stagnation_cycles) > 1:
            changed = sum(1 for i in range(1, len(stagnation_cycles))
                          if stagnation_cycles[i] != stagnation_cycles[i - 1])
            ax2.annotate(
                f"step changes: {changed}",
                xy=(0.02, 0.85), xycoords="axes fraction",
                fontsize=8, color="#333333",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8),
            )

        # --- Bottom: structural_entropy ---
        if entropy_series:
            ax3.plot(x_entropy, entropy_series, color="#2CA02C", linewidth=2, label="structural_entropy")
            ax3.scatter(x_entropy, entropy_series, color="#2CA02C", s=40, zorder=5)
            ax3.annotate(
                f"final entropy: {entropy_series[-1]:.4f} nats",
                xy=(0.98, 0.85), xycoords="axes fraction",
                fontsize=8, ha="right", color="#333333",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8),
            )
        else:
            ax3.text(0.5, 0.5, "No nodes found.", ha="center", va="center",
                     transform=ax3.transAxes, fontsize=11)
            ax3.axis("off")
        ax3.set_ylabel("structural_entropy (nats)", fontsize=9)
        ax3.set_xlabel("node index (insertion order)", fontsize=9)
        ax3.legend(fontsize=8, loc="upper right")
        ax3.grid(True, alpha=0.3)

        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"Policy drift plot: {output_path} ({len(timeline)} policy generations, {len(entropy_series)} nodes)")


# ---------------------------------------------------------------------------
# Module-level metrics helper
# ---------------------------------------------------------------------------

def collect_metrics_global(investigation_id: str, base_dir=None) -> dict:
    """
    Compute current DAG diversity metrics for investigation_id from the global
    index (no per-agent store iteration needed).

    Returns a dict with keys:
        total_nodes, unique_key_combos, structural_entropy (nats),
        mutation_node_count, cascade_node_count
    """
    snap = GraphSnapshot(investigation_id, base_dir=base_dir)
    snap._load()
    nodes = snap._nodes or []
    if not nodes:
        return {
            "total_nodes": 0, "unique_key_combos": 0,
            "structural_entropy": 0.0, "mutation_node_count": 0,
            "cascade_node_count": 0,
        }
    combo_counts: dict = {}
    for n in nodes:
        combo = frozenset(k for k in n["payload_keys"] if k != "mutation_provenance")
        combo_counts[combo] = combo_counts.get(combo, 0) + 1
    n_total = len(nodes)
    entropy = -sum(
        (c / n_total) * math.log(c / n_total)
        for c in combo_counts.values() if c > 0
    )
    mutation_nodes = sum(1 for n in nodes if "mutation_provenance" in n["payload_keys"])
    # cascade children: produced by a peer reactor in response to a mutation child
    # identified by having a mutation parent in the same investigation
    mutation_ids = {n["id"] for n in nodes if "mutation_provenance" in n["payload_keys"]}
    edges = snap._edges or []
    cascade_nodes = sum(
        1 for n in nodes
        if any(e["source"] in mutation_ids for e in edges if e["target"] == n["id"])
    )
    return {
        "total_nodes":        n_total,
        "unique_key_combos":  len(combo_counts),
        "structural_entropy": round(entropy, 4),
        "mutation_node_count": mutation_nodes,
        "cascade_node_count":  cascade_nodes,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Artifact DAG snapshot and visualization tool."
    )
    parser.add_argument(
        "--investigation", required=True,
        help="investigation_id to snapshot (e.g. inv_test)"
    )
    parser.add_argument(
        "--agents", nargs="*",
        help="Restrict to specific agent names (default: all agents)"
    )
    parser.add_argument(
        "--base-dir",
        help="Override ~/.scienceclaw/artifacts base directory"
    )
    parser.add_argument(
        "--out",
        help="Path to write JSON snapshot (e.g. /tmp/snap.json)"
    )
    parser.add_argument(
        "--render",
        help="Path to render DAG PNG (e.g. /tmp/dag.png)"
    )
    parser.add_argument(
        "--policy",
        help="Path to render policy drift PNG (e.g. /tmp/policy.png)"
    )

    args = parser.parse_args()

    if not any([args.out, args.render, args.policy]):
        parser.error("Specify at least one of --out, --render, --policy")

    base_dir = Path(args.base_dir) if args.base_dir else None
    snap = GraphSnapshot(
        investigation_id=args.investigation,
        agents=args.agents,
        base_dir=base_dir,
    )

    if args.out:
        snap.export_json(args.out)

    if args.render:
        snap.render_png(args.render)

    if args.policy:
        snap.plot_policy_drift(args.policy)


if __name__ == "__main__":
    main()
