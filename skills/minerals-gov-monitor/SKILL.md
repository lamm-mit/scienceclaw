---
name: minerals-gov-monitor
description: Monitor government and regulator releases relevant to critical minerals and materials via domain-targeted web discovery with policy tagging
metadata:
  openclaw:
    emoji: "🏛️"
    requires:
      bins:
        - python3
---

# Minerals Government Monitor

Monitor policy and release signals from government and regulator domains (US, EU, UK, Canada, Australia, OECD by default).

## Usage

```bash
# Default government domain set
python3 {baseDir}/scripts/gov_monitor.py --commodity lithium --commodity rare_earth

# Custom domain allowlist
python3 {baseDir}/scripts/gov_monitor.py \
  --domains usgs.gov,energy.gov,europa.eu,gov.uk \
  --country china --country united states --format json
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--domains` | Comma-separated domain allowlist | built-in gov list |
| `--commodity` | Commodity term (repeatable) | - |
| `--country` | Country term (repeatable) | - |
| `--max-results` | Max records returned | 25 |
| `--format` | summary, detailed, json | summary |

## Output Schema

Each record includes:
`url`, `source`, `published_at`, `title`, `summary`, `commodity_tags`, `country_tags`, `policy_signal`, `confidence`, `retrieved_at`, `source_type`, `monitor_domain`.

## Notes

- Uses domain-constrained web search (`site:domain ...`) for targeted discovery.
- Use `minerals-web-ingest` to fetch and store full content for downstream indexing.
