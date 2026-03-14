"""
Knowledge Graph - Concept and relationship tracking

Stores a graph of scientific concepts and their relationships:
- Nodes: Proteins, compounds, methods, findings, papers
- Edges: Relationships (correlates, contradicts, extends, requires, causes)

File format: ~/.scienceclaw/knowledge/{agent_name}/graph.json
Structure: {"nodes": {node_id: {...}}, "edges": [{source, target, type, metadata}]}
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from uuid import uuid4


class KnowledgeGraph:
    """Graph database for agent knowledge and relationships"""
    
    # Predefined node types
    NODE_TYPES = ["protein", "compound", "method", "finding", "paper", "organism", "disease", "concept"]
    
    # Predefined edge types
    EDGE_TYPES = [
        "correlates",      # A correlates with B (positive relationship)
        "contradicts",     # A contradicts B (conflicting findings)
        "extends",         # A extends/builds on B
        "requires",        # A requires B (dependency)
        "causes",          # A causes B (causal relationship)
        "inhibits",        # A inhibits B
        "activates",       # A activates B
        "binds_to",        # A binds to B (protein-compound, protein-protein)
        "similar_to",      # A is similar to B
        "derived_from"     # A derived from B (source/citation)
    ]
    
    def __init__(self, agent_name: str, base_dir: Optional[str] = None):
        """
        Initialize knowledge graph for specific agent
        
        Args:
            agent_name: Name of the agent
            base_dir: Base directory for knowledge graphs (default: ~/.scienceclaw/knowledge)
        """
        self.agent_name = agent_name
        if base_dir is None:
            base_dir = os.path.expanduser("~/.scienceclaw/knowledge")
        
        self.kg_dir = Path(base_dir) / agent_name
        self.kg_dir.mkdir(parents=True, exist_ok=True)
        
        self.graph_path = self.kg_dir / "graph.json"
        
        # Initialize graph file if it doesn't exist
        if not self.graph_path.exists():
            self._save_graph({
                "nodes": {},
                "edges": []
            })
        
        self.graph = self._load_graph()
    
    def _load_graph(self) -> Dict[str, Any]:
        """Load graph from JSON file"""
        try:
            with open(self.graph_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"nodes": {}, "edges": []}
    
    def _save_graph(self, graph: Optional[Dict[str, Any]] = None):
        """Save graph to JSON file"""
        if graph is None:
            graph = self.graph
        
        with open(self.graph_path, 'w') as f:
            json.dump(graph, f, indent=2)
    
    def add_node(self, name: str, node_type: str, properties: Optional[Dict[str, Any]] = None,
                 source: Optional[str] = None, **kwargs) -> str:
        """
        Add a node to the knowledge graph
        
        Args:
            name: Name/label of the concept
            node_type: Type of node (protein, compound, method, finding, paper, etc.)
            properties: Additional properties (structure, function, pmid, etc.)
            source: Source of information (journal entry, post_id, pmid)
            **kwargs: Additional metadata
            
        Returns:
            Node ID
            
        Example:
            node_id = kg.add_node(
                name="CRISPR-Cas9",
                node_type="method",
                properties={
                    "description": "Gene editing system using Cas9 nuclease",
                    "organisms": ["bacteria", "mammalian cells"],
                    "applications": ["gene knockout", "gene insertion"]
                },
                source="pmid:12345678"
            )
        """
        # Check if node already exists
        existing_id = self._find_node_by_name(name, node_type)
        if existing_id:
            # Update existing node
            self.graph["nodes"][existing_id]["properties"].update(properties or {})
            self.graph["nodes"][existing_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_graph()
            return existing_id
        
        # Create new node
        node_id = str(uuid4())
        
        node = {
            "id": node_id,
            "name": name,
            "type": node_type,
            "properties": properties or {},
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": kwargs
        }
        
        self.graph["nodes"][node_id] = node
        self._save_graph()
        
        return node_id
    
    def _find_node_by_name(self, name: str, node_type: Optional[str] = None) -> Optional[str]:
        """Find node ID by name (case-insensitive)"""
        name_lower = name.lower()
        for node_id, node in self.graph["nodes"].items():
            if node["name"].lower() == name_lower:
                if node_type is None or node["type"] == node_type:
                    return node_id
        return None
    
    def add_edge(self, source_id: str, target_id: str, edge_type: str,
                 properties: Optional[Dict[str, Any]] = None, 
                 confidence: str = "medium", evidence: Optional[str] = None) -> bool:
        """
        Add an edge (relationship) between two nodes
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            edge_type: Type of relationship (correlates, contradicts, extends, etc.)
            properties: Additional properties about the relationship
            confidence: Confidence in relationship (high, medium, low)
            evidence: Evidence for relationship (journal entry, pmid, etc.)
            
        Returns:
            True if successful, False if nodes don't exist
            
        Example:
            kg.add_edge(
                source_id=lipid_node_id,
                target_id=delivery_node_id,
                edge_type="correlates",
                properties={
                    "correlation": "positive",
                    "strength": "strong",
                    "context": "muscle tissue delivery"
                },
                confidence="high",
                evidence="pmid:12345678"
            )
        """
        # Verify nodes exist
        if source_id not in self.graph["nodes"] or target_id not in self.graph["nodes"]:
            return False
        
        # Check if edge already exists
        for edge in self.graph["edges"]:
            if (edge["source"] == source_id and edge["target"] == target_id and 
                edge["type"] == edge_type):
                # Update existing edge
                edge["properties"].update(properties or {})
                edge["confidence"] = confidence
                edge["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_graph()
                return True
        
        # Create new edge
        edge = {
            "source": source_id,
            "target": target_id,
            "type": edge_type,
            "properties": properties or {},
            "confidence": confidence,
            "evidence": evidence,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.graph["edges"].append(edge)
        self._save_graph()
        
        return True
    
    def add_finding(self, finding: str, related_concepts: List[Dict[str, str]],
                   relationships: Optional[List[Dict[str, str]]] = None,
                   source: Optional[str] = None, **kwargs) -> str:
        """
        Add a finding and automatically link to related concepts
        
        Args:
            finding: Description of the finding
            related_concepts: List of related concepts [{"name": "X", "type": "protein"}, ...]
            relationships: List of relationships to create [{"from": "X", "to": "Y", "type": "correlates"}, ...]
            source: Source of finding (journal entry, pmid, post_id)
            **kwargs: Additional metadata
            
        Returns:
            Finding node ID
            
        Example:
            finding_id = kg.add_finding(
                finding="DLin-MC3-DMA shows superior muscle tissue uptake compared to other ionizable lipids",
                related_concepts=[
                    {"name": "DLin-MC3-DMA", "type": "compound"},
                    {"name": "muscle tissue", "type": "organism"},
                    {"name": "tissue uptake", "type": "concept"}
                ],
                relationships=[
                    {"from": "DLin-MC3-DMA", "to": "tissue uptake", "type": "correlates"}
                ],
                source="pmid:12345678",
                confidence="high"
            )
        """
        # Create finding node
        finding_id = self.add_node(
            name=finding,
            node_type="finding",
            properties=kwargs,
            source=source
        )
        
        # Add related concept nodes and link to finding
        concept_ids = {}
        for concept in related_concepts:
            concept_id = self.add_node(
                name=concept["name"],
                node_type=concept["type"],
                source=source
            )
            concept_ids[concept["name"]] = concept_id
            
            # Link concept to finding
            self.add_edge(
                source_id=concept_id,
                target_id=finding_id,
                edge_type="supports",
                evidence=source
            )
        
        # Add relationships between concepts
        if relationships:
            for rel in relationships:
                from_id = concept_ids.get(rel["from"])
                to_id = concept_ids.get(rel["to"])
                
                if from_id and to_id:
                    self.add_edge(
                        source_id=from_id,
                        target_id=to_id,
                        edge_type=rel["type"],
                        confidence=rel.get("confidence", "medium"),
                        evidence=source
                    )
        
        return finding_id
    
    def query_related(self, node_id: str, edge_types: Optional[List[str]] = None,
                     max_depth: int = 1) -> Dict[str, Any]:
        """
        Query nodes related to a given node
        
        Args:
            node_id: ID of the node to query from
            edge_types: Filter by edge types (correlates, contradicts, etc.)
            max_depth: Maximum depth to traverse (1 = direct neighbors only)
            
        Returns:
            Dictionary with related nodes and paths
            
        Example:
            # Find all nodes that correlate with a specific compound
            related = kg.query_related(compound_id, edge_types=["correlates"])
        """
        if node_id not in self.graph["nodes"]:
            return {"error": "Node not found"}
        
        visited = set()
        results = {
            "source_node": self.graph["nodes"][node_id],
            "related_nodes": [],
            "relationships": []
        }
        
        def traverse(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            # Find edges from current node
            for edge in self.graph["edges"]:
                if edge["source"] == current_id:
                    # Filter by edge type
                    if edge_types and edge["type"] not in edge_types:
                        continue
                    
                    target_id = edge["target"]
                    if target_id in self.graph["nodes"]:
                        results["related_nodes"].append(self.graph["nodes"][target_id])
                        results["relationships"].append(edge)
                        
                        if depth < max_depth:
                            traverse(target_id, depth + 1)
                
                # Also check edges to current node (bidirectional)
                elif edge["target"] == current_id:
                    if edge_types and edge["type"] not in edge_types:
                        continue
                    
                    source_id = edge["source"]
                    if source_id in self.graph["nodes"]:
                        results["related_nodes"].append(self.graph["nodes"][source_id])
                        results["relationships"].append(edge)
                        
                        if depth < max_depth:
                            traverse(source_id, depth + 1)
        
        traverse(node_id, 0)
        
        return results
    
    def find_contradictions(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find contradicting findings in the knowledge graph
        
        Args:
            node_id: Optional node ID to find contradictions for (if None, finds all)
            
        Returns:
            List of contradiction pairs
            
        Example:
            # Find all contradictions
            contradictions = kg.find_contradictions()
            
            # Find contradictions related to specific finding
            contradictions = kg.find_contradictions(finding_id)
        """
        contradictions = []
        
        for edge in self.graph["edges"]:
            if edge["type"] == "contradicts":
                source = self.graph["nodes"].get(edge["source"])
                target = self.graph["nodes"].get(edge["target"])
                
                if source and target:
                    # Filter by node_id if provided
                    if node_id and node_id not in [edge["source"], edge["target"]]:
                        continue
                    
                    contradictions.append({
                        "finding_a": source,
                        "finding_b": target,
                        "edge": edge
                    })
        
        return contradictions
    
    def search_nodes(self, query: str, node_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search nodes by text
        
        Args:
            query: Text to search for (case-insensitive)
            node_types: Filter by node types
            
        Returns:
            List of matching nodes
        """
        query_lower = query.lower()
        results = []
        
        for node in self.graph["nodes"].values():
            # Filter by type
            if node_types and node["type"] not in node_types:
                continue
            
            # Search in name and properties
            node_str = json.dumps(node).lower()
            if query_lower in node_str:
                results.append(node)
        
        return results
    
    def get_node_by_name(self, name: str, node_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get node by name"""
        node_id = self._find_node_by_name(name, node_type)
        if node_id:
            return self.graph["nodes"][node_id]
        return None
    
    def export_graph(self, format: str = "json", output_path: Optional[str] = None) -> str:
        """
        Export knowledge graph
        
        Args:
            format: Export format (json, graphml, cytoscape)
            output_path: Path to write file (default: graph_export.{format} in kg dir)
            
        Returns:
            Path to exported file
        """
        if format == "json":
            if output_path is None:
                output_path = self.kg_dir / "graph_export.json"
            else:
                output_path = Path(output_path)
            
            with open(output_path, 'w') as f:
                json.dump(self.graph, f, indent=2)
        
        elif format == "cytoscape":
            # Export in Cytoscape.js format
            if output_path is None:
                output_path = self.kg_dir / "graph_export_cytoscape.json"
            else:
                output_path = Path(output_path)
            
            cytoscape_data = {
                "elements": {
                    "nodes": [
                        {"data": {**node, "label": node["name"]}} 
                        for node in self.graph["nodes"].values()
                    ],
                    "edges": [
                        {"data": {**edge, "id": f"{edge['source']}_{edge['target']}"}}
                        for edge in self.graph["edges"]
                    ]
                }
            }
            
            with open(output_path, 'w') as f:
                json.dump(cytoscape_data, f, indent=2)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return str(output_path)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph
        
        Returns:
            Dictionary with node/edge counts, types, etc.
        """
        stats = {
            "total_nodes": len(self.graph["nodes"]),
            "total_edges": len(self.graph["edges"]),
            "nodes_by_type": {},
            "edges_by_type": {}
        }
        
        # Count nodes by type
        for node in self.graph["nodes"].values():
            node_type = node.get("type", "unknown")
            stats["nodes_by_type"][node_type] = stats["nodes_by_type"].get(node_type, 0) + 1
        
        # Count edges by type
        for edge in self.graph["edges"]:
            edge_type = edge.get("type", "unknown")
            stats["edges_by_type"][edge_type] = stats["edges_by_type"].get(edge_type, 0) + 1
        
        return stats
    
    def get_principles(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all principle nodes from the knowledge graph.

        Args:
            domain: Optional domain filter (biology, chemistry, materials, general).
                    If None, returns all principles regardless of domain.

        Returns:
            List of principle node dicts with name, properties, etc.
        """
        principles = []
        for node in self.graph["nodes"].values():
            if node.get("type") != "principle":
                continue
            if domain is not None:
                node_domain = node.get("properties", {}).get("domain", "general")
                if node_domain != domain:
                    continue
            principles.append(node)
        # Sort by evidence_count descending
        principles.sort(
            key=lambda n: n.get("properties", {}).get("evidence_count", 0),
            reverse=True
        )
        return principles

    def visualize_neighborhood(self, node_id: str, max_depth: int = 2) -> str:
        """
        Generate ASCII visualization of node neighborhood
        
        Args:
            node_id: ID of the node to visualize
            max_depth: Maximum depth to traverse
            
        Returns:
            ASCII art visualization
        """
        if node_id not in self.graph["nodes"]:
            return "Node not found"
        
        related = self.query_related(node_id, max_depth=max_depth)
        
        lines = []
        lines.append(f"\nKnowledge Graph Neighborhood for: {related['source_node']['name']}")
        lines.append("=" * 80)
        
        for edge in related["relationships"]:
            source = self.graph["nodes"][edge["source"]]
            target = self.graph["nodes"][edge["target"]]
            
            lines.append(f"\n[{source['name']}] --({edge['type']})--> [{target['name']}]")
            if edge.get("confidence"):
                lines.append(f"  Confidence: {edge['confidence']}")
            if edge.get("evidence"):
                lines.append(f"  Evidence: {edge['evidence']}")
        
        return "\n".join(lines)
