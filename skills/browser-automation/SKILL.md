---
name: browser-automation
description: Playwright-based browser automation for scraping JavaScript-rendered scientific databases
metadata:
---

## Overview

Web browser automation using Playwright for scraping JavaScript-rendered scientific databases, automating form submissions, and capturing dynamic content unavailable via static scraping. Renders pages fully (including React/Vue/Angular SPAs) and extracts clean text content.

Useful for databases that require JavaScript to display data, interactive tools that need form interaction, and pages where content loads asynchronously after the initial HTML response.

## Usage

```bash
# Fetch a JavaScript-rendered page
python3 skills/browser-automation/scripts/browser_fetch.py \
  --url "https://www.rcsb.org/structure/1TUP"

# Wait for specific element before extracting
python3 skills/browser-automation/scripts/browser_fetch.py \
  --url "https://www.ncbi.nlm.nih.gov/gene/672" \
  --wait-for ".gene-summary"

# Extract text content
python3 skills/browser-automation/scripts/browser_fetch.py \
  --url "https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL25/" \
  --extract-text

# Save screenshot
python3 skills/browser-automation/scripts/browser_fetch.py \
  --url "https://alphafold.ebi.ac.uk/entry/P04637" \
  --screenshot /tmp/p53_alphafold.png
```

## Output Format

```json
{
  "url": "https://www.rcsb.org/structure/1TUP",
  "content": "1TUP Structure Summary\n\nTumor suppressor p53 bound to DNA...",
  "title": "RCSB PDB - 1TUP",
  "status": "success"
}
```

## Setup

Install Playwright and its browser binaries:

```bash
pip install playwright
playwright install chromium
```
