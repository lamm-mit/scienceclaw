---
name: softjax
description: Soft differentiable drop-in replacements for non-differentiable JAX functions (abs, relu, sort, argmax, comparison, logical operators, etc.) with adjustable softening strength.
source_type: github
auth_required: false
repository_url: "https://github.com/a-paulus/softjax"
reference_url: "https://arxiv.org/abs/2603.08824"
---

## softjax

Soft differentiable drop-in replacements for non-differentiable JAX functions (abs, relu, sort, argmax, comparison, logical operators, etc.) with adjustable softening strength.

### Code repository

<https://github.com/a-paulus/softjax>

**Use this as the implementation source:** clone the repo and follow its README for install, dependencies, and how to run code or experiments. The generated client prints JSON with a suggested ``git clone`` command.

### Paper (arXiv — explanation)

<https://arxiv.org/abs/2603.08824>

This is the **paper** reference. The client can optionally fetch live Atom metadata (title, abstract) for agents; it does **not** run training or upstream research code by itself.

### What “running” this client does

The `*_client.py` script prints **JSON** that combines a **GitHub repository** (clone URL + suggested ``git clone``) with **optional paper context** from arXiv (live Atom metadata when **reference_url** is arXiv). Run the real code by cloning the repo and following its README — the skill is your agent-facing entrypoint, not a substitute for the repo’s install steps.

To call a **REST API** instead, set ``BASE_URL`` in `scripts/softjax_client.py` or wrap the upstream CLI with ``subprocess`` after clone.

### How to run the method (from the source)

Extracted for **operators and agents**. Confirm against the upstream repository or paper before relying on it in production.

## Prerequisites
- Python 3.11 or higher
- JAX library installed

## Installation
```bash
pip install softjax
```

## How to run

SoftJAX is a library providing drop-in soft replacements for non-differentiable JAX functions. Use it in Python scripts by importing and calling soft operators:

```python
import jax.numpy as jnp
import softjax as sj

# Example: soft ReLU
x = jnp.array([-0.2, -1.0, 0.3, 1.0])
print(sj.relu(x))  # soft mode by default
print(sj.relu(x, mode="hard"))  # hard (non-differentiable) mode
```

### Elementwise operators
```python
sj.abs(x)
sj.relu(x)
sj.clip(x, min_val, max_val)
sj.sign(x)
sj.round(x)
sj.heaviside(x)
```

### Array-valued operators
```python
sj.max(x, method="neuralsort", softness=0.1)
sj.min(x)
sj.sort(x, method="neuralsort", softness=0.1)  # supports multiple methods
sj.quantile(x, q=0.5)
sj.median(x)
sj.top_k(x, k=3)
sj.rank(x, descending=False)
```

### Operators returning indices
```python
sj.argmax(x)  # returns soft distribution over indices
sj.argmin(x)
sj.argsort(x)
sj.top_k(x, k=3)  # returns (values, soft_indices)
```

### Comparison operators
```python
sj.greater(x, y)
sj.equal(x, y)
sj.less(x, y)
sj.isclose(x, y)
```

### Logical operators
```python
sj.logical_and(a, b)
sj.logical_or(a, b)
sj.logical_not(a)
sj.logical_xor(a, b)
sj.all(a)
sj.any(a)
```

### Selection operators
```python
sj.where(condition, x, y)
```

### Straight-through estimators (hard forward, soft backward)
```python
sj.relu_st(x)
sj.sort_st(x)
sj.top_k_st(x, k=3)
sj.greater_st(x, y)
```

### Autograd-safe operators (stable gradients at boundaries)
```python
sj.sqrt(x)
sj.arcsin(x)
sj.arccos(x)
sj.log(x)  # safe at 0
sj.div(a, b)  # safe at division by zero
sj.norm(x)  # safe at zero vector
```

## Configuration

Key parameters available across operators:
- **`mode`**: Control softening behavior ('hard', 'soft', 'smooth', 'c0', 'c1', 'c2')
- **`softness`**: Adjust approximation strength (float, higher = closer to hard function)
- **`method`**: For sort-like operators, choose algorithm ('softsort', 'neuralsort', 'fast_soft_sort', 'smooth_sort', 'ot', 'sorting_network')

### Example with parameters
```python
# Soft sort with custom softness
result = sj.sort(x, method="fast_soft_sort", softness=2.0, mode="c1")

# Soft argmax returning distribution
soft_argmax = sj.argmax(x, mode="soft")

# Straight-through sort (hard forward, soft backward for gradient)
result = sj.sort_st(x, method="neuralsort", softness=0.1)
```

See documentation at https://a-paulus.github.io/softjax/ for full API details.

*The same text lives in* ``scripts/USAGE.md`` *for tools that prefer reading files under* ``scripts/``*.*

### Parameters

  --mode  (str)  [optional, default=soft]  Softening mode: 'hard' (non-differentiable), 'soft' (default, smooth approximation), 'smooth', 'c0', 'c1', 'c2' for different continuity guarantees.
  --softness  (float)  [optional, default=None]  Strength of softening; controls smoothness and boundedness of soft function. Adjustable per operator and method.
  --method  (str)  [optional, default=neuralsort]  Algorithm for soft operators like sort: 'softsort', 'neuralsort', 'fast_soft_sort', 'smooth_sort', 'ot', 'sorting_network'.
  --k  (int)  [optional, default=None]  Number of top elements for top_k operations.
  --q  (float)  [optional, default=None]  Quantile parameter (0–1) for quantile and argquantile operations.
  --descending  (bool)  [optional, default=True]  Sort order for rank operation: True for descending, False for ascending.

### Usage

```bash
python3 scripts/softjax_client.py sj.sort(x, method='neuralsort', softness=0.1, mode='soft')
```

### Example Output

```json
array([-0.8792, -0.1641, 0.2767, 0.8738])
```
