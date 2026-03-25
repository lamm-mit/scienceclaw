# Usage: text_to_lora

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

---

**Scientia client:** `python3 scripts/text_to_lora_client.py` with the flags in `SKILL.md` — prints JSON on stdout for agents.
