---
name: firecrawl-scraper
description: Web scraping of JavaScript-rendered scientific websites using Firecrawl API
metadata:
  openclaw:
    emoji: "🕷️"
    requires:
      bins:
        - python3
---

## Overview

Web scraping using the Firecrawl API for JavaScript-rendered scientific websites, database pages, and literature sources. Returns clean Markdown content optimized for LLM processing. Handles dynamic content, authentication flows, and complex single-page applications that static scrapers cannot access.

Particularly useful for scraping scientific databases with JavaScript-heavy frontends, preprint servers, supplementary data pages, and research institution websites.

## Usage

```bash
# Scrape a scientific database page as markdown
python3 skills/firecrawl-scraper/scripts/firecrawl_scrape.py --url "https://www.uniprot.org/uniprotkb/P53_HUMAN"

# Scrape and return raw HTML
python3 skills/firecrawl-scraper/scripts/firecrawl_scrape.py --url "https://www.rcsb.org/structure/1TUP" --format html

# Use explicit API key
python3 skills/firecrawl-scraper/scripts/firecrawl_scrape.py \
  --url "https://www.biorxiv.org/content/10.1101/2024.01.01.000001" \
  --api-key fc-yourkey123 \
  --format markdown
```

## Output Format

```json
{
  "url": "https://www.uniprot.org/uniprotkb/P53_HUMAN",
  "content": "# Cellular tumor antigen p53\n\n**Organism:** Homo sapiens...",
  "format": "markdown",
  "title": "P53_HUMAN - Cellular tumor antigen p53",
  "links": [
    "https://www.uniprot.org/uniprotkb/P04637",
    "https://www.rcsb.org/structure/2OCJ"
  ]
}
```

## Setup

Set your Firecrawl API key as an environment variable:

```bash
export FIRECRAWL_API_KEY=fc-yourkey123
```

Or pass it directly via `--api-key`. Get a key at https://firecrawl.dev.
