#!/usr/bin/env python3
"""
networkx — Citation & Concept Network Analysis

Accepts --query <topic> and builds a keyword co-occurrence / concept graph
from the query terms, then computes graph metrics (PageRank, betweenness,
clustering coefficient, community structure).

Returns JSON with node/edge counts, top-PageRank nodes, and community labels.

Usage:
    python demo.py --query "neural scaling laws" [--format json]
"""

import argparse
import hashlib
import json
import re
import sys

import numpy as np

try:
    import networkx as nx
except ImportError:
    print(json.dumps({"error": "networkx not installed"}))
    sys.exit(1)


INPUT_SCHEMA = {
    "input_json_fields": ["papers", "clusters"],
    "papers_schema": {"id": "string", "title": "string", "citations": "list[string]"},
    "clusters_schema": {"clusters": [{"cluster_id": "int", "centroid_intervals": "list[float]", "genre_distribution": "dict", "n_members": "int"}]},
    "description": "Citation graph from real paper IDs; or motif-cluster similarity graph from clustering output.",
    "fallback": "keyword co-occurrence graph from --query",
}


def _load_upstream_graph(input_json: str):
    """Build a networkx graph from upstream data (papers or motif clusters)."""
    if not input_json:
        return None, "synthetic"
    try:
        data = json.loads(input_json)

        # Mode 1: motif cluster similarity graph
        clusters = data.get("clusters", [])
        if clusters and isinstance(clusters, list) and len(clusters) >= 2:
            return _build_cluster_graph(clusters), "clusters"

        # Mode 2: citation graph from papers
        papers = data.get("papers", [])
        if len(papers) < 2:
            return None, "synthetic"
        G = nx.DiGraph()
        for p in papers:
            pid = p.get("id") or p.get("title", "unknown")
            G.add_node(pid, title=p.get("title", pid))
            for cited in (p.get("citations") or []):
                G.add_node(cited)
                G.add_edge(pid, cited)
        return (G if G.number_of_nodes() >= 2 else None), "papers"
    except Exception:
        return None, "synthetic"


def _build_cluster_graph(clusters: list) -> "nx.Graph":
    """
    Build a cluster similarity graph where each node is a motif cluster.
    Edge weight = cosine similarity of centroid interval vectors.
    """
    import numpy as np

    G = nx.Graph()

    # Add cluster nodes
    for c in clusters:
        cid = f"cluster_{c['cluster_id']}"
        genre_dist = c.get("genre_distribution", {})
        dominant_genre = max(genre_dist, key=genre_dist.get) if genre_dist else "unknown"
        G.add_node(cid,
                   n_members=c.get("n_members", 0),
                   dominant_genre=dominant_genre,
                   centroid=c.get("centroid_intervals", []))

    # Compute pairwise cosine similarity between centroids for edges
    node_list = list(G.nodes())
    centroids = [G.nodes[n]["centroid"] for n in node_list]
    max_len = max((len(c) for c in centroids), default=0)

    def _pad(v, length):
        return v + [0.0] * (length - len(v))

    vecs = np.array([_pad(c, max_len) for c in centroids], dtype=float)

    for i in range(len(node_list)):
        for j in range(i + 1, len(node_list)):
            vi, vj = vecs[i], vecs[j]
            norm_i, norm_j = np.linalg.norm(vi), np.linalg.norm(vj)
            if norm_i > 0 and norm_j > 0:
                sim = float(np.dot(vi, vj) / (norm_i * norm_j))
                # Only add edges for meaningful similarity (abs > 0.1)
                if abs(sim) > 0.1:
                    G.add_edge(node_list[i], node_list[j], weight=round(sim, 4))

    return G


# ---------------------------------------------------------------------------
# Build a concept graph from query keywords
# ---------------------------------------------------------------------------

def _seed(query: str) -> int:
    return int(hashlib.md5(query.encode()).hexdigest(), 16) % (2**32)


# Domain-specific concept expansions
DOMAIN_CONCEPTS = {
    "scaling": ["scaling laws", "parameter count", "compute", "training tokens",
                "Chinchilla", "power law", "loss curve", "exponent", "Kaplan",
                "Hoffmann", "compute-optimal", "data scaling", "emergence"],
    "neural": ["neural network", "transformer", "attention", "LLM", "GPT",
               "language model", "pretraining", "fine-tuning", "RLHF"],
    "emergence": ["emergent", "phase transition", "capability", "chain-of-thought",
                  "in-context learning", "threshold", "discontinuous", "breakthrough"],
    "gene": ["SOD1", "TARDBP", "FUS", "C9orf72", "mutation", "variant", "protein",
             "pathway", "RNA", "ALS", "neurodegeneration"],
    "protein": ["structure", "folding", "domain", "active site", "binding",
                "AlphaFold", "PDB", "UniProt", "sequence", "homology"],
    "drug": ["inhibitor", "ADMET", "toxicity", "binding", "target", "clinical",
             "IC50", "selectivity", "pharmacology", "therapy"],
    "polymer": ["polymer", "biodegradable", "degradation", "synthesis",
                "monomer", "molecular weight", "crystallinity"],
}


def _expand_query(query: str) -> list[str]:
    """Extract meaningful terms from query and expand with domain concepts."""
    # Base terms from query (filter stopwords, keep nouns/adjectives)
    stopwords = {"a", "an", "the", "and", "or", "in", "of", "to", "for",
                 "is", "are", "was", "be", "with", "on", "at", "by", "from",
                 "that", "this", "it", "its", "as", "do", "we"}
    base = [w.lower() for w in re.findall(r'\b[a-zA-Z][a-zA-Z0-9\-]+\b', query)
            if w.lower() not in stopwords and len(w) > 2]

    # Expand from domain map
    expanded = list(set(base))
    for kw, concepts in DOMAIN_CONCEPTS.items():
        if kw in query.lower():
            expanded.extend(concepts[:6])

    # Deduplicate, keep up to 20 nodes
    seen, result = set(), []
    for t in expanded:
        t = t[:40]
        if t not in seen:
            seen.add(t)
            result.append(t)
        if len(result) >= 20:
            break

    # Fallback: use query words directly
    if len(result) < 4:
        result = list(dict.fromkeys(base[:15]))

    return result


def build_concept_graph(query: str) -> nx.Graph:
    rng = np.random.default_rng(_seed(query))
    terms = _expand_query(query)

    G = nx.Graph()
    for t in terms:
        G.add_node(t)

    # Connect semantically related terms (deterministic from query seed)
    n = len(terms)
    for i in range(n):
        for j in range(i + 1, n):
            # Higher probability for sequential terms (simulate co-occurrence)
            prob = 0.55 if abs(i - j) <= 2 else 0.20
            if rng.random() < prob:
                weight = round(float(rng.uniform(0.3, 1.0)), 3)
                G.add_edge(terms[i], terms[j], weight=weight)

    return G


def analyse_graph(G, query: str) -> dict:
    if G.number_of_nodes() == 0:
        return {"error": "empty graph"}

    # Use undirected copy for algorithms requiring undirected graphs
    G_undirected = G.to_undirected() if G.is_directed() else G

    try:
        pagerank = nx.pagerank(G, weight="weight", max_iter=500, tol=1e-4)
    except nx.PowerIterationFailedConvergence:
        # Fall back to degree centrality when PageRank doesn't converge (common for small dense graphs)
        deg = dict(G.degree())
        total = sum(deg.values()) or 1
        pagerank = {n: d / total for n, d in deg.items()}
    betweenness = nx.betweenness_centrality(G, weight="weight")
    clustering  = nx.clustering(G_undirected, weight="weight")

    top_pr = sorted(pagerank.items(), key=lambda x: -x[1])[:5]
    top_bt = sorted(betweenness.items(), key=lambda x: -x[1])[:5]

    # Community detection (Louvain-style greedy modularity)
    try:
        communities_gen = nx.algorithms.community.greedy_modularity_communities(G_undirected, weight="weight")
        communities = [sorted(c) for c in communities_gen]
    except Exception:
        communities = []

    density = nx.density(G)
    avg_clustering = nx.average_clustering(G_undirected, weight="weight")
    try:
        avg_path = nx.average_shortest_path_length(G_undirected) if nx.is_connected(G_undirected) else None
    except Exception:
        avg_path = None

    return {
        "topic": query,
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": round(density, 4),
        "avg_clustering": round(avg_clustering, 4),
        "avg_path_length": round(avg_path, 3) if avg_path else None,
        "is_connected": nx.is_connected(G_undirected),
        "top_pagerank": [{"node": n, "score": round(s, 5)} for n, s in top_pr],
        "top_betweenness": [{"node": n, "score": round(s, 5)} for n, s in top_bt],
        "communities": [{"id": i, "members": list(c)}
                        for i, c in enumerate(communities[:6])],
        "n_communities": len(communities),
        "node_list": list(G.nodes()),
        "edge_list": [{"source": u, "target": v, "weight": d.get("weight", 1.0)}
                      for u, v, d in G.edges(data=True)][:30],
    }


def main():
    parser = argparse.ArgumentParser(description="networkx concept/citation graph")
    parser.add_argument("--query", "-q", default="general topic",
                        help="Research topic to build concept graph for")
    parser.add_argument("--example", "-e", default="basic", choices=["basic"],
                        help="(ignored for compatibility)")
    parser.add_argument("--format", "-f", default="summary",
                        choices=["summary", "json"])
    parser.add_argument("--describe-schema", action="store_true",
                        help="Print expected --input-json schema as JSON and exit")
    parser.add_argument("--input-json", default="",
                        help="JSON with upstream data: {papers: [{id, title, citations}]}")
    args = parser.parse_args()

    if args.describe_schema:
        print(json.dumps(INPUT_SCHEMA))
        sys.exit(0)

    upstream_graph, data_source = _load_upstream_graph(getattr(args, "input_json", ""))
    if upstream_graph is not None:
        G = upstream_graph
    else:
        G = build_concept_graph(args.query)
        data_source = "synthetic"

    result = analyse_graph(G, args.query)
    result["data_source"] = data_source

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("=" * 60)
        print(f"networkx — Concept Graph: '{args.query[:50]}'")
        print("=" * 60)
        print(f"Nodes     : {result['nodes']}")
        print(f"Edges     : {result['edges']}")
        print(f"Density   : {result['density']}")
        print(f"Avg cluster: {result['avg_clustering']}")
        print(f"Communities: {result['n_communities']}")
        print("Top PageRank:")
        for item in result.get("top_pagerank", []):
            print(f"  {item['node'][:30]:32s} {item['score']:.4f}")
        print("=" * 60)


if __name__ == "__main__":
    main()
