---
name: fabric
description: Pattern-based analysis using Fabric's 242+ specialized prompts for summarizing papers and extracting insights
metadata:
  openclaw:
    emoji: "🧵"
    requires:
      bins:
        - python3
---

## Overview

Pattern-based analysis framework with 242+ specialized prompts (Fabric patterns) for summarizing papers, extracting insights, threat modeling, and content analysis. Executes Fabric CLI patterns against text input or file content for rapid structured analysis.

Fabric patterns are expert-crafted prompts that produce consistently structured outputs. Scientific patterns include: `summarize`, `extract_wisdom`, `extract_insights`, `analyze_paper`, `create_summary`, `extract_main_idea`, and many more.

## Usage

```bash
# Summarize a scientific paper (paste text as input)
python3 skills/fabric/scripts/fabric_run.py \
  --pattern summarize \
  --input "Full paper text here..."

# Extract key insights from a paper
python3 skills/fabric/scripts/fabric_run.py \
  --pattern extract_wisdom \
  --input /path/to/paper.txt

# List all available patterns
python3 skills/fabric/scripts/fabric_run.py \
  --pattern summarize \
  --input "" \
  --list-patterns

# Analyze a research paper for key contributions
python3 skills/fabric/scripts/fabric_run.py \
  --pattern analyze_paper \
  --input "Abstract: We present a novel CRISPR delivery method..."
```

## Output Format

```json
{
  "pattern": "extract_wisdom",
  "output": "# SUMMARY\n\nThe paper presents...\n\n# IDEAS\n\n- Key insight 1\n- Key insight 2\n\n# QUOTES\n...",
  "status": "success"
}
```

## Setup

Install Fabric:
```bash
go install github.com/danielmiessler/fabric@latest
# or
pip install fabric-ai
```

Without Fabric installed, the tool lists available scientific patterns and provides guidance.
