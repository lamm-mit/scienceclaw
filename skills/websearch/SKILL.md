---
name: websearch
description: Search the web for scientific information using DuckDuckGo
metadata:
  {
    "openclaw": {
      "emoji": "🔍",
      "requires": {
        "bins": ["python3"]
      }
    }
  }
---

# Web Search

Search the web for scientific information using DuckDuckGo (no API key required).

## Usage

### Basic search:
```bash
python3 {baseDir}/scripts/web_search.py --query "CRISPR gene editing mechanism"
```

### Science-focused search:
```bash
python3 {baseDir}/scripts/web_search.py --query "protein folding" --science
```

### Get more results:
```bash
python3 {baseDir}/scripts/web_search.py --query "AlphaFold structure prediction" --max-results 20
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Search query | Required |
| `--max-results` | Maximum results | 10 |
| `--science` | Add science-focused terms | False |
| `--format` | Output format: summary, detailed, json | summary |

## Examples

```bash
# General science search
python3 {baseDir}/scripts/web_search.py --query "machine learning drug discovery"

# Focused biology search
python3 {baseDir}/scripts/web_search.py --query "kinase inhibitor cancer" --science

# JSON output for parsing
python3 {baseDir}/scripts/web_search.py --query "CRISPR" --format json
```

## Notes

- Uses DuckDuckGo HTML search (no API key needed)
- Results include title, URL, and snippet
- Add `--science` to focus on scientific sources
