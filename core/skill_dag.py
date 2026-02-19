"""
Skill DAG - Dependency graph for skill execution orchestration.

Adapted from AgentSkillOS (github.com/ynulihao/AgentSkillOS) graph.py and models.py.

Provides:
- DependencyGraph: DAG with topological sort and parallel phase generation
- SkillNode: node in the execution graph with status tracking
- build_graph_from_plan: constructs graph from LLM-planned node list
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SkillType(str, Enum):
    PRIMARY = "primary"   # Produces final investigation output
    HELPER  = "helper"    # Feeds data into primary skills


class NodeStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"   # dependency failed; cascaded skip


class NodeFailureReason(str, Enum):
    SUCCESS          = "success"
    TIMEOUT          = "timeout"
    RATE_LIMIT       = "rate_limit"
    SKILL_ERROR      = "skill_error"
    DEPENDENCY_FAILED = "dependency_failed"
    UNKNOWN          = "unknown"


# ---------------------------------------------------------------------------
# SkillNode
# ---------------------------------------------------------------------------

@dataclass
class SkillNode:
    """A skill in the dependency graph."""
    id: str
    name: str                                       # skill directory name (e.g. "pubmed")
    skill_type: SkillType = SkillType.HELPER
    depends_on: List[str] = field(default_factory=list)   # node IDs this depends on
    purpose: str = ""                               # why this skill is included
    status: NodeStatus = NodeStatus.PENDING
    failure_reason: NodeFailureReason = NodeFailureReason.SUCCESS

    # Execution outputs
    result: Optional[dict] = None                  # parsed JSON output from the skill
    outputs_summary: str = ""                      # short summary for downstream nodes
    downstream_hint: str = ""                      # hint to consumer nodes about the output

    # Execution params
    params: dict = field(default_factory=dict)     # CLI params to pass to the skill

    @property
    def is_terminal(self) -> bool:
        return self.status in (NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "skill_type": self.skill_type.value,
            "depends_on": self.depends_on,
            "purpose": self.purpose,
            "status": self.status.value,
            "failure_reason": self.failure_reason.value,
            "outputs_summary": self.outputs_summary,
            "downstream_hint": self.downstream_hint,
            "params": self.params,
        }


# ---------------------------------------------------------------------------
# ExecutionPhase
# ---------------------------------------------------------------------------

@dataclass
class ExecutionPhase:
    """A group of nodes that can run in parallel (no inter-dependencies)."""
    phase_number: int
    node_ids: List[str]
    mode: str = "parallel"  # "parallel" or "sequential"

    def to_dict(self) -> dict:
        return {
            "phase": self.phase_number,
            "node_ids": self.node_ids,
            "mode": self.mode,
        }


# ---------------------------------------------------------------------------
# DependencyGraph
# ---------------------------------------------------------------------------

class DependencyGraph:
    """
    Directed acyclic graph for skill execution planning.

    Features:
    - Add nodes with dependencies
    - Detect cycles (DFS)
    - Topological sort
    - Generate parallel execution phases
    - Track execution status and cascade failures
    """

    def __init__(self):
        self.nodes: Dict[str, SkillNode] = {}
        # node_id -> set of node_ids that depend ON it (forward edges)
        self._dependents: Dict[str, Set[str]] = {}
        # node_id -> set of node_ids it depends on (reverse edges, for quick lookup)
        self._dependencies: Dict[str, Set[str]] = {}

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def add_node(self, node: SkillNode):
        """Register a node and wire its dependency edges."""
        self.nodes[node.id] = node
        self._dependents.setdefault(node.id, set())
        self._dependencies.setdefault(node.id, set())

        for dep_id in node.depends_on:
            self._dependents.setdefault(dep_id, set()).add(node.id)
            self._dependencies[node.id].add(dep_id)

    def remove_node(self, node_id: str):
        """Remove a node and clean up adjacency structures."""
        if node_id not in self.nodes:
            return
        node = self.nodes.pop(node_id)
        # Remove from dependency sets of other nodes
        for dep_id in node.depends_on:
            self._dependents.get(dep_id, set()).discard(node_id)
        # Remove its own entries
        self._dependents.pop(node_id, None)
        self._dependencies.pop(node_id, None)
        # Remove references to it from other nodes' dependency sets
        for deps in self._dependencies.values():
            deps.discard(node_id)

    def get_node(self, node_id: str) -> Optional[SkillNode]:
        return self.nodes.get(node_id)

    # ------------------------------------------------------------------
    # Graph analysis
    # ------------------------------------------------------------------

    def detect_cycle(self) -> bool:
        """Return True if the graph contains a cycle (DFS coloring)."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in self.nodes}

        def dfs(nid: str) -> bool:
            color[nid] = GRAY
            for dependent in self._dependents.get(nid, set()):
                if color.get(dependent) == GRAY:
                    return True  # back edge → cycle
                if color.get(dependent) == WHITE and dfs(dependent):
                    return True
            color[nid] = BLACK
            return False

        return any(dfs(nid) for nid in self.nodes if color[nid] == WHITE)

    def topological_sort(self) -> List[str]:
        """
        Return node IDs in dependency-first order (Kahn's algorithm).
        Raises ValueError if a cycle is detected.
        """
        in_degree = {nid: len(self._dependencies.get(nid, set())) for nid in self.nodes}
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order: List[str] = []

        while queue:
            # Sort for determinism
            queue.sort()
            nid = queue.pop(0)
            order.append(nid)
            for dependent in sorted(self._dependents.get(nid, set())):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self.nodes):
            raise ValueError("Cycle detected in skill dependency graph")

        return order

    def get_execution_phases(self) -> List[ExecutionPhase]:
        """
        Group nodes into parallel execution tiers.

        All nodes within a phase have no dependencies on each other,
        so they can run concurrently. Phases must run in order.
        """
        # BFS level-assignment
        level: Dict[str, int] = {}
        for nid in self.topological_sort():
            deps = self._dependencies.get(nid, set())
            if not deps:
                level[nid] = 0
            else:
                level[nid] = max(level[d] for d in deps if d in level) + 1

        max_level = max(level.values()) if level else 0
        phases = []
        for lvl in range(max_level + 1):
            node_ids = sorted(nid for nid, l in level.items() if l == lvl)
            if node_ids:
                phases.append(ExecutionPhase(phase_number=lvl, node_ids=node_ids))
        return phases

    # ------------------------------------------------------------------
    # Execution tracking
    # ------------------------------------------------------------------

    def get_ready_nodes(self) -> List[SkillNode]:
        """Return nodes whose dependencies have all completed."""
        ready = []
        for nid, node in self.nodes.items():
            if node.status != NodeStatus.PENDING:
                continue
            deps = self._dependencies.get(nid, set())
            if all(
                self.nodes[d].status == NodeStatus.COMPLETED
                for d in deps if d in self.nodes
            ):
                ready.append(node)
        return ready

    def update_status(self, node_id: str, status: NodeStatus,
                      failure_reason: NodeFailureReason = NodeFailureReason.SUCCESS):
        """Update a node's execution status."""
        node = self.nodes.get(node_id)
        if node:
            node.status = status
            node.failure_reason = failure_reason

    def fail_node(self, node_id: str, reason: NodeFailureReason = NodeFailureReason.SKILL_ERROR):
        """
        Mark a node as failed and cascade SKIPPED status to all
        transitive dependents.
        """
        self.update_status(node_id, NodeStatus.FAILED, reason)
        self._cascade_skip(node_id)

    def _cascade_skip(self, failed_id: str):
        queue = list(self._dependents.get(failed_id, set()))
        visited: Set[str] = set()
        while queue:
            nid = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            node = self.nodes.get(nid)
            if node and node.status == NodeStatus.PENDING:
                self.update_status(nid, NodeStatus.SKIPPED, NodeFailureReason.DEPENDENCY_FAILED)
                queue.extend(self._dependents.get(nid, set()))

    def is_complete(self) -> bool:
        """True when every node has reached a terminal state."""
        return all(n.is_terminal for n in self.nodes.values())

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_dependents(self, node_id: str) -> List[str]:
        """Nodes that depend on node_id."""
        return sorted(self._dependents.get(node_id, set()))

    def get_dependencies(self, node_id: str) -> List[str]:
        """Nodes that node_id depends on."""
        return sorted(self._dependencies.get(node_id, set()))

    def get_stats(self) -> dict:
        status_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}
        for node in self.nodes.values():
            s = node.status.value
            t = node.skill_type.value
            status_counts[s] = status_counts.get(s, 0) + 1
            type_counts[t] = type_counts.get(t, 0) + 1
        return {
            "total": len(self.nodes),
            "by_status": status_counts,
            "by_type": type_counts,
            "complete": self.is_complete(),
        }

    def to_dict(self) -> dict:
        return {
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "phases": [p.to_dict() for p in self.get_execution_phases()],
            "stats": self.get_stats(),
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_graph_from_plan(nodes_data: List[dict]) -> DependencyGraph:
    """
    Build a DependencyGraph from a list of node dicts, as returned by
    the LLM planner in skill_tree_searcher.py.

    Expected dict keys:
        id          : str  - unique node identifier
        name        : str  - skill name (matches registry)
        depends_on  : list - list of node IDs this node depends on
        purpose     : str  - why this skill is used
        skill_type  : str  - "primary" or "helper" (optional, default "helper")
        params      : dict - CLI parameters for the skill (optional)

    Example input:
        [
          {"id": "lit",     "name": "pubmed",  "depends_on": [],       "purpose": "Find papers"},
          {"id": "protein", "name": "uniprot", "depends_on": ["lit"],  "purpose": "Characterize proteins"},
          {"id": "chem",    "name": "pubchem", "depends_on": ["lit"],  "purpose": "Find compounds"},
          {"id": "admet",   "name": "tdc",     "depends_on": ["chem"], "purpose": "Predict ADMET", "skill_type": "primary"},
        ]
    """
    graph = DependencyGraph()

    for nd in nodes_data:
        node = SkillNode(
            id=nd["id"],
            name=nd["name"],
            skill_type=SkillType(nd.get("skill_type", "helper")),
            depends_on=nd.get("depends_on", []),
            purpose=nd.get("purpose", ""),
            params=nd.get("params", {}),
        )
        graph.add_node(node)

    if graph.detect_cycle():
        raise ValueError("LLM-generated plan contains a dependency cycle")

    return graph
