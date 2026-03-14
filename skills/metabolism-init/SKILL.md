# Metabolism Initialization Skill Overview

This skill enables **knowledge metabolism initialization** for research topics through a structured Day 0 baseline-building process.

## Key Components

**Configuration Setup**: The system checks for `metabolism/config.json` and creates it if absent, capturing research direction, keywords, categories, and processing history.

**Directory Structure**: Establishes organized workspace with subdirectories for knowledge, hypotheses, experiments, conversations, and logging.

**Three-Phase Workflow**:

1. **Broad Literature Survey** — Delegates to `/research-collect` to gather foundational and recent works without date restrictions, generating metadata and downloads

2. **Paper Analysis** — Extracts core methodologies and conclusions from TeX sources or PDFs, tracking processed IDs to avoid duplication

3. **Knowledge State Construction** — Creates indexed summaries mapping identified topics with cross-references, timelines, and open questions

**Documentation**: Generates `metabolism/knowledge/_index.md` with research goals, topic tables, and relationship mapping, plus topic-specific markdown files and timestamped initialization logs.

## Operational Principles

The skill operates autonomously post-configuration, avoiding data fabrication and requiring content verification before modifications. It spawns sessions that share the working directory, streamlining collaborative processes.
