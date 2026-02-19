#!/usr/bin/env python3
"""
Diagramming tool - generate Mermaid syntax diagrams for biological pathways,
molecular networks, experimental workflows, and research architecture.
"""

import argparse
import json
import os
import re
import sys


def tokenize_description(description: str) -> list:
    """Extract meaningful tokens from the description for diagram nodes."""
    # Split on common separators and filter short words
    tokens = re.split(r"[\s,;|&]+", description)
    tokens = [t.strip().title() for t in tokens if len(t.strip()) > 2]
    return tokens[:8] if len(tokens) > 8 else tokens


def generate_flowchart(description: str) -> str:
    """Generate a Mermaid flowchart (graph TD)."""
    tokens = tokenize_description(description)

    if not tokens:
        tokens = ["Start", "Process", "Analyze", "Result"]

    # Build a linear chain with the first token as title
    lines = ["graph TD"]
    lines.append(f'  A["{description}"]')

    node_ids = [chr(ord("B") + i) for i in range(len(tokens))]

    for i, (nid, token) in enumerate(zip(node_ids, tokens)):
        lines.append(f'  {nid}["{token}"]')

    # Connect A to first node, then chain
    if node_ids:
        lines.append(f"  A --> {node_ids[0]}")
        for i in range(len(node_ids) - 1):
            lines.append(f"  {node_ids[i]} --> {node_ids[i+1]}")

    return "\n".join(lines)


def generate_sequence(description: str) -> str:
    """Generate a Mermaid sequence diagram."""
    tokens = tokenize_description(description)

    # Use first two tokens as participants, rest as messages
    participants = tokens[:2] if len(tokens) >= 2 else ["Actor", "System"]
    messages = tokens[2:] if len(tokens) > 2 else ["Interact", "Respond", "Complete"]

    lines = ["sequenceDiagram"]
    for p in participants:
        lines.append(f"  participant {p}")

    # Alternate messages between participants
    for i, msg in enumerate(messages):
        sender = participants[i % 2]
        receiver = participants[(i + 1) % 2]
        lines.append(f"  {sender}->>+{receiver}: {msg}")
        lines.append(f"  {receiver}-->>-{sender}: Done")

    return "\n".join(lines)


def generate_er(description: str) -> str:
    """Generate a Mermaid ER diagram."""
    tokens = tokenize_description(description)

    entities = tokens[:4] if len(tokens) >= 4 else (tokens + ["Entity"])[:4]
    # Pad if needed
    while len(entities) < 2:
        entities.append(f"Entity{len(entities)}")

    lines = ["erDiagram"]
    # Create relationships between consecutive entities
    for i in range(len(entities) - 1):
        lines.append(f'  {entities[i]} ||--o{{ {entities[i+1]} : "has"')

    # Add sample attributes to first entity
    lines.append(f"  {entities[0]} {{")
    lines.append(f"    int id PK")
    lines.append(f"    string name")
    lines.append(f"    string description")
    lines.append("  }")

    return "\n".join(lines)


def generate_mindmap(description: str) -> str:
    """Generate a Mermaid mind map."""
    tokens = tokenize_description(description)

    branches = tokens[:6] if len(tokens) >= 6 else (tokens + ["Concept"] * 6)[:6]

    lines = ["mindmap"]
    lines.append(f"  root(({description}))")

    # Group into pairs as sub-branches
    for i, branch in enumerate(branches):
        lines.append(f"    {branch}")

    return "\n".join(lines)


def generate_timeline(description: str) -> str:
    """Generate a Mermaid timeline diagram."""
    tokens = tokenize_description(description)

    lines = ["timeline"]
    lines.append(f"  title {description}")

    # Distribute tokens as events across years
    base_year = 2020
    events_per_section = max(1, len(tokens) // 4)

    for i, token in enumerate(tokens):
        year = base_year + (i // max(1, events_per_section))
        lines.append(f"  {year} : {token}")

    return "\n".join(lines)


GENERATORS = {
    "flowchart": generate_flowchart,
    "sequence": generate_sequence,
    "er": generate_er,
    "mindmap": generate_mindmap,
    "timeline": generate_timeline,
}


def main():
    parser = argparse.ArgumentParser(
        description="Generate Mermaid diagrams for scientific workflows and networks"
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=list(GENERATORS.keys()),
        help="Diagram type to generate",
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Description of the content to diagram",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save the .mmd file",
    )
    args = parser.parse_args()

    try:
        generator = GENERATORS[args.type]
        mermaid_code = generator(args.description)
    except Exception as e:
        result = {"error": str(e), "type": args.type, "description": args.description}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    if args.output:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
            with open(args.output, "w") as f:
                f.write(mermaid_code)
        except Exception as e:
            result = {
                "error": f"Failed to save file: {e}",
                "type": args.type,
                "mermaid_code": mermaid_code,
                "description": args.description,
            }
            print(json.dumps(result, indent=2))
            sys.exit(1)

    result = {
        "type": args.type,
        "mermaid_code": mermaid_code,
        "description": args.description,
    }
    if args.output:
        result["saved_to"] = args.output

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
