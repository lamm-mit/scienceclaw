# Parallel Web Systems API Skill Overview

## Core Purpose
This skill enables web search, content extraction, and comprehensive research using the Parallel Chat API and Extract API. It serves as the primary tool for all internet-based information gathering in scientific writing workflows.

## Key Capabilities

**Search Function**: Delivers synthesized summaries with citations through the Parallel Chat API's base model, ideal for quick lookups and factual queries.

**Deep Research**: Produces detailed intelligence reports using the core model, best suited for market analysis, competitive intelligence, and multi-source synthesis.

**URL Extraction**: Limited to citation verification and special cases where specific URL content confirmation is needed.

## Critical Requirements

The documentation emphasizes that "every web search and deep research result MUST be saved to the project's `sources/` folder." This mandatory practice ensures reproducibility and maintains an audit trail of all research activities.

## Model Options

Two research models are available:
- **Base**: 15-100 seconds latency; ideal for standard searches
- **Core**: 60 seconds to 5 minutes; optimal for comprehensive reports

## Setup & Access

Users must configure the `PARALLEL_API_KEY` environment variable and install required Python packages (openai and parallel-web). The API platform is accessible at https://platform.parallel.ai.

## Integration Note

The skill differentiates from academic-specific tools—purely scholarly queries should route to research-lookup instead, while general web searches remain within this skill's scope.