# Literature Survey Workflow Summary

This document describes **research-collect**, a CLI skill for conducting systematic literature surveys. Here are the key components:

## Purpose
Automate paper discovery, filtering, and organization to support downstream research skills.

## Five-Phase Workflow

**Phase 1 (Prep)**: Generate 4-8 search terms and establish directory structure.

**Phase 2 (Search Loop)**: For each term:
- Query arXiv with `arxiv_search`
- Score results (1-5 scale); retain ≥4
- Download relevant papers
- Store metadata in `papers/_meta/{id}.json`

**Phase 3 (Code References)**:
- Identify top 5 papers (score ≥4)
- Search GitHub using paper titles + keywords
- Clone 3-5 repositories to `repos/`
- Document selections in `prepare_res.md`

**Phase 4 (Organization)**: Cluster papers into 3-6 research directions; organize into `papers/{direction}/` folders based on metadata analysis.

**Phase 5 (Reporting)**: Generate `survey/report.md` with summary, directions, top papers, and recommended reading order.

## Key Principles
- **Incremental processing** prevents context bloat
- **Metadata-driven** classification using JSON files
- **File structure** directly mirrors categorization

## Available Tools
- `arxiv_search`: Query papers
- `arxiv_download`: Retrieve documents
- `github_search`: Find reference repositories
