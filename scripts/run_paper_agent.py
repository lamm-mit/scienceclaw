#!/usr/bin/env python3
"""
CLI runner for PaperAgent — generates arXiv-style LaTeX reports and figures
from ScienceClaw investigation artifacts.

Usage:
    python3 scripts/run_paper_agent.py \\
        --topic "climate-driven vector-borne disease emergence" \\
        --case-dir ~/LAMM/scienceclaw_cai/cs6-climate \\
        --agents ClimateSignalExtractor NicheMapper SurveillanceAnalyst \\
        --post

Outputs (in case-dir/):
    synthesis_report.tex    arXiv-style LaTeX paper
    synthesis_report.pdf    compiled PDF (if pdflatex installed)
    refs.bib                auto-generated BibTeX bibliography
    synthesis_post.md       markdown mirror for Infinite posting
    sci1.png … sciN.png     figures from artifact payloads
"""

import argparse
import sys
from pathlib import Path

# Resolve scienceclaw root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from autonomous.paper_agent import PaperAgent, setup_paper_agent_profile


def main():
    parser = argparse.ArgumentParser(
        description="Generate arXiv-style paper + figures from ScienceClaw artifacts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--topic", required=True, help="Research topic / investigation title")
    parser.add_argument(
        "--case-dir",
        required=True,
        type=Path,
        help="Directory where outputs will be written (can be an existing case study dir)",
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        default=None,
        metavar="AGENT",
        help="Agent names whose artifacts to include (default: all agents in global index)",
    )
    parser.add_argument(
        "--agent-name",
        default="PaperAgent",
        help="Name of the paper-writing agent (default: PaperAgent)",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Restrict artifact collection to a specific session ID",
    )
    parser.add_argument(
        "--investigation-id",
        default=None,
        help="Restrict artifact collection to a specific investigation ID",
    )
    parser.add_argument(
        "--post",
        action="store_true",
        default=False,
        help="Post synthesis_post.md to Infinite after generation",
    )
    parser.add_argument(
        "--setup-profile",
        action="store_true",
        default=False,
        help="Create/overwrite the PaperAgent profile in ~/.scienceclaw/profiles/",
    )
    args = parser.parse_args()

    case_dir = args.case_dir.expanduser().resolve()
    case_dir.mkdir(parents=True, exist_ok=True)

    if args.setup_profile:
        profile_path = setup_paper_agent_profile()
        print(f"Profile written: {profile_path}")

    agent = PaperAgent(agent_name=args.agent_name)
    result = agent.run(
        topic=args.topic,
        case_dir=case_dir,
        agent_names=args.agents,
        session_id=args.session_id,
        investigation_id=args.investigation_id,
        post_to_infinite=args.post,
    )

    if result.get("success"):
        print("\n=== PaperAgent complete ===")
        for key, val in result.items():
            if key != "success":
                print(f"  {key}: {val}")
    else:
        print(f"\nPaperAgent failed: {result.get('error', 'unknown error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
