---
name: minerals-web-ingest
description: Ingest and normalize web pages for critical-minerals intelligence, with optional Firecrawl fetching, deduplication manifest, and JSONL export
metadata:
  openclaw:
    emoji: "🧾"
    requires:
      bins:
        - python3
      env:
        - FIRECRAWL_API_KEY
---

# Minerals Web Ingest

Fetch and normalize full-page content from discovered URLs, deduplicate by content hash, and emit records suitable for indexing and analysis.

## Usage

```bash
# Ingest URLs from monitor output
python3 {baseDir}/scripts/web_ingest.py \
  --input-json monitor_records.json \
  --output-jsonl ingested_records.jsonl \
  --format summary

# Direct URL ingest
python3 {baseDir}/scripts/web_ingest.py \
  --url https://www.energy.gov/articles/example \
  --url https://www.usgs.gov/news/example \
  --format json

# Prefer Firecrawl (if FIRECRAWL_API_KEY is set)
python3 {baseDir}/scripts/web_ingest.py --input-json gov_records.json --prefer-firecrawl
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--input-json` | JSON input file with URL records | - |
| `--url` | Direct URL input (repeatable) | - |
| `--output-jsonl` | Optional JSONL output path | - |
| `--manifest-path` | URL->content hash dedupe manifest | `~/.scienceclaw/minerals_web_ingest_manifest.json` |
| `--timeout` | HTTP timeout seconds | 30 |
| `--max-chars` | Max chars stored per page | 12000 |
| `--prefer-firecrawl` | Use Firecrawl first, fallback to requests | false |
| `--format` | summary, detailed, json | summary |

## Output Schema

Ingested records include:
`url`, `source`, `published_at`, `title`, `summary`, `commodity_tags`, `country_tags`, `policy_signal`, `confidence`, `retrieved_at`, `source_type`, `content`, `content_hash`.

## Notes

- If Firecrawl is unavailable or fails, script falls back to requests + BeautifulSoup extraction.
- Manifest-based dedupe prevents reprocessing unchanged pages.
- Use this output as input to corpus indexing or profile-generation pipelines.
