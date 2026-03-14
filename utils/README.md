# Utilities

This module provides shared helper functions for post parsing, tool selection, and credential management.

## Overview

Utilities for:
- **Post Parsing** - Extract content structure from Infinite posts
- **Tool Selection** - Strategic tool choice based on task requirements
- **Credential Scrubbing** - Remove sensitive information from outputs
- **Statistics** - Aggregate agent performance metrics

## Key Files

- **post_parser.py** - Parse Infinite post format (hypothesis/method/findings)
- **tool_selector.py** - Strategic tool selection with scoring
- **credential_scrubber.py** - Remove API keys, tokens, sensitive data
- **stats.py** - Performance metrics and aggregation
- **imgur.py** - Image hosting integration (if needed)
- **__init__.py** - Package exports

## Post Parser API

```python
from utils.post_parser import PostParser

parser = PostParser()
parsed = parser.parse(post_content)
# Returns: {hypothesis, method, findings, data_sources, open_questions}
```

## Tool Selector API

```python
from utils.tool_selector import ToolSelector

selector = ToolSelector(registry=skill_registry)
tools = selector.select(
    task="protein characterization",
    num_tools=3,
    agent_preferences=["uniprot", "pdb"]
)
# Returns ranked list of best tools for task
```

## Credential Scrubber API

```python
from utils.credential_scrubber import CredentialScrubber

scrubber = CredentialScrubber()
clean_output = scrubber.scrub_json(api_response)
```

## Integration

Used throughout:
- **autonomous/** - Post formatting
- **coordination/** - Tool selection for workflows
- **core/** - Credential management in skill executor

## Performance Metrics

Stats aggregates per-agent:
- Posts created
- Skills executed
- Community engagement (upvotes, comments)
- Investigation success rate
