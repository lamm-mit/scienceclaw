---
name: comtrade-trade
description: Query UN Comtrade bilateral trade flows (USD, kg) for critical minerals by HS code, country, and year
metadata:
  openclaw:
    emoji: "🚢"
    requires:
      bins:
        - python3
      env:
        - UNCOMTRADE_API_KEY
---

# UN Comtrade Trade Data

Query UN Comtrade for bilateral trade flows of critical minerals. Returns trade values (USD), net weight (kg), and flow direction (imports/exports) by HS commodity code, reporter country, partner country, and year.

## Usage

### Search by mineral name:
```bash
python3 {baseDir}/scripts/comtrade_query.py --mineral lithium
```

### Search by HS code:
```bash
python3 {baseDir}/scripts/comtrade_query.py --hs-code 282520 --reporter 842
```

### Filter by country and flow:
```bash
python3 {baseDir}/scripts/comtrade_query.py --mineral cobalt --reporter 842 --flow X --year 2022
```

### JSON output:
```bash
python3 {baseDir}/scripts/comtrade_query.py --mineral rare_earth --format json --year 2023
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--mineral` | Critical mineral name (lithium, cobalt, rare_earth, graphite, nickel, manganese, gallium, germanium, copper, hree, lree) | - |
| `--hs-code` | HS commodity code (alternative to --mineral) | - |
| `--reporter` | Reporter country code (e.g., 842 for USA, 156 for China) | 0 (all) |
| `--partner` | Partner country code | 0 (world) |
| `--flow` | Trade flow: M (imports), X (exports), M,X (both) | M,X |
| `--year` | Year(s), comma-separated | 2023 |
| `--limit` | Maximum records to return | 500 |
| `--format` | Output format: summary, detailed, json | summary |

## Available Minerals

| Name | HS Codes | Description |
|------|----------|-------------|
| `lithium` | 253090, 282520, 283691, 850650 | Ores, oxide/hydroxide, carbonate, batteries |
| `cobalt` | 2605, 282200, 810520, 810590 | Ores, oxides, unwrought, articles |
| `rare_earth` | 2846, 280530 | REE compounds, REE metals |
| `hree` | 284690 | Heavy REE compounds |
| `lree` | 284610 | Light REE compounds |
| `graphite` | 250410, 250490, 380110 | Natural (amorphous, crystalline), artificial |
| `nickel` | 2604, 7501, 750210, 750220, 281122 | Ores, matte, unwrought, alloys, oxides |
| `manganese` | 2602, 811100 | Ores, unwrought |
| `gallium` | 811292 | Unwrought |
| `germanium` | 811299 | Other base metals |
| `copper` | 7402, 7403 | Refined, unrefined |

## Examples

```bash
# US lithium imports
python3 {baseDir}/scripts/comtrade_query.py --mineral lithium --reporter 842 --flow M --year 2023

# Global cobalt trade flows
python3 {baseDir}/scripts/comtrade_query.py --mineral cobalt --format detailed

# China rare earth exports
python3 {baseDir}/scripts/comtrade_query.py --mineral rare_earth --reporter 156 --flow X --year 2022

# Nickel trade by specific HS code
python3 {baseDir}/scripts/comtrade_query.py --hs-code 2604 --format json
```

## Notes

- Requires `UNCOMTRADE_API_KEY` environment variable
- Country codes follow UN M49 standard (842=USA, 156=China, 276=Germany, etc.)
- Use 0 for "all countries" or "world"
- HS codes follow Harmonized System classification
- API has rate limits; be conservative with large queries
