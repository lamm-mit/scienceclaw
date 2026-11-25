---
name: firecrawl-search
description: Web search with optional page Markdown for each result using the Firecrawl Search API
metadata:
    skill-author: Firecrawl
---

# Firecrawl Search

Search the web through the Firecrawl Search API. Returns title, URL and description per result. With `--scrape`, it also requests clean Markdown for each result in the same call and keeps up to `--max-content` characters per result. Works without an API key on Firecrawl's keyless tier; set `FIRECRAWL_API_KEY` for higher rate limits.

Companion to `firecrawl-scraper`: use this skill to find pages, and `firecrawl-scraper` when you already have the URL.

## Capabilities

- Web search with title, URL and description per result
- Page Markdown in the same call with `--scrape`, truncated locally to `--max-content`
- Restrict results to academic hosts with `--science`, or filter by `--category research|pdf|developer`
- Time filters with `--tbs` (for example `qdr:w` for the past week)
- JSON output on stdout by default for chaining into other skills

## Usage

### Basic search:
```bash
python3 {baseDir}/scripts/firecrawl_search.py --query "CRISPR base editing efficiency"
```

### Science-focused search:
```bash
python3 {baseDir}/scripts/firecrawl_search.py --query "protein folding" --science
```

### Search and read the pages in one call:
```bash
python3 {baseDir}/scripts/firecrawl_search.py --query "AlphaFold3 accuracy benchmarks" --scrape --max-results 3
```

### Recent results only:
```bash
python3 {baseDir}/scripts/firecrawl_search.py --query "lithium solid electrolyte" --tbs qdr:m
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Search query | Required |
| `--max-results`, `--limit` | Maximum results (1 to 100) | 10 |
| `--science` | Restrict to academic hosts (NCBI, Nature, Science, PubMed, bioRxiv) | False |
| `--category` | Filter by `research`, `pdf` or `developer` | None |
| `--tbs` | Time filter: `qdr:h`, `qdr:d`, `qdr:w`, `qdr:m`, `qdr:y`, or `sbd:1` to sort by date | None |
| `--scrape` | Also return page Markdown for each result | False |
| `--max-content` | Characters of Markdown kept per result when `--scrape` is set | 4000 |
| `--format` | Output format: json, summary, detailed | json |
| `--api-key` | Firecrawl API key (falls back to `FIRECRAWL_API_KEY`) | None |
| `--timeout` | Request timeout in seconds | 30 |

## Examples

```bash
# General science search
python3 {baseDir}/scripts/firecrawl_search.py --query "machine learning drug discovery"

# Academic hosts only, human-readable output
python3 {baseDir}/scripts/firecrawl_search.py --query "kinase inhibitor cancer" --science --format summary

# PDFs only
python3 {baseDir}/scripts/firecrawl_search.py --query "perovskite solar cell stability review" --category pdf

# JSON output for parsing (the default)
python3 {baseDir}/scripts/firecrawl_search.py --query "CRISPR" --format json
```

## Output Format

```json
{
  "query": "CRISPR base editing efficiency",
  "source": "firecrawl",
  "count": 2,
  "results": [
    {
      "position": 1,
      "title": "Base editing: precision chemistry on the genome ...",
      "url": "https://www.nature.com/articles/s41576-018-0059-1",
      "description": "Base editors enable direct, irreversible conversion of one base pair to another ..."
    },
    {
      "position": 2,
      "title": "Improving base editing efficiency ...",
      "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
      "description": "..."
    }
  ],
  "summary": "Found 2 results for 'CRISPR base editing efficiency'"
}
```

With `--category`, each result also carries a `category` field (`research`, `pdf` or `developer`). With `--scrape`, results can also carry a `markdown` field, truncated to `--max-content` characters, and a `markdown_truncated` flag. Any API `warnings` are passed through at the top level.

## Setup

No key is required to get started. For higher rate limits, set a Firecrawl API key as an environment variable:

```bash
export FIRECRAWL_API_KEY=fc-yourkey123
```

Or pass it directly via `--api-key`. Get a key at https://www.firecrawl.dev/.

## Notes

- Uses `POST https://api.firecrawl.dev/v2/search`
- With an API key, search costs 2 credits per 10 results, rounded up. `--scrape` adds 1 credit per web page (1 credit per page for PDFs), so keep `--max-results` small when scraping. Keyless calls are rate-limited per IP instead of billed; when the limit is hit the script returns a JSON error with the retry time
- `--science` uses Firecrawl's `includeDomains` filter with the same hosts the `websearch` skill targets
- `--category research` returns academic web pages under `data.web` today. After Firecrawl's 2026-11-16 change it returns paper records (`paperId`, `primaryId`, `abstract`, `score`) under `data.research`, with no page URL or scraped Markdown. The script reads both shapes and resolves `arxiv:` and `doi:` identifiers to URLs
- Status messages go to stderr, so stdout is always parseable JSON by default
