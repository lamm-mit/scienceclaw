#!/usr/bin/env python3
"""
Emergent Session — Live Discussion Thread on Infinite

Manages the live discussion thread that IS the investigation result.
Each agent contribution is posted as a labeled comment on an anchor post,
making the multi-agent process transparent and observable in real time.

Roles are NOT pre-assigned. The LLM is given the current thread and asked
what role is missing — then names that role freely based on context.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EmergentSession:
    """
    Manages the live Infinite discussion thread for an emergent investigation.

    The anchor post is created first; every agent contribution becomes a
    labeled comment (or a reply to another comment). The thread IS the output.
    """

    def __init__(self, client, dry_run: bool = False):
        """
        Args:
            client: Authenticated InfiniteClient instance.
            dry_run: If True, log actions without posting to Infinite.
        """
        self.client = client
        self.dry_run = dry_run
        self.post_id: Optional[str] = None
        self.thread: List[Dict[str, Any]] = []
        self._comment_counter = 0  # for dry-run IDs

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def create_anchor_post(self, topic: str, community: str) -> str:
        """
        Create the investigation anchor post.

        The anchor is a stub that frames the topic; the real content
        accumulates in the comment thread below it.

        Returns:
            post_id string
        """
        title = f"Live Investigation: {topic}"
        content = (
            f"**Emergent multi-agent investigation in progress.**\n\n"
            f"Topic: {topic}\n\n"
            f"Agents will contribute findings, challenges, and synthesis as comments "
            f"below. Roles emerge from context — watch the thread grow.\n\n"
            f"*This post is updated live as agents investigate.*"
        )

        if self.dry_run:
            post_id = f"dry-run-post-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            logger.info(f"[dry-run] Would create anchor post: '{title}' in m/{community}")
            print(f"\n  [DRY RUN] Anchor post: '{title}' -> {post_id}")
        else:
            try:
                result = self.client.create_post(
                    community=community,
                    title=title,
                    content=content,
                )
                post_id = (
                    result.get("post", {}).get("id")
                    or result.get("id")
                    or f"unknown-{datetime.now().strftime('%H%M%S')}"
                )
            except Exception as e:
                logger.error(f"Failed to create anchor post: {e}")
                post_id = f"error-{datetime.now().strftime('%H%M%S')}"

        self.post_id = post_id
        logger.info(f"Anchor post created: {post_id}")
        return post_id

    def post_contribution(
        self,
        agent_name: str,
        role: str,
        content: str,
        parent_id: Optional[str] = None,
        client=None,
    ) -> str:
        """
        Post an agent contribution as a labeled comment on the anchor post.

        The comment is formatted as:
            [AgentName | Role]
            <content>

        Args:
            agent_name: Name of the contributing agent.
            role: Role label (e.g. "Investigator", "Critic", "Synthesizer").
            content: The contribution text.
            parent_id: If replying to a specific comment, pass that comment's ID.

        Returns:
            comment_id string
        """
        if not self.post_id:
            raise RuntimeError("create_anchor_post() must be called before post_contribution()")

        labeled_content = f"[{agent_name} | {role}]\n{content}"

        if self.dry_run:
            self._comment_counter += 1
            comment_id = f"dry-run-comment-{self._comment_counter}"
            reply_info = f" (reply to {parent_id})" if parent_id else ""
            logger.info(
                f"[dry-run] Would post comment{reply_info}: [{agent_name} | {role}] -> {comment_id}"
            )
            print(f"\n  [DRY RUN] [{agent_name} | {role}]{reply_info}")
            print(f"  {content[:200]}{'...' if len(content) > 200 else ''}")
        else:
            active_client = client or self.client
            try:
                result = active_client.create_comment(
                    post_id=self.post_id,
                    content=labeled_content,
                    parent_id=parent_id,
                )
                comment_id = (
                    result.get("comment", {}).get("id")
                    or result.get("id")
                    or f"unknown-{datetime.now().strftime('%H%M%S')}"
                )
            except Exception as e:
                logger.error(f"Failed to post contribution: {e}")
                self._comment_counter += 1
                comment_id = f"error-{self._comment_counter}"

        # Record in local thread state
        entry = {
            "agent": agent_name,
            "role": role,
            "content": content,
            "comment_id": comment_id,
            "parent_id": parent_id,
            "timestamp": datetime.now().isoformat(),
        }
        self.thread.append(entry)
        logger.info(f"Contribution recorded: [{agent_name} | {role}] -> {comment_id}")
        return comment_id

    def read_thread(self) -> List[Dict[str, Any]]:
        """
        Return the current thread state (local copy, not re-fetched from API).

        Returns:
            List of contribution dicts with keys:
            agent, role, content, comment_id, parent_id, timestamp
        """
        return list(self.thread)

    def suggest_next_role(
        self,
        agent_name: str,
        profile: Dict[str, Any],
        thread: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """
        Ask the LLM what role this agent should play next given the thread.

        The LLM is given full thread context and must:
        1. Identify what angle is missing or under-explored.
        2. Name a role for that angle (no enumerated choices — free-form).
        3. Return "none_needed" if the thread is converged.

        Args:
            agent_name: The agent about to act.
            profile: Agent's domain, skills, personality dict.
            thread: Current thread entries.

        Returns:
            Dict with keys: role, reasoning, focus
            role="none_needed" if no contribution is needed.
        """
        thread_summary = self._format_thread_for_prompt(thread)
        agent_domain = profile.get("domain", "mixed")
        agent_skills = profile.get("skills", [])
        agent_personality = profile.get("personality", "")

        system_prompt = (
            "You are advising a scientific research agent on what role to play "
            "in an ongoing multi-agent investigation thread.\n\n"
            "Rules:\n"
            "- Examine the thread and identify the MOST IMPORTANT gap, challenge, "
            "or unresolved angle that would genuinely advance the investigation.\n"
            "- Name a SPECIFIC role for addressing it (e.g. 'BBB-Penetration Critic', "
            "'Structural Validator', 'Mechanism Synthesizer', 'Clinical Evidence Reviewer'). "
            "Be precise — generic labels like 'investigator' are only acceptable if truly "
            "no investigation has occurred yet.\n"
            "- The agent's contribution MUST address something left unresolved. "
            "State explicitly what was left unresolved and how this role addresses it.\n"
            "- If the thread is converged (last 2+ contributions only confirm earlier "
            "findings without adding new angles), return role='none_needed'.\n"
            "- If the agent's domain/skills are not suited to the gap, return role='none_needed'.\n\n"
            "Output JSON only:\n"
            "{\n"
            '  "role": "Role name (or none_needed)",\n'
            '  "reasoning": "What the previous contributions left unresolved and why this role fills that gap",\n'
            '  "focus": "Specific search query or angle for the investigation (5-8 words max)"\n'
            "}"
        )

        user_prompt = (
            f"Agent: {agent_name}\n"
            f"Domain: {agent_domain}\n"
            f"Skills: {', '.join(agent_skills)}\n"
            f"Personality: {agent_personality}\n\n"
            f"Current thread ({len(thread)} contributions):\n"
            f"{thread_summary}\n\n"
            "What role should this agent play next? If the thread is converged or "
            "this agent's skills don't fill a gap, return none_needed."
        )

        try:
            from core.llm_client import get_llm_client
            llm = get_llm_client(agent_name=agent_name)
            response = llm.call(
                prompt=system_prompt + "\n\n" + user_prompt,
                max_tokens=300,
                session_id=f"emergent_role_{agent_name}",
            )
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "role": result.get("role", "none_needed"),
                    "reasoning": result.get("reasoning", ""),
                    "focus": result.get("focus", ""),
                }
        except Exception as e:
            logger.warning(f"LLM role suggestion failed for {agent_name}: {e}")

        # Fallback: if thread is empty, suggest investigator; else none_needed
        if not thread:
            return {
                "role": "Investigator",
                "reasoning": "Thread is empty; initial literature investigation needed.",
                "focus": "",
            }
        return {
            "role": "none_needed",
            "reasoning": "LLM unavailable; skipping to avoid redundant contribution.",
            "focus": "",
        }

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _format_thread_for_prompt(self, thread: List[Dict[str, Any]]) -> str:
        """Format thread entries as readable text for LLM prompts."""
        if not thread:
            return "(empty — no contributions yet)"
        lines = []
        for i, entry in enumerate(thread, 1):
            reply = f" [reply to {entry['parent_id']}]" if entry.get("parent_id") else ""
            lines.append(
                f"{i}. [{entry['agent']} | {entry['role']}]{reply}\n"
                f"   {entry['content'][:300]}{'...' if len(entry['content']) > 300 else ''}"
            )
        return "\n\n".join(lines)
