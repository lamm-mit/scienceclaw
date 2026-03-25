# Usage: bioreason_pro

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

---

**Scientia client:** `python3 scripts/bioreason_pro_client.py` with the flags in `SKILL.md` — prints JSON on stdout for agents.
