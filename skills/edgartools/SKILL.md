# EDGARTools

Python library for accessing SEC EDGAR filings (1994–present). Company financials, insider trading, institutional holdings, and more without manual EDGAR navigation.

## Installation

```bash
pip install edgartools
```

## Required Setup

```python
from edgar import set_identity

# REQUIRED: EDGAR requires identification for all requests
set_identity("Your Name your.email@example.com")
```

## Core Usage

### Company Lookup

```python
from edgar import Company, find_company

# By ticker symbol
apple = Company("AAPL")
nvidia = Company("NVDA")

# By CIK number
company = Company(320193)

# Search by name
results = find_company("Moderna")
```

### Filing Retrieval

```python
company = Company("MRNA")

# Get all filings
filings = company.get_filings()

# Filter by form type
annual_reports = company.get_filings(form="10-K")
quarterly_reports = company.get_filings(form="10-Q")
current_reports = company.get_filings(form="8-K")
proxy_statements = company.get_filings(form="DEF 14A")

# Get most recent filing
latest_10k = company.get_filings(form="10-K").latest(1)

# Get filings from date range
filings_2023 = company.get_filings(form="10-K", date="2023-01-01:2023-12-31")
```

### Financial Data (XBRL Parsing)

```python
# Get financial statements from 10-K
tenk = company.get_filings(form="10-K").latest(1)
filing = tenk[0]

# Access XBRL financial data
financials = filing.financials

income_stmt = financials.income_statement
balance_sheet = financials.balance_sheet
cash_flow = financials.cashflow_statement

# As pandas DataFrame
import pandas as pd
df = income_stmt.to_dataframe()
print(df[["NetIncomeLoss", "Revenues", "GrossProfit"]])

# Key metrics
revenue = income_stmt["Revenues"].value
net_income = income_stmt["NetIncomeLoss"].value
total_assets = balance_sheet["Assets"].value
```

### Insider Trading (Form 4)

```python
# Get recent insider transactions
insider_trades = company.get_filings(form="4")

for filing in insider_trades[:10]:
    transaction = filing.obj()
    print(f"Filer: {transaction.reporting_owner}")
    print(f"Type: {transaction.transaction_type}")  # Buy/Sell
    print(f"Shares: {transaction.transaction_shares}")
    print(f"Price: {transaction.transaction_price}")
    print(f"Date: {transaction.transaction_date}")
```

### 13F Institutional Holdings

```python
# Get hedge fund / institutional holdings
blackrock = Company("BLK")
form_13f = blackrock.get_filings(form="13F-HR").latest(1)[0]

holdings = form_13f.obj()
holdings_df = holdings.to_dataframe()

# Top holdings
print(holdings_df.nlargest(20, "value")[["nameOfIssuer", "shares", "value"]])
```

### Full-Text Search

```python
from edgar import full_text_search

# Search across all SEC filings
results = full_text_search("mRNA vaccine efficacy", form="10-K", date_range="2023:2024")
```

## Practical Examples

### Biotech Drug Pipeline from 10-K

```python
company = Company("MRNA")
filing = company.get_filings(form="10-K").latest(1)[0]

# Access full document text
doc = filing.document
text = doc.text()

# Search for pipeline section
import re
pipeline_section = re.search(r"(Pipeline|Product Candidates)(.*?)(?=\n#{1,3} )",
                              text, re.DOTALL)
```

### Track Insider Selling Before Drug Approval

```python
company = Company("BIIB")  # Biogen
insider_trades = company.get_filings(form="4", date="2023-01-01:2024-01-01")

sells = []
for f in insider_trades:
    t = f.obj()
    if hasattr(t, 'transaction_type') and 'S' in str(t.transaction_type):
        sells.append({
            "owner": t.reporting_owner,
            "shares": t.transaction_shares,
            "date": t.transaction_date
        })
```

### Multi-Year Revenue Trend

```python
company = Company("PFE")  # Pfizer
annual_filings = company.get_filings(form="10-K")[:5]  # Last 5 years

revenues = []
for f in annual_filings:
    fin = f.financials
    revenues.append({
        "year": f.filing_date.year,
        "revenue": fin.income_statement["Revenues"].value
    })
```

## Output Format

All financial data returns as structured Python objects with `.to_dataframe()` support. Filings return `Filing` objects with `.obj()` for parsed content, `.text()` for raw text, `.document` for full filing.

## Limitations

- Some older filings (pre-2009) lack XBRL structured data
- Rate limits apply (EDGAR enforces ~10 req/sec)
- Must call `set_identity()` or requests will be blocked
