#!/usr/bin/env python3
"""
Delete Infinite comments on a given post whose content starts with a prefix,
e.g. remove a specific PlotAgent comment from an investigation thread.
"""

import argparse
from pathlib import Path

from skills.infinite.scripts.infinite_client import InfiniteClient


def _get_infinite_client(agent_name: str) -> InfiniteClient:
    home = Path.home()
    cfg = home / ".scienceclaw" / "profiles" / agent_name / "infinite_config.json"
    if not cfg.exists():
        cfg = home / ".scienceclaw" / "infinite_config.json"
    return InfiniteClient(config_file=str(cfg))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete comments on an Infinite post whose content starts with a given prefix."
    )
    parser.add_argument(
        "--post-id",
        required=True,
        help="Infinite post ID (UUID) to operate on.",
    )
    parser.add_argument(
        "--prefix",
        required=True,
        help="Comment content prefix to match (e.g. '[PlotAgent] — investigation-plotter').",
    )
    parser.add_argument(
        "--agent-name",
        default="PlotAgent",
        help="Agent name whose credentials to use (must own the comments to delete).",
    )

    args = parser.parse_args()
    post_id = args.post_id.strip()
    prefix = args.prefix.strip()
    agent_name = args.agent_name.strip() or "PlotAgent"

    client = _get_infinite_client(agent_name)
    if not client.jwt_token:
        raise SystemExit(f"{agent_name} is not authenticated for Infinite (no JWT token).")

    raw = client.get_comments(post_id)
    if isinstance(raw, dict) and "error" in raw:
        raise SystemExit(f"Failed to fetch comments: {raw['error']}")

    # API typically returns a dict with a "comments" array, but fall back to treating
    # the whole response as the list if already an array-like.
    if isinstance(raw, dict):
        comments = raw.get("comments") or raw.get("data") or []
    else:
        comments = raw

    to_delete = []
    for c in comments:
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        content = (c.get("content") or "").lstrip()
        if cid and content.startswith(prefix):
            to_delete.append(cid)

    if not to_delete:
        print(f"No comments starting with '{prefix}' found on post {post_id}.")
        return

    print(f"Found {len(to_delete)} matching comment(s). Deleting…")
    for cid in to_delete:
        resp = client.delete_comment(cid)
        if "error" in resp:
            print(f"  ⚠  Failed to delete {cid}: {resp['error']}")
        else:
            print(f"  ✓ Deleted comment {cid}")


if __name__ == "__main__":
    main()

