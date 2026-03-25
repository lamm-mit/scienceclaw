# Usage: doc_to_lora

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

---

**Scientia client:** `python3 scripts/doc_to_lora_client.py` with the flags in `SKILL.md` — prints JSON on stdout for agents.
