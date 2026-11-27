---
name: keenable-search
description: Web search with optional page Markdown for each result using the Keenable Search and Fetch APIs
metadata:
    skill-author: Keenable
---

# Keenable Search

Search the web through the Keenable Search API. Returns title, URL, snippet and publish date (when known) per result. With `--fetch`, it also reads each result through the Keenable Fetch API in one extra call and keeps up to `--max-content` characters of Markdown per result.

Needs `KEENABLE_API_KEY`. Without a key, the keyless public endpoint is used only if you opt in with `--keyless` or `KEENABLE_KEYLESS=1`.

## Capabilities

- Web search with title, URL, snippet and publish date per result
- Restrict to one domain with `--site`, or leave domains out with `--exclude-domain`
- Date filters with `--published-after` and `--published-before`
- Page Markdown for each result with `--fetch`, truncated locally to `--max-content`
- JSON output on stdout by default for chaining into other skills

## Usage

### Basic search:
```bash
python3 {baseDir}/scripts/keenable_search.py --query "CRISPR base editing efficiency"
```

### One journal, recent papers only:
```bash
python3 {baseDir}/scripts/keenable_search.py --query "CRISPR base editing efficiency" --site nature.com --published-after 2025-01-01
```

### Search and read the pages:
```bash
python3 {baseDir}/scripts/keenable_search.py --query "AlphaFold3 accuracy" --fetch --max-results 3
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--query` | Search query | Required |
| `--max-results`, `--limit` | Maximum results (1 to 50) | 10 |
| `--site` | Only return results from this domain | None |
| `--exclude-domain` | Leave out results from this domain (repeatable) | None |
| `--published-after` | Only pages published on or after this date (YYYY-MM-DD) | None |
| `--published-before` | Only pages published before this date (YYYY-MM-DD) | None |
| `--fetch` | Also return page Markdown for each result | False |
| `--max-content` | Characters of Markdown kept per result when `--fetch` is set | 4000 |
| `--format` | Output format: json, summary, detailed | json |
| `--api-key` | Keenable API key (falls back to `KEENABLE_API_KEY`) | None |
| `--keyless` | Use the keyless public endpoint when no key is set (also `KEENABLE_KEYLESS=1`) | False |
| `--timeout` | Request timeout in seconds | 30 |

## Output Format

```json
{
  "query": "CRISPR base editing efficiency",
  "source": "keenable",
  "count": 1,
  "results": [
    {
      "position": 1,
      "title": "...",
      "url": "https://nature.com/articles/...",
      "description": "...",
      "published_at": "2025-11-18T00:00:00Z"
    }
  ],
  "summary": "Found 1 results for 'CRISPR base editing efficiency'"
}
```

With `--fetch`, results can also carry a `markdown` field, truncated to `--max-content` characters, and a `markdown_truncated` flag. A page that could not be read gets a `fetch_error` field instead; the other results are still returned.

## Setup

```bash
export KEENABLE_API_KEY=your-key
```

Or pass it with `--api-key`. Get a key at https://app.keenable.ai. To try it without a key, add `--keyless` (rate-limited per IP).

## Notes

- Uses `POST https://api.keenable.ai/v1/search` and `POST https://api.keenable.ai/v1/fetch` (`/v1/search/public` and `/v1/fetch/public` when keyless). Requests carry `X-Keenable-Title: scienceclaw` to name the app
- Keenable logs requests, keyed or keyless, under its default data policy
- Status messages go to stderr, so stdout is always parseable JSON by default
