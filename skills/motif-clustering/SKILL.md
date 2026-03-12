# motif-clustering

Clusters melodic motifs using scikit-learn (KMeans or hierarchical clustering) with optional UMAP projection. Takes motif JSON (from motif-detection) and groups them by interval similarity.

## Usage

```bash
python3 skills/motif-clustering/scripts/motif_clustering.py --query "bach motifs" --n-clusters 8 --method kmeans
python3 skills/motif-clustering/scripts/motif_clustering.py --query "bach motifs" --method hierarchical
```

## Output

```json
{
  "method": "kmeans",
  "n_clusters": 8,
  "clusters": [
    {
      "cluster_id": 0,
      "n_members": 12,
      "centroid_intervals": [2, -1, 2],
      "genre_distribution": {"baroque": 8, "folk": 4},
      "top_motifs": ["m_0001", "m_0012"]
    }
  ],
  "silhouette_score": 0.47,
  "inertia": 234.5
}
```

## Dependencies

- scikit-learn
- music21
