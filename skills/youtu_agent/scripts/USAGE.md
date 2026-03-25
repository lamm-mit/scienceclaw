# Usage: youtu_agent

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip
- API keys for LLM providers (DeepSeek, OpenAI, etc.)
- Optional: API keys for tools (Serper for web search, Jina for web reading)

## Installation

Clone and set up the repository:

```bash
git clone https://github.com/TencentCloudADP/youtu-agent.git
cd youtu-agent
uv sync  # or, `make sync`
source ./.venv/bin/activate
cp .env.example .env
```

Alternatively, use Docker:

```bash
# Refer to docker/README.md for Docker-based setup with interactive frontend
```

## How to run

### Interactive CLI Chat

```bash
# Basic agent (no internet search)
python scripts/cli_chat.py --config simple/base

# Agent with web search capabilities
python scripts/cli_chat.py --config simple/base_search
```

### Generate Agent Automatically

```bash
# Interactively clarify requirements and auto-generate a config
python scripts/gen_simple_agent.py

# Run the generated config
python scripts/cli_chat.py --config generated/xxx
```

### Run Examples

```bash
# SVG generator (requires SERPER_API_KEY and JINA_API_KEY)
python examples/svg_generator/main.py

# SVG generator with web UI
python examples/svg_generator/main_web.py
```

### Run Evaluations

```bash
# Prepare WebWalkerQA dataset
python scripts/data/process_web_walker_qa.py

# Run evaluation
python scripts/run_eval.py --config_name ww --exp_id <your_exp_id> --dataset WebWalkerQA_15 --concurrency 5
```

## Configuration

### Environment Variables

Edit `.env` file with required API keys:

```bash
# LLM Configuration (OpenAI API format compatible)
UTU_LLM_TYPE=chat.completions
UTU_LLM_MODEL=deepseek-chat
UTU_LLM_BASE_URL=https://api.deepseek.com/v1
UTU_LLM_API_KEY=replace-to-your-api-key

# Optional: Judge LLM (for evaluation)
JUDGE_LLM_TYPE=chat.completions
JUDGE_LLM_MODEL=deepseek-chat
JUDGE_LLM_BASE_URL=https://api.deepseek.com/v1
JUDGE_LLM_API_KEY=replace-to-your-api-key

# Tool APIs (optional, for web search)
SERPER_API_KEY=your-serper-api-key
JINA_API_KEY=your-jina-api-key
```

### Alternative: Tencent Cloud DeepSeek

```bash
UTU_LLM_TYPE=chat.completions
UTU_LLM_MODEL=deepseek-v3
UTU_LLM_BASE_URL=https://api.lkeap.cloud.tencent.com/v1
UTU_LLM_API_KEY=replace-with-your-api-key
```

### Agent Configuration Files

Agent configurations are YAML files in `configs/agents/`. Example structure:

```yaml
defaults:
  - /model/base
  - /tools/search@toolkits.search
  - _self_

agent:
  name: simple-tool-agent
  instructions: "You are a helpful assistant that can search the web."
```

### Web UI Frontend

Download and install the frontend package:

```bash
curl -LO https://github.com/Tencent/Youtu-agent/releases/download/frontend%2Fv0.2.0/utu_agent_ui-0.2.0-py3-none-any.whl
uv pip install utu_agent_ui-0.2.0-py3-none-any.whl
```

Then run web-enabled examples:

```bash
python examples/svg_generator/main_web.py
# Access at http://127.0.0.1:8848/
```

---

**Scientia client:** `python3 scripts/youtu_agent_client.py` with the flags in `SKILL.md` — prints JSON on stdout for agents.
