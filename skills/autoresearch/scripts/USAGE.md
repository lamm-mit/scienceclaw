# Usage: autoresearch

## Prerequisites

- Single NVIDIA GPU (tested on H100)
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) project manager

## Installation

```bash
# 1. Install uv project manager (if you don't already have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Download data and train tokenizer (one-time, ~2 min)
uv run prepare.py
```

## How to run

**Manual single training experiment (~5 min):**

```bash
uv run train.py
```

**Autonomous agent mode:**

Point your AI agent (Claude, Codex, etc.) to the `program.md` file and prompt:

```
Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.
```

The agent will autonomously:
1. Read `program.md` for instructions
2. Modify `train.py` (hyperparameters, architecture, optimizer, batch size, etc.)
3. Run training for exactly 5 minutes
4. Evaluate using `val_bpb` (validation bits per byte)
5. Keep or discard changes based on improvement
6. Repeat autonomously

## Configuration

**Key files to understand:**

- **`prepare.py`** — Fixed constants, one-time data prep (downloads training data, trains BPE tokenizer), runtime utilities. Do not modify.
- **`train.py`** — Single file edited by the agent. Contains GPT model, optimizer (Muon + AdamW), training loop. Fair game: architecture, hyperparameters, batch size, optimizer settings.
- **`program.md`** — Baseline instructions for agents. Edit this to customize agent behavior and research setup.

**Training constraints:**

- **Fixed 5-minute time budget** (wall clock, excluding startup/compilation) regardless of compute platform
- **Metric:** `val_bpb` (validation bits per byte, lower is better, vocab-size-independent)
- **Expected frequency:** ~12 experiments/hour, ~100 experiments overnight

**For smaller compute platforms** (MacBook, etc.), tune in `prepare.py` and `train.py`:
- Use smaller dataset (e.g., [TinyStories](https://huggingface.co/datasets/karpathy/tinystories-gpt4-clean))
- Decrease `vocab_size` (from 8192 to 4096, 2048, or 256 bytes)
- Lower `MAX_SEQ_LEN` (down to 256)
- Reduce `EVAL_TOKENS` for faster validation
- Lower `DEPTH` (default 8, try 4)
- Use `WINDOW_PATTERN: "L"` instead of `"SSSL"`
- Reduce `TOTAL_BATCH_SIZE` to `2**14` (~16K) or lower

Refer to [notable forks](https://github.com/karpathy/autoresearch#notable-forks) for CPU/MacOS/Windows/AMD variants.

---

**Scientia client:** `python3 scripts/autoresearch_client.py` with the flags in `SKILL.md` — prints JSON on stdout for agents.
