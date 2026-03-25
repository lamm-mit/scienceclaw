---
name: doc_to_lora
description: A method to instantly internalize document contexts into language models using LoRA without fine-tuning.
source_type: github
auth_required: true
repository_url: "https://github.com/SakanaAI/doc-to-lora"
reference_url: "https://arxiv.org/abs/2602.15902"
---

## doc_to_lora

A method to instantly internalize document contexts into language models using LoRA without fine-tuning.

### Code repository

<https://github.com/SakanaAI/doc-to-lora>

**Use this as the implementation source:** clone the repo and follow its README for install, dependencies, and how to run code or experiments. The generated client prints JSON with a suggested ``git clone`` command.

### Paper (arXiv — explanation)

<https://arxiv.org/abs/2602.15902>

This is the **paper** reference. The client can optionally fetch live Atom metadata (title, abstract) for agents; it does **not** run training or upstream research code by itself.

### What “running” this client does

The `*_client.py` script prints **JSON** that combines a **GitHub repository** (clone URL + suggested ``git clone``) with **optional paper context** from arXiv (live Atom metadata when **reference_url** is arXiv). Run the real code by cloning the repo and following its README — the skill is your agent-facing entrypoint, not a substitute for the repo’s install steps.

To call a **REST API** instead, set ``BASE_URL`` in `scripts/doc_to_lora_client.py` or wrap the upstream CLI with ``subprocess`` after clone.

### How to run the method (from the source)

Extracted for **operators and agents**. Confirm against the upstream repository or paper before relying on it in production.

## Prerequisites
- Python 3.8+
- CUDA-capable GPU (recommended)
- Hugging Face account for model access

## Installation
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
./install.sh
```

## Configuration
### Hugging Face Authentication
Login to Hugging Face to download pre-trained models:
```bash
uv run huggingface-cli login
```

### Download Pre-Trained Models
```bash
uv run huggingface-cli download SakanaAI/doc-to-lora --local-dir trained_d2l --include "/"
```

## How to run

### Interactive Demo
```bash
uv run demo/app.py
```

### Python API Usage (Non-batched)
```python
import torch
from ctx_to_lora.model_loading import get_tokenizer
from ctx_to_lora.modeling.hypernet import ModulatedPretrainedModel

# Load model
checkpoint_path = "trained_d2l/gemma_demo/checkpoint-80000/pytorch_model.bin"
state_dict = torch.load(checkpoint_path, weights_only=False)
model = ModulatedPretrainedModel.from_state_dict(
    state_dict, train=False, use_sequence_packing=False
)
model.reset()
tokenizer = get_tokenizer(model.base_model.name_or_path)

# Prepare input
doc = open("data/sakana_wiki.txt", "r").read()
chat = [{"role": "user", "content": "Tell me about Sakana AI."}]
chat_ids = tokenizer.apply_chat_template(
    chat,
    add_special_tokens=False,
    return_attention_mask=False,
    add_generation_prompt=True,
    return_tensors="pt",
).to(model.device)

# Internalize document and generate
model.internalize(doc)
outputs = model.generate(input_ids=chat_ids, max_new_tokens=512)
print(tokenizer.decode(outputs[0]))

# Reset to remove internalized context
model.reset()
```

### Experimental Scripts
Run experiments from repository root using `uv run`:

**Main Experiment:**
```bash
uv run scripts/main_exp/0-download_data.sh
uv run scripts/main_exp/1-train.sh
uv run scripts/main_exp/eval/*.sh
```

**NIAH (Needle in a Haystack):**
```bash
uv run scripts/niah/0-gen_data.sh
uv run scripts/niah/1-train.sh
uv run scripts/niah/2-eval.sh
```

### Data Viewer
View self-generated data samples:
```bash
uv run webui/self_gen_viewer.py
```
See [webui/SELF_GEN_VIEWER.md](webui/SELF_GEN_VIEWER.md) for details.

## Configuration
- **Model checkpoint paths**: Specify via `checkpoint_path` parameter
- **Base model**: Configured in checkpoint; supports Gemma and other Hugging Face models
- **Batched inference**: For batched operations, see `src/ctx_to_lora/modeling/hypernet.py`
- **API keys**: Requires Hugging Face token for model downloads

*The same text lives in* ``scripts/USAGE.md`` *for tools that prefer reading files under* ``scripts/``*.*

### Parameters

  --api-key  (str)  [required]  API key for authentication
  --checkpoint-path  (str)  [required]  Path to the trained D2L model checkpoint (pytorch_model.bin)
  --doc  (str)  [required]  Document text or file path to internalize
  --query  (str)  [required]  User query or chat message to generate response for
  --max-new-tokens  (int)  [optional, default=512]  Maximum number of tokens to generate

### Usage

```bash
python3 scripts/doc_to_lora_client.py uv run demo/app.py
```

### Example Output

```json
{"response": "Generated text influenced by internalized document"}
```
