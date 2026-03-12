#!/usr/bin/env python3
"""
Fabric pattern runner - execute Fabric CLI patterns for paper summarization,
insight extraction, and content analysis. Falls back to listing patterns
if Fabric is not installed.
"""

import argparse
import json
import os
import subprocess
import sys

SCIENTIFIC_PATTERNS = [
    "summarize",
    "extract_wisdom",
    "extract_insights",
    "analyze_paper",
    "create_summary",
    "extract_main_idea",
    "extract_ideas",
    "extract_recommendations",
    "extract_references",
    "extract_article_wisdom",
    "extract_extraordinary_claims",
    "extract_patterns",
    "extract_predictions",
    "extract_questions",
    "extract_sponsors",
    "analyze_claims",
    "analyze_tech_impact",
    "check_agreement",
    "compare_and_contrast",
    "create_aphorisms",
    "create_explanation",
    "create_keynote",
    "create_report_finding",
    "explain_code",
    "explain_docs",
    "explain_math",
    "find_logical_fallacies",
    "improve_writing",
    "label_and_rate",
    "rate_content",
    "rate_value",
    "summarize_debate",
    "summarize_git_changes",
    "summarize_micro",
    "summarize_newsletter",
    "summarize_paper",
    "summarize_rpg_session",
    "to_flashcards",
    "write_essay",
    "write_micro_essay",
    "write_seminar_intro",
]


def is_fabric_installed() -> bool:
    """Check if the fabric CLI is available."""
    try:
        result = subprocess.run(
            ["fabric", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_fabric(pattern: str, input_text: str) -> dict:
    """Execute a Fabric pattern against input text."""
    result = subprocess.run(
        ["fabric", "--pattern", pattern],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            f"Fabric exited with code {result.returncode}: {stderr}"
        )

    return {
        "pattern": pattern,
        "output": result.stdout.strip(),
        "status": "success",
    }


def resolve_input(input_arg: str) -> str:
    """If input_arg is a file path, read it; otherwise treat as raw text."""
    if input_arg and os.path.isfile(input_arg):
        with open(input_arg, "r", encoding="utf-8") as f:
            return f.read()
    return input_arg


def main():
    parser = argparse.ArgumentParser(
        description="Run Fabric patterns for scientific paper analysis and insight extraction"
    )
    parser.add_argument(
        "--pattern",
        required=True,
        help="Fabric pattern name (e.g. summarize, extract_wisdom, analyze_paper)",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input text or path to a text file to analyze",
    )
    parser.add_argument(
        "--list-patterns",
        action="store_true",
        help="List available scientific patterns and exit",
    )
    args = parser.parse_args()

    if args.list_patterns:
        result = {
            "pattern": args.pattern,
            "output": "",
            "status": "patterns_listed",
            "available_patterns": SCIENTIFIC_PATTERNS,
            "total": len(SCIENTIFIC_PATTERNS),
            "note": (
                "These are popular Fabric patterns for scientific work. "
                "Full pattern list: https://github.com/danielmiessler/fabric/tree/main/patterns"
            ),
        }
        print(json.dumps(result, indent=2))
        return

    if not is_fabric_installed():
        result = {
            "pattern": args.pattern,
            "output": "",
            "status": "fabric_not_installed",
            "error": (
                "Fabric CLI not found. Install with: "
                "go install github.com/danielmiessler/fabric@latest"
            ),
            "available_patterns": SCIENTIFIC_PATTERNS,
            "note": (
                "Without Fabric, you can use the pattern names above as system prompts "
                "directly with an LLM. Fabric patterns are at: "
                "https://github.com/danielmiessler/fabric/tree/main/patterns"
            ),
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    try:
        input_text = resolve_input(args.input)
        result = run_fabric(args.pattern, input_text)
    except subprocess.TimeoutExpired:
        result = {
            "pattern": args.pattern,
            "output": "",
            "status": "error",
            "error": "Fabric timed out after 120 seconds.",
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)
    except Exception as e:
        result = {
            "pattern": args.pattern,
            "output": "",
            "status": "error",
            "error": str(e),
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
