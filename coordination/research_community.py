"""
Transparent Research Community — Multi-Agent Forum Simulation

Agents behave like participants in an online research community:
- Post independently (no shared memory in R1)
- Comment on each other's posts (R2)
- Reply to comments received (R3)
- Vote with justifications (R4)
- Revise or maintain stances (R5)
- Optional meta-post linking all posts (R6)

Roles (self-assembled per topic via LLM):
  Proposer   — bold initial claim, deep investigation
  Skeptic    — challenges methodology / evidence gaps
  Replicator — independently verifies Proposer using different tools
  Integrator — connects findings to broader context
  Arbiter    — votes + mediates, does NOT post in R1

Usage:
    community = ResearchCommunity()
    result = community.simulate("ibuprofen COX-2 selectivity", dry_run=True)
"""

import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------

ROLE_PERSONAS = {
    "proposer": (
        "You make bold, specific, mechanistic claims based on your investigation. "
        "You commit to a clear stance with quantitative evidence and are open to "
        "revising only when the data compels you."
    ),
    "skeptic": (
        "You challenge methodology, probe evidence gaps, and scrutinize statistical "
        "claims. You are constructive but relentless in demanding rigour. You investigate "
        "the same topic from the angle most likely to reveal weaknesses."
    ),
    "replicator": (
        "You independently verify the Proposer's central claim using a different set "
        "of computational tools. You report convergent or divergent findings objectively."
    ),
    "integrator": (
        "You connect individual findings to the broader scientific landscape—related "
        "pathways, clinical implications, cross-species comparisons. You rarely disagree "
        "outright but always add context."
    ),
    "arbiter": (
        "You are a neutral mediator. You do not post original research in Round 1. "
        "You read all posts carefully and vote based on evidence quality, not popularity. "
        "Your final verdict in R5 is the most balanced assessment in the forum."
    ),
}

ROLE_TOPIC_FOCUS = {
    "proposer": "direct mechanism and primary evidence for",
    "skeptic": "limitations, confounders, and contradictory evidence for",
    "replicator": "independent computational verification of",
    "integrator": "broader biological and clinical context of",
    "arbiter": None,  # Arbiter does not investigate
}

# Default role set (LLM may override)
DEFAULT_ROLES = ["proposer", "skeptic", "replicator", "integrator"]
FULL_ROLES = ["proposer", "skeptic", "replicator", "integrator", "arbiter"]


# ---------------------------------------------------------------------------
# ResearchCommunity
# ---------------------------------------------------------------------------

class ResearchCommunity:
    """
    Simulates a transparent multi-agent online research community.

    Each agent investigates independently, then interacts in structured rounds.
    Full console transparency: every action is printed as it happens.
    """

    def __init__(self):
        self.scienceclaw_dir = Path(__file__).parent.parent

    # ------------------------------------------------------------------ #
    # Public entry point                                                   #
    # ------------------------------------------------------------------ #

    def simulate(
        self,
        topic: str,
        community: str = "biology",
        num_agents: int = 4,
        dry_run: bool = False,
        include_meta_post: bool = False,
    ) -> Dict[str, Any]:
        """
        Run a full research community simulation.

        Args:
            topic:            Research topic
            community:        Infinite community to post to
            num_agents:       Number of agents (2–5). Arbiter added automatically if ≥4.
            dry_run:          If True, no Infinite API calls are made
            include_meta_post: If True, run optional R6 meta-post

        Returns:
            Full simulation state dict
        """
        num_agents = max(2, min(5, num_agents))

        print(f"\n{'='*70}")
        print(f"=== RESEARCH COMMUNITY: {topic.upper()} ===")
        print(f"{'='*70}")
        print(f"Community: {community} | Agents: {num_agents} | Dry-run: {dry_run}")

        # --- Spawn agents ---
        agents = self._spawn_agents(topic, num_agents)
        agent_names = " | ".join(a["name"] for a in agents)
        print(f"Agents: {agent_names}\n")

        # Shared state
        posts: List[Dict] = []      # {post_id, agent_name, role, title, content, upvotes, downvotes}
        comments: List[Dict] = []   # {comment_id, post_id, parent_id, agent_name, role, content, upvotes, downvotes}
        votes: List[Dict] = []      # {voter, role, target_type, target_id, value, justification}
        stances: Dict[str, Dict] = {}

        # Infinite client (shared — each agent uses its own auth in real run)
        client = None
        if not dry_run:
            try:
                import sys
                sys.path.insert(0, str(self.scienceclaw_dir))
                from skills.infinite.scripts.infinite_client import InfiniteClient
                client = InfiniteClient()
            except Exception as e:
                logger.warning(f"InfiniteClient init failed: {e}. Falling back to dry_run.")
                dry_run = True

        # ---- ROUND 1 ----
        posts = self._run_round1(topic, agents, community, client, dry_run)

        # ---- ROUND 2 ----
        self._run_round2(posts, agents, comments, client, dry_run)

        # ---- ROUND 3 ----
        self._run_round3(posts, agents, comments, client, dry_run)

        # ---- ROUND 4 ----
        self._run_round4(posts, agents, comments, votes, client, dry_run)

        # ---- ROUND 5 ----
        self._run_round5(posts, agents, comments, stances, client, dry_run)

        # ---- ROUND 6 (optional) ----
        meta_post_id = None
        if include_meta_post:
            meta_post_id = self._run_round6(topic, posts, agents, community, client, dry_run)

        # ---- Final board ----
        self._print_board(posts, comments, votes)
        self._print_stance_table(stances)

        return {
            "topic": topic,
            "community": community,
            "dry_run": dry_run,
            "agents": [{"name": a["name"], "role": a["role"]} for a in agents],
            "posts": posts,
            "comments": comments,
            "votes": votes,
            "stances": stances,
            "meta_post_id": meta_post_id,
        }

    # ------------------------------------------------------------------ #
    # Agent spawning                                                       #
    # ------------------------------------------------------------------ #

    def _spawn_agents(self, topic: str, num_agents: int) -> List[Dict]:
        """Create agents with LLM-selected roles (fallback: default order)."""
        roles = self._select_roles(topic, num_agents)
        agents = []
        for role in roles:
            short_id = uuid.uuid4().hex[:4]
            name = f"{role.capitalize()}-{short_id}"
            focused_topic = self._derive_focused_topic(topic, role)
            agents.append({
                "name": name,
                "role": role,
                "persona": ROLE_PERSONAS[role],
                "focused_topic": focused_topic,
                "post_id": None,
                "investigation": None,
            })
        return agents

    def _select_roles(self, topic: str, num_agents: int) -> List[str]:
        """Use LLM to pick roles appropriate for the topic."""
        if num_agents < 2:
            return ["proposer", "skeptic"]

        candidate_roles = FULL_ROLES if num_agents >= 4 else DEFAULT_ROLES
        target_roles = candidate_roles[:num_agents]

        try:
            from core.llm_client import get_llm_client
            client = get_llm_client(agent_name="RolePicker")
            prompt = (
                f"Topic: \"{topic}\"\n\n"
                f"Available roles: {', '.join(FULL_ROLES)}\n"
                f"Select exactly {num_agents} roles most suited to this topic. "
                f"Rules:\n"
                f"- Always include 'proposer'\n"
                f"- Always include 'skeptic' if num_agents >= 2\n"
                f"- Include 'arbiter' only if num_agents >= 4\n"
                f"Output ONLY a JSON array of role strings, e.g.: [\"proposer\", \"skeptic\"]"
            )
            response = client.call(prompt=prompt, max_tokens=60, session_id="role_picker")
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                roles = json.loads(match.group())
                # Validate
                roles = [r for r in roles if r in FULL_ROLES]
                if len(roles) == num_agents and "proposer" in roles:
                    return roles
        except Exception:
            pass

        return target_roles

    def _derive_focused_topic(self, main_topic: str, role: str) -> Optional[str]:
        """Derive a role-specific investigation sub-topic via LLM."""
        if role == "arbiter":
            return None
        focus_hint = ROLE_TOPIC_FOCUS.get(role, "investigating")
        try:
            from core.llm_client import get_llm_client
            client = get_llm_client(agent_name=f"{role.capitalize()}-focus")
            prompt = (
                f"Main research topic: \"{main_topic}\"\n"
                f"Agent role: {role} — focus: {focus_hint} this topic\n\n"
                f"Write a single focused search query (3–7 words) for this role. "
                f"Output ONLY the query, nothing else."
            )
            response = client.call(prompt=prompt, max_tokens=30, session_id=f"focus_{role}")
            q = response.strip().strip('"').strip("'")
            if q and 2 <= len(q.split()) <= 10 and '.' not in q:
                return q
        except Exception:
            pass
        return f"{focus_hint} {main_topic}"

    # ------------------------------------------------------------------ #
    # Round 1 — Discovery                                                  #
    # ------------------------------------------------------------------ #

    def _run_round1(
        self,
        topic: str,
        agents: List[Dict],
        community: str,
        client,
        dry_run: bool,
    ) -> List[Dict]:
        print(f"\n{'─'*70}")
        print("--- ROUND 1: DISCOVERY ---")
        print(f"{'─'*70}")

        import sys
        sys.path.insert(0, str(self.scienceclaw_dir))
        from autonomous.deep_investigation import run_deep_investigation

        posts = []

        for agent in agents:
            if agent["role"] == "arbiter":
                print(f"[R1] {agent['name']} [ARBITER] — observing, not posting")
                continue

            focused_topic = agent["focused_topic"] or topic
            print(f"[R1] {agent['name']} ({agent['role']}) investigating: \"{focused_topic}\"...")

            try:
                inv_result = run_deep_investigation(
                    agent_name=agent["name"],
                    topic=focused_topic,
                    community=community,
                    agent_profile={
                        "name": agent["name"],
                        "role": agent["role"],
                        "persona": agent["persona"],
                    },
                )
                agent["investigation"] = inv_result
            except Exception as e:
                logger.error(f"Deep investigation failed for {agent['name']}: {e}")
                inv_result = {
                    "title": f"{topic} — {agent['role']} analysis",
                    "hypothesis": f"Investigation of {focused_topic}",
                    "findings": f"Analysis of {focused_topic} from {agent['role']} perspective.",
                    "method": "Multi-tool computational investigation",
                    "investigation_results": {"tools_used": [], "papers": [], "proteins": [], "compounds": []},
                }
                agent["investigation"] = inv_result

            title = inv_result.get("title", f"{topic} — {agent['role']} perspective")
            content = self._build_post_content(agent, inv_result)

            # Initial stance = first sentence of hypothesis
            hypothesis = inv_result.get("hypothesis", "")
            initial_stance = (hypothesis[:200] + "...") if len(hypothesis) > 200 else hypothesis
            if not initial_stance:
                initial_stance = title

            post_id = None
            if not dry_run and client:
                try:
                    result = client.create_post(
                        community=community,
                        title=title,
                        content=content,
                        data_sources=inv_result.get("investigation_results", {}).get("tools_used", []),
                    )
                    post_id = (result.get("post", {}) or {}).get("id") or result.get("id")
                except Exception as e:
                    logger.error(f"Post failed for {agent['name']}: {e}")

            if post_id is None:
                post_id = f"dry_{agent['name']}_{uuid.uuid4().hex[:6]}"

            agent["post_id"] = post_id

            post_record = {
                "post_id": post_id,
                "agent_name": agent["name"],
                "role": agent["role"],
                "title": title,
                "content": content,
                "initial_stance": initial_stance,
                "upvotes": 0,
                "downvotes": 0,
            }
            posts.append(post_record)

            print(f"  → Posted: {post_id} — \"{title}\"")

        return posts

    def _build_post_content(self, agent: Dict, inv: Dict) -> str:
        """Format investigation result as a post body."""
        parts = []
        hypothesis = inv.get("hypothesis", "")
        method = inv.get("method", "Multi-tool computational investigation")
        findings = inv.get("findings", "")

        if hypothesis:
            parts.append(f"**Hypothesis:** {hypothesis}")
        if method:
            parts.append(f"**Method:** {method}")
        if findings:
            parts.append(f"**Findings:** {findings}")

        ir = inv.get("investigation_results", {})
        tools_used = ir.get("tools_used", [])
        if tools_used:
            parts.append(f"**Tools:** {', '.join(tools_used)}")

        parts.append(f"\n*Role: {agent['role'].capitalize()} | Agent: {agent['name']}*")
        return "\n\n".join(parts)

    # ------------------------------------------------------------------ #
    # Round 2 — Peer Review                                               #
    # ------------------------------------------------------------------ #

    def _run_round2(
        self,
        posts: List[Dict],
        agents: List[Dict],
        comments: List[Dict],
        client,
        dry_run: bool,
    ) -> None:
        print(f"\n{'─'*70}")
        print("--- ROUND 2: PEER REVIEW ---")
        print(f"{'─'*70}")

        for agent in agents:
            # Each agent comments on up to 2 other posts
            others = [p for p in posts if p["agent_name"] != agent["name"]][:2]
            for target_post in others:
                action = self._choose_action(agent, target_post)
                content = self._generate_comment(agent, target_post, action, round_num=2)

                comment_id = None
                if not dry_run and client:
                    try:
                        resp = client.create_comment(
                            post_id=target_post["post_id"],
                            content=content,
                        )
                        comment_id = (resp.get("comment", {}) or {}).get("id") or resp.get("id")
                    except Exception as e:
                        logger.error(f"Comment failed: {e}")

                if comment_id is None:
                    comment_id = f"dry_comment_{uuid.uuid4().hex[:6]}"

                record = {
                    "comment_id": comment_id,
                    "post_id": target_post["post_id"],
                    "parent_id": None,
                    "agent_name": agent["name"],
                    "role": agent["role"],
                    "content": content,
                    "upvotes": 0,
                    "downvotes": 0,
                    "round": 2,
                }
                comments.append(record)

                action_verb = action.upper()
                print(f"[R2] {agent['name']} {action_verb}S {target_post['agent_name']}: \"{content[:120]}...\"")

    def _choose_action(self, agent: Dict, target_post: Dict) -> str:
        """Choose comment action: challenge / support / extend."""
        role_defaults = {
            "skeptic": "challenge",
            "replicator": "support",
            "integrator": "extend",
            "proposer": "extend",
            "arbiter": "support",
        }
        return role_defaults.get(agent["role"], "support")

    def _generate_comment(
        self,
        agent: Dict,
        target_post: Dict,
        action: str,
        round_num: int,
        parent_comment: Optional[Dict] = None,
    ) -> str:
        """Use LLM to generate a role-shaped comment."""
        if parent_comment:
            context = (
                f"You are replying to a comment on your own post.\n"
                f"Original comment: \"{parent_comment['content'][:400]}\"\n"
                f"Your task: acknowledge valid points and defend/refine your stance."
            )
        else:
            context = (
                f"You are reading this post:\n"
                f"Title: {target_post['title']}\n"
                f"Content snippet: {target_post['content'][:500]}\n\n"
                f"Your action: {action} this post based on your role."
            )

        prompt = (
            f"You are {agent['name']}, a research agent.\n"
            f"Role: {agent['role']}\n"
            f"Persona: {agent['persona']}\n\n"
            f"{context}\n\n"
            f"Write a single focused scientific comment (2–4 sentences). "
            f"Be specific — cite mechanisms, numbers, or tool names where possible. "
            f"Output ONLY the comment text."
        )

        try:
            from core.llm_client import get_llm_client
            llm = get_llm_client(agent_name=agent["name"])
            response = llm.call(
                prompt=prompt,
                max_tokens=200,
                session_id=f"comment_{agent['name']}_{uuid.uuid4().hex[:4]}",
            )
            return response.strip()
        except Exception:
            pass

        # Fallback
        fallbacks = {
            "challenge": f"The methodology here raises concerns — the evidence for '{target_post['title'][:60]}' requires stronger statistical support.",
            "support": f"These findings align with my own investigation; the computational approach is sound.",
            "extend": f"Building on this: broader context suggests additional pathways worth exploring in relation to this claim.",
        }
        return fallbacks.get(action, "Interesting findings worth further investigation.")

    # ------------------------------------------------------------------ #
    # Round 3 — Response                                                   #
    # ------------------------------------------------------------------ #

    def _run_round3(
        self,
        posts: List[Dict],
        agents: List[Dict],
        comments: List[Dict],
        client,
        dry_run: bool,
    ) -> None:
        print(f"\n{'─'*70}")
        print("--- ROUND 3: RESPONSE ---")
        print(f"{'─'*70}")

        for agent in agents:
            if agent["role"] == "arbiter":
                continue

            # Find own post
            own_post = next((p for p in posts if p["agent_name"] == agent["name"]), None)
            if not own_post:
                continue

            # Find top comment on own post (first R2 comment)
            top_comment = next(
                (c for c in comments if c["post_id"] == own_post["post_id"] and c["round"] == 2),
                None,
            )
            if not top_comment:
                continue

            content = self._generate_comment(
                agent, own_post, action="reply", round_num=3, parent_comment=top_comment
            )

            comment_id = None
            if not dry_run and client:
                try:
                    resp = client.create_comment(
                        post_id=own_post["post_id"],
                        content=content,
                        parent_id=top_comment["comment_id"],
                    )
                    comment_id = (resp.get("comment", {}) or {}).get("id") or resp.get("id")
                except Exception as e:
                    logger.error(f"Reply failed: {e}")

            if comment_id is None:
                comment_id = f"dry_reply_{uuid.uuid4().hex[:6]}"

            record = {
                "comment_id": comment_id,
                "post_id": own_post["post_id"],
                "parent_id": top_comment["comment_id"],
                "agent_name": agent["name"],
                "role": agent["role"],
                "content": content,
                "upvotes": 0,
                "downvotes": 0,
                "round": 3,
            }
            comments.append(record)

            commenter = top_comment["agent_name"]
            print(f"[R3] {agent['name']} REPLIES to {commenter}: \"{content[:120]}...\"")

    # ------------------------------------------------------------------ #
    # Round 4 — Voting                                                     #
    # ------------------------------------------------------------------ #

    def _run_round4(
        self,
        posts: List[Dict],
        agents: List[Dict],
        comments: List[Dict],
        votes: List[Dict],
        client,
        dry_run: bool,
    ) -> None:
        print(f"\n{'─'*70}")
        print("--- ROUND 4: VOTING ---")
        print(f"{'─'*70}")

        # Agents vote on all posts + all top-level comments
        top_comments = [c for c in comments if c.get("parent_id") is None]

        for agent in agents:
            # Vote on posts
            for post in posts:
                if post["agent_name"] == agent["name"]:
                    continue  # Can't vote own post

                value, justification = self._generate_vote(agent, post, "post")
                self._record_vote(
                    agent, "post", post["post_id"], value, justification,
                    votes, client, dry_run
                )

                arbiter_tag = " [ARBITER]" if agent["role"] == "arbiter" else ""
                sign = f"+{value}" if value > 0 else str(value)
                print(
                    f"[R4] {agent['name']}{arbiter_tag} votes {sign} on "
                    f"{post['agent_name']}: \"{justification}\""
                )
                # Update tally
                if value > 0:
                    post["upvotes"] += 1
                elif value < 0:
                    post["downvotes"] += 1

            # Vote on top-level comments
            for comment in top_comments:
                if comment["agent_name"] == agent["name"]:
                    continue

                value, justification = self._generate_vote(agent, comment, "comment")
                self._record_vote(
                    agent, "comment", comment["comment_id"], value, justification,
                    votes, client, dry_run
                )

                if value > 0:
                    comment["upvotes"] += 1
                elif value < 0:
                    comment["downvotes"] += 1

    def _generate_vote(
        self, agent: Dict, target: Dict, target_type: str
    ) -> Tuple[int, str]:
        """Use LLM to decide vote direction + 1-sentence justification."""
        if target_type == "post":
            snippet = f"Post: \"{target['title']}\"\nContent: {target.get('content','')[:300]}"
        else:
            snippet = f"Comment: \"{target.get('content','')[:300]}\""

        prompt = (
            f"You are {agent['name']} ({agent['role']}).\n"
            f"Persona: {agent['persona']}\n\n"
            f"Evaluate this {target_type}:\n{snippet}\n\n"
            f"Decide:\n"
            f"1. Vote: output exactly one of: +1, 0, -1\n"
            f"2. Justification: one sentence explaining why\n\n"
            f"Output JSON only: {{\"vote\": <int>, \"justification\": \"<string>\"}}"
        )

        try:
            from core.llm_client import get_llm_client
            llm = get_llm_client(agent_name=agent["name"])
            response = llm.call(
                prompt=prompt,
                max_tokens=100,
                session_id=f"vote_{agent['name']}_{uuid.uuid4().hex[:4]}",
            )
            match = re.search(r'\{.*?\}', response, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                vote_val = int(parsed.get("vote", 1))
                vote_val = max(-1, min(1, vote_val))
                justification = str(parsed.get("justification", ""))[:200]
                return vote_val, justification
        except Exception:
            pass

        # Fallback: skeptics vote -1 on non-own, others vote +1
        if agent["role"] == "skeptic":
            return -1, "Insufficient evidence to support this claim without further validation."
        return 1, "Methodologically sound with relevant computational evidence."

    def _record_vote(
        self,
        agent: Dict,
        target_type: str,
        target_id: str,
        value: int,
        justification: str,
        votes: List[Dict],
        client,
        dry_run: bool,
    ) -> None:
        votes.append({
            "voter": agent["name"],
            "role": agent["role"],
            "target_type": target_type,
            "target_id": target_id,
            "value": value,
            "justification": justification,
        })

        if not dry_run and client and value != 0:
            try:
                client.vote(
                    target_type=target_type,
                    target_id=target_id,
                    value=value,
                )
            except Exception as e:
                logger.error(f"Vote failed: {e}")

    # ------------------------------------------------------------------ #
    # Round 5 — Final Stance                                               #
    # ------------------------------------------------------------------ #

    def _run_round5(
        self,
        posts: List[Dict],
        agents: List[Dict],
        comments: List[Dict],
        stances: Dict[str, Dict],
        client,
        dry_run: bool,
    ) -> None:
        print(f"\n{'─'*70}")
        print("--- ROUND 5: FINAL STANCE ---")
        print(f"{'─'*70}")

        for agent in agents:
            own_post = next((p for p in posts if p["agent_name"] == agent["name"]), None)

            # Arbiter posts final verdict on the highest-voted post
            if agent["role"] == "arbiter":
                if not posts:
                    continue
                best_post = max(posts, key=lambda p: p["upvotes"] - p["downvotes"])
                own_post = best_post

            if not own_post:
                continue

            # Collect comments received on own post (or best post for arbiter)
            received_comments = [
                c for c in comments
                if c["post_id"] == own_post["post_id"] and c["agent_name"] != agent["name"]
            ]

            initial_stance = own_post.get("initial_stance", "Initial investigation stance")
            final_content, changed = self._generate_stance_update(
                agent, initial_stance, received_comments
            )

            comment_id = None
            if not dry_run and client:
                try:
                    resp = client.create_comment(
                        post_id=own_post["post_id"],
                        content=final_content,
                    )
                    comment_id = (resp.get("comment", {}) or {}).get("id") or resp.get("id")
                except Exception as e:
                    logger.error(f"Stance comment failed: {e}")

            if comment_id is None:
                comment_id = f"dry_stance_{uuid.uuid4().hex[:6]}"

            comments.append({
                "comment_id": comment_id,
                "post_id": own_post["post_id"],
                "parent_id": None,
                "agent_name": agent["name"],
                "role": agent["role"],
                "content": final_content,
                "upvotes": 0,
                "downvotes": 0,
                "round": 5,
            })

            stances[agent["name"]] = {
                "initial": initial_stance[:150],
                "final": final_content[:150],
                "changed": changed,
            }

            change_label = "CHANGED" if changed else "maintained"
            print(f"[R5] {agent['name']} ({agent['role']}) — stance {change_label}")
            print(f"     \"{final_content[:160]}...\"")

    def _generate_stance_update(
        self,
        agent: Dict,
        initial_stance: str,
        received_comments: List[Dict],
    ) -> Tuple[str, bool]:
        """LLM generates final stance comment; returns (content, changed_bool)."""
        comments_text = "\n".join(
            f"- {c['agent_name']} ({c['role']}): {c['content'][:200]}"
            for c in received_comments[:5]
        )

        prompt = (
            f"You are {agent['name']} ({agent['role']}).\n"
            f"Persona: {agent['persona']}\n\n"
            f"Your initial stance: \"{initial_stance}\"\n\n"
            f"Comments you received:\n{comments_text or '(none)'}\n\n"
            f"Write a final stance comment (3–5 sentences). "
            f"Did the peer critique change your view? Be honest. "
            f"End with: STANCE: CHANGED or STANCE: MAINTAINED\n\n"
            f"Output ONLY the comment text including the STANCE line."
        )

        try:
            from core.llm_client import get_llm_client
            llm = get_llm_client(agent_name=agent["name"])
            response = llm.call(
                prompt=prompt,
                max_tokens=300,
                session_id=f"stance_{agent['name']}_{uuid.uuid4().hex[:4]}",
            )
            content = response.strip()
            changed = "STANCE: CHANGED" in content.upper()
            return content, changed
        except Exception:
            pass

        fallback = (
            f"After reviewing peer commentary, my assessment of the evidence remains consistent "
            f"with my initial findings. The core claim stands pending additional validation. "
            f"STANCE: MAINTAINED"
        )
        return fallback, False

    # ------------------------------------------------------------------ #
    # Round 6 — Meta-post (optional)                                       #
    # ------------------------------------------------------------------ #

    def _run_round6(
        self,
        topic: str,
        posts: List[Dict],
        agents: List[Dict],
        community: str,
        client,
        dry_run: bool,
    ) -> Optional[str]:
        print(f"\n{'─'*70}")
        print("--- ROUND 6: META-POST (INTEGRATOR) ---")
        print(f"{'─'*70}")

        integrator = next((a for a in agents if a["role"] == "integrator"), agents[-1])

        summary_lines = [f"# Research Community: {topic}\n"]
        summary_lines.append("## Post Summaries\n")
        for p in posts:
            votes_str = f"↑{p['upvotes']} ↓{p['downvotes']}"
            summary_lines.append(f"- **{p['agent_name']}** ({p['role']}): {p['title']} — {votes_str}")

        meta_content = "\n".join(summary_lines)
        meta_title = f"Community Synthesis: {topic}"

        meta_post_id = None

        if not dry_run and client:
            try:
                result = client.create_post(
                    community=community,
                    title=meta_title,
                    content=meta_content,
                )
                meta_post_id = (result.get("post", {}) or {}).get("id") or result.get("id")

                # Link all posts to meta-post
                for p in posts:
                    try:
                        client.link_post(
                            from_post_id=meta_post_id,
                            to_post_id=p["post_id"],
                            link_type="cite",
                            context=f"Part of community investigation on {topic}",
                        )
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Meta-post failed: {e}")

        if meta_post_id is None:
            meta_post_id = f"dry_meta_{uuid.uuid4().hex[:6]}"

        print(f"[R6] {integrator['name']} created meta-post: {meta_post_id}")
        print(f"     \"{meta_title}\"")
        return meta_post_id

    # ------------------------------------------------------------------ #
    # Display                                                              #
    # ------------------------------------------------------------------ #

    def _print_board(
        self,
        posts: List[Dict],
        comments: List[Dict],
        votes: List[Dict],
    ) -> None:
        print(f"\n{'='*70}")
        print("=== COMMUNITY BOARD ===")
        print(f"{'='*70}")

        for post in posts:
            votes_str = f"↑{post['upvotes']} ↓{post['downvotes']}"
            print(f"\nPOST  {post['agent_name']}: \"{post['title']}\"  {votes_str}")

            # Top-level comments on this post
            top_comments = [
                c for c in comments
                if c["post_id"] == post["post_id"] and c.get("parent_id") is None
            ]
            for comment in top_comments:
                c_votes = f"↑{comment['upvotes']} ↓{comment['downvotes']}"
                snippet = comment["content"][:100].replace("\n", " ")
                print(f"  └─ [{comment['agent_name']}] \"{snippet}\"  {c_votes}")

                # Replies to this comment
                replies = [
                    c for c in comments
                    if c.get("parent_id") == comment["comment_id"]
                ]
                for reply in replies:
                    r_snippet = reply["content"][:80].replace("\n", " ")
                    print(f"      └─ [{reply['agent_name']}] \"{r_snippet}\"")

    def _print_stance_table(self, stances: Dict[str, Dict]) -> None:
        print(f"\n{'='*70}")
        print("=== STANCE EVOLUTION ===")
        print(f"{'='*70}")
        print(f"{'Agent':<22} {'Initial':<35} {'Final':<35} {'Changed'}")
        print(f"{'─'*22} {'─'*35} {'─'*35} {'─'*10}")
        for agent_name, s in stances.items():
            initial = (s["initial"][:32] + "...") if len(s["initial"]) > 35 else s["initial"]
            final = (s["final"][:32] + "...") if len(s["final"]) > 35 else s["final"]
            changed = "YES" if s["changed"] else "NO"
            print(f"{agent_name:<22} {initial:<35} {final:<35} {changed}")
        print()
