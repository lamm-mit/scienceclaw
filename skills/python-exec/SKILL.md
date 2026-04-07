---
name: python-exec
description: Execute arbitrary Python code and return stdout. NumPy, pandas, scipy, matplotlib, and other scientific libraries are available.
---

# python-exec

Execute a Python code snippet in a subprocess and return its stdout output.

## Usage

```bash
python3 scripts/python_exec.py --code "import numpy as np; print(np.mean([1,2,3]))"
```

## Output

Returns stdout from the executed code (up to 8000 chars). If execution fails, returns stderr prefixed with `[stderr]:`.

## Available libraries

NumPy, pandas, scipy, matplotlib, scikit-learn, biopython, rdkit, and any other package installed in the environment.
