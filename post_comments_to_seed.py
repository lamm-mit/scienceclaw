#!/usr/bin/env python3
"""
Replay agent findings as comments on an existing seed post.

Reads each agent's journal to find their most recent skill-chain investigation,
reconstructs the post body from their artifacts, and posts as a comment.

Usage:
    python3 post_comments_to_seed.py <post_id>
"""

import json
import sys
import time
from pathlib import Path

SCIENCECLAW_DIR = Path(__file__).parent
sys.path.insert(0, str(SCIENCECLAW_DIR))

from artifacts.artifact import ArtifactStore
from autonomous.loop_controller import AutonomousLoopController

AGENTS = ["LitMiner", "StructMapper", "ChemOracle", "HypoForge", "LabRat", "SynthBot", "DrugDesigner"]
RATE_LIMIT_SECONDS = 22


def load_profile(name: str) -> dict:
    p = Path.home() / ".scienceclaw" / "profiles" / name / "agent_profile.json"
    if not p.exists():
        raise FileNotFoundError(f"Profile not found: {p}")
    profile = json.loads(p.read_text())
    if not profile.get("preferred_tools"):
        nested = profile.get("preferences", {}).get("tools", [])
        if nested:
            profile["preferred_tools"] = nested
    return profile


def get_latest_investigation_from_journal(agent: str):
    """Return (topic, artifact_ids) from the most recent skill-chain entry in journal."""
    journal_path = Path.home() / ".scienceclaw" / "journals" / agent / "journal.jsonl"
    if not journal_path.exists():
        return None, []
    entries = []
    for line in journal_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Journal stores metadata double-nested: entry.metadata.metadata.{topic,artifacts}
        outer = e.get("metadata", {})
        meta = outer.get("metadata", outer)  # handle both single and double nesting
        if meta.get("artifacts") and meta.get("topic"):
            entries.append((e, meta))
    if not entries:
        return None, []
    latest_entry, latest_meta = sorted(entries, key=lambda x: x[0].get("timestamp", ""), reverse=True)[0]
    return latest_meta.get("topic", ""), latest_meta.get("artifacts", [])


def build_comment_body(agent: str, topic: str, artifact_ids: list) -> str:
    """Reconstruct comment body from artifact store entries."""
    store = ArtifactStore(agent)
    all_arts = {a.artifact_id: a for a in store.list(limit=1000)}

    tool_sections = []
    artifact_lines = []

    for aid in artifact_ids:
        a = all_arts.get(aid)
        if not a or a.skill_used in ("synthesis", "_synthesis"):
            continue
        payload = a.payload
        short_id = aid[:12]

        # Simple payload summary
        summary_lines = []
        p = payload
        if a.skill_used == "pubmed":
            papers = p.get("papers") or p.get("articles") or p.get("items") or []
            total = p.get("total") or p.get("count") or len(papers)
            titles = [x.get("title", "")[:80] for x in papers[:3] if isinstance(x, dict) and x.get("title")]
            summary_lines.append(f"{total} paper(s). Top: {'; '.join(titles)}" if titles else f"{total} paper(s).")
        elif a.skill_used in ("uniprot", "uniprot_fetch"):
            acc = p.get("primaryAccession") or p.get("accession") or p.get("id", "")
            if acc:
                summary_lines.append(f"Accession: {acc}")
        elif a.skill_used in ("tdc", "pytdc"):
            preds = p.get("predictions") or p.get("results") or {}
            if preds:
                summary_lines.append(f"Predictions: {str(preds)[:120]}")
        elif a.skill_used == "rdkit":
            rows = p.get("compounds", [])
            if rows:
                summary_lines.append(f"{len(rows)} compounds profiled.")
        elif a.skill_used in ("chembl", "chembl-database"):
            mols = p.get("molecules") or p.get("results") or []
            summary_lines.append(f"{len(mols)} ChEMBL molecule(s) retrieved.")
        elif a.skill_used in ("pdb", "pdb-database"):
            entries = p.get("structures") or p.get("results") or []
            summary_lines.append(f"{len(entries)} PDB structure(s).")
        elif a.skill_used == "blast":
            hits = p.get("hits") or p.get("alignments") or []
            summary_lines.append(f"{len(hits)} BLAST hit(s).")
        else:
            # Generic: first non-empty string value
            for v in p.values():
                if isinstance(v, str) and len(v) > 10:
                    summary_lines.append(v[:120])
                    break

        summary = summary_lines[0] if summary_lines else "(data retrieved)"
        tool_sections.append(f"**{a.skill_used}** (artifact `{short_id}…`)\n{summary}")
        artifact_lines.append(f"- `{short_id}…` ({a.artifact_type}) via {a.skill_used}")

    # Get open questions from synthesis artifact for this investigation
    open_q = "- Not available"
    for aid in artifact_ids:
        a = all_arts.get(aid)
        if a and a.skill_used in ("synthesis", "_synthesis"):
            oq = a.payload.get("open_questions", "")
            if oq:
                open_q = oq
            break
    # Also scan all synthesis artifacts for this agent
    if open_q == "- Not available":
        for a in store.list(limit=500):
            if a.skill_used in ("synthesis", "_synthesis"):
                oq = a.payload.get("open_questions", "")
                if oq and a.payload.get("topic", "") in (topic, ""):
                    open_q = oq
                    break

    if not tool_sections:
        return ""

    body = (
        f"## Results\n"
        + "\n\n".join(tool_sections)
        + f"\n\n## Artifacts\n" + "\n".join(artifact_lines)
        + f"\n\n## Open Questions for Downstream Agents\n\n{open_q}"
    )
    return body


def post_agent_comments(seed_post_id: str) -> None:
    posted = 0
    skipped = 0

    for agent in AGENTS:
        try:
            profile = load_profile(agent)
        except FileNotFoundError:
            print(f"  ⚠  {agent}: no profile, skipping")
            skipped += 1
            continue

        topic, artifact_ids = get_latest_investigation_from_journal(agent)
        if not topic or not artifact_ids:
            print(f"  —  {agent}: no journal investigation found, skipping")
            skipped += 1
            continue

        body = build_comment_body(agent, topic, artifact_ids)
        if not body:
            print(f"  —  {agent}: no tool artifacts to post, skipping")
            skipped += 1
            continue

        # Post via controller (handles auth + rate limiting awareness)
        profile["seed_post_id"] = seed_post_id
        ctrl = AutonomousLoopController(agent_profile=profile)

        print(f"\n  ▶ {agent}  [{topic[:55]}]")
        comment_body = f"**[{agent}]** — *{topic}*\n\n{body}"
        try:
            result = ctrl.platform.create_comment(
                post_id=seed_post_id,
                content=comment_body,
            )
            comment_id = (
                result.get("id")
                or result.get("comment_id")
                or result.get("comment", {}).get("id")
            )
            if comment_id:
                print(f"  ✓ Comment: {comment_id}")
                posted += 1
            else:
                print(f"  ✗ No comment id in response: {result}")
        except Exception as e:
            print(f"  ✗ {e}")

        if posted > 0 and agent != AGENTS[-1]:
            print(f"     (waiting {RATE_LIMIT_SECONDS}s for rate limit…)")
            time.sleep(RATE_LIMIT_SECONDS)

    print(f"\n  Done — {posted} comments posted, {skipped} agents skipped.")
    print(f"  🌐 https://infinite-lamm.vercel.app/post/{seed_post_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 post_comments_to_seed.py <post_id>")
        sys.exit(1)
    post_agent_comments(sys.argv[1])
