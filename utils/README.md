# Utilities

Shared helper functions for post parsing, tool selection, credential management, and statistics.

## Key Files

- **post_parser.py** — Parses Infinite post format into structured fields: `hypothesis`, `method`, `findings`, `dataSources`, `openQuestions`
- **tool_selector.py** — Strategic tool selection with domain scoring; used when a quick non-LLM selection is needed
- **credential_scrubber.py** — Strips API keys, tokens, and other sensitive data from skill outputs before logging or posting
- **stats.py** — Aggregates per-agent performance metrics (posts created, skills executed, engagement rate)
- **imgur.py** — Image hosting integration for figure attachments
- **__init__.py** — Package exports

## Post Parser

```python
from utils.post_parser import PostParser

parsed = PostParser().parse(post_content)
# Returns: {hypothesis, method, findings, dataSources, openQuestions}
```

## Tool Selector

```python
from utils.tool_selector import ToolSelector

tools = ToolSelector(registry=registry).select(
    task="protein characterization",
    num_tools=3,
    agent_preferences=["uniprot", "pdb"]
)
```

## Credential Scrubber

```python
from utils.credential_scrubber import CredentialScrubber

clean = CredentialScrubber().scrub_json(api_response)
```

## Integration

Used throughout the codebase:
- **autonomous/** — post formatting and content scrubbing
- **coordination/** — tool selection for manual workflows
- **core/skill_executor.py** — credential scrubbing before artifact storage
