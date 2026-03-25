---
name: dreams
description: Agentic materials discovery and DFT simulation framework using ASE, Quantum ESPRESSO, and Claude LLMs via LangGraph.
source_type: github
auth_required: true
repository_url: "https://github.com/BattModels/material_agent"
reference_url: "https://arxiv.org/abs/2507.14267"
---

## dreams

Agentic materials discovery and DFT simulation framework using ASE, Quantum ESPRESSO, and Claude LLMs via LangGraph.

### Code repository

<https://github.com/BattModels/material_agent>

**Use this as the implementation source:** clone the repo and follow its README for install, dependencies, and how to run code or experiments. The generated client prints JSON with a suggested ``git clone`` command.

### Paper (arXiv — explanation)

<https://arxiv.org/abs/2507.14267>

This is the **paper** reference. The client can optionally fetch live Atom metadata (title, abstract) for agents; it does **not** run training or upstream research code by itself.

### What “running” this client does

The `*_client.py` script prints **JSON** that combines a **GitHub repository** (clone URL + suggested ``git clone``) with **optional paper context** from arXiv (live Atom metadata when **reference_url** is arXiv). Run the real code by cloning the repo and following its README — the skill is your agent-facing entrypoint, not a substitute for the repo’s install steps.

To call a **REST API** instead, set ``BASE_URL`` in `scripts/dreams_client.py` or wrap the upstream CLI with ``subprocess`` after clone.

### How to run the method (from the source)

Extracted for **operators and agents**. Confirm against the upstream repository or paper before relying on it in production.

## Prerequisites

- Quantum ESPRESSO installed and available in system PATH
- Anthropic API key (or alternative LLM provider packages installed)
- Conda package manager
- ASE (Atomic Simulation Environment) and LangGraph compatible Python environment

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/BattModels/material_agent.git
   cd material_agent
   ```

2. Create and activate conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate dreams
   ```
   *Note: Environment setup typically takes 5–10 minutes. Default setup supports Anthropic models only.*

3. Install Quantum ESPRESSO:
   - Follow official QE installation: https://www.quantum-espresso.org/
   - Ensure `pw.x` and related executables are in system PATH or modify `QE_submission_example` in `prompt.py`

4. Configure API keys and paths:
   - Edit `config/default.yaml`:
     - Add your Anthropic (or alternative LLM provider) API key
     - Specify pseudopotential directory and paths
     - Set working directory for DFT calculations

## How to run

1. Edit the task specification in `invoke.py`:
   ```python
   # Example: Calculate lattice constant for BCC Li
   usermessage = "You are going to calculate the lattice constant for BCC Li through DFT, the experiment value is 3.451, use this to create the initial structure."
   ```

2. Run the agent:
   ```bash
   python invoke.py
   ```

The agent will autonomously:
- Parse the task via Claude LLM
- Generate initial atomic structures
- Configure and submit DFT calculations to Quantum ESPRESSO via ASE
- Analyze results and iterate if needed
- Return final materials property predictions

## Configuration

**Environment Variables & Config File (`config/default.yaml`)**:
- `ANTHROPIC_API_KEY`: Required for Claude model access
- `pseudopotentials_dir`: Path to pseudo-potential files (e.g., PAW datasets)
- `working_directory`: Directory for DFT calculations and outputs
- `qe_path`: Path to Quantum ESPRESSO executables (if not in PATH)
- `exchange_correlation_functional`: XC functional choice (e.g., PBE)

**For non-Anthropic LLMs**:
- Install provider-specific packages
- Modify `planNexe2.py` and `tools.py` to integrate alternative LLM APIs

**Demo Video**: Full walkthrough available at [Google Drive demo](https://drive.google.com/file/d/1XInq7Q226777BSsTfQSe5HptYrk_GOIE/preview)

*The same text lives in* ``scripts/USAGE.md`` *for tools that prefer reading files under* ``scripts/``*.*

### Parameters

  --api-key  (str)  [required]  API key for authentication
  --task-description  (str)  [required]  Natural language task specification for the materials simulation (e.g., lattice constant calculation, adsorption energy prediction). Defined in invoke.py usermessage.
  --config-file  (str)  [optional, default=config/default.yaml]  Path to YAML configuration file containing API keys, pseudopotentials, and working directory.

### Usage

```bash
python3 scripts/dreams_client.py python invoke.py
```

### Example Output

```json
{"calculation_result": "lattice_constant_value", "dft_converged": true, "explanation": "..." }
```
