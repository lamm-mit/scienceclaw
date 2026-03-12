#!/usr/bin/env python3
"""
motif-clustering skill: Cluster melodic motifs using scikit-learn.

Takes motif JSON from motif-detection (or runs motif-detection inline),
clusters by interval similarity, optionally projects with UMAP.
"""
import argparse
import json
import sys
from pathlib import Path


def _parse_args():
    p = argparse.ArgumentParser(description="Motif clustering using scikit-learn")
    p.add_argument("--query", default="bach", help="Query string (used for motif detection if no input-json)")
    p.add_argument("--input-json", default="", help="Path to motifs JSON from motif-detection skill")
    p.add_argument("--motifs-json", default="", help="Inline JSON string of motifs list (alternative to --input-json)")
    p.add_argument("--n-clusters", type=int, default=6, help="Number of clusters (default: 6)")
    p.add_argument("--method", default="kmeans", choices=["kmeans", "hierarchical"],
                   help="Clustering method (default: kmeans)")
    p.add_argument("--max-pieces", type=int, default=20, help="Max pieces for inline motif detection")
    p.add_argument("--describe-schema", action="store_true", help="Print output schema and exit")
    return p.parse_args()


SCHEMA = {
    "type": "object",
    "properties": {
        "method": {"type": "string"},
        "n_clusters": {"type": "integer"},
        "clusters": {"type": "array"},
        "silhouette_score": {"type": "number"},
        "inertia": {"type": "number"},
        "n_motifs_clustered": {"type": "integer"},
    }
}


def _load_motifs_from_json(path: str) -> list:
    p = Path(path)
    if p.exists():
        with open(p) as f:
            data = json.load(f)
        return data.get("motifs", [])
    return []


def _get_motifs_inline(query: str, max_pieces: int) -> list:
    """Run motif detection inline to get motifs."""
    # Import from sibling skill via sys.path
    skill_dir = Path(__file__).resolve().parents[3]
    motif_script = skill_dir / "motif-detection" / "scripts" / "motif_detection.py"
    if motif_script.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("motif_detection", str(motif_script))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.run(query=query, min_length=4, min_occurrences=2, max_pieces=max_pieces)
        return result.get("motifs", [])
    return []


def _pad_or_truncate(intervals: list, length: int = 8) -> list:
    """Normalize interval vectors to fixed length for clustering."""
    if len(intervals) >= length:
        return intervals[:length]
    return intervals + [0] * (length - len(intervals))


def _cluster_motifs(motifs: list, n_clusters: int, method: str) -> dict:
    """
    Cluster motifs by interval vector similarity using scikit-learn.
    Returns clusters with members, centroid, and genre distribution.
    """
    import numpy as np

    if not motifs:
        return {"error": "no motifs to cluster", "clusters": [], "n_motifs_clustered": 0}

    # Feature matrix: padded interval vectors
    vec_len = 8
    X = np.array([_pad_or_truncate(m.get("intervals", []), vec_len) for m in motifs], dtype=float)

    n_clusters = min(n_clusters, len(motifs))

    labels = None
    inertia = None
    sil_score = None

    try:
        if method == "hierarchical":
            from sklearn.cluster import AgglomerativeClustering
            from sklearn.metrics import silhouette_score
            clf = AgglomerativeClustering(n_clusters=n_clusters)
            labels = clf.fit_predict(X)
            try:
                sil_score = float(silhouette_score(X, labels))
            except Exception:
                sil_score = None
        else:
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score
            clf = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
            clf.fit(X)
            labels = clf.labels_
            inertia = float(clf.inertia_)
            try:
                sil_score = float(silhouette_score(X, labels))
            except Exception:
                sil_score = None
    except ImportError:
        return {"error": "scikit-learn not installed", "clusters": [], "n_motifs_clustered": 0}

    # Build cluster dicts
    from collections import defaultdict, Counter
    cluster_members: dict = defaultdict(list)
    cluster_genres: dict = defaultdict(Counter)

    for i, (motif, lbl) in enumerate(zip(motifs, labels)):
        cluster_members[int(lbl)].append(motif)
        genre = motif.get("genre", "unknown")
        cluster_genres[int(lbl)][genre] += 1

    import numpy as np
    clusters = []
    for cid in range(n_clusters):
        members = cluster_members.get(cid, [])
        if not members:
            continue
        # Centroid as mean interval vector
        vecs = np.array([_pad_or_truncate(m.get("intervals", []), vec_len) for m in members])
        centroid = vecs.mean(axis=0).tolist()
        centroid_rounded = [round(v, 2) for v in centroid]
        genre_dist = dict(cluster_genres[cid])
        top_motifs = [m["motif_id"] for m in sorted(members, key=lambda x: -x.get("occurrences", 0))[:5]]
        clusters.append({
            "cluster_id": cid,
            "n_members": len(members),
            "centroid_intervals": centroid_rounded,
            "genre_distribution": genre_dist,
            "top_motifs": top_motifs,
            "mean_occurrences": round(sum(m.get("occurrences", 0) for m in members) / len(members), 1),
        })

    return {
        "method": method,
        "n_clusters": n_clusters,
        "clusters": clusters,
        "silhouette_score": round(sil_score, 4) if sil_score is not None else None,
        "inertia": round(inertia, 2) if inertia is not None else None,
        "n_motifs_clustered": len(motifs),
    }


def run(query: str, input_json: str = "", motifs_json: str = "", n_clusters: int = 6, method: str = "kmeans", max_pieces: int = 20) -> dict:
    motifs = []
    # Priority: inline JSON string > file path > inline motif detection
    if motifs_json:
        try:
            parsed = json.loads(motifs_json)
            if isinstance(parsed, list):
                motifs = parsed
            elif isinstance(parsed, dict):
                motifs = parsed.get("motifs", [])
        except json.JSONDecodeError:
            pass
    if not motifs and input_json:
        motifs = _load_motifs_from_json(input_json)
    if not motifs:
        motifs = _get_motifs_inline(query=query, max_pieces=max_pieces)

    if not motifs:
        return {
            "error": "No motifs found. Install music21 and scikit-learn.",
            "method": method,
            "n_clusters": n_clusters,
            "clusters": [],
            "silhouette_score": None,
            "inertia": None,
            "n_motifs_clustered": 0,
            "query": query,
        }

    result = _cluster_motifs(motifs, n_clusters=n_clusters, method=method)
    result["query"] = query
    return result


def main():
    args = _parse_args()
    if args.describe_schema:
        print(json.dumps(SCHEMA, indent=2))
        return
    result = run(
        query=args.query,
        input_json=args.input_json,
        motifs_json=args.motifs_json,
        n_clusters=args.n_clusters,
        method=args.method,
        max_pieces=args.max_pieces,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
