# Alpha Vantage

Financial market data for stocks, forex, cryptocurrencies, commodities, economic indicators, and 50+ technical indicators.

## Setup

```bash
export ALPHA_VANTAGE_API_KEY="your_key"
# Free tier: 25 requests/day, 5 req/min
# Premium: up to 1200 req/min
```

Get a free key at: https://www.alphavantage.co/support/#api-key

## Core Data Functions

### Stock Data
```python
import requests

BASE = "https://www.alphavantage.co/query"
KEY = os.environ["ALPHA_VANTAGE_API_KEY"]

# Intraday time series (1min, 5min, 15min, 30min, 60min)
r = requests.get(BASE, params={
    "function": "TIME_SERIES_INTRADAY",
    "symbol": "AAPL",
    "interval": "5min",
    "apikey": KEY
})

# Daily adjusted (splits/dividends adjusted)
r = requests.get(BASE, params={
    "function": "TIME_SERIES_DAILY_ADJUSTED",
    "symbol": "MSFT",
    "outputsize": "compact",  # 'compact'=100 pts, 'full'=20yr
    "apikey": KEY
})

# Company overview
r = requests.get(BASE, params={
    "function": "OVERVIEW",
    "symbol": "IBM",
    "apikey": KEY
})

# Earnings (quarterly + annual)
r = requests.get(BASE, params={
    "function": "EARNINGS",
    "symbol": "TSLA",
    "apikey": KEY
})
```

### Forex & Crypto
```python
# Forex real-time rate
r = requests.get(BASE, params={
    "function": "CURRENCY_EXCHANGE_RATE",
    "from_currency": "USD",
    "to_currency": "JPY",
    "apikey": KEY
})

# Crypto daily
r = requests.get(BASE, params={
    "function": "DIGITAL_CURRENCY_DAILY",
    "symbol": "BTC",
    "market": "USD",
    "apikey": KEY
})
```

### Commodities & Economic Indicators
```python
# Crude oil (WTI/Brent) - monthly/weekly/daily
r = requests.get(BASE, params={
    "function": "WTI",
    "interval": "monthly",
    "apikey": KEY
})

# GDP, CPI, Unemployment, Federal Funds Rate
for fn in ["REAL_GDP", "CPI", "UNEMPLOYMENT", "FEDERAL_FUNDS_RATE"]:
    r = requests.get(BASE, params={"function": fn, "apikey": KEY})
```

### Technical Indicators (50+)
```python
# SMA, EMA, RSI, MACD, Bollinger Bands, etc.
r = requests.get(BASE, params={
    "function": "RSI",
    "symbol": "AAPL",
    "interval": "daily",
    "time_period": 14,
    "series_type": "close",
    "apikey": KEY
})

r = requests.get(BASE, params={
    "function": "MACD",
    "symbol": "AAPL",
    "interval": "daily",
    "series_type": "close",
    "apikey": KEY
})
```

## Available Functions (Key Selection)

| Category | Functions |
|----------|-----------|
| Stocks | TIME_SERIES_INTRADAY, TIME_SERIES_DAILY, TIME_SERIES_DAILY_ADJUSTED, TIME_SERIES_WEEKLY, TIME_SERIES_MONTHLY |
| Fundamentals | OVERVIEW, EARNINGS, INCOME_STATEMENT, BALANCE_SHEET, CASH_FLOW |
| Search | SYMBOL_SEARCH, MARKET_STATUS, LISTING_STATUS |
| Forex | FX_INTRADAY, FX_DAILY, CURRENCY_EXCHANGE_RATE |
| Crypto | CRYPTO_INTRADAY, DIGITAL_CURRENCY_DAILY, CRYPTO_RATING |
| Commodities | WTI, BRENT, NATURAL_GAS, COPPER, ALUMINUM, WHEAT, CORN, SUGAR, COFFEE |
| Economy | REAL_GDP, REAL_GDP_PER_CAPITA, TREASURY_YIELD, FEDERAL_FUNDS_RATE, CPI, INFLATION, RETAIL_SALES, UNEMPLOYMENT |
| Technical | SMA, EMA, VWAP, MACD, STOCH, RSI, ADX, CCI, AROON, BBANDS, OBV, AD, MFI, ... (50+ total) |

## Rate Limit Handling

```python
import time

def av_request(params, retries=3):
    params["apikey"] = os.environ["ALPHA_VANTAGE_API_KEY"]
    for attempt in range(retries):
        r = requests.get("https://www.alphavantage.co/query", params=params)
        data = r.json()
        if "Note" in data:  # Rate limit hit
            time.sleep(60)
            continue
        if "Information" in data:  # Daily limit exceeded
            raise Exception(f"Daily API limit reached: {data['Information']}")
        return data
    raise Exception("Rate limit: too many retries")
```

## Use Cases for Scientific Research

- **Biotech stock tracking**: Monitor pharmaceutical/biotech company valuations around drug approvals
- **Commodity analysis**: Track raw material prices relevant to chemical synthesis costs
- **Economic context**: GDP/CPI data for research funding environment analysis
- **Correlation studies**: Link scientific breakthroughs to market reactions

## Output Format

All responses are JSON. Time series data structure:
```json
{
  "Meta Data": {"1. Information": "...", "2. Symbol": "AAPL", ...},
  "Time Series (5min)": {
    "2024-01-15 16:00:00": {
      "1. open": "185.00",
      "2. high": "185.50",
      "3. low": "184.80",
      "4. close": "185.20",
      "5. volume": "1234567"
    }
  }
}
```
