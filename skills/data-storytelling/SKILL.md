---
name: data-storytelling
description: Transform scientific findings into compelling research narratives for papers, grants, and presentations
metadata:
---

## Overview

Transforms scientific data and findings into compelling research narratives with clear structure, effective framing, and audience-appropriate communication. Generates structured narratives for academic papers, grant applications, conference presentations, and press releases.

Tailors language complexity, emphasis, and structure to the target audience: rigorous and mechanistic for academic peers, accessible and impact-focused for the general public, persuasive and outcomes-oriented for grant reviewers, and concise and punchy for conference abstracts.

## Usage

```bash
# Generate an academic abstract
python3 skills/data-storytelling/scripts/story_structure.py \
  --findings "We identified that BACE1 inhibition reduces amyloid-beta production by 67% in APP transgenic mice, with IC50 of 12 nM and favorable BBB penetration (Kp,uu = 0.8)" \
  --audience academic \
  --format abstract

# Generate a grant introduction
python3 skills/data-storytelling/scripts/story_structure.py \
  --findings "Novel kinase inhibitor reduces tumor growth 80% in xenograft model, 5x selectivity vs off-targets, oral bioavailability 65%" \
  --audience grant \
  --format introduction

# Generate a press release for public communication
python3 skills/data-storytelling/scripts/story_structure.py \
  --findings "Machine learning model predicts drug side effects with 94% accuracy using protein interaction data" \
  --audience general \
  --format press-release

# Generate a conference discussion section
python3 skills/data-storytelling/scripts/story_structure.py \
  --findings "Cryo-EM structure reveals allosteric site 25 Angstrom from active site, explaining cooperative binding" \
  --audience conference \
  --format discussion
```

## Output Format

```json
{
  "audience": "academic",
  "format": "abstract",
  "narrative": "Background: Alzheimer's disease affects...\n\nObjective: To determine...\n\nMethods: Using computational screening...\n\nResults: We identified...\n\nConclusion: These findings suggest...",
  "key_messages": [
    "BACE1 inhibition reduces amyloid-beta by 67%",
    "IC50 of 12 nM demonstrates high potency",
    "BBB penetration confirmed for CNS delivery"
  ],
  "word_count": 187
}
```
