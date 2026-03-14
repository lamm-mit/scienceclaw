---
name: minerals-news-monitor
description: Discover critical-minerals and materials signals from newspapers, blogs, and industry media using web search, with normalized policy/commodity tagging
metadata:
  openclaw:
    emoji: "📰"
    requires:
      bins:
        - python3
---

# Minerals News Monitor

Discover relevant links from newspapers, blogs, and industry outlets for critical minerals and materials topics.

## Usage

```bash
# Broad monitoring
python3 {baseDir}/scripts/news_monitor.py --query "critical minerals" --max-results 20

# Commodity/country targeted monitoring
python3 {baseDir}/scripts/news_monitor.py \
  --commodity lithium --commodity cobalt \
  --country china --country canada \
  --format json

# Blogs only
python3 {baseDir}/scripts/news_monitor.py --query "battery materials" --source-type blogs
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Base search query | critical minerals |
| `--commodity` | Commodity term (repeatable) | - |
| `--country` | Country term (repeatable) | - |
| `--max-results` | Max records returned | 20 |
| `--source-type` | all, news, blogs | all |
| `--format` | summary, detailed, json | summary |

## Output Schema

Each record includes:
`url`, `source`, `published_at`, `title`, `summary`, `commodity_tags`, `country_tags`, `policy_signal`, `confidence`, `retrieved_at`, `source_type`.

## Notes

- Uses DuckDuckGo HTML results (no API key required).
- Designed for discovery; use `minerals-web-ingest` to fetch full content and persist hashes.
