# TimesFM Forecasting

Google TimesFM 2.5 — 200M parameter foundation model for zero-shot univariate time series forecasting. No training required; works out-of-the-box on new datasets.

## Key Capabilities

- **Zero-shot**: Forecasts without fine-tuning on your data
- **Probabilistic**: Outputs point forecast + 10 quantile levels (5%, 10%, 20%, 80%, 90%, 95%)
- **Flexible horizon**: Any forecast length; model patchifies input automatically
- **Hardware**: CPU, CUDA (NVIDIA GPU), MPS (Apple Silicon)
- **Context length**: Up to 512 time steps of history

## System Requirements

Run `check_system.py` before loading the model:

```bash
python3 scripts/check_system.py --model v2.5 --json
```

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 1.5 GB free | 4+ GB |
| GPU VRAM | 2 GB (optional) | 8+ GB |
| Disk | ~800 MB | 2+ GB |
| Python | 3.10+ | 3.11 |

## Installation

```bash
pip install timesfm torch numpy pandas psutil
# OR from requirements.txt:
pip install -r skills/timesfm-forecasting/requirements.txt
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/check_system.py` | Preflight: RAM/GPU/disk/packages check |
| `scripts/forecast_csv.py` | End-to-end CSV forecasting with output |

## Quick Start

```bash
# 1. Check system
python3 scripts/check_system.py --model v2.5

# 2. Forecast from CSV (auto-detects columns)
python3 scripts/forecast_csv.py \
    --input data/timeseries.csv \
    --horizon 30 \
    --output results/forecast.csv

# 3. Forecast specific columns
python3 scripts/forecast_csv.py \
    --input data/gene_expression.csv \
    --date-col "timepoint" \
    --value-col "expression_level" \
    --horizon 14 \
    --format json
```

## Python API (Direct)

```python
import timesfm
import numpy as np

# Load model (downloads ~800MB from Hugging Face on first run)
tfm = timesfm.TimesFm(
    hparams=timesfm.TimesFmHparams(
        backend="gpu",           # "cpu", "gpu", or "tpu"
        per_core_batch_size=32,
        horizon_len=30,
    ),
    checkpoint=timesfm.TimesFmCheckpoint(
        huggingface_repo_id="google/timesfm-2.5-500m-pytorch"
    ),
)
tfm.load_from_checkpoint(repo_id="google/timesfm-2.5-500m-pytorch")

# Forecast
historical_values = np.array([1.0, 2.3, 1.8, 3.1, 2.9, ...])  # Your time series

point_forecast, quantile_forecast = tfm.forecast(
    inputs=[historical_values],
    freq=[0],  # 0=high-freq, 1=medium, 2=low
)

print("Point forecast:", point_forecast[0])  # Shape: (horizon_len,)
print("80% PI:", quantile_forecast[0, :, 6])  # 80th percentile
print("20% PI:", quantile_forecast[0, :, 3])  # 20th percentile
```

## Frequency Parameter

| `freq` value | Use for |
|-------------|---------|
| 0 | Sub-daily (hourly, minute-level) |
| 1 | Daily |
| 2 | Weekly, monthly, quarterly, annual |

## Use Cases for Scientific Research

- **Gene expression over time**: Forecast expression trajectories from time-course data
- **Drug concentration**: PK/PD modeling with probabilistic uncertainty bounds
- **Clinical trial metrics**: Project patient outcomes across study timepoints
- **Environmental monitoring**: Air quality, temperature, CO2 forecasts
- **Epidemic curves**: Project infection counts with uncertainty intervals
- **Experimental replicates**: Forecast future experimental values for power analysis

## Output Interpretation

```
Point forecast:  [1.2, 1.5, 1.8, ...]  # Most likely values
90% PI lower:    [0.8, 1.0, 1.2, ...]  # 5th percentile
90% PI upper:    [1.6, 2.0, 2.4, ...]  # 95th percentile
```

The 80% prediction interval means ~80% of actual future values will fall within bounds — useful for experimental design and sample size calculations.

## Model Versions

| Version | Params | Notes |
|---------|--------|-------|
| v1.0 | 200M | Original release |
| v2.0 | 200M | Improved accuracy |
| v2.5 | 500M | Best accuracy, recommended |
