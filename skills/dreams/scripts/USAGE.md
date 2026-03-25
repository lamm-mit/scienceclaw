# Usage: dreams

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

---

**Scientia client:** `python3 scripts/dreams_client.py` with the flags in `SKILL.md` — prints JSON on stdout for agents.
