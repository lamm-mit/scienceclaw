---
name: diagramming
description: Generate Mermaid diagrams for biological pathways, molecular networks, and experimental workflows
metadata:
---

## Overview

Generate technical diagrams using Mermaid syntax for biological pathways, molecular networks, experimental workflows, and research architecture. Outputs Mermaid code ready for rendering in GitHub, Notion, Obsidian, or any Mermaid-compatible renderer.

Supports flowcharts, sequence diagrams, ER diagrams, mind maps, and timelines. Generated diagrams can be saved as .mmd files or embedded directly in markdown documents.

## Usage

```bash
# Generate a flowchart of a drug discovery workflow
python3 skills/diagramming/scripts/diagram_generate.py \
  --type flowchart \
  --description "CRISPR gene editing workflow"

# Generate a mind map of a research topic
python3 skills/diagramming/scripts/diagram_generate.py \
  --type mindmap \
  --description "Alzheimer's disease molecular mechanisms"

# Generate a timeline and save to file
python3 skills/diagramming/scripts/diagram_generate.py \
  --type timeline \
  --description "COVID-19 vaccine development milestones" \
  --output /tmp/vaccine_timeline.mmd

# Generate an ER diagram for database schema
python3 skills/diagramming/scripts/diagram_generate.py \
  --type er \
  --description "genomics database schema with patients samples variants"

# Generate a sequence diagram
python3 skills/diagramming/scripts/diagram_generate.py \
  --type sequence \
  --description "antibody antigen binding mechanism"
```

## Output Format

```json
{
  "type": "flowchart",
  "mermaid_code": "graph TD\n  A[CRISPR gene editing workflow] --> B[Design gRNA]\n  B --> C[Validate Off-targets]\n  C --> D[Deliver to Cells]\n  D --> E[Verify Editing]\n  E --> F[Results]",
  "description": "CRISPR gene editing workflow"
}
```

Paste the `mermaid_code` into any Mermaid renderer or embed in markdown with triple backticks and `mermaid` language tag.
