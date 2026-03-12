#!/usr/bin/env python3
"""
scientific-writing — Scientific writing assistant (CLI).

This skill is invoked by autonomous loops as a *structured writing* utility.
It must accept `--query` and always return machine-readable JSON when asked.

Important: this tool does NOT claim facts about the world. It produces
templates and writing scaffolds grounded only in the provided query string.

Usage:
    python demo.py --query "topic" [--mode outline|hypothesis|synthesis] [--format json]
"""

import argparse
import json
import sys
from datetime import datetime, timezone


def _outline(query: str) -> str:
    return "\n".join(
        [
            "## Title",
            f"{query.strip() or 'Untitled'}",
            "",
            "## Abstract (template)",
            "- **Background**: <1–2 sentences of context>",
            "- **Question**: <what is being tested?>",
            "- **Approach**: <methods/tools/data you will use>",
            "- **Key finding**: <what you expect to show (avoid overstating)>",
            "- **Implication**: <why it matters>",
            "",
            "## Introduction (template)",
            "- Define the problem and why it matters",
            "- Summarize key prior work (with citations you will add)",
            "- State the gap",
            "",
            "## Methods (template)",
            "- Data sources",
            "- Experimental/analysis pipeline",
            "- Quality controls and failure modes",
            "",
            "## Results (template)",
            "- Result 1: <headline + evidence>",
            "- Result 2: <headline + evidence>",
            "",
            "## Discussion (template)",
            "- Interpretation",
            "- Limitations",
            "- Follow-up experiments",
        ]
    )


def _hypothesis(query: str) -> str:
    return "\n".join(
        [
            "## Hypothesis (template)",
            f"- **Topic**: {query.strip() or '<topic>'}",
            "- **Mechanism**: <proposed causal mechanism>",
            "- **Variable / parameter**: <what you will vary or measure>",
            "- **Prediction**: <what should change, in what direction>",
            "- **Confirming evidence**: <what pattern would support it>",
            "- **Refuting evidence**: <what pattern would falsify it>",
        ]
    )


def _synthesis(query: str) -> str:
    return "\n".join(
        [
            "## Synthesis scaffold (template)",
            f"- **Topic**: {query.strip() or '<topic>'}",
            "- **What we observed**: <bullet evidence>",
            "- **How it fits together**: <mechanistic integration>",
            "- **Most important uncertainty**: <what you still don’t know>",
            "- **Next step**: <the smallest test that reduces uncertainty>",
        ]
    )


def generate(query: str, mode: str = "outline") -> dict:
    m = (mode or "outline").strip().lower()
    if m == "hypothesis":
        md = _hypothesis(query)
    elif m == "synthesis":
        md = _synthesis(query)
    else:
        m = "outline"
        md = _outline(query)

    return {
        "skill": "scientific-writing",
        "status": "ok",
        "mode": m,
        "topic": query or "",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "note": "Template/scaffold only; does not assert factual claims.",
        "markdown": md,
    }


def main():
    parser = argparse.ArgumentParser(description='scientific-writing demonstration')
    parser.add_argument(
        '--query', '-q',
        default="",
        help='Topic/prompt for the writing scaffold'
    )
    parser.add_argument(
        '--mode', '-m',
        default='outline',
        choices=['outline', 'hypothesis', 'synthesis'],
        help='Which scaffold to generate (default: outline)'
    )
    parser.add_argument(
        '--format', '-f',
        default='summary',
        choices=['summary', 'json'],
        help='Output format (default: summary)'
    )

    args = parser.parse_args()

    try:
        result = generate(query=args.query, mode=args.mode)

        if args.format == 'json':
            print(json.dumps(result, indent=2))
        else:
            print("=" * 70)
            print(f"{result['skill']} - {result['mode']}")
            print("=" * 70)
            print(f"Status: {result['status']}")
            if args.query:
                print(f"\nTopic: {args.query}")
            print(f"\n{result['markdown']}")
            print("=" * 70)

    except Exception as e:
        # Keep the skill executor from hard-failing the whole chain.
        print(json.dumps({"skill": "scientific-writing", "status": "error", "error": str(e)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
