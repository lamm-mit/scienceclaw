---
name: corpus-search
description: Semantic search over critical minerals PDF corpus — rare earth, lithium, cobalt, nickel supply chain, trade policy, extraction, and materials research via Pinecone
metadata:
  openclaw:
    emoji: "📑"
    requires:
      bins:
        - python3
      env:
        - PINECONE_API_KEY
---

# Corpus Search — Critical Minerals PDF Corpus

Semantic search over a local collection of critical minerals PDFs (USGS, UN Comtrade, World Bank, SEC, WTO, Mindat, MinCan reports). Documents are chunked, embedded with `llama-text-embed-v2`, and stored in a Pinecone index for fast similarity search.

## Usage

### Search the corpus:
```bash
python3 {baseDir}/scripts/search_corpus.py --query "rare earth separation techniques"
```

### Filter by commodity:
```bash
python3 {baseDir}/scripts/search_corpus.py --query "supply chain risks" --commodity lithium
```

### Filter by source organization:
```bash
python3 {baseDir}/scripts/search_corpus.py --query "trade flows" --source Comtrade
```

### Reranked results (higher quality):
```bash
python3 {baseDir}/scripts/search_corpus.py --query "cobalt extraction" --rerank --top-k 20
```

### JSON output:
```bash
python3 {baseDir}/scripts/search_corpus.py --query "graphite processing" --format json
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Semantic search query | Required |
| `--commodity` | Filter by commodity keyword (e.g., lithium, cobalt, rare earth) | - |
| `--source` | Filter by source organization (e.g., USGS, Comtrade, SEC) | - |
| `--top-k` | Number of results to retrieve | 10 |
| `--rerank` | Enable reranking with pinecone-rerank-v0 | false |
| `--format` | Output format: summary, detailed, json | summary |
| `--index-name` | Pinecone index name | scienceclaw-minerals-corpus |

## Ingestion

Before searching, ingest PDFs into the Pinecone index:

```bash
# Dry run — list PDFs that would be ingested:
python3 {baseDir}/scripts/ingest_corpus.py --corpus-dir ~/critical-minerals-data/ --dry-run

# Ingest all PDFs:
python3 {baseDir}/scripts/ingest_corpus.py --corpus-dir ~/critical-minerals-data/

# Force re-ingest (ignore manifest):
python3 {baseDir}/scripts/ingest_corpus.py --corpus-dir ~/critical-minerals-data/ --force-reingest
```

### Ingestion Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--corpus-dir` | Directory containing PDFs | ~/critical-minerals-data/ |
| `--index-name` | Pinecone index name | scienceclaw-minerals-corpus |
| `--force-reingest` | Re-ingest all files, ignoring manifest | false |
| `--dry-run` | List files without ingesting | false |

## Notes

- Requires `PINECONE_API_KEY` environment variable
- PDFs are chunked at ~600 tokens with 100-token overlap
- Source organization is auto-detected from directory name (e.g., `usgs/`, `sec/`)
- Commodity is auto-detected via keyword scanning
- Incremental updates: only new or modified files are re-ingested (SHA-256 manifest)
- Reranking uses `pinecone-rerank-v0` for higher quality results at the cost of latency
