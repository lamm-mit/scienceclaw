---
name: code-execution
description: Agentic computation — iteratively write code, run commands, read results, and reason about next steps
metadata:
---

# Code Execution Skill

An interactive computation environment where the agent can iteratively write files, run shell commands, read output, and decide what to do next — like a researcher working at a terminal.

This is NOT a single-script skill. It provides an agentic loop with three actions:

## Available Actions

### `write_file`
Write content to a file (Python scripts, SLURM submission scripts, etc.)
```json
{"action": "write_file", "path": "relax.py", "content": "import ..."}
```

### `run_command`
Execute a shell command and observe the output.
```json
{"action": "run_command", "command": "python3 relax.py"}
```
```json
{"action": "run_command", "command": "sbatch submit.sh"}
```
```json
{"action": "run_command", "command": "squeue -u $USER"}
```
```json
{"action": "run_command", "command": "cat results.json"}
```

### `done`
Signal that the computation is complete and return results.
```json
{"action": "done", "result": {"status": "completed", "findings": [...]}}
```

## Typical Workflow

1. Write a Python script that generates structures
2. Run it
3. Write a SLURM submission script for GPU work
4. Submit with `sbatch`
5. Check status with `squeue` or `sacct`
6. Read results with `cat`
7. Analyze and report

## Guidelines

- Refer to other skills' SKILL.md for API documentation (UMA, HPC, materials)
- Print progress to stderr, final results to stdout as JSON
- For GPU work: write a self-contained Python script, wrap it in a SLURM script, submit with sbatch
- Check job status before reading results
- Each action gets one response — plan each step carefully
