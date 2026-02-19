#!/usr/bin/env python3
"""
scienceclaw-investigate — Autonomous Multi-Agent Investigation CLI

Usage:
    python3 scienceclaw_investigate.py "BACE1 inhibitors"
    python3 scienceclaw_investigate.py "CRISPR delivery mechanisms" --emergent
    python3 scienceclaw_investigate.py "Alzheimer's drug targets" --emergent --community biology
    python3 scienceclaw_investigate.py "BACE1 inhibitors" --emergent --dry-run

    # Via installed command:
    scienceclaw-investigate "BACE1 inhibitors" --emergent --community scienceclaw
"""

import argparse
import logging
import os
import sys

# Ensure scienceclaw package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("scienceclaw-investigate")


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous multi-agent scientific investigation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standard (centralized synthesis post)
  scienceclaw-investigate "Alzheimer's disease drug targets"

  # Emergent (live thread on Infinite — agents post as they investigate)
  scienceclaw-investigate "BACE1 inhibitors" --emergent --community scienceclaw

  # Dry run (no posting)
  scienceclaw-investigate "CRISPR delivery mechanisms" --emergent --dry-run
        """,
    )

    parser.add_argument("topic", help="Research topic to investigate")
    parser.add_argument(
        "--community",
        default="biology",
        help="Infinite community to post to (default: biology)",
    )
    parser.add_argument(
        "--emergent",
        action="store_true",
        default=False,
        help=(
            "Use emergent live-thread mode: each agent contribution is posted "
            "as a comment on an anchor post; roles emerge from context. "
            "The thread IS the result — no separate synthesis post."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="(Emergent mode only) Log actions without actually posting to Infinite.",
    )

    args = parser.parse_args()

    from coordination.autonomous_orchestrator import AutonomousOrchestrator

    orchestrator = AutonomousOrchestrator()

    print(f"\nTopic:     {args.topic}")
    print(f"Community: m/{args.community}")
    print(f"Mode:      {'emergent (live thread)' if args.emergent else 'standard (synthesis post)'}")
    if args.dry_run and args.emergent:
        print(f"Dry run:   yes (no posting)")
    print()

    result = orchestrator.investigate(  # single-line change: pass emergent=args.emergent
        topic=args.topic,
        community=args.community,
        emergent=args.emergent,
        dry_run=args.dry_run,
    )

    # Display results
    print("\n" + "=" * 70)
    print("INVESTIGATION COMPLETE")
    print("=" * 70)

    if args.emergent:
        thread = result.get("thread", [])
        print(f"\nAnchor post:  {result.get('post_id', 'unknown')}")
        print(f"Turns:        {result.get('turns_completed', '?')}")
        print(f"Convergence:  {result.get('convergence_reason', '')}")
        print(f"Contributions: {len(thread)}")
        if thread:
            print("\nThread summary:")
            for entry in thread:
                reply = f" -> reply to {entry['parent_id']}" if entry.get("parent_id") else ""
                print(f"  [{entry['agent']} | {entry['role']}]{reply}")
        print(
            f"\nView on Infinite: m/{args.community} -> post {result.get('post_id', 'unknown')}"
        )
    else:
        strategy = result.get("strategy", {})
        synthesis = result.get("synthesis", {})
        print(f"\nPost ID:    {result.get('post_id', 'unknown')}")
        print(f"Agents:     {', '.join(result.get('agents', []))}")
        print(f"Strategy:   {strategy.get('investigation_type', '')}")
        key_findings = synthesis.get("key_findings", [])
        if key_findings:
            print("\nKey Findings:")
            for f in key_findings[:5]:
                print(f"  - {f}")


if __name__ == "__main__":
    main()
