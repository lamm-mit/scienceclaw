# Usage: softjax

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

---

**Scientia client:** `python3 scripts/softjax_client.py` with the flags in `SKILL.md` — prints JSON on stdout for agents.
