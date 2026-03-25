---
name: text_to_lora
description: Generate task-specific LoRA adapters from natural language descriptions using a trained T2L model for instant transformer adaptation.
source_type: github
auth_required: true
repository_url: "https://github.com/SakanaAI/text-to-lora"
reference_url: "https://openreview.net/forum?id=zWskCdu3QA"
---

## text_to_lora

Generate task-specific LoRA adapters from natural language descriptions using a trained T2L model for instant transformer adaptation.

### Code repository

<https://github.com/SakanaAI/text-to-lora>

**Use this as the implementation source:** clone the repo and follow its README for install, dependencies, and how to run code or experiments. The generated client prints JSON with a suggested ``git clone`` command.

### Primary resource (landing page)

<https://openreview.net/forum?id=zWskCdu3QA>

This is the paper or artifact home from DOI/registry metadata — **not** a JSON API. If this URL is **arXiv**, the generated client can still fetch **live Atom metadata** (title, abstract, authors) without a ``BASE_URL``. For other hosts, the client uses stub mode until you set a real ``BASE_URL`` for a REST service.

### What “running” this client does

The `*_client.py` script prints **JSON** that combines a **GitHub repository** (clone URL + suggested ``git clone``) with **optional paper context** from arXiv (live Atom metadata when **reference_url** is arXiv). Run the real code by cloning the repo and following its README — the skill is your agent-facing entrypoint, not a substitute for the repo’s install steps.

To call a **REST API** instead, set ``BASE_URL`` in `scripts/text_to_lora_client.py` or wrap the upstream CLI with ``subprocess`` after clone.

### How to run the method (from the source)

Extracted for **operators and agents**. Confirm against the upstream repository or paper before relying on it in production.

## Prerequisites

- Python 3.10
- >16GB GPU memory (to run demo with both models simultaneously)
- `uv` package manager (see https://docs.astral.sh/uv/getting-started/installation/)
- Hugging Face account and CLI login for model access

## Installation

```bash
git clone https://github.com/SakanaAI/text-to-lora.git
cd text-to-lora
uv self update
uv venv --python 3.10 --seed
uv sync
uv pip install https://github.com/Dao-AILab/flash-attention/releases/download/v2.6.3/flash_attn-2.6.3+cu123torch2.3cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
uv pip install src/fishfarm
```

## How to run

### Download trained T2L checkpoints

Required before running any demo:

```bash
uv run huggingface-cli login
uv run huggingface-cli download SakanaAI/text-to-lora --local-dir . --include "trained_t2l/*"
```

### Generate LoRA from task description

```bash
uv run python scripts/generate_lora.py trained_t2l/llama_8b_t2l "This task challenges your problem-solving abilities through mathematical reasoning. You must carefully read each scenario and systematically work through the data to compute the final outcome."
```

For smaller GPUs, use Gemma-2-2B:

```bash
uv run python scripts/generate_lora.py trained_t2l/gemma_2b_t2l "This task challenges your problem-solving abilities through mathematical reasoning. You must carefully read each scenario and systematically work through the data to compute the final outcome."
```

### Evaluate generated LoRA

```bash
uv run python scripts/run_eval.py --model-dir meta-llama/Llama-3.1-8B-Instruct --lora-dirs {PATH_TO_GENERATED_LORA} --save-results --tasks gsm8k
```

### Run Web UI demo

Runs Mistral-7B-Instruct-v0.2 locally alongside T2L:

```bash
uv run python webui/app.py
```

### Evaluate T2L checkpoint

```bash
WANDB_MODE=disabled uv run python scripts/eval_hypermod_checkpoint.py --checkpoint_path trained_t2l/gemma_2b_t2l/hypermod.pt --full_eval --use-icl
```

### Train T2L (SFT)

Start async evaluator in separate process:

```bash
uv run watcher.py
```

Then run training script (each ~5 days on H100):

```bash
./scripts/train_t2l_mistral.sh
./scripts/train_t2l_llama.sh
./scripts/train_t2l_gemma.sh
```

### Train T2L (Reconstruction)

First train oracle LoRA baselines (takes many hours):

```bash
./scripts/train_lora_baselines.sh
```

Then train T2L to reconstruct:

```bash
WANDB_MODE=disabled uv run python scripts/train_hyper_recon.py configs/hyper_lora_decontam_lol_tasks.yaml --model_dir=mistralai/Mistral-7B-Instruct-v0.2/ --emb_model=Alibaba-NLP/gte-large-en-v1.5 --warmup_frac=0.1 --lr=1e-3 --epochs=10000 --n_train_ds=479 --exp_setup=hyper_lora --encoder_type=linear --pred_z_score=True --n_descs_per_ds=128 --n_embs_per_sampled_task=1 --n_tasks_per_batch=4 --factorized=False --delta_w_scaling=10000 --shared_AB_head=True
```

## Configuration

- **Hugging Face Auth**: Run `uv run huggingface-cli login` before downloading models/datasets
- **WANDB_MODE**: Set `WANDB_MODE=disabled` to disable Weights & Biases logging
- **Flash Attention wheel**: The provided wheel is for CUDA 12.3 and torch 2.3. Adjust URL if your hardware differs.
- **vLLM non-determinism**: Known issue—evaluation runs may show small variance even with fixed seed due to vLLM's LoRA implementation
- **Dataset connection issues**: If Hugging Face datasets server rejects connections during SFT training, retry until datasets are cached locally

*The same text lives in* ``scripts/USAGE.md`` *for tools that prefer reading files under* ``scripts/``*.*

### Parameters

  --api-key  (str)  [required]  API key for authentication
  --t2l-directory  (str)  [required]  Path to the trained T2L model directory (e.g., trained_t2l/llama_8b_t2l)
  --task-description  (str)  [required]  Natural language description of the task for which to generate a LoRA adapter
  --model-dir  (str)  [optional, default=None]  Base model directory for evaluation (e.g., meta-llama/Llama-3.1-8B-Instruct)
  --lora-dirs  (str)  [optional, default=None]  Path to generated LoRA directory for evaluation
  --tasks  (str)  [optional, default=None]  Comma-separated list of evaluation tasks (e.g., gsm8k)
  --save-results  (bool)  [optional, default=False]  Save evaluation results to disk
  --use-icl  (bool)  [optional, default=False]  Include 3-shot in-context examples in evaluation queries
  --checkpoint-path  (str)  [optional, default=None]  Path to T2L hypermod checkpoint for evaluation

### Usage

```bash
python3 scripts/text_to_lora_client.py uv run python scripts/generate_lora.py trained_t2l/llama_8b_t2l "This task challenges your problem-solving abilities through mathematical reasoning."
```

### Example Output

```json
{"lora_path": "/path/to/generated/lora", "model": "base_model_name"}
```
