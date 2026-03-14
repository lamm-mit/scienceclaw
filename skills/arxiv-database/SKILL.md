# arXiv Database Skill Summary

This CLI skill enables searching and retrieving academic preprints from arXiv.org through its public Atom API. It's maintained by Orchestra Research under an MIT license.

## Key Capabilities

The tool supports multiple search approaches: keyword queries across titles and abstracts, author-specific lookups, arXiv ID retrieval, category browsing, and PDF downloads. Results return as structured JSON containing paper metadata like titles, abstracts, author lists, submission dates, and direct links.

## Primary Use Cases

According to the documentation, deploy this skill when exploring research literature in computer science, machine learning, physics, mathematics, statistics, or related quantitative fields. It's particularly valuable for "building literature review datasets for AI/ML research" and monitoring specific research communities.

## Search Syntax

The API uses field prefixes (`ti:` for titles, `au:` for authors, `cat:` for categories) combined with Boolean operators. Users can construct sophisticated queries like: `"(abs:RLHF OR abs:reinforcement learning from human feedback) AND cat:cs.CL"` to filter results precisely.

## Notable Limitations

The skill searches only metadata rather than full paper text. It lacks citation metrics (requiring OpenAlex for that data), caps results at 300 per query, and operates under rate-limiting constraints of approximately one request per three seconds.
