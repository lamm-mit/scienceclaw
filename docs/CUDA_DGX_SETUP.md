# CUDA setup on NVIDIA DGX Spark

So that packages that build CUDA extensions (e.g. **pufferlib**) can find CUDA on DGX Spark:

## 1. Shell environment (recommended)

`~/.bashrc` is already updated to set CUDA for interactive shells:

- `CUDA_HOME=/usr/local/cuda`
- `PATH` and `LD_LIBRARY_PATH` updated

**Use a new terminal** (or run `source ~/.bashrc`) so these are set before:

```bash
cd scienceclaw
.venv/bin/pip install --no-build-isolation pufferlib
```

## 2. Venv-level fallbacks (already in place)

- **pip build hook:** `pip/_vendor/pyproject_hooks/_in_process/_in_process.py` sets `os.environ["CUDA_HOME"] = "/usr/local/cuda"` at startup so the build backend subprocess sees CUDA.
- **torch:** `torch/utils/cpp_extension.py` uses `os.environ.get("CUDA_HOME")` when the module-level `CUDA_HOME` is not set (`_join_cuda_home` and `_check_cuda_version`).

These live inside `.venv` and may be overwritten by future pip/torch upgrades; re-apply or rely on the shell env.

## 3. Install pufferlib

```bash
# From project root, with CUDA_HOME set (e.g. after source ~/.bashrc)
cd scienceclaw
.venv/bin/pip install --no-build-isolation pufferlib
```

If the build fails with **ninja** or **architecture** errors:

- Install ninja for faster builds: `pip install ninja` or system `ninja`.
- Pufferlib’s CUDA build may still fail on some ARM+GPU setups (e.g. `IndexError` in `_get_cuda_arch_flags`); that is a torch/pufferlib compatibility issue, not a missing CUDA_HOME.

## 4. Verify CUDA

```bash
.venv/bin/python3 -c "import os; os.environ.setdefault('CUDA_HOME','/usr/local/cuda'); import torch.utils.cpp_extension as e; print('CUDA_HOME', e.library_paths(device_type='cuda')[:1])"
nvcc --version
```
