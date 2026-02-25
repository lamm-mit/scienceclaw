# Hedge Fund Monitor

OFR (Office of Financial Research) Hedge Fund Monitor REST API. Free, no authentication required. Provides regulatory data from SEC Form PF, CFTC futures positions, and FICC repo market.

## Base URL

```
https://data.financialresearch.gov/hf/v1
```

## Available Datasets

| Endpoint | Source | Description |
|----------|--------|-------------|
| `/pfdata` | SEC Form PF | Hedge fund AUM, leverage, liquidity, strategy |
| `/cftcdata` | CFTC | Futures/options positions by trader category |
| `/ficcdata` | FICC/DTCC | Repo market volumes and rates |

## API Usage

### Form PF Data (Hedge Fund Fundamentals)

```python
import requests

BASE = "https://data.financialresearch.gov/hf/v1"

# Get available series/metrics
r = requests.get(f"{BASE}/pfdata/series")
series = r.json()
print([s["seriesId"] for s in series])

# Fetch a specific series (e.g., total AUM)
r = requests.get(f"{BASE}/pfdata/series/data", params={
    "seriesId": "pf_total_nav",     # Net Asset Value
    "startDate": "2020-01-01",
    "endDate": "2024-12-31",
    "frequency": "quarterly"
})
data = r.json()

# Available Form PF series include:
# pf_total_nav          - Total AUM across reporting funds
# pf_gross_leverage     - Gross leverage ratios
# pf_net_leverage       - Net leverage ratios
# pf_liquidity_profile  - Fund liquidity metrics
# pf_counterparty_conc  - Counterparty concentration
# pf_strategy_breakdown - AUM by strategy (equity L/S, macro, credit, etc.)
# pf_redemption_terms   - Redemption notice periods, gates
```

### CFTC Futures Data

```python
# Trader category positions (large trader reporting)
r = requests.get(f"{BASE}/cftcdata/series/data", params={
    "seriesId": "cftc_hf_net_positions",  # Hedge fund net futures positions
    "commodity": "equity_index",
    "startDate": "2023-01-01",
    "endDate": "2024-12-31"
})

# Available CFTC series:
# cftc_hf_net_positions   - HF net long/short in futures
# cftc_hf_gross_long      - Gross long positions
# cftc_hf_gross_short     - Gross short positions
# cftc_leverage_ratio     - Leverage by contract type
```

### FICC Repo Market Data

```python
# Repo market participation by hedge funds
r = requests.get(f"{BASE}/ficcdata/series/data", params={
    "seriesId": "ficc_hf_repo_volume",
    "startDate": "2023-01-01",
    "endDate": "2024-12-31"
})

# Available FICC series:
# ficc_hf_repo_volume     - HF repo borrowing volumes
# ficc_hf_repo_rates      - Weighted average repo rates
# ficc_clearing_volumes   - Total FICC clearing volumes
```

## Response Format

```json
{
  "seriesId": "pf_total_nav",
  "description": "Total Net Asset Value - All Reporting Funds",
  "unit": "billions USD",
  "frequency": "quarterly",
  "data": [
    {"date": "2024-09-30", "value": 4823.6},
    {"date": "2024-06-30", "value": 4712.1},
    {"date": "2024-03-31", "value": 4598.4}
  ]
}
```

## Full Workflow Example

```python
import requests
import json
from datetime import datetime

BASE = "https://data.financialresearch.gov/hf/v1"

def get_hf_series(series_id, start="2020-01-01", end=None):
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")
    r = requests.get(f"{BASE}/pfdata/series/data", params={
        "seriesId": series_id,
        "startDate": start,
        "endDate": end
    })
    r.raise_for_status()
    return r.json()

# Fetch leverage and AUM data
leverage = get_hf_series("pf_gross_leverage")
aum = get_hf_series("pf_total_nav")

# Correlate with market stress periods
for period in leverage["data"]:
    print(f"{period['date']}: Leverage = {period['value']}x")
```

## Use Cases for Scientific Research

- **Systemic risk analysis**: Track leverage buildup before market disruptions
- **Strategy evolution**: How hedge fund strategies shift over economic cycles
- **Repo market stress**: FICC data shows funding market pressures
- **Cross-market analysis**: Correlate HF positioning with commodity/biotech sector movements

## Data Coverage

- **Form PF**: Quarterly, from 2012 (JOBS Act requirement)
- **CFTC**: Weekly Commitments of Traders, from 1986
- **FICC**: Daily repo data, from 2014
- **Update frequency**: Quarterly (PF), weekly (CFTC), daily (FICC)
- **Authentication**: None required
- **Rate limits**: None published; be reasonable (< 100 req/min)
