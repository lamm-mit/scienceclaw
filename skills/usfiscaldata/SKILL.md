# US Fiscal Data

US Treasury Fiscal Data API. Free, no authentication required. 54 datasets, 182+ tables covering national debt, federal spending, revenue, exchange rates, savings bonds, and interest rates.

## Base URL

```
https://api.fiscaldata.treasury.gov/services/api/fiscal_service
```

**Important:** All numeric values are returned as **strings**. Convert explicitly.

## Quick Start

```python
import requests

BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"

def treasury_get(endpoint, params=None):
    r = requests.get(f"{BASE}/{endpoint}", params=params or {})
    r.raise_for_status()
    return r.json()

# List all available datasets
datasets = treasury_get("v1/accounting/od/debt_outstanding")
```

## Key Datasets

### National Debt

```python
# Total public debt outstanding (daily)
debt = treasury_get("v2/accounting/od/debt_outstanding", {
    "fields": "record_date,tot_pub_debt_out_amt",
    "sort": "-record_date",
    "page[size]": 30,
    "filter": "record_date:gte:2024-01-01"
})

for row in debt["data"]:
    print(f"{row['record_date']}: ${float(row['tot_pub_debt_out_amt']):,.0f}")

# Debt by category (marketable vs non-marketable)
debt_cat = treasury_get("v2/accounting/od/debt_outstanding", {
    "fields": "record_date,debt_catg,debt_catg_desc,close_today_bal",
    "filter": "record_date:eq:2024-09-30"
})
```

### Federal Spending & Revenue (Monthly Treasury Statement)

```python
# Monthly receipts and outlays
mts = treasury_get("v1/accounting/mts/mts_table_1", {
    "fields": "record_date,current_month_rcpt_outly_amt,prior_yr_rcpt_outly_amt,line_code_nbr,line_nm",
    "sort": "-record_date",
    "page[size]": 50
})

# Budget categories
budget = treasury_get("v1/accounting/mts/mts_table_5", {
    "fields": "record_date,current_month_gross_outly_amt,classification_desc",
    "filter": "record_date:gte:2024-01-01",
    "sort": "-record_date"
})
```

### Exchange Rates

```python
# Treasury Reporting Rates of Exchange (quarterly)
fx = treasury_get("v1/accounting/od/rates_of_exchange", {
    "fields": "country,country_currency_desc,exchange_rate,record_date",
    "filter": "record_date:gte:2024-01-01",
    "sort": "-record_date,country"
})

for row in fx["data"][:10]:
    print(f"{row['country_currency_desc']}: {row['exchange_rate']} per USD ({row['record_date']})")
```

### Treasury Securities & Interest Rates

```python
# Average interest rates on US debt
rates = treasury_get("v2/accounting/od/avg_interest_rates", {
    "fields": "record_date,security_desc,avg_interest_rate_amt",
    "filter": "record_date:gte:2024-01-01",
    "sort": "-record_date"
})

# Treasury securities outstanding
securities = treasury_get("v1/debt/tsy/pub_debt_securities_type", {
    "fields": "record_date,security_type_desc,securities_outstanding_amt",
    "sort": "-record_date",
    "page[size]": 20
})
```

### Savings Bonds

```python
# I-bond and EE bond rates
ibond = treasury_get("v2/accounting/od/savings_bonds_pcs", {
    "fields": "record_date,bond_series,issue_price,redemp_value",
    "filter": "bond_series:eq:I",
    "sort": "-record_date",
    "page[size]": 12
})
```

## Query Parameters

| Parameter | Format | Example |
|-----------|--------|---------|
| `fields` | comma-separated | `fields=record_date,tot_debt_out_amt` |
| `filter` | `field:op:value` | `filter=record_date:gte:2024-01-01` |
| `sort` | `field` or `-field` | `sort=-record_date` |
| `page[size]` | integer (max 10000) | `page[size]=100` |
| `page[number]` | integer | `page[number]` |
| `format` | `json` or `csv` | `format=json` |

### Filter Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `eq` | equals | `record_date:eq:2024-09-30` |
| `gt` | greater than | `record_date:gt:2024-01-01` |
| `gte` | greater than or equal | `record_date:gte:2024-01-01` |
| `lt` | less than | `record_date:lt:2025-01-01` |
| `lte` | less than or equal | `record_date:lte:2024-12-31` |
| `in` | in list | `security_type:in:(Note,Bond)` |

## Discover Available Tables

```python
# Meta endpoint: list all tables
meta = requests.get("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/").json()

# Get table schema (field names and types)
schema = treasury_get("v1/accounting/od/debt_outstanding/")
print(schema["meta"]["labels"])  # Field descriptions
print(schema["meta"]["dataTypes"])  # Data types
```

## Response Format

```json
{
  "data": [
    {"record_date": "2024-11-01", "tot_pub_debt_out_amt": "35891234567890.12"},
    {"record_date": "2024-10-31", "tot_pub_debt_out_amt": "35874321098765.43"}
  ],
  "meta": {
    "count": 2,
    "labels": {"record_date": "Record Date", "tot_pub_debt_out_amt": "Total Public Debt Outstanding Amount"},
    "dataTypes": {"record_date": "DATE", "tot_pub_debt_out_amt": "CURRENCY"},
    "total-count": 9846,
    "total-pages": 985
  },
  "links": {
    "self": "...", "first": "...", "prev": "...", "next": "...", "last": "..."
  }
}
```

## Use Cases for Scientific Research

- **Research funding context**: Federal R&D spending trends from budget data
- **Economic indicators**: Connect macroeconomic conditions to research investment
- **Currency risk**: Exchange rates for international collaboration cost analysis
- **NIH/NSF funding cycles**: Correlate federal fiscal data with grant funding patterns
- **Inflation analysis**: CPI and debt growth for research cost projections

## Rate Limits & Access

- **Authentication**: None required
- **Rate limits**: Not published; generous for reasonable usage (< 100 req/min)
- **Data freshness**: Daily for debt data; monthly for MTS; quarterly for exchange rates
- **Historical depth**: Most tables go back to 1990s–2000s; some to 1970s
