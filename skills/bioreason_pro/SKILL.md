---
name: bioreason_pro
description: Multimodal reasoning LLM for protein function prediction integrating protein embeddings with biological context to generate structured reasoning traces and functional annotations.
source_type: github
auth_required: false
repository_url: "https://github.com/bowang-lab/BioReason-Pro"
reference_url: "https://www.biorxiv.org/content/10.64898/2026.03.19.712954v1"
---

## bioreason_pro

Multimodal reasoning LLM for protein function prediction integrating protein embeddings with biological context to generate structured reasoning traces and functional annotations.

### Code repository

<https://github.com/bowang-lab/BioReason-Pro>

**Use this as the implementation source:** clone the repo and follow its README for install, dependencies, and how to run code or experiments. The generated client prints JSON with a suggested ``git clone`` command.

### Primary resource (landing page)

<https://www.biorxiv.org/content/10.64898/2026.03.19.712954v1>

This is the paper or artifact home from DOI/registry metadata — **not** a JSON API. If this URL is **arXiv**, the generated client can still fetch **live Atom metadata** (title, abstract, authors) without a ``BASE_URL``. For other hosts, the client uses stub mode until you set a real ``BASE_URL`` for a REST service.

### What “running” this client does

The `*_client.py` script prints **JSON** that combines a **GitHub repository** (clone URL + suggested ``git clone``) with **optional paper context** from arXiv (live Atom metadata when **reference_url** is arXiv). Run the real code by cloning the repo and following its README — the skill is your agent-facing entrypoint, not a substitute for the repo’s install steps.

To call a **REST API** instead, set ``BASE_URL`` in `scripts/bioreason_pro_client.py` or wrap the upstream CLI with ``subprocess`` after clone.

### How to run the method (from the source)

Extracted for **operators and agents**. Confirm against the upstream repository or paper before relying on it in production.

## Prerequisites
- Python 3.11+
- CUDA/GPU for best performance

## Installation

```bash
# Clone the repository
git clone https://github.com/bowang-lab/BioReason-Pro.git
cd BioReason-Pro

# Install package
pip install -e .
```

## How to run

The README does not document specific CLI commands for running inference or training. However, the project provides:

1. **Web Interface**: Try BioReason-Pro directly at [bioreason.net](https://bioreason.net)
2. **Precomputed Predictions**: Access 240,000+ precomputed protein predictions at [bioreason.net/atlas](https://bioreason.net/atlas)
3. **Model Checkpoints**: Available on HuggingFace collection ([wanglab/bioreason-pro](https://huggingface.co/collections/wanglab/bioreason-pro))
   - GO-GPT: https://huggingface.co/wanglab/gogpt
   - BioReason-Pro SFT: https://huggingface.co/wanglab/bioreason-pro-sft
   - BioReason-Pro RL: https://huggingface.co/wanglab/bioreason-pro-rl

4. **Datasets**: Training and evaluation datasets available at [HuggingFace collection](https://huggingface.co/collections/wanglab/bioreason-pro) with detailed download and usage instructions

## Configuration

The README does not document specific environment variables, API keys, or configuration parameters. For detailed usage instructions on running inference or training, refer to the repository's code or documentation at https://github.com/bowang-lab/BioReason-Pro or the project website at https://bioreason.net.

*The same text lives in* ``scripts/USAGE.md`` *for tools that prefer reading files under* ``scripts/``*.*

### Parameters



### Usage

```bash
python3 scripts/bioreason_pro_client.py 
```

### Example Output

```json

```
