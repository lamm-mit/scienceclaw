---
name: prompt-engineering-patterns
description: Generate optimized LLM prompts using chain-of-thought, ReAct, and other scientific reasoning patterns
metadata:
---

## Overview

Advanced LLM prompt optimization patterns for scientific reasoning: chain-of-thought, tree-of-thought, few-shot learning, ReAct, and self-consistency. Generates optimized prompts tailored to scientific investigation tasks and specific domains (biology, chemistry, materials, etc.).

Use this tool to construct better prompts before querying an LLM, ensuring rigorous scientific reasoning, hypothesis generation, and evidence-based conclusions.

## Usage

```bash
# Generate a chain-of-thought prompt for a biology task
python3 skills/prompt-engineering-patterns/scripts/prompt_optimize.py \
  --task "Identify potential drug targets for Alzheimer's disease" \
  --pattern chain-of-thought \
  --domain biology

# Generate a ReAct prompt for tool-using agents
python3 skills/prompt-engineering-patterns/scripts/prompt_optimize.py \
  --task "Predict BBB permeability of novel kinase inhibitors" \
  --pattern react \
  --domain chemistry

# Generate a tree-of-thought prompt
python3 skills/prompt-engineering-patterns/scripts/prompt_optimize.py \
  --task "Evaluate CRISPR delivery mechanisms" \
  --pattern tree-of-thought

# Generate few-shot prompt for a specific scientific task
python3 skills/prompt-engineering-patterns/scripts/prompt_optimize.py \
  --task "Classify protein-protein interactions from sequence features" \
  --pattern few-shot \
  --domain biology
```

## Output Format

```json
{
  "pattern": "chain-of-thought",
  "task": "Identify potential drug targets for Alzheimer's disease",
  "optimized_prompt": "You are an expert computational biologist...\n\nTask: Identify potential drug targets for Alzheimer's disease\n\nLet's think through this step by step:\n1. First, consider the molecular mechanisms...",
  "explanation": "Chain-of-thought prompting elicits step-by-step reasoning, improving accuracy on complex scientific tasks by up to 40% compared to direct answering."
}
```
