# ScienceClaw for Domain Scientists

This guide is for researchers who want to use ScienceClaw as a practical scientific assistant without needing to understand every part of the codebase first.

This fork of ScienceClaw is specifically geared toward critical minerals and materials workflows (for example, commodity profiling, policy monitoring, and web-intel ingestion).

It explains what the system does, how to run it reproducibly, where evidence comes from, and how to use key workflows for literature-driven and critical-minerals investigations.

## 1) What ScienceClaw Is

ScienceClaw is an autonomous, tool-using research system built on OpenClaw. It can:

- propose hypotheses from a topic prompt
- select relevant tools ("skills") from a large catalog
- execute tool chains to gather evidence
- run computational checks (when relevant)
- synthesize findings into structured reports/posts
- generate publication-style figures from result artifacts

The repository supports both:

- single-agent investigations
- multi-agent coordinated investigations (investigator, validator, critic, synthesizer patterns)

In this fork, those capabilities are tuned for critical minerals and materials research.

For a broader, general-purpose ScienceClaw experience across many scientific domains, use the upstream main repository:

- https://github.com/lamm-mit/scienceclaw

## 2) Who This Guide Is For

This document assumes you are comfortable with scientific workflows and basic command-line usage, but not necessarily with agent framework internals.

If you only need to run investigations and inspect outputs, this guide is enough.

## 3) Core Concepts

### Skills

A skill is a focused tool wrapper (usually a script + metadata) for a data source or computation.

Examples:

- literature search and metadata extraction
- sequence/structure queries
- chemistry/property estimations
- materials and minerals monitoring

Skills live under:

- `/Users/nancywashton/scienceclaw/skills/`

### Tool Chaining

A single investigation typically uses 5-12 skills in sequence/parallel. For example:

1. discover papers and reports
2. extract entities (targets/materials/compounds)
3. compute supporting metrics
4. validate/refine conclusions

### Evidence-First Outputs

Results are strongest when skills return parseable data (JSON/structured output), which is then synthesized. You should treat final text as an interpretation layer over tool outputs, not a substitute for source verification.

## 4) Installation and Environment

### Prerequisites

- macOS or Linux shell environment
- Python 3.10+ recommended
- Node.js >= 22 (for OpenClaw tooling)

### Setup

```bash
git clone https://github.com/lamm-mit/scienceclaw.git
cd scienceclaw
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional command setup from this repo:

```bash
./install_scienceclaw_command.sh
```

### API Keys and Optional Services

Some skills require external credentials. Common examples in this repo include:

- `UNCOMTRADE_API_KEY` (trade records)
- `SERPAPI_KEY` (some literature/Scholar paths)
- `FIRECRAWL_API_KEY` (optional richer web ingestion path)

If a key is missing, many scripts degrade gracefully for affected sections and emit warnings.

## 5) First Investigation (Minimal)

If command shims are installed:

```bash
scienceclaw-post --agent MyAgent --topic "CRISPR base editing off-targets" --community biology --dry-run
```

If you prefer Python entry points:

```python
from autonomous.deep_investigation import run_deep_investigation

result = run_deep_investigation(
    agent_name="MyAgent",
    topic="CRISPR base editing off-targets",
    community="biology",
)

print(result["title"])
print(result["hypothesis"])
print(result["findings"])
print(result["figures"])
```

Use `--dry-run` while validating your setup so you can inspect outputs before posting anywhere.

## 6) Critical-Minerals Workflow (Scientist-Focused)

The repository includes a dedicated minerals intelligence pipeline that combines production/trade/risk/policy with web signal monitoring.

### Commodity Profile

Primary script:

- `/Users/nancywashton/scienceclaw/skills/commodity-profile/scripts/generate_profile.py`

Run a full profile:

```bash
python3 /Users/nancywashton/scienceclaw/skills/commodity-profile/scripts/generate_profile.py \
  --commodity "Lithium"
```

JSON output for downstream analysis:

```bash
python3 /Users/nancywashton/scienceclaw/skills/commodity-profile/scripts/generate_profile.py \
  --commodity "Graphite" \
  --year 2022 \
  --format json
```

Sections currently supported:

- `production`
- `trade`
- `risk`
- `research`
- `policy`
- `intel`

Select sections explicitly:

```bash
python3 /Users/nancywashton/scienceclaw/skills/commodity-profile/scripts/generate_profile.py \
  --commodity "Cobalt" \
  --sections production,risk,intel \
  --intel-max-results 20
```

### What `intel` Does

The `intel` section chains three skills:

- `minerals-news-monitor` for broad media discovery
- `minerals-gov-monitor` for regulator/government-domain discovery
- `minerals-web-ingest` for full-page content normalization and dedupe

This is intended for early warning and policy-signal tracking, not final policy adjudication. Always review high-impact claims against source documents.

### Running Monitors Individually

News/industry monitor:

```bash
python3 /Users/nancywashton/scienceclaw/skills/minerals-news-monitor/scripts/news_monitor.py \
  --query "critical minerals export controls" \
  --commodity lithium \
  --commodity cobalt \
  --max-results 20 \
  --format json
```

Government/regulator monitor:

```bash
python3 /Users/nancywashton/scienceclaw/skills/minerals-gov-monitor/scripts/gov_monitor.py \
  --commodity lithium \
  --country "united states" \
  --country china \
  --max-results 25 \
  --format json
```

Web ingest:

```bash
python3 /Users/nancywashton/scienceclaw/skills/minerals-web-ingest/scripts/web_ingest.py \
  --input-json gov_records.json \
  --output-jsonl ingested_records.jsonl \
  --format summary
```

## 7) Reproducibility and Scientific Hygiene

For reliable science workflows, use this checklist:

1. Pin your environment.
2. Record command lines and timestamps.
3. Prefer `--format json` outputs for archival/reanalysis.
4. Keep raw tool outputs alongside synthesized summaries.
5. Track API-key-dependent sections and missing-data fallbacks.
6. Re-run high-impact analyses at least once.

Recommended pattern:

- write raw JSON artifacts to a run-specific folder
- run synthesis from those artifacts where possible
- include script version/commit hash in your notes

## 8) Understanding Outputs

Most tool outputs have three levels:

- summary text (quick read)
- detailed text (human inspection)
- JSON (best for reproducibility and post-processing)

For publication pipelines, consume JSON first and generate tables/figures from that.

## 9) Validation and Sanity Checks

Before trusting a new workflow setup:

```bash
python3 -m py_compile \
  /Users/nancywashton/scienceclaw/skills/commodity-profile/scripts/generate_profile.py \
  /Users/nancywashton/scienceclaw/skills/minerals-news-monitor/scripts/news_monitor.py \
  /Users/nancywashton/scienceclaw/skills/minerals-gov-monitor/scripts/gov_monitor.py \
  /Users/nancywashton/scienceclaw/skills/minerals-web-ingest/scripts/web_ingest.py
```

And check CLI contracts:

```bash
python3 /Users/nancywashton/scienceclaw/skills/commodity-profile/scripts/generate_profile.py --help
python3 /Users/nancywashton/scienceclaw/skills/minerals-news-monitor/scripts/news_monitor.py --help
python3 /Users/nancywashton/scienceclaw/skills/minerals-gov-monitor/scripts/gov_monitor.py --help
python3 /Users/nancywashton/scienceclaw/skills/minerals-web-ingest/scripts/web_ingest.py --help
```

## 10) Common Failure Modes

### Missing package/import errors

- Activate the virtual environment.
- Reinstall requirements.

### Empty trade or literature results

- Confirm relevant API keys are set.
- Verify commodity naming and year range.

### Web ingestion has high skip/error counts

- Increase timeout.
- retry with fewer URLs.
- optionally configure Firecrawl for difficult pages.

### Agent selected odd skills

- Inspect skill-selection behavior and run topic-specific tests.
- Force narrower topics for initial validation runs.

## 11) Extending for Your Domain

To adapt ScienceClaw for a new scientific subdomain:

1. start with existing skills and test composition
2. add one narrow new skill at a time
3. enforce structured JSON output from new scripts
4. add examples and constraints in the skill `SKILL.md`
5. validate selection behavior on representative prompts

Keep each skill focused on one data source or transform. Smaller skills chain more reliably than broad monoliths.

## 12) Where to Go Next

- This fork's project overview: `/Users/nancywashton/scienceclaw/README.md`
- Upstream (general-purpose) ScienceClaw repository: `https://github.com/lamm-mit/scienceclaw`
- Architecture details: `/Users/nancywashton/scienceclaw/ARCHITECTURE.md`
- Extended docs: `/Users/nancywashton/scienceclaw/DOCS.md`
- Skill discovery and exploration:

```bash
python3 /Users/nancywashton/scienceclaw/skill_catalog.py --stats
python3 /Users/nancywashton/scienceclaw/skill_catalog.py --search "minerals"
python3 /Users/nancywashton/scienceclaw/skill_catalog.py --suggest "rare earth separation policy risk"
```

## 13) Recommended Team Workflow

For lab or project teams, a practical pattern is:

1. One person defines investigation prompts and acceptance criteria.
2. One person runs and archives raw JSON outputs.
3. One person validates top claims against source URLs.
4. One person synthesizes narrative and figures for reporting.

This separation helps keep generated narrative grounded in auditable evidence.
