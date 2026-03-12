#!/usr/bin/env python3
"""
umap-learn — Uniform Manifold Approximation and Projection

Accepts --query <topic> and embeds a synthetic high-dimensional dataset
(whose cluster structure reflects the query domain) into 2D using UMAP.
Returns JSON with 2D coordinates, cluster labels, and embedding statistics.

Usage:
    python demo.py --query "neural scaling laws" [--format json]
"""

import argparse
import hashlib
import json
import sys

import numpy as np

try:
    import umap
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
except ImportError as e:
    print(json.dumps({"error": f"missing dependency: {e}"}))
    sys.exit(1)


INPUT_SCHEMA = {
    "input_json_fields": ["vectors", "labels"],
    "vectors_schema": {"vectors": "list[list[number]]", "labels": "list[string]"},
    "description": "UMAP 2D embedding of real feature vectors with labels.",
    "fallback": "synthetic clustered dataset from --query",
}


def _load_upstream_vectors(input_json: str):
    """Parse vectors and labels from --input-json. Returns (array, labels) or None."""
    if not input_json:
        return None
    try:
        data = json.loads(input_json)
        vecs = data.get("vectors", [])
        labels = data.get("labels", [])
        if len(vecs) < 4:
            return None
        arr = np.array(vecs, dtype=float)
        if arr.ndim != 2:
            return None
        if not labels:
            labels = [str(i) for i in range(len(vecs))]
        return arr, labels
    except Exception:
        return None


def _seed(query: str) -> int:
    return int(hashlib.md5(query.encode()).hexdigest(), 16) % (2**32)


DOMAIN_CLUSTERS = {
    "scaling": ["parameter-scaling", "data-scaling", "compute-optimal",
                "emergent", "over-trained"],
    "gene":    ["pathogenic", "benign", "VUS", "splicing", "frameshift"],
    "drug":    ["CNS-active", "peripheral", "high-clearance", "low-solubility", "approved"],
    "polymer": ["biodegradable", "hydrophobic", "crosslinked", "amorphous", "crystalline"],
    "protein": ["alpha-helical", "beta-sheet", "disordered", "membrane", "soluble"],
}


def _get_clusters(query: str) -> list[str]:
    q = query.lower()
    for kw, labels in DOMAIN_CLUSTERS.items():
        if kw in q:
            return labels
    # Generic
    return [f"cluster_{i}" for i in range(4)]


def build_and_embed(query: str, n_samples: int = 120, n_dim: int = 12,
                    upstream_vectors=None) -> dict:
    rng = np.random.default_rng(_seed(query))
    data_source = "synthetic"

    if upstream_vectors is not None:
        X_raw, point_labels = upstream_vectors
        data_source = "upstream"
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_raw)
        n_neighbors = min(15, len(X_raw) - 1)
        reducer = umap.UMAP(
            n_components=2,
            n_neighbors=n_neighbors,
            min_dist=0.1,
            random_state=_seed(query) % (2**31),
        )
        embedding = reducer.fit_transform(X_scaled)
        points = [
            {"x": round(float(embedding[i, 0]), 4),
             "y": round(float(embedding[i, 1]), 4),
             "label": point_labels[i]}
            for i in range(len(X_raw))
        ]
        return {
            "topic": query,
            "n_samples": len(X_raw),
            "n_dimensions_input": X_raw.shape[1],
            "n_dimensions_output": 2,
            "data_source": data_source,
            "embedding_sample": points,
            "umap_params": {"n_neighbors": n_neighbors, "min_dist": 0.1},
        }

    cluster_labels = _get_clusters(query)
    n_clusters = len(cluster_labels)
    n_per = n_samples // n_clusters

    # Generate clustered data in high-dim space
    X_list, y_list = [], []
    centers = rng.normal(0, 3, (n_clusters, n_dim))
    for k, label in enumerate(cluster_labels):
        X_k = centers[k] + rng.normal(0, 0.8, (n_per, n_dim))
        X_list.append(X_k)
        y_list.extend([k] * n_per)

    X = np.vstack(X_list)
    y = np.array(y_list)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=15,
        min_dist=0.1,
        random_state=_seed(query) % (2**31),
    )
    embedding = reducer.fit_transform(X_scaled)

    # Compute cluster compactness in embedding space
    cluster_stats = []
    for k, label in enumerate(cluster_labels):
        mask = (y == k)
        pts = embedding[mask]
        centroid = pts.mean(axis=0)
        spread = float(np.sqrt(((pts - centroid)**2).sum(axis=1)).mean())
        cluster_stats.append({
            "label": label,
            "n_points": int(mask.sum()),
            "centroid_x": round(float(centroid[0]), 4),
            "centroid_y": round(float(centroid[1]), 4),
            "spread": round(spread, 4),
        })

    # Silhouette-like separation (between-cluster centroid distances)
    centroids = np.array([[s["centroid_x"], s["centroid_y"]] for s in cluster_stats])
    dists = []
    for i in range(len(centroids)):
        for j in range(i + 1, len(centroids)):
            d = float(np.linalg.norm(centroids[i] - centroids[j]))
            dists.append(d)
    avg_separation = round(float(np.mean(dists)), 4) if dists else 0.0

    # Sample up to 50 embedding points for JSON output
    sample_idx = rng.choice(len(X), min(50, len(X)), replace=False)
    points = [
        {"x": round(float(embedding[i, 0]), 4),
         "y": round(float(embedding[i, 1]), 4),
         "cluster": cluster_labels[int(y[i])]}
        for i in sample_idx
    ]

    return {
        "topic": query,
        "n_samples": len(X),
        "n_dimensions_input": n_dim,
        "n_dimensions_output": 2,
        "n_clusters": n_clusters,
        "cluster_labels": cluster_labels,
        "cluster_stats": cluster_stats,
        "avg_cluster_separation": avg_separation,
        "embedding_sample": points,
        "data_source": data_source,
        "umap_params": {"n_neighbors": 15, "min_dist": 0.1},
    }


def main():
    parser = argparse.ArgumentParser(description="UMAP dimensionality reduction")
    parser.add_argument("--query", "-q", default="general topic",
                        help="Research topic for embedding")
    parser.add_argument("--format", "-f", default="summary",
                        choices=["summary", "json"])
    parser.add_argument("--describe-schema", action="store_true",
                        help="Print expected --input-json schema as JSON and exit")
    parser.add_argument("--input-json", default="",
                        help="JSON with upstream data: {vectors: [[...]], labels: [...]}")
    args = parser.parse_args()

    if args.describe_schema:
        print(json.dumps(INPUT_SCHEMA))
        sys.exit(0)

    upstream_vectors = _load_upstream_vectors(getattr(args, "input_json", ""))
    result = build_and_embed(args.query, upstream_vectors=upstream_vectors)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("=" * 60)
        print(f"UMAP — 2D Embedding: '{args.query[:50]}'")
        print("=" * 60)
        print(f"Samples     : {result.get('n_samples', '?')}  ({result.get('n_dimensions_input', '?')}D → 2D)")
        n_clusters = result.get('n_clusters')
        cluster_labels = result.get('cluster_labels', [])
        if n_clusters is not None:
            print(f"Clusters    : {n_clusters}  ({', '.join(cluster_labels)})")
        avg_sep = result.get('avg_cluster_separation')
        if avg_sep is not None:
            print(f"Avg cluster separation: {avg_sep}")
        cluster_stats = result.get('cluster_stats', [])
        if cluster_stats:
            print("Cluster stats:")
            for cs in cluster_stats:
                print(f"  {cs['label']:25s} n={cs['n_points']}  spread={cs['spread']:.3f}")
        print("=" * 60)


if __name__ == "__main__":
    main()
