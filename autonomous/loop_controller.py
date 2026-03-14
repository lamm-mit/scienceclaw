#!/usr/bin/env python3
"""
Autonomous Loop Controller

Main orchestration class for the agent's autonomous investigation cycles.
Integrates memory, reasoning, and platform interaction into a continuous
scientific discovery loop.

Every 6 hours, the agent:
1. Observes the community (reads posts, identifies gaps)
2. Generates hypotheses from gaps
3. Selects the most promising hypothesis
4. Conducts a full investigation
5. Shares findings with the community
6. Engages with peers (comments, upvotes)

Author: ScienceClaw Team
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class EntityQuery(BaseModel):
    """Validated entity extracted from thread context for a specific skill."""
    entity: str = Field(..., min_length=1, max_length=80)

    @field_validator("entity")
    @classmethod
    def must_be_entity_not_sentence(cls, v: str) -> str:
        """Reject generic fallback sentences the LLM sometimes produces."""
        bad = {"required", "analysis", "computational", "further",
               "investigation", "relationships", "evidence", "suggests",
               "no results", "not found"}
        if any(w in v.lower() for w in bad):
            raise ValueError(f"Looks like a sentence, not an entity: {v!r}")
        return v.strip("\"'")


# Add skills to path for platform clients
SCIENCECLAW_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCIENCECLAW_DIR / "skills" / "infinite" / "scripts"))

# Import memory and reasoning components
from memory import AgentJournal, InvestigationTracker, KnowledgeGraph
from reasoning import ScientificReasoningEngine
from coordination import SessionManager, AgentDiscoveryService
from utils.credential_scrubber import scrub


class AutonomousLoopController:
    """
    Main orchestrator for autonomous scientific investigation cycles.
    
    Integrates all components:
    - Memory system (journal, investigations, knowledge graph)
    - Scientific reasoning engine (gaps, hypotheses, experiments)
    - Platform client (Infinite)
    - Agent profile (interests, preferred tools)
    """
    
    def __init__(self, agent_profile: Dict[str, Any]):
        """
        Initialize the autonomous loop controller.
        
        Args:
            agent_profile: Agent's profile (interests, tools, personality)
                Expected keys:
                - name: Agent name
                - bio: Agent description
                - profile: Expertise preset (biology, chemistry, mixed)
                - interests: List of research interests
                - preferred_organisms: List of organisms (biology agents)
                - preferred_proteins: List of proteins (biology agents)
                - preferred_compounds: List of compounds (chemistry agents)
                - preferred_tools: List of tool names
                - curiosity_style: How agent explores (systematic, opportunistic, deep-dive)
                - communication_style: How agent writes (formal, casual, technical)
        """
        self.agent_profile = agent_profile
        self.agent_name = agent_profile.get("name", "ScienceClawAgent")

        # Optional seed post: when set, findings are posted as comments on this
        # post instead of as new top-level posts.  Passed via the profile key
        # "seed_post_id" or the SCIENCECLAW_SEED_POST_ID environment variable.
        import os
        self.seed_post_id: Optional[str] = (
            agent_profile.get("seed_post_id")
            or os.environ.get("SCIENCECLAW_SEED_POST_ID")
            or ""
        )

        # Initialize memory components
        self.journal = AgentJournal(agent_name=self.agent_name)
        self.investigations = InvestigationTracker(agent_name=self.agent_name)
        self.knowledge_graph = KnowledgeGraph(agent_name=self.agent_name)
        
        # Initialize reasoning engine
        self.reasoning_engine = ScientificReasoningEngine(
            agent_name=self.agent_name
        )
        
        # Initialize session manager for multi-agent coordination
        self.session_manager = SessionManager(agent_name=self.agent_name)

        # Initialize artifact reactor for peer artifact reactions
        from artifacts.artifact import ArtifactStore
        from artifacts.reactor import ArtifactReactor
        self._artifact_store = ArtifactStore(agent_name=self.agent_name)
        self._reactor = ArtifactReactor(
            agent_name=self.agent_name,
            agent_profile=agent_profile,
            artifact_store=self._artifact_store,
        )

        # Initialize discovery service (Phase 2)
        self.discovery_service = AgentDiscoveryService()

        # Initialize the Infinite platform client — prefer per-agent config if it exists
        self.platform = self._initialize_platform()

        print(f"[AutonomousLoopController] Initialized for agent: {self.agent_name}")
        print(f"[AutonomousLoopController] Platform: {self.platform.__class__.__name__ if self.platform else 'disabled'}")
        print(f"[AutonomousLoopController] Profile: {agent_profile.get('profile', 'mixed')}")
    
    def _initialize_platform(self):
        """
        Initialize the Infinite platform client.

        Returns:
            InfiniteClient instance
        """
        if self.agent_profile.get("disable_platform"):
            return None
        # Per-agent config takes priority (enables distinct identities in multi-agent demo)
        per_agent_config = (
            Path.home() / ".scienceclaw" / "profiles" / self.agent_name / "infinite_config.json"
        )
        default_config = Path.home() / ".scienceclaw" / "infinite_config.json"
        infinite_config = per_agent_config if per_agent_config.exists() else default_config
        if infinite_config.exists():
            try:
                from infinite_client import InfiniteClient
                return InfiniteClient(config_file=infinite_config)
            except Exception as e:
                print(f"[Platform] Infinite initialization failed: {scrub(str(e))}")

        if self.agent_profile.get("disable_platform"):
            return None
        raise RuntimeError("No platform configured. Run setup.py to configure Infinite.")
    
    def run_heartbeat_cycle(self) -> Dict[str, Any]:
        """
        Run a complete autonomous heartbeat cycle.
        
        This is the main entry point called by heartbeat_daemon.py every 6 hours.
        
        Steps:
        1. Check notifications/DMs
        2. Observe community (read posts, identify gaps)
        3. Generate hypotheses from gaps
        4. Select best hypothesis
        5. Conduct investigation
        6. Share findings
        7. Engage with peers
        
        Returns:
            Summary of cycle activities
        """
        cycle_start = datetime.now()
        print(f"\n{'='*60}")
        print(f"🦞 HEARTBEAT CYCLE START: {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        summary = {
            "cycle_start": cycle_start.isoformat(),
            "steps_completed": [],
            "errors": []
        }
        
        try:
            # Step 1: Check notifications/DMs
            print("📬 Step 1: Checking notifications and DMs...")
            if self.platform:
                self._check_notifications()
            else:
                print("   (platform disabled) skipping notifications")
            summary["steps_completed"].append("check_notifications")
            
            # Step 1.5: Check for collaborative sessions
            print("\n🤝 Step 1.5: Checking collaborative sessions...")
            self._check_collaborative_sessions()
            summary["steps_completed"].append("check_collaborative_sessions")

            # Step 1.6: Agent discovery (Phase 2)
            print("\n🔍 Step 1.6: Agent discovery - looking for collaborative opportunities...")
            discovery_summary = self._discover_and_join_sessions()
            summary["discovery_summary"] = discovery_summary
            summary["steps_completed"].append("agent_discovery")

            # Step 2: Deep investigation directly from agent interests.
            # The artifact reactor drives cross-agent chaining — no gap detector needed.
            print("\n🔬 Step 2: Running deep investigation on agent interests...")
            investigation_id, post_id = self._run_interest_investigation()
            summary["investigation_id"] = investigation_id
            if post_id:
                summary["post_id"] = post_id
            summary["steps_completed"].append("conduct_investigation")

            # Step 3: React to peer artifacts (lock-and-key artifact chaining)
            print("\n🔗 Step 3: Reacting to peer artifacts...")
            reaction_children = self._reactor.react(
                limit=3, investigation_id=investigation_id or ""
            )
            if reaction_children:
                print(f"   Produced {len(reaction_children)} reaction artifact(s)")
                self._post_reaction_findings(reaction_children)
                summary["reaction_artifacts"] = len(reaction_children)

                # Detect fulfillment artifacts and synthesize insights from them
                fulfillments = [
                    c for c in reaction_children
                    if "_fulfilled_need" in c.payload
                ]
                if fulfillments:
                    print(f"   Synthesizing from {len(fulfillments)} fulfillment artifact(s)...")
                    self._synthesize_from_fulfillments(fulfillments)
                    summary["fulfillment_artifacts"] = len(fulfillments)
            else:
                print("   No compatible peer artifacts found yet")
            summary["steps_completed"].append("react_to_peer_artifacts")
            
            # Step 7: Engage with peers
            print("\n🤝 Step 7: Engaging with peers...")
            if self.platform:
                engagement = self.engage_with_peers()
                print(f"   Upvoted: {engagement['upvotes']}, Commented: {engagement['comments']}")
                summary["engagement"] = engagement
            else:
                print("   (platform disabled) skipping peer engagement")
            summary["steps_completed"].append("engage_with_peers")
            
        except Exception as e:
            print(f"\n❌ Error during heartbeat cycle: {scrub(str(e))}")
            summary["errors"].append(str(e))
        
        cycle_end = datetime.now()
        duration = (cycle_end - cycle_start).total_seconds()
        summary["cycle_end"] = cycle_end.isoformat()
        summary["duration_seconds"] = duration
        
        print(f"\n{'='*60}")
        print(f"✅ HEARTBEAT CYCLE COMPLETE: {duration:.1f}s")
        print(f"{'='*60}\n")
        
        # Log cycle to journal
        self.journal.log_observation(
            content=f"Completed heartbeat cycle with {len(summary['steps_completed'])} steps",
            observation=f"Completed heartbeat cycle with {len(summary['steps_completed'])} steps",
            source="autonomous_loop",
            metadata={
                "summary": summary,
                "duration_seconds": duration
            }
        )
        
        return summary
    
    def observe_community(self) -> List[Dict[str, Any]]:
        """
        Observe the community and identify knowledge gaps.
        
        Steps:
        1. Fetch recent posts from relevant communities
        2. Parse posts for scientific content
        3. Use gap detector to identify open questions and contradictions
        4. Filter gaps by agent's interests
        
        Returns:
            List of knowledge gaps with context
        """
        gaps = []
        
        try:
            # Get relevant communities from agent profile
            profile = self.agent_profile.get("profile", "mixed")
            communities = self._get_relevant_communities(profile)
            
            # Fetch recent posts from each community
            all_posts = []
            for community in communities:
                print(f"   Reading from m/{community}...")
                try:
                    result = self.platform.get_posts(
                        community=community,
                        sort="new",
                        limit=10
                    )
                    posts = result.get("posts", result if isinstance(result, list) else [])
                    all_posts.extend(posts)
                except Exception as e:
                    print(f"   Warning: Failed to fetch from m/{community}: {scrub(str(e))}")
            
            print(f"   Retrieved {len(all_posts)} posts")
            
            # Detect gaps using reasoning engine
            # Use gap detector directly, passing posts as context
            from reasoning.gap_detector import GapDetector
            gap_detector = GapDetector(
                knowledge_graph=self.knowledge_graph,
                journal=self.journal
            )
            detected_gaps = gap_detector.detect_gaps(context={"posts": all_posts})

            # Bootstrap: if no gaps found yet and agent has research interests,
            # seed one gap per interest so the first heartbeat cycle can proceed
            if not detected_gaps:
                interests = self.agent_profile.get(
                    "interests",
                    self.agent_profile.get("research", {}).get("interests", [])
                )
                for interest in interests[:3]:
                    detected_gaps.append({
                        "type": "interest_gap",
                        "description": f"Unexplored research area: {interest}",
                        "priority": "medium",
                        "source": "agent_interests",
                    })

            # Enrich gaps with context from posts
            for gap in detected_gaps:
                # Add agent interests for filtering
                gap["agent_interests"] = self.agent_profile.get("interests", [])
                gap["agent_profile"] = profile
                gaps.append(gap)

            # Filter gaps by relevance to agent's interests
            gaps = self._filter_gaps_by_interests(gaps)
            
            print(f"   Filtered to {len(gaps)} relevant gaps")
            
        except Exception as e:
            print(f"   Error observing community: {scrub(str(e))}")
        
        return gaps
    
    def generate_hypotheses(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate testable hypotheses from knowledge gaps.
        
        Args:
            gaps: List of knowledge gaps from observe_community()
        
        Returns:
            List of hypotheses with metadata
        """
        hypotheses = []
        
        for gap in gaps[:5]:  # Limit to top 5 gaps
            try:
                # Use hypothesis generator directly
                from reasoning.hypothesis_generator import HypothesisGenerator
                hypothesis_gen = HypothesisGenerator()
                hypothesis = hypothesis_gen.generate_from_gap(gap)
                if hypothesis:
                    hypotheses.append(hypothesis)
            except Exception as e:
                print(f"   Warning: Failed to generate hypothesis for gap: {scrub(str(e))}")
        
        return hypotheses
    
    def select_hypothesis(self, hypotheses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select the best hypothesis to investigate.
        
        Selection criteria (in order of priority):
        1. Novelty - Not recently investigated
        2. Feasibility - Tools available, reasonable scope
        3. Impact - Alignment with agent interests
        4. Testability - Clear experimental design
        
        Args:
            hypotheses: List of candidate hypotheses
        
        Returns:
            Selected hypothesis with metadata
        """
        if not hypotheses:
            return None
        
        # Score each hypothesis
        scored = []
        for hyp in hypotheses:
            score = self._score_hypothesis(hyp)
            scored.append((score, hyp))
        
        # Sort by score (descending)
        scored.sort(reverse=True, key=lambda x: x[0])
        
        # Return top hypothesis
        best_score, best_hyp = scored[0]
        print(f"   Scores: {[s for s, h in scored]}")
        print(f"   Best score: {best_score:.2f}")
        
        return best_hyp
    
    def conduct_investigation(self, hypothesis: Dict[str, Any]) -> str:
        """
        Conduct a full scientific investigation for a hypothesis.
        
        This is the core scientific method implementation:
        1. Create investigation record
        2. Design experiment
        3. Execute experiment
        4. Analyze results
        5. Draw conclusions
        6. Update knowledge graph
        
        Args:
            hypothesis: Selected hypothesis to investigate
        
        Returns:
            Investigation ID
        """
        # Use reasoning engine's investigate method
        investigation_id = self.reasoning_engine.run_scientific_cycle(context=hypothesis)
        
        # The run_scientific_cycle returns a summary, extract the investigation_id
        if isinstance(investigation_id, dict):
            investigation_id = investigation_id.get("investigation_id", "unknown")
        
        return investigation_id
    
    def share_findings(self, investigation_id: str) -> Optional[str]:
        """
        Share investigation findings with the community.
        
        Creates a scientific post in the standard format:
        - Title: Concise summary
        - Content: Full analysis
        - Hypothesis: Research question
        - Method: Tools and approach
        - Findings: Key results with data
        - Data Sources: Citations
        - Open Questions: Unanswered questions
        
        Args:
            investigation_id: ID of completed investigation
        
        Returns:
            Post ID if successful, None otherwise
        """
        try:
            # Retrieve investigation
            investigation = self.investigations.get_investigation(investigation_id)
            if not investigation:
                print(f"   Investigation not found: {investigation_id}")
                return None
            
            # Check the status field
            if investigation["status"] not in ["complete", "completed"]:
                print(f"   Investigation not complete: {investigation['status']}")
                return None
            
            # Format post content
            title = self._format_post_title(investigation)
            content = self._format_post_content(investigation)
            
            # Determine community
            community = self._select_community_for_post(investigation)

            if self.seed_post_id:
                # Demo mode: thread all findings as comments on the shared seed post
                print(f"   Commenting on seed post {self.seed_post_id[:12]}...")
                comment_body = (
                    f"**[{self.agent_name}] {title}**\n\n"
                    + content
                )
                result = self.platform.create_comment(
                    post_id=self.seed_post_id,
                    content=comment_body,
                )
                post_id = (
                    result.get("id")
                    or result.get("comment_id")
                    or result.get("comment", {}).get("id")
                )
            else:
                # Normal mode: create a new top-level post
                print(f"   Posting to m/{community}...")
                result = self.platform.create_post(
                    title=title,
                    content=content,
                    community=community,
                    hypothesis=investigation.get("hypothesis", ""),
                    method=self._extract_method(investigation),
                    findings=self._extract_findings(investigation),
                )
                post_id = (
                    result.get("id")
                    or result.get("post_id")
                    or result.get("post", {}).get("id")
                )
            
            # Log to journal
            self.journal.log_observation(
                content=f"Posted findings to m/{community}",
                observation=f"Posted findings to m/{community}",
                source="autonomous_loop",
                metadata={
                    "post_id": post_id,
                    "investigation_id": investigation_id,
                    "community": community
                }
            )
            
            return post_id
            
        except Exception as e:
            print(f"   Error sharing findings: {scrub(str(e))}")
            return None
    
    def engage_with_peers(self) -> Dict[str, int]:
        """
        Engage with community posts (upvote, comment, and follow-up investigations).

        Strategy:
        - Read recent posts from relevant communities
        - Upvote high-quality, evidence-based posts
        - Comment on posts related to agent's expertise
        - For interesting peer posts, run a complementary DeepInvestigation and
          post the findings as a follow-up comment or new post

        Returns:
            Engagement summary (upvotes, comments, follow_ups counts)
        """
        engagement = {"upvotes": 0, "comments": 0, "follow_ups": 0}

        try:
            # Get relevant communities
            profile = self.agent_profile.get("profile", "mixed")
            communities = self._get_relevant_communities(profile)

            for community in communities:
                try:
                    # Fetch recent posts
                    result = self.platform.get_posts(
                        community=community,
                        sort="hot",
                        limit=5
                    )
                    posts = result.get("posts", result if isinstance(result, list) else [])

                    for post in posts[:3]:  # Engage with top 3
                        post_author = post.get("author", {})
                        post_author_name = (
                            post_author.get("name") if isinstance(post_author, dict)
                            else str(post_author)
                        )

                        # Skip own posts
                        if post_author_name == self.agent_name:
                            continue

                        # Upvote if high quality
                        if self._should_upvote(post):
                            try:
                                self.platform.vote_post(post["id"], 1)
                                engagement["upvotes"] += 1
                            except Exception as e:
                                print(f"   Warning: Upvote failed: {scrub(str(e))}")

                        # Comment if relevant
                        if self._should_comment(post):
                            comment_text = self._generate_comment(post)
                            if comment_text:
                                try:
                                    self.platform.create_comment(
                                        post_id=post["id"],
                                        content=comment_text
                                    )
                                    engagement["comments"] += 1
                                except Exception as e:
                                    print(f"   Warning: Comment failed: {scrub(str(e))}")

                        # ── Peer-aware follow-up investigation ──────────────
                        if self._should_follow_up(post):
                            self._run_peer_followup(post, community, engagement)

                except Exception as e:
                    print(f"   Warning: Engagement failed for m/{community}: {scrub(str(e))}")

        except Exception as e:
            print(f"   Error during peer engagement: {scrub(str(e))}")

        return engagement

    def _should_follow_up(self, post: Dict[str, Any]) -> bool:
        """Return True if this post is interesting enough for a complementary investigation."""
        interests = [i.lower() for i in self.agent_profile.get("interests", [])]
        post_text = (
            post.get("title", "") + " " +
            post.get("hypothesis", "") + " " +
            post.get("findings", "")
        ).lower()

        # Must match at least one interest
        relevant = any(i in post_text for i in interests)

        # Avoid posts we already commented on with a follow-up (check title prefix)
        post_title = post.get("title", "")
        already_following = post_title.startswith("[Follow-up]")

        # 30 % random chance to avoid spamming every single post
        import random
        return relevant and not already_following and random.random() < 0.30

    def _run_peer_followup(self, post: Dict[str, Any], community: str,
                           engagement: Dict[str, int]):
        """
        Run a complementary DeepInvestigation on the peer's topic and post the
        findings as a follow-up, referencing the original post.
        """
        try:
            from autonomous.deep_investigation import run_deep_investigation

            peer_topic = post.get("title", "").strip()
            if not peer_topic:
                return

            # Build a complementary angle based on this agent's profile
            profile_type = self.agent_profile.get("profile", "mixed")
            angle_map = {
                "biology":   "protein structure and gene-level mechanisms of",
                "chemistry": "chemical properties and drug-target interactions for",
                "mixed":     "multi-disciplinary mechanistic insights into",
            }
            angle = angle_map.get(profile_type, "computational insights into")
            followup_topic = f"{angle} {peer_topic}"

            print(f"   🔁 Follow-up investigation: {followup_topic[:80]}...")
            content = run_deep_investigation(
                agent_name=self.agent_name,
                topic=followup_topic,
                community=community,
                agent_profile=self.agent_profile,
            )

            if not content or not content.get("title"):
                return

            # Post the follow-up as a new post referencing the original
            post_id_ref = post.get("id", "")
            followup_title = f"[Follow-up] {content['title'][:100]}"
            followup_content = (
                f"> In response to post by {post.get('author', {}).get('name', 'a peer agent')}.\n\n"
                + content.get("content", "")
            )

            # Attach figure paths if generated
            figures = content.get("figures", [])
            if figures:
                followup_content += "\n\n**Generated Figures:**\n"
                for fp in figures:
                    followup_content += f"- `{fp}`\n"

            result = self.platform.create_post(
                title=followup_title,
                content=followup_content,
                community=community,
                hypothesis=content.get("hypothesis", ""),
                method=content.get("method", ""),
                findings=content.get("findings", ""),
            )
            if result.get("id") or result.get("post_id"):
                engagement["follow_ups"] += 1
                print(f"   ✅ Follow-up posted to m/{community}")

        except Exception as e:
            print(f"   Warning: Follow-up investigation failed: {scrub(str(e))}")
    
    def _check_notifications(self):
        """Check for DMs and notifications."""
        try:
            # Get notifications from platform
            result = self.platform.get_notifications(unread_only=True, limit=20)
            
            if "error" not in result:
                notifications = result.get("notifications", [])
                print(f"   Unread notifications: {len(notifications)}")
                
                # Process each notification
                for notif in notifications[:10]:  # Limit to 10 per cycle
                    notif_type = notif.get("type")
                    
                    # Handle human intervention comments (highest priority)
                    comment_type = notif.get("commentType") or notif.get("metadata", {}).get("commentType")
                    if comment_type in ("progress", "redirect", "conclude", "force-close"):
                        self._handle_intervention_comment(notif, comment_type)
                    # Handle mentions
                    elif notif_type == "mention":
                        self._handle_mention(notif)

                    # Handle replies
                    elif notif_type == "reply":
                        self._handle_reply(notif)

                    # Mark as read
                    self.platform.mark_notification_read(notif["id"])
            else:
                print(f"   Could not fetch notifications: {result.get('error')}")
                
        except Exception as e:
            print(f"   Error checking notifications: {scrub(str(e))}")
    
    def _handle_mention(self, notif: Dict[str, Any]):
        """Handle a mention notification."""
        try:
            content = notif.get("content", "")
            metadata = notif.get("metadata", {})
            post_id = metadata.get("postId")
            
            # Simple acknowledgment (in production, use GPT for context-aware response)
            if post_id:
                interests = self.agent_profile.get("interests", ["science"])
                reply = f"Thanks for the mention! I'm researching {interests[0]}. Happy to collaborate!"
                
                # Comment on the post
                self.platform.create_comment(post_id, reply)
                print(f"   Replied to mention in post {post_id[:8]}...")
                
        except Exception as e:
            print(f"   Error handling mention: {scrub(str(e))}")
    
    def _handle_reply(self, notif: Dict[str, Any]):
        """Handle a reply notification (placeholder)."""
        # In production, could analyze reply and respond
        print(f"   Received reply: {notif.get('content', '')[:50]}...")

    def _handle_intervention_comment(self, notif: Dict[str, Any], comment_type: str):
        """Handle a typed human intervention comment on an active investigation post."""
        try:
            metadata = notif.get("metadata", {})
            post_id = metadata.get("postId")
            content = notif.get("content", "")

            # Log in journal so intervention is part of auditable provenance
            if hasattr(self, 'journal') and self.journal:
                self.journal.log_observation(
                    f"Human intervention ({comment_type}) on post {post_id}: {content[:200]}",
                    investigation_id=post_id
                )

            if comment_type == "progress":
                # Reply with current investigation status
                if post_id:
                    active = []
                    if hasattr(self, 'investigation_tracker') and self.investigation_tracker:
                        active = self.investigation_tracker.get_active_investigations()
                    status_lines = [f"Status update for investigation {post_id[:8]}:"]
                    if active:
                        inv = next((i for i in active if i.get("id") == post_id), active[0])
                        status_lines.append(f"- Steps completed: {', '.join(inv.get('completed_steps', []))}")
                        status_lines.append(f"- Current hypothesis: {inv.get('current_hypothesis', 'selecting next')}")
                        status_lines.append(f"- Next planned: {inv.get('next_step', 'gap detection')}")
                    else:
                        status_lines.append("- No active investigation found for this post.")
                    self.platform.create_comment(post_id, "\n".join(status_lines))
                    print(f"   Responded to progress request on post {post_id[:8]}...")

            elif comment_type == "redirect":
                # Promote the redirected sub-question to top of hypothesis queue
                if content:
                    if not hasattr(self, '_redirected_hypotheses'):
                        self._redirected_hypotheses = []
                    self._redirected_hypotheses.insert(0, {
                        "text": content,
                        "source": "human_redirect",
                        "post_id": post_id,
                        "priority": "high",
                    })
                    print(f"   Queued redirect hypothesis (priority override): {content[:80]}...")

            elif comment_type in ("conclude", "force-close"):
                # Mark current investigation for immediate synthesis and closure
                if not hasattr(self, '_investigations_to_conclude'):
                    self._investigations_to_conclude = []
                self._investigations_to_conclude.append(post_id)
                print(f"   Flagged post {post_id[:8] if post_id else '?'} for immediate conclusion ({comment_type})...")

        except Exception as e:
            print(f"   Error handling intervention comment ({comment_type}): {scrub(str(e))}")

    def _check_collaborative_sessions(self):
        """Check for collaborative investigation sessions and participate."""
        try:
            # List active sessions
            active_sessions = self.session_manager.list_active_sessions()
            
            if not active_sessions:
                print("   No active collaborative sessions")
                return
            
            print(f"   Found {len(active_sessions)} active sessions")
            
            # Look for sessions to join
            for session_summary in active_sessions[:3]:  # Limit to 3 per cycle
                session_id = session_summary["id"]
                
                # Skip if already a participant
                if self.agent_name in session_summary["participants"]:
                    # Check for available tasks to claim
                    available_tasks = self.session_manager.find_available_tasks(session_id)
                    if available_tasks:
                        # Claim and execute first available task
                        self._participate_in_session(session_id, available_tasks[0])
                else:
                    # Consider joining based on topic relevance
                    if self._should_join_session(session_summary):
                        self._join_and_participate(session_id)
                        
        except Exception as e:
            print(f"   Error checking collaborative sessions: {scrub(str(e))}")
    
    def _get_relevant_communities(self, profile: str) -> List[str]:
        """Get list of communities relevant to agent's profile."""
        if profile == "biology":
            return ["biology", "scienceclaw"]
        elif profile == "chemistry":
            return ["chemistry", "scienceclaw"]
        else:  # mixed
            return ["biology", "chemistry", "scienceclaw"]
    
    def _filter_gaps_by_interests(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter gaps to those relevant to agent's interests."""
        interests = [i.lower() for i in self.agent_profile.get("interests", [])]
        if not interests:
            return gaps  # No filtering if no interests specified
        
        filtered = []
        for gap in gaps:
            gap_text = (gap.get("description", "") + " " + gap.get("context", "")).lower()
            if any(interest in gap_text for interest in interests):
                filtered.append(gap)
        
        return filtered if filtered else gaps[:3]  # Return all if none match

    def _post_hypotheses_to_communities(self, hypotheses: List[Dict[str, Any]]) -> int:
        """
        Post a list of hypotheses to appropriate communities based on keyword routing.

        Returns the number of hypotheses successfully posted.
        """
        COMMUNITY_KEYWORDS = {
            "protein-design": ["protein", "folding", "structure", "alphafold", "pdb", "uniprot"],
            "drug-discovery": ["drug", "compound", "admet", "bbb", "smiles", "binding", "inhibitor", "sar"],
            "materials": ["material", "scaffold", "biocompatible", "surface", "polymer"],
            "biology": ["gene", "crispr", "expression", "genomic", "organism", "cell"],
            "chemistry": ["reaction", "synthesis", "chemical", "molecule", "rdkit", "pubchem"],
        }

        posted = 0
        agent_name = self.agent_profile.get("name", "Agent")
        for hyp in hypotheses:
            text = hyp.get("hypothesis", hyp.get("statement", "")).lower()
            community = "scienceclaw"  # default
            for comm, keywords in COMMUNITY_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    community = comm
                    break
            try:
                self.platform.create_post(
                    title=text[:80],
                    content=text,
                    community=community,
                    agent_name=agent_name,
                )
                posted += 1
            except Exception:
                pass
        return posted

    def _discover_and_join_sessions(self) -> Dict[str, Any]:
        """
        Phase 2: Discover and join collaborative sessions matching agent's skills.

        Process:
        1. Register agent in discovery index
        2. Find sessions matching agent's skills
        3. Find sessions matching agent's interests
        4. Join most relevant sessions
        5. Optionally claim investigations if interested

        Returns:
            Summary of discovery and joining actions
        """
        summary = {
            "registered": False,
            "sessions_found": 0,
            "sessions_joined": 0,
            "investigations_claimed": 0
        }

        try:
            # Step 1: Register agent in discovery index
            print("   Registering agent in discovery index...")
            self.discovery_service.register_agent(
                agent_name=self.agent_name,
                profile=self.agent_profile,
                status="available"
            )
            summary["registered"] = True

            # Step 2: Find sessions by skill match
            print("   Searching for sessions matching my skills...")
            skills = self.agent_profile.get("preferred_tools", [])
            skill_sessions = self.discovery_service.find_sessions_by_skill(skills, limit=5)
            summary["sessions_found"] += len(skill_sessions)

            # Step 3: Find sessions by interest match
            print("   Searching for sessions matching my interests...")
            interests = self.agent_profile.get("interests", [])
            interest_str = " ".join(interests) if interests else "general science"
            interest_sessions = self.discovery_service.find_sessions_by_interest(interest_str, limit=5)
            summary["sessions_found"] += len(interest_sessions)

            # Combine and deduplicate sessions
            all_sessions = {}
            for session in skill_sessions + interest_sessions:
                session_id = session["session_id"]
                if session_id not in all_sessions:
                    all_sessions[session_id] = session

            # Step 4: Join top sessions
            print(f"   Found {len(all_sessions)} open sessions. Joining relevant ones...")
            for session_id, session_info in list(all_sessions.items())[:3]:  # Join up to 3 sessions
                try:
                    # Join session
                    join_result = self.session_manager.join_session(session_id)
                    if join_result.get("status") in ("joined", "already_joined"):
                        summary["sessions_joined"] += 1
                        print(f"     ✓ Joined: {session_info['topic']}")

                        # Step 5: Optionally claim investigations if very relevant
                        # (Only claim if high skill/interest match)
                        suggested_invs = session_info.get("suggestion_count", 0)
                        if suggested_invs > 0 and self.agent_profile.get("curiosity_style") != "skeptic":
                            # Try to claim first investigation (if many investigations)
                            session_data = self.session_manager.get_session(session_id)
                            if session_data and session_data.get("suggested_investigations"):
                                first_inv = session_data["suggested_investigations"][0]
                                claim_result = self.session_manager.claim_investigation(
                                    session_id,
                                    first_inv["id"]
                                )
                                if claim_result.get("status") == "claimed":
                                    summary["investigations_claimed"] += 1
                                    print(f"       - Claimed investigation: {first_inv['description']}")

                except Exception as e:
                    print(f"     ✗ Error joining session: {scrub(str(e))}")
                    summary["join_errors"] = summary.get("join_errors", 0) + 1

        except Exception as e:
            print(f"   Error during discovery: {scrub(str(e))}")
            summary["discovery_error"] = str(e)

        return summary

    def _score_hypothesis(self, hypothesis: Dict[str, Any]) -> float:
        """
        Score a hypothesis for selection priority.
        
        Criteria:
        - Novelty: 0-1 (not recently investigated)
        - Feasibility: 0-1 (tools available, reasonable scope)
        - Impact: 0-1 (alignment with interests)
        - Testability: 0-1 (clear experimental design)
        
        Returns:
            Score from 0-4 (sum of criteria)
        """
        score = 0.0
        
        # Novelty: Check if topic was recently investigated
        topics = self.journal.get_investigated_topics()
        hyp_text = hypothesis.get("hypothesis", "").lower()
        if not any(topic.lower() in hyp_text for topic in topics):
            score += 1.0
        else:
            score += 0.3  # Some novelty even if topic revisited
        
        # Feasibility: Check if required tools are available
        tools_needed = hypothesis.get("tools_needed", [])
        preferred_tools = self.agent_profile.get("preferred_tools", [])
        if tools_needed:
            tools_available = sum(1 for t in tools_needed if t in preferred_tools)
            score += tools_available / len(tools_needed)
        else:
            score += 0.5  # Neutral if no tools specified
        
        # Impact: Alignment with interests
        interests = self.agent_profile.get("interests", [])
        if interests:
            interest_match = sum(
                1 for interest in interests
                if interest.lower() in hyp_text
            )
            score += min(interest_match / len(interests), 1.0)
        else:
            score += 0.5  # Neutral if no interests
        
        # Testability: Has clear experimental design
        if hypothesis.get("experiment_design"):
            score += 1.0
        elif hypothesis.get("tools_needed"):
            score += 0.5
        
        return score
    
    def _format_post_title(self, investigation: Dict[str, Any]) -> str:
        """Generate post title from investigation."""
        hypothesis = investigation.get("hypothesis", "Scientific Investigation")
        # Truncate to reasonable length
        if len(hypothesis) > 80:
            return hypothesis[:77] + "..."
        return hypothesis
    
    def _format_post_content(self, investigation: Dict[str, Any]) -> str:
        """Generate formatted post content from investigation."""
        lines = []
        
        # Hypothesis
        lines.append("## Hypothesis")
        lines.append(investigation.get("hypothesis", "N/A"))
        lines.append("")
        
        # Method
        lines.append("## Method")
        lines.append(self._extract_method(investigation))
        lines.append("")
        
        # Findings
        lines.append("## Findings")
        lines.append(self._extract_findings(investigation))
        lines.append("")
        
        # Data sources
        lines.append("## Data Sources")
        data_sources = self._extract_data_sources(investigation)
        if data_sources:
            lines.append(data_sources)
        else:
            lines.append("See investigation logs")
        lines.append("")
        
        # Open questions
        lines.append("## Open Questions")
        open_questions = investigation.get("open_questions", [])
        if open_questions:
            for q in open_questions:
                lines.append(f"- {q}")
        else:
            lines.append("- Further validation needed")
        
        return "\n".join(lines)
    
    def _extract_method(self, investigation: Dict[str, Any]) -> str:
        """Extract method description from investigation."""
        experiments = investigation.get("experiments", [])
        if not experiments:
            return "No experiments conducted"
        
        tools_used = set()
        for exp in experiments:
            tool = exp.get("tool")
            if tool:
                tools_used.add(tool)
        
        return f"Used {len(experiments)} experiment(s) with tools: {', '.join(sorted(tools_used))}"
    
    def _extract_findings(self, investigation: Dict[str, Any]) -> str:
        """Extract findings summary from investigation."""
        conclusion = investigation.get("conclusion")
        if isinstance(conclusion, dict):
            return conclusion.get("summary", "Investigation complete. See full results.")
        elif isinstance(conclusion, str):
            return conclusion
        else:
            return "Investigation complete. See full results."
    
    def _extract_data_sources(self, investigation: Dict[str, Any]) -> str:
        """Extract data source citations from investigation."""
        experiments = investigation.get("experiments", [])
        sources = []
        for exp in experiments:
            result = exp.get("result", {})
            if result.get("data"):
                sources.append(f"- {exp.get('tool', 'Tool')}: {exp.get('timestamp', 'N/A')}")
        
        return "\n".join(sources) if sources else ""
    
    def _select_community_for_post(self, investigation: Dict[str, Any]) -> str:
        """Determine which community to post to based on investigation topic."""
        profile = self.agent_profile.get("profile", "mixed")
        
        # Default community based on profile
        if profile == "biology":
            return "biology"
        elif profile == "chemistry":
            return "chemistry"
        else:
            # For mixed, try to infer from tools used
            experiments = investigation.get("experiments", [])
            biology_tools = {"blast", "pubmed", "uniprot", "pdb", "sequence"}
            chemistry_tools = {"pubchem", "chembl", "tdc", "cas", "nistwebbook", "rdkit"}
            
            bio_count = sum(
                1 for exp in experiments
                if exp.get("tool") in biology_tools
            )
            chem_count = sum(
                1 for exp in experiments
                if exp.get("tool") in chemistry_tools
            )
            
            if bio_count > chem_count:
                return "biology"
            elif chem_count > bio_count:
                return "chemistry"
            else:
                return "scienceclaw"  # Mixed or unclear
    
    def _should_upvote(self, post: Dict[str, Any]) -> bool:
        """Determine if post deserves an upvote."""
        # Upvote if:
        # - Has hypothesis and findings (evidence-based)
        # - Not already upvoted by this agent
        # - Has positive karma (community approved)
        
        has_hypothesis = bool(post.get("hypothesis"))
        has_findings = bool(post.get("findings"))
        karma = post.get("karma", 0)
        
        return has_hypothesis and has_findings and karma >= 0
    
    def _should_comment(self, post: Dict[str, Any]) -> bool:
        """Determine if agent should comment on post."""
        # Comment if:
        # - Post is in agent's area of expertise
        # - Post has open questions
        # - Post methodology could be improved
        
        interests = [i.lower() for i in self.agent_profile.get("interests", [])]
        if not interests:
            return False
        
        post_text = (
            post.get("title", "") + " " +
            post.get("content", "") + " " +
            post.get("hypothesis", "")
        ).lower()
        
        # Check relevance
        relevant = any(interest in post_text for interest in interests)
        
        # Don't over-comment
        comment_count = post.get("commentCount", 0)
        
        return relevant and comment_count < 3
    
    def _generate_comment(self, post: Dict[str, Any]) -> Optional[str]:
        """Generate a thoughtful comment for a post."""
        # This is a simple implementation
        # In production, this would use GPT to generate contextual comments
        
        # For now, just acknowledge interesting findings
        findings = post.get("findings", "")
        if findings:
            return f"Interesting findings! This aligns with my research on {self.agent_profile.get('interests', ['science'])[0]}. Have you considered using additional validation tools?"
        
        return None


# Helper methods for collaborative sessions
    def _should_join_session(self, session_summary: Dict[str, Any]) -> bool:
        """Determine if agent should join a collaborative session."""
        topic = session_summary.get("topic", "").lower()
        interests = [i.lower() for i in self.agent_profile.get("interests", [])]
        
        # Join if topic matches interests
        if any(interest in topic for interest in interests):
            # Check if session has available tasks
            if session_summary.get("completed_tasks", 0) < session_summary.get("total_tasks", 0):
                return True
        
        return False
    
    def _join_and_participate(self, session_id: str):
        """Join a session and claim a task."""
        try:
            # Join session
            result = self.session_manager.join_session(session_id)
            
            if result.get("status") in ["joined", "already_joined"]:
                print(f"   Joined session: {session_id}")
                
                # Find and claim an available task
                available = self.session_manager.find_available_tasks(session_id)
                if available:
                    self._participate_in_session(session_id, available[0])
            else:
                print(f"   Could not join session: {result.get('error')}")
                
        except Exception as e:
            print(f"   Error joining session: {scrub(str(e))}")
    
    def _participate_in_session(self, session_id: str, task: Dict[str, Any]):
        """Execute a collaborative session task."""
        try:
            task_id = task["id"]
            
            # Claim task
            claim_result = self.session_manager.claim_task(session_id, task_id)
            
            if claim_result.get("status") != "claimed":
                print(f"   Could not claim task {task_id}: {claim_result.get('error')}")
                return
            
            print(f"   Claimed task: {task['description']}")
            
            # Execute task using the specified tool
            tool = task.get("tool")
            parameters = task.get("parameters", {})
            
            # Use experiment executor
            from reasoning.executor import ExperimentExecutor
            executor = ExperimentExecutor()
            
            result = executor.execute_experiment(tool, parameters)
            
            # Share result to session
            finding = {
                "task_id": task_id,
                "result": result,
                "interpretation": f"Completed task: {task['description']}",
                "tool": tool,
                "parameters": parameters
            }
            
            self.session_manager.share_to_session(session_id, finding)
            print(f"   Completed and shared task: {task_id}")
            
            # Log to journal
            self.journal.log_observation(
                content=f"Participated in collaborative session {session_id}",
                observation=f"Completed task {task_id} for collaborative investigation",
                source="collaborative_session",
                metadata={
                    "session_id": session_id,
                    "task_id": task_id,
                    "tool": tool
                }
            )
            
        except Exception as e:
            print(f"   Error participating in session: {scrub(str(e))}")


    def _run_interest_investigation(self):
        """
        Run each of the agent's preferred tools on one of its research interests,
        save the outputs as artifacts, then post a structured comment that includes:
          - Key results from each tool
          - Tool names + artifact IDs (enables chaining verification)
          - Open questions / hints for downstream agents

        Returns (investigation_id, post_id).
        """
        interests = self.agent_profile.get(
            "interests",
            self.agent_profile.get("research", {}).get("interests", [])
        )
        preferred_tools = self.agent_profile.get("preferred_tools", [])
        if not preferred_tools:
            print("   No tools configured — skipping")
            return None, None

        # Filter to only skills present in the registry (avoids "not found" skips)
        from core.skill_registry import get_registry as _get_registry
        registry_skills = set(_get_registry().skills.keys())
        available_tools = [t for t in preferred_tools if t in registry_skills]
        if not available_tools:
            print(f"   None of the preferred tools are registered — skipping")
            return None, None
        if len(available_tools) < len(preferred_tools):
            missing = set(preferred_tools) - set(available_tools)
            print(f"   Skipping unregistered tools: {sorted(missing)}")
        preferred_tools = available_tools

        # Skip re-investigation if we already posted a comment on the seed post
        # Agents with allow_reinvestigation=True in their profile bypass this guard;
        # tool rotation (random.sample) ensures each re-run fires different tools.
        if self.seed_post_id and self.platform and not self.agent_profile.get("allow_reinvestigation", False):
            try:
                resp = self.platform.get_comments(self.seed_post_id)
                comments = resp.get("comments", []) if isinstance(resp, dict) else resp
                agent_tag = f"**[{self.agent_name}]**"
                if any(agent_tag in c.get("content", "") for c in comments):
                    print(f"   Already commented on seed post — skipping re-investigation")
                    return None, None
            except Exception:
                pass

        # If demo_topic is set, override agent interests so all agents investigate it
        demo_topic = self.agent_profile.get("demo_topic", "")
        if demo_topic:
            interests = [demo_topic]
        if not interests:
            print("   No interests or demo_topic configured — skipping")
            return None, None

        # Check peer synthesis artifacts for open questions — if a peer agent
        # has flagged something specific to investigate, prioritise that as our topic.
        peer_topic = None
        try:
            from artifacts.artifact import ArtifactStore as _AS
            from pathlib import Path as _Path
            _base = _Path.home() / ".scienceclaw" / "artifacts"
            _global = _base / "global_index.jsonl"
            if _global.exists():
                _consumed_path = _base / self.agent_name / "consumed.txt"
                _consumed = set(_consumed_path.read_text().splitlines()) if _consumed_path.exists() else set()
                for _line in reversed(_global.read_text().splitlines()):
                    try:
                        _e = __import__("json").loads(_line)
                    except Exception:
                        continue
                    if _e.get("producer_agent") == self.agent_name:
                        continue
                    if _e.get("artifact_id") in _consumed:
                        continue
                    if _e.get("artifact_type") != "synthesis":
                        continue
                    # Load full artifact to get open_questions
                    _store_path = _base / _e["producer_agent"] / "store.jsonl"
                    if not _store_path.exists():
                        continue
                    for _l2 in _store_path.read_text().splitlines():
                        try:
                            _a = __import__("json").loads(_l2)
                        except Exception:
                            continue
                        if _a.get("artifact_id") != _e["artifact_id"]:
                            continue
                        _oq = _a.get("payload", {}).get("open_questions", "")
                        if not _oq:
                            break
                        # Extract first numbered question as a focused topic
                        import re as _re2
                        _qs = _re2.findall(r"\d+\.\s+(.+)", _oq)
                        if _qs:
                            peer_topic = _qs[0].strip()[:120]
                        break
                    if peer_topic:
                        break
        except Exception:
            pass

        # Rotate through interests so each heartbeat explores a different angle
        try:
            idx = len(self.journal.search("", limit=1000)) % len(interests)
        except Exception:
            idx = 0
        # demo_topic pins the investigation — never let peer questions override it
        if self.agent_profile.get("demo_topic"):
            topic = interests[idx]
        else:
            topic = peer_topic or interests[idx]
        if peer_topic and not self.agent_profile.get("demo_topic"):
            print(f"   Topic (from peer open question): {topic}")
        import re as _re
        forced_inv = (
            self.agent_profile.get("investigation_id")
            or self.agent_profile.get("investigation_id_override")
            or ""
        )
        if forced_inv:
            investigation_id = _re.sub(r"[^a-z0-9_]", "_", str(forced_inv).lower())[:60]
            print(f"   Investigation: {investigation_id} (forced)")
        else:
            investigation_id = _re.sub(r"[^a-z0-9_]", "_", topic.lower())[:40]
            print(f"   Investigation: {investigation_id}")
        print(f"   Topic: {topic}")
        # Per-cycle tool rotation: if more than 4 tools available, sample 4
        # so each round a different subset fires
        import random as _random
        if len(preferred_tools) > 4:
            preferred_tools = _random.sample(preferred_tools, 4)
        print(f"   Tools (this cycle): {preferred_tools}")

        community = self._select_community_for_topic(topic)
        disable_llm = bool(self.agent_profile.get("disable_llm", False))

        # Ask LLM once: what is the key entity for this topic, given the agent's tools?
        # Used as the default focused query for entity-specific tools.
        # Skip extraction for screening/discovery domains — there is no single entity;
        # candidates are found emergently by the screening tool itself.
        _key_entity = self.agent_profile.get("key_entity_override") or topic
        _pt = set(preferred_tools)
        _materials_tools = {"materials", "pymatgen", "ase", "nistwebbook", "materials-project"}
        _music_tools = {"motif-clustering", "midi-generator", "chord-analysis", "music-corpus"}
        _bio_tools = {"pubmed", "uniprot", "blast", "tdc", "pubchem", "chembl"}
        _is_screening_domain = bool(_pt & _materials_tools)
        _skip_key_entity_llm = bool(self.agent_profile.get("key_entity_override"))
        if not disable_llm and not _is_screening_domain and not _skip_key_entity_llm:
            try:
                from core.llm_client import get_llm_client as _get_llm
                if _pt & _music_tools and not (_pt & _bio_tools):
                    _entity_hint = "musical key, composer name, or piece title"
                else:
                    _entity_hint = (
                        "drug name, gene symbol, protein name, compound name, "
                        "or other domain-specific entity"
                    )
                _ke = _get_llm(agent_name=self.agent_name).call(
                    prompt=(
                        f"Topic: {topic}\n"
                        f"Agent tools: {', '.join(preferred_tools)}\n\n"
                        f"What is the single most specific {_entity_hint} "
                        "that this agent should search for given its tools and topic? "
                        "Reply with ONLY that entity name or formula, nothing else."
                    ),
                    max_tokens=20,
                ).strip().strip("\"'")
                if _ke and len(_ke.split()) <= 4:
                    _key_entity = _ke
            except Exception:
                pass
        if not _is_screening_domain:
            print(f"   Key entity: {_key_entity}")

        # --- Run each preferred tool and collect results + artifacts ---
        from core.skill_registry import get_registry
        from core.skill_executor import get_executor
        from artifacts.artifact import ArtifactStore

        registry = get_registry()
        executor = get_executor()
        artifact_store = ArtifactStore(agent_name=self.agent_name)

        # Candidates discovered by the `materials` screening tool within this cycle.
        # Populated when materials returns {"candidates": [...]} so that pymatgen
        # can iterate over them instead of using the hardcoded key entity.
        _discovered_material_candidates: list = []

        # ------------------------------------------------------------------
        # Deterministic "need broadcast" artifact (emergent coordination seed)
        # ------------------------------------------------------------------
        # In demo mode, a seeder can pass explicit broadcast_needs via the agent
        # profile. Persist them as an artifact early so downstream agents can
        # react even if a later tool errors or returns empty.
        try:
            broadcast_needs = self.agent_profile.get("broadcast_needs", []) or []
            if broadcast_needs and investigation_id:
                # Avoid duplicating needs broadcasts for the same (agent, inv_id)
                # across repeated heartbeats.
                already = False
                try:
                    from pathlib import Path as _PathNB
                    import json as _jsonNB
                    _gidx = _PathNB.home() / ".scienceclaw" / "artifacts" / "global_index.jsonl"
                    if _gidx.exists():
                        for _line in reversed(_gidx.read_text(encoding="utf-8").splitlines()[-400:]):
                            try:
                                _e = _jsonNB.loads(_line)
                            except Exception:
                                continue
                            if (_e.get("producer_agent") == self.agent_name
                                    and _e.get("investigation_id") == investigation_id
                                    and _e.get("needs")):
                                already = True
                                break
                except Exception:
                    already = False
                if not already:
                    artifact_store.create_and_save(
                        skill_used="_synthesis",
                        payload={
                            "event": "broadcast_needs",
                            "topic": topic,
                            "agent": self.agent_name,
                            "need_count": len(broadcast_needs),
                        },
                        investigation_id=investigation_id,
                        needs=broadcast_needs,
                    )
        except Exception:
            pass

        tool_query_overrides = self.agent_profile.get("tool_query_overrides", {}) or {}
        tool_param_overrides = self.agent_profile.get("tool_param_overrides", {}) or {}
        strict_tools = bool(self.agent_profile.get("strict_tool_results", False))

        def _is_empty_payload(payload_obj) -> bool:
            if payload_obj is None:
                return True
            if isinstance(payload_obj, dict):
                if payload_obj.get("error"):
                    return True
                if "total" in payload_obj:
                    try:
                        if int(payload_obj.get("total") or 0) <= 0:
                            return True
                    except Exception:
                        pass
                for k in ("papers", "articles", "results", "items"):
                    if k in payload_obj and isinstance(payload_obj.get(k), list) and len(payload_obj.get(k)) == 0:
                        return True
            if isinstance(payload_obj, list) and len(payload_obj) == 0:
                return True
            if isinstance(payload_obj, str) and not payload_obj.strip():
                return True
            return False

        tool_sections = []    # For the structured post
        artifact_refs = []    # (artifact_id, artifact_type, tool_name, summary)

        # Code-library skills: they expose Python APIs, not query endpoints.
        # Their demo.py scripts return availability metadata only — no scientific data.
        # Skip direct invocation; the artifact reactor can invoke them once upstream
        # SMILES/sequence data is available.
        _LIBRARY_ONLY_SKILLS = set()

        for tool_name in preferred_tools:
            if tool_name in _LIBRARY_ONLY_SKILLS:
                print(f"   {tool_name}: code-library skill — skipping direct invocation "
                      f"(requires SMILES/sequence input from a prior tool)")
                continue

            skill_meta = registry.skills.get(tool_name)
            if not skill_meta:
                print(f"   Skill '{tool_name}' not found in registry — skipping")
                continue

            # For entity-specific tools, refine the query from accumulated results if available,
            # otherwise use the key entity derived above.
            _ENTITY_TOOLS = {"chembl", "uniprot", "pdb", "pdb-database",
                             "pubchem", "string", "string-database", "kegg", "kegg-database",
                             "reactome", "reactome-database",
                             "nistwebbook", "cas", "hmdb-database",
                             "ensembl-database", "alphafold-database"}
            focused_query = _key_entity
            if tool_name in _ENTITY_TOOLS:
                # Prefer thread-aware extraction: read existing comments and ask LLM what
                # entity to use.  This avoids passing full topic sentences to entity APIs.
                _entity_type_hint = {
                    "uniprot": "protein name or UniProt accession",
                    "pdb": "PDB ID or protein name",
                    "pdb-database": "PDB ID or protein name",
                    "chembl": "drug or compound name",
                    "pubchem": "compound name or CID",
                    "string": "gene symbol",
                    "string-database": "gene symbol",
                    "kegg": "gene symbol or pathway ID",
                    "kegg-database": "gene symbol or pathway name",
                    "reactome": "gene symbol or pathway name",
                    "reactome-database": "gene symbol or pathway name",
                    "blast": "protein sequence or gene name",
                    "nistwebbook": "compound name",
                    "ensembl-database": "gene symbol (e.g. SOD1, TARDBP, FUS)",
                    "alphafold-database": "protein name or UniProt accession",
                }.get(tool_name, "entity name")
                _thread_entity = self._extract_entity_from_thread(tool_name, _entity_type_hint)
                if _thread_entity:
                    focused_query = _thread_entity
                    print(f"   Entity override for {tool_name}: {focused_query!r}")
            elif tool_name not in _ENTITY_TOOLS:
                # Discovery tools: use the LLM-extracted key entity as the query.
                # The full topic string is too noisy for database APIs.
                focused_query = _key_entity
            if tool_name in tool_query_overrides and tool_query_overrides.get(tool_name):
                focused_query = str(tool_query_overrides[tool_name])
                print(f"   Query override for {tool_name}: {focused_query!r}")

            # Build params — let the skill's own SKILL.md define what it needs;
            # we just provide the most useful query we have.
            params = {"query": focused_query}
            if tool_name == "uniprot":
                params = {"search": focused_query}
            elif tool_name == "ensembl-database":
                # ensembl_query.py uses --gene, not --query
                params = {"gene": focused_query}
            elif tool_name in ("string-database", "string"):
                # string_api.py CLI uses --query for comma/space-separated gene names
                params = {"query": focused_query}
            elif tool_name in ("reactome-database", "reactome"):
                # reactome_query.py uses positional subcommand "search <term>"
                # Executor will pass --query which the script rejects → retry logic kicks in.
                # Override here to pass query in a way the script handles gracefully.
                params = {"query": focused_query}
            elif tool_name == "chembl":
                params = {"query": focused_query, "max_results": "5"}
            elif tool_name == "askcos":
                compounds = self.agent_profile.get("research", {}).get("compounds", [])
                if not compounds:
                    print(f"   {tool_name}: no SMILES in profile — skipping")
                    continue
                params = {"smiles": compounds[0], "top": "5"}
            elif tool_name in ("tdc", "pytdc"):
                compounds = self.agent_profile.get("research", {}).get("compounds", [])
                if not compounds:
                    print(f"   {tool_name}: no SMILES in profile — skipping")
                    continue
                params = {"smiles": compounds[0]}
            elif tool_name == "rdkit":
                compounds = self.agent_profile.get("research", {}).get("compounds", [])
                compound_names = self.agent_profile.get("research", {}).get("compound_names", [])
                if not compounds:
                    continue
                # Override executables to use molecular_properties.py (JSON output, --smiles support)
                import copy as _copy
                _rdkit_meta = _copy.deepcopy(skill_meta)
                _mp = [e for e in _rdkit_meta.get("executables", [])
                       if Path(e).name == "molecular_properties.py"]
                if _mp:
                    _rdkit_meta["executables"] = _mp
                # Run RDKit on ALL compounds in the panel to produce a comparative dataset
                print(f"   Running {tool_name} panel ({len(compounds)} compounds)...", end=" ", flush=True)
                all_rows = []
                for idx_c, smi in enumerate(compounds):
                    try:
                        _r = executor.execute_skill(
                            skill_name=tool_name,
                            skill_metadata=_rdkit_meta,
                            parameters={"smiles": smi},
                            timeout=20,
                        )
                        if _r.get("status") == "success":
                            row = _r.get("result", {})
                            if isinstance(row, dict):
                                row["smiles"] = smi
                                row["compound_name"] = compound_names[idx_c] if idx_c < len(compound_names) else smi[:20]
                                all_rows.append(row)
                    except Exception:
                        pass
                if not all_rows:
                    print("no results")
                    continue
                # Save a single aggregate artifact with all rows
                import json as _json
                agg_payload = {
                    "compounds": all_rows,
                    "count": len(all_rows),
                    "compound_names": [r.get("compound_name","") for r in all_rows],
                    # Expose first compound's keys at top level for reactor matching
                    **{k: all_rows[0][k] for k in ("smiles", "compound_name") if k in all_rows[0]},
                }
                try:
                    artifact = artifact_store.create_and_save(
                        skill_used=tool_name,
                        payload=agg_payload,
                        investigation_id=investigation_id,
                    )
                    short_id = artifact.artifact_id[:12]
                    print(f"artifact {short_id}…")
                except Exception as e:
                    short_id = "n/a"
                artifact = None
                print(f"artifact save failed: {scrub(str(e))}")
                summary = self._summarise_payload(tool_name, agg_payload, topic=topic, use_llm=not disable_llm)
                if not self._is_junk_summary(summary):
                    tool_sections.append(f"**{tool_name}** (artifact `{short_id}…`)\n{summary}")
                else:
                    print(f"   ↳ {tool_name}: suppressing junk section (artifact saved for audit)")
                if artifact:
                    artifact_refs.append((artifact.artifact_id, artifact.artifact_type, tool_name, summary))
                continue  # skip the generic execute below
            elif tool_name in ("molfeat", "datamol", "medchem"):
                # SMILES-based tools — run on all compounds in the agent's panel
                compounds = self.agent_profile.get("research", {}).get("compounds", [])
                compound_names = self.agent_profile.get("research", {}).get("compound_names", [])
                if not compounds:
                    print(f"   {tool_name}: no SMILES in profile — skipping")
                    continue
                # Map tool → specific functional script (registry lists ALL scripts; we
                # must override executables to avoid running the legacy demo.py)
                _smiles_script_name = {
                    "molfeat": "molfeat_featurize.py",
                    "datamol": "datamol_process.py",
                    "medchem": "medchem_evaluate.py",
                }.get(tool_name)
                import copy as _copy
                _meta = _copy.deepcopy(skill_meta)
                _specific = [e for e in _meta.get("executables", [])
                             if Path(e).name == _smiles_script_name]
                if _specific:
                    _meta["executables"] = _specific
                elif not _meta.get("executables"):
                    print(f"   {tool_name}: no executables found — skipping")
                    continue
                print(f"   Running {tool_name} panel ({len(compounds)} compounds)...", end=" ", flush=True)
                all_rows = []
                for idx_c, smi in enumerate(compounds):
                    try:
                        _r = executor.execute_skill(
                            skill_name=tool_name,
                            skill_metadata=_meta,
                            parameters={"smiles": smi},
                            timeout=30,
                        )
                        if _r.get("status") == "success":
                            row = _r.get("result", {})
                            if isinstance(row, dict):
                                row["smiles"] = smi
                                row["compound_name"] = compound_names[idx_c] if idx_c < len(compound_names) else smi[:20]
                                all_rows.append(row)
                    except Exception:
                        pass
                if not all_rows:
                    print("no results")
                    continue
                import json as _json
                agg_payload = {
                    "compounds": all_rows,
                    "count": len(all_rows),
                    "compound_names": [r.get("compound_name", "") for r in all_rows],
                    **{k: all_rows[0][k] for k in ("smiles", "compound_name") if k in all_rows[0]},
                }
                try:
                    artifact = artifact_store.create_and_save(
                        skill_used=tool_name,
                        payload=agg_payload,
                        investigation_id=investigation_id,
                    )
                    short_id = artifact.artifact_id[:12]
                    print(f"artifact {short_id}…")
                except Exception as e:
                    short_id = "n/a"
                    artifact = None
                    print(f"artifact save failed: {scrub(str(e))}")
                summary = self._summarise_payload(tool_name, agg_payload, topic=topic, use_llm=not disable_llm)
                if not self._is_junk_summary(summary):
                    tool_sections.append(f"**{tool_name}** (artifact `{short_id}…`)\n{summary}")
                else:
                    print(f"   ↳ {tool_name}: suppressing junk section (artifact saved for audit)")
                if artifact:
                    artifact_refs.append((artifact.artifact_id, artifact.artifact_type, tool_name, summary))
                continue  # skip the generic execute below
            elif tool_name == "materials":
                # Always run in screening mode with JSON output so candidates are parseable
                params = {"screen": True, "query": focused_query, "format": "json"}
            elif tool_name == "blast":
                params = {"query": focused_query, "program": "blastp"}
            elif tool_name in ("pdb", "pdb-database"):
                params = {"query": focused_query, "limit": "3"}
            elif tool_name == "motif-clustering":
                # focused_query may be a JSON motifs blob (set by tool_query_overrides)
                # Route it to --motifs-json if it looks like JSON, otherwise use --query
                fq = focused_query.strip()
                if fq.startswith("{") or fq.startswith("["):
                    params = {"motifs_json": fq, "query": "bach"}
                else:
                    params = {"query": fq}
            elif tool_name in ("networkx", "networkx-demo"):
                # focused_query may be a JSON clusters blob — route to --input-json
                fq = focused_query.strip()
                if fq.startswith("{") or fq.startswith("["):
                    params = {"input_json": fq, "query": "music motif clusters"}
                else:
                    params = {"query": fq}
            elif tool_name == "midi-generator":
                # focused_query may be a JSON clusters blob — route to --clusters-json
                fq = focused_query.strip()
                if fq.startswith("{") or fq.startswith("["):
                    params = {"clusters_json": fq, "query": "{}"}
                else:
                    params = {"query": fq or "{}"}
            elif tool_name == "pymatgen" and not _discovered_material_candidates:
                print(f"   pymatgen: waiting for materials screening candidates — skipping")
                continue
            elif tool_name == "pymatgen" and _discovered_material_candidates:
                # Panel: run structure_analyzer.py on each screened material candidate
                import copy as _copy
                _pymatgen_meta = _copy.deepcopy(skill_meta)
                _sa = [e for e in _pymatgen_meta.get("executables", [])
                       if Path(e).name == "structure_analyzer.py"]
                if _sa:
                    _pymatgen_meta["executables"] = _sa
                top_candidates = _discovered_material_candidates[:20]
                print(f"   Running pymatgen panel ({len(top_candidates)} candidates)...", end=" ", flush=True)
                all_rows = []
                for cand in top_candidates:
                    # Prefer exact MP ID (unambiguous polymorph) over formula
                    mp_id = cand.get("material_id", "")
                    query = mp_id if mp_id else (cand.get("formula") or "")
                    if not query:
                        continue
                    try:
                        _r = executor.execute_skill(
                            skill_name=tool_name,
                            skill_metadata=_pymatgen_meta,
                            parameters={"query": query, "format": "json"},
                            timeout=45,
                        )
                        if _r.get("status") == "success":
                            row = _r.get("result", {})
                            if isinstance(row, dict):
                                row["screened_candidate"] = cand
                                all_rows.append(row)
                    except Exception:
                        pass
                if not all_rows:
                    print("no results")
                    continue
                import json as _json
                agg_payload = {
                    "structures": all_rows,
                    "count": len(all_rows),
                    "candidates_analyzed": [r.get("query", r.get("screened_candidate", {}).get("formula", "")) for r in all_rows],
                }
                try:
                    artifact = artifact_store.create_and_save(
                        skill_used=tool_name,
                        payload=agg_payload,
                        investigation_id=investigation_id,
                    )
                    short_id = artifact.artifact_id[:12]
                    print(f"artifact {short_id}…")
                except Exception as e:
                    artifact = None
                    short_id = "n/a"
                    print(f"artifact save failed: {scrub(str(e))}")
                summary = self._summarise_payload(tool_name, agg_payload, topic=topic, use_llm=not disable_llm)
                if not self._is_junk_summary(summary):
                    tool_sections.append(f"**{tool_name}** (artifact `{short_id}…`)\n{summary}")
                else:
                    print(f"   ↳ {tool_name}: suppressing junk section (artifact saved for audit)")
                if artifact:
                    artifact_refs.append((artifact.artifact_id, artifact.artifact_type, tool_name, summary))
                continue  # skip generic execute

            # Optional per-tool extra CLI params for demos (e.g. evolve_steps for esm)
            extra_params = tool_param_overrides.get(tool_name)
            if isinstance(extra_params, dict) and extra_params:
                try:
                    params = {**params, **extra_params}
                except Exception:
                    pass

            # Pre-execution dedup: if a peer already ran this exact tool in this
            # investigation, skip — output will be identical and saves API/compute cost.
            # Exempt tools that feed downstream within this cycle (materials→pymatgen chain).
            # materials is exempt only if this agent also uses pymatgen (needs it to populate candidate panel)
            _needs_materials_for_panel = "pymatgen" in preferred_tools
            _CYCLE_FEED_TOOLS = {"pymatgen", "pubmed", "arxiv", "openalex-database"}
            if _needs_materials_for_panel:
                _CYCLE_FEED_TOOLS.add("materials")
            _pre_skip = False
            if tool_name not in _CYCLE_FEED_TOOLS:
                try:
                    _gidx_pre = Path.home() / ".scienceclaw" / "artifacts" / "global_index.jsonl"
                    if _gidx_pre.exists():
                        import json as _json_pre
                        for _gl in _gidx_pre.read_text(encoding="utf-8").splitlines():
                            try:
                                _ge = _json_pre.loads(_gl)
                            except Exception:
                                continue
                            if (_ge.get("skill_used") == tool_name
                                    and _ge.get("investigation_id") == investigation_id
                                    and _ge.get("producer_agent") != self.agent_name):
                                print(f"   {tool_name}: peer {_ge.get('producer_agent','?')} already ran this — skipping")
                                _pre_skip = True
                                break
                except Exception:
                    pass
            if _pre_skip:
                continue

            print(f"   Running {tool_name}...", end=" ", flush=True)
            try:
                result = executor.execute_skill(
                    skill_name=tool_name,
                    skill_metadata=skill_meta,
                    parameters=params,
                    timeout=45,
                )
            except Exception as e:
                print(f"error: {scrub(str(e))}")
                if strict_tools:
                    raise
                continue

            if result.get("status") != "success":
                print(f"failed ({result.get('error','unknown')})")
                if strict_tools:
                    raise RuntimeError(f"{tool_name} failed: {result.get('error','unknown')}")
                continue

            payload = result.get("result", {})

            # If materials screening returned candidates, store for pymatgen panel
            if (tool_name == "materials" and isinstance(payload, dict)
                    and isinstance(payload.get("candidates"), list)
                    and payload["candidates"]):
                _discovered_material_candidates = payload["candidates"]
                print(f"   ↳ Discovered {len(_discovered_material_candidates)} material candidates for pymatgen panel")

            if not isinstance(payload, dict):
                raw = str(payload)
                # Build structured payload so the artifact reactor can match keys
                # against downstream skill --params (e.g. "query" matches --query,
                # "accession" matches --accession).
                structured: dict = {"output": raw[:500], "raw": raw}
                # Carry forward the query that produced this artifact so any skill
                # accepting --query / --search can react to it.
                if params.get("query"):
                    structured["query"]  = params["query"]
                    structured["search"] = params["query"]
                # Extract UniProt accessions  (e.g. P00533)
                import re as _re
                accs = _re.findall(r'\b[OPQ][0-9][A-Z0-9]{3}[0-9]\b|'
                                   r'\b[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2}\b',
                                   raw)
                if accs:
                    structured["accession"] = accs[0]
                # Extract PDB IDs  (4-char alphanumeric like 1ATP, 6W63)
                pdbs = _re.findall(r'\b[0-9][A-Z0-9]{3}\b', raw)
                if pdbs:
                    structured["pdb_id"] = pdbs[0]
                # Extract SMILES-like strings (contains C/N/O + = or ( characters)
                smiles_cands = _re.findall(r'[A-Za-z][A-Za-z0-9@\[\]()=#\+\-]{6,}', raw)
                smiles_cands = [s for s in smiles_cands if any(c in s for c in '()=#')]
                if smiles_cands:
                    structured["smiles"] = smiles_cands[0]
                payload = structured

            # Save artifact
            try:
                rq = "empty" if _is_empty_payload(payload) else "ok"
                artifact = artifact_store.create_and_save(
                    skill_used=tool_name,
                    payload=payload,
                    investigation_id=investigation_id,
                    result_quality=rq,
                )
                short_id = artifact.artifact_id[:12]
                print(f"artifact {short_id}…")
            except Exception as e:
                print(f"artifact save failed: {scrub(str(e))}")
                short_id = "n/a"
                artifact = None
                if strict_tools:
                    raise
            if strict_tools and _is_empty_payload(payload):
                raise RuntimeError(f"{tool_name} returned empty results for query={focused_query!r}")

            # Cross-agent duplicate check: if another agent already produced the same
            # content (same content_hash) within the same investigation, skip it.
            # Different investigations are independent — no cross-investigation dedup.
            # Same-agent re-runs are always allowed (agent posts its own findings).
            _duplicate = False
            if artifact:
                try:
                    from pathlib import Path as _Path2
                    _gidx = _Path2.home() / ".scienceclaw" / "artifacts" / "global_index.jsonl"
                    if _gidx.exists():
                        import json as _json2
                        for _gline in _gidx.read_text().splitlines():
                            try:
                                _ge = _json2.loads(_gline)
                            except Exception:
                                continue
                            if (_ge.get("content_hash") == artifact.content_hash
                                    and _ge.get("artifact_id") != artifact.artifact_id
                                    and _ge.get("producer_agent") != self.agent_name
                                    and _ge.get("investigation_id") == investigation_id):
                                _duplicate = True
                                print(f"   ↳ {tool_name}: content_hash already in this investigation "
                                      f"(producer={_ge.get('producer_agent','?')}) — skipping section")
                                break
                except Exception:
                    pass

            # Extract a 1-2 line human-readable summary from payload
            summary = self._summarise_payload(tool_name, payload, topic=topic, use_llm=not disable_llm)
            if not _duplicate and not self._is_junk_summary(summary):
                tool_sections.append(f"**{tool_name}** (artifact `{short_id}…`)\n{summary}")
            elif _duplicate:
                pass  # artifact_refs still appended below for audit
            else:
                print(f"   ↳ {tool_name}: suppressing junk section (artifact saved for audit)")
            if artifact:
                artifact_refs.append((artifact.artifact_id, artifact.artifact_type, tool_name, summary))

        if not tool_sections:
            print("   No tools produced results")
            return investigation_id, None

        # --- Build structured post body ---
        # Open questions: LLM-generated from actual findings, not mechanical interest subtraction
        hints = "- None identified"
        if not disable_llm:
            try:
                from autonomous.llm_reasoner import LLMScientificReasoner
                reasoner = LLMScientificReasoner(self.agent_name)
                findings_text = "\n".join(tool_sections)[:1200]
                prompt = (
                    f"Research topic: {topic}\n\n"
                    f"Findings so far:\n{findings_text}\n\n"
                    "Based on these specific findings, list 2-3 concrete open questions "
                    "that a peer agent with different computational tools (e.g. structure prediction, ADMET, "
                    "literature search, sequence analysis) could investigate next. Each question should reference "
                    "something specific found above (a compound name, protein, mechanism, etc). "
                    "All questions must be answerable computationally — do NOT suggest wet-lab experiments, "
                    "assays, or any physical/biological testing. "
                    "Output as a numbered list (1. 2. 3.). No preamble."
                )
                raw = reasoner._call_llm(prompt, max_tokens=400).strip()
                if raw:
                    hints = raw
            except Exception:
                pass

        # Save a synthesis artifact containing open_questions so peer agents
        # can read them via the artifact reactor and use them as investigation topics.
        try:
            broadcast_needs = self.agent_profile.get("broadcast_needs", []) or []
            synthesis_payload = {
                "open_questions": hints,
                "topic": topic,
                "agent": self.agent_name,
                "artifact_count": len(artifact_refs),
                # First question as a short query field for reactor key-matching
                "query": hints.splitlines()[0].lstrip("1. ").lstrip("- ")[:120] if hints else topic,
            }
            artifact_store.create_and_save(
                skill_used="_synthesis",
                payload=synthesis_payload,
                investigation_id=investigation_id,
                needs=broadcast_needs,
            )
        except Exception:
            pass

        artifact_lines = "\n".join(
            f"- `{aid[:12]}…` ({atype}) via {tname}" for aid, atype, tname, _ in artifact_refs
        )

        body = (
            f"## Results\n"
            + "\n\n".join(tool_sections)
            + f"\n\n## Artifacts\n{artifact_lines if artifact_lines else '— none saved'}"
            + f"\n\n## Open Questions for Downstream Agents\n\n**What should be investigated next:**\n\n{hints}"
        )

        post_id = self._post_investigation_content(
            {"title": topic, "content": body}, community
        )

        self.journal.log_observation(
            content=f"Ran {len(tool_sections)} tool(s) on: {topic}",
            observation=f"Skill-chain investigation on '{topic}'",
            source="skill_chain_investigation",
            metadata={"topic": topic, "post_id": post_id,
                      "artifacts": [a[0] for a in artifact_refs]},
        )
        return investigation_id, post_id

    def _extract_entity_from_thread(self, skill_name: str, entity_type: str) -> Optional[str]:
        """
        Read seed post comments, ask LLM to return JSON {entity: <name>},
        validate with EntityQuery Pydantic model.
        Returns clean entity string or None.
        """
        if self.agent_profile.get("disable_llm"):
            return None
        if not self.seed_post_id or not self.platform:
            return None
        try:
            resp = self.platform.get_comments(self.seed_post_id)
            comments = resp.get("comments", []) if isinstance(resp, dict) else resp
            if not comments:
                return None
            context = "\n---\n".join(
                c.get("content", "")[:200] for c in comments[-5:]
            )
            prompt = (
                f"These are comments from a multi-agent scientific investigation:\n\n"
                f"{context}\n\n"
                f"Extract the single best {entity_type} to query '{skill_name}' with.\n"
                f"Respond with ONLY valid JSON in this exact format:\n"
                f'{{\"entity\": \"<name>\"}}\n'
                f"Example: {{\"entity\": \"TP53\"}} or {{\"entity\": \"APR-246\"}}"
            )
            from core.llm_client import get_llm_client
            _client = get_llm_client(agent_name=self.agent_name)
            raw = _client.call(prompt=prompt, max_tokens=60).strip()
            m = re.search(r'\{[^}]+\}', raw)
            if not m:
                return None
            data = json.loads(m.group())
            result = EntityQuery(**data)
            return result.entity
        except Exception:
            return None

    _JUNK_PHRASES = [
        "did not return any", "nothing scientifically meaningful", "too broad",
        "entirely of unrelated", "does not contain any scientifically",
        "not return any specific", "failed to retrieve relevant",
        "no scientifically meaningful",
        "cannot connect to askcos", "start a local deployment",
        "requires authentication",
    ]

    def _is_junk_summary(self, text: str) -> bool:
        t = text.lower()
        return any(phrase in t for phrase in self._JUNK_PHRASES)

    def _summarise_payload(self, tool_name: str, payload: dict,
                           topic: str = "", use_llm: bool = True) -> str:
        """Return a 1-3 line human-readable summary of a skill output payload.

        Tries known structured extractors first; falls back to an LLM call
        that reads the actual payload and extracts scientific meaning rather
        than dumping raw scalar keys.
        """
        lines = []
        # Tool-specific key extraction for common structured outputs
        if tool_name == "askcos":
            if payload.get("error"):
                return payload["error"]
            suggestions = payload.get("suggestions", [])
            total = payload.get("total_templates_matched", 0)
            target = payload.get("target", "")
            model = payload.get("model", "reaxys")
            if suggestions:
                lines.append(
                    f"ASKCOS ({model}): {total} templates matched for {target}"
                )
                for s in suggestions[:5]:
                    reagent = f" [reagent: {s['necessary_reagent']}]" if s.get("necessary_reagent") else ""
                    lines.append(
                        f"  #{s['rank']} score={s['score']:.4f} "
                        f"(n={s['template_count']}) → {s['reactants_smiles']}{reagent}"
                    )
            elif total == 0:
                return f"ASKCOS ({model}): no templates matched for {target}"
        elif tool_name in ("pubmed", "openalex-database", "arxiv", "semantic-scholar"):
            papers = (
                payload.get("papers") or payload.get("articles")
                or payload.get("items") or payload.get("results") or []
            )
            total = payload.get("total") or payload.get("count") or len(papers)
            if papers and isinstance(papers[0], dict):
                titles = [p.get("title", "")[:80] for p in papers[:3] if p.get("title")]
                if titles:
                    lines.append(f"{total} paper(s). Top: {'; '.join(titles)}")
        elif tool_name in ("uniprot", "uniprot_fetch"):
            acc = payload.get("primaryAccession") or payload.get("accession") or payload.get("id", "")
            name = (payload.get("proteinDescription", {}) or {})
            name = (name.get("recommendedName", {}) or {}).get("fullName", {})
            name = (name.get("value", "") if isinstance(name, dict) else "") or payload.get("protein_name", "")
            gene = ""
            genes = payload.get("genes", [])
            if genes and isinstance(genes[0], dict):
                gene = genes[0].get("geneName", {}).get("value", "")
            if acc:
                lines.append(f"{acc} ({gene or 'unknown gene'}) — {name or 'protein'}")
        elif tool_name in ("tdc", "pytdc"):
            preds = payload.get("predictions") or payload.get("results") or {}
            score = payload.get("score")
            if preds:
                lines.append(f"Predictions: {str(preds)[:120]}")
            elif score is not None:
                lines.append(f"Score: {score}")
        elif tool_name == "rdkit":
            rows = payload.get("compounds", [])
            if rows:
                # Multi-compound panel
                lines.append(f"{len(rows)} compounds profiled:")
                for row in rows[:5]:
                    name = row.get("compound_name", row.get("smiles","")[:15])
                    mw = row.get("Molecular Weight") or row.get("molecular_weight") or row.get("MW","?")
                    logp = row.get("LogP") or row.get("logP") or row.get("MolLogP","?")
                    qed = row.get("QED Score") or row.get("QED") or row.get("qed", "?")
                    lines.append(f"  {name}: MW={mw}, logP={logp}, QED={qed}")
            else:
                mw = payload.get("Molecular Weight") or payload.get("molecular_weight") or payload.get("MW")
                logp = payload.get("LogP") or payload.get("logP") or payload.get("MolLogP")
                qed = payload.get("QED Score") or payload.get("QED") or payload.get("qed")
                if mw:
                    lines.append(f"MW={mw}, logP={logp}, QED={qed}")
        elif tool_name == "pubchem":
            cid = payload.get("cid") or (payload.get("compounds") or [{}])[0].get("cid", "")
            name = payload.get("name") or payload.get("iupac_name", "")
            smiles = payload.get("canonical_smiles") or payload.get("smiles", "")
            if cid:
                lines.append(f"CID {cid} — {name}" + (f" | SMILES: {smiles[:60]}" if smiles else ""))
        elif tool_name in ("pdb", "pdb-database"):
            structs = payload.get("structures") or payload.get("hits") or payload.get("items") or []
            if structs and isinstance(structs[0], dict):
                ids = [s.get("pdb_id") or s.get("id", "") for s in structs[:3] if s]
                lines.append(f"{len(structs)} structure(s): {', '.join(i for i in ids if i)}")
            else:
                lines.append(f"{len(structs)} structure(s) found")
        elif tool_name == "blast":
            hits = payload.get("hits") or []
            if hits and isinstance(hits[0], dict):
                top = hits[0]
                lines.append(f"{len(hits)} hit(s). Top: {top.get('id','')} "
                              f"identity={top.get('identity','?')}% e={top.get('evalue','?')}")
            else:
                lines.append(f"{len(hits)} BLAST hit(s)")
        elif tool_name == "pymatgen":
            # Panel output: {"structures": [...], "count": N, "candidates_analyzed": [...]}
            structs = payload.get("structures") or []
            count = payload.get("count") or len(structs)
            if structs:
                lines.append(f"Structural analysis of {count} ceramic candidate(s):")
                for row in structs[:8]:
                    cand = row.get("screened_candidate", {})
                    formula = (row.get("composition", {}) or {}).get("reduced_formula") \
                              or cand.get("formula") or row.get("query", "?")
                    mp_id = cand.get("material_id", "")
                    mp_str = f" [{mp_id}]" if mp_id else ""
                    density = (row.get("lattice", {}) or {}).get("density") \
                              or cand.get("density", "?")
                    sg = (row.get("symmetry", {}) or {}).get("spacegroup_symbol", "?")
                    crystal = (row.get("symmetry", {}) or {}).get("crystal_system", "")
                    bm = cand.get("band_gap")
                    bm_str = f", band_gap={bm:.2f} eV" if bm is not None else ""
                    lines.append(
                        f"  {formula}{mp_str}: density={density:.3f} g/cm³, "
                        f"space group={sg} ({crystal}){bm_str}"
                    )
            elif payload.get("candidates_analyzed"):
                lines.append(f"Analyzed: {', '.join(payload['candidates_analyzed'][:5])}")
        elif tool_name == "materials":
            # Screening output: {"candidates": [...], "total_screened": N}
            cands = payload.get("candidates") or []
            total = payload.get("total_screened") or len(cands)
            filters = payload.get("filters") or {}
            if cands:
                lines.append(
                    f"Screened {total} ceramic candidates "
                    f"(density ≤ {filters.get('max_density','?')} g/cm³, "
                    f"band_gap ≥ {filters.get('min_band_gap','?')} eV):"
                )
                for c in cands[:8]:
                    lines.append(
                        f"  {c.get('formula','?')} [{c.get('material_id','?')}] — "
                        f"density={c.get('density','?')} g/cm³, "
                        f"band_gap={c.get('band_gap','?')} eV, "
                        f"sg={c.get('spacegroup','?')}"
                    )
        elif tool_name == "chembl":
            items = payload.get("molecules") or payload.get("items") or payload.get("results") or []
            if not items and payload.get("molecule_chembl_id"):
                items = [payload]
            if isinstance(items, list) and items and isinstance(items[0], dict):
                for item in items[:3]:
                    name = item.get("pref_name") or item.get("molecule_chembl_id", "")
                    props = item.get("molecule_properties") or {}
                    mw = props.get("full_mwt") or props.get("mw_freebase") or props.get("molecular_weight", "?")
                    logp = props.get("alogp") or props.get("cx_logp", "?")
                    qed = props.get("qed_weighted", "?")
                    if mw == "?" and logp == "?" and qed == "?":
                        continue
                    phase = item.get("max_phase", "?")
                    smiles = (item.get("molecule_structures") or {}).get("canonical_smiles", "")[:50]
                    lines.append(f"**{name}** — MW={mw}, logP={logp}, QED={qed}, phase={phase}"
                                 + (f"\n  SMILES: `{smiles}…`" if smiles else ""))

        elif tool_name == "pymc":
            model = payload.get("model", "BayesianModel")
            n = payload.get("n_observations", "?")
            xlbl = payload.get("x_label", "x")
            ylbl = payload.get("y_label", "y")
            post = payload.get("posterior", {})
            slope = post.get("slope_mean")
            ci_lo = payload.get("alpha_lower") or (payload.get("credible_interval") or [None])[0]
            ci_hi = payload.get("alpha_upper") or (payload.get("credible_interval") or [None, None])[1]
            topic_str = payload.get("topic", "")
            intercept = post.get("intercept_mean")
            if slope is not None:
                lines.append(
                    f"{model} ({n} obs): slope={slope:.4f} "
                    f"[95% CI {ci_lo:.4f}–{ci_hi:.4f}], intercept={intercept:.4f} "
                    f"({xlbl} → {ylbl})"
                    + (f" — topic: {topic_str}" if topic_str else "")
                )
            elif topic_str:
                lines.append(f"Bayesian model fit for: {topic_str} ({n} obs)")

        elif tool_name in ("datavis", "scientific-visualization"):
            fig = payload.get("figure_path") or (payload.get("files") or [""])[0]
            n = payload.get("n", "?")
            topic_str = payload.get("topic", "")
            if fig:
                lines.append(f"Figure saved: {fig} (n={n})" + (f" — {topic_str}" if topic_str else ""))
            elif topic_str:
                lines.append(f"Visualization generated for: {topic_str} (n={n})")

        # If structured extraction yielded nothing, use LLM for any tool
        if not lines and use_llm:
            try:
                from autonomous.llm_reasoner import LLMScientificReasoner
                reasoner = LLMScientificReasoner(self.agent_name)
                # Serialize payload concisely — drop huge lists, keep first 3 items
                import json as _json
                def _trim(obj, depth=0):
                    if depth > 2: return "…"
                    if isinstance(obj, list): return [_trim(x, depth+1) for x in obj[:3]]
                    if isinstance(obj, dict): return {k: _trim(v, depth+1) for k, v in list(obj.items())[:10]}
                    return obj
                payload_preview = _json.dumps(_trim(payload), ensure_ascii=False)[:2500]
                prompt = (
                    f"You are a scientific research assistant. An agent ran the tool '{tool_name}'"
                    + (f" on topic '{topic}'" if topic else "") + ".\n\n"
                    f"Tool output (JSON):\n{payload_preview}\n\n"
                    "Write 2-3 complete sentences summarising the scientifically interesting findings. "
                    "Be specific: mention compound names, protein IDs, scores, mechanisms, or binding data if present. "
                    "Always finish your last sentence with a period. "
                    "Do NOT mention metadata fields like availability_type, black_box_warning, etc. "
                    "If there is nothing scientifically meaningful, say so in one sentence."
                )
                summary = reasoner._call_llm(prompt, max_tokens=350).strip()
                if summary:
                    lines.append(summary)
            except Exception:
                pass

        # Last resort: note what was empty rather than dumping noise
        if not lines:
            lines.append(f"(Tool returned data but no scientifically extractable values)")
        return "\n".join(lines)

    def _select_community_for_topic(self, topic: str) -> str:
        """Pick the most appropriate community for a given topic string."""
        t = topic.lower()
        if any(w in t for w in ["protein", "gene", "sequence", "blast", "uniprot", "pdb", "alphafold"]):
            return "biology"
        if any(w in t for w in ["compound", "smiles", "admet", "drug", "inhibitor", "warhead",
                                  "kinase", "scaffold", "chembl", "rdkit", "pubchem"]):
            return "chemistry"
        profile = self.agent_profile.get("profile", "mixed")
        return "biology" if profile == "biology" else "chemistry"

    def _post_investigation_content(self, content: dict, community: str) -> Optional[str]:
        """Post deep-investigation content as a comment (seed mode) or new post."""
        if not self.platform:
            return None
        try:
            title = content.get("title", "Findings")
            body = content.get("content", "")
            if self.seed_post_id:
                print(f"   Commenting on seed post {self.seed_post_id[:12]}...")
                comment_body = f"**[{self.agent_name}]** — *{title}*\n\n{body}"
                result = self.platform.create_comment(
                    post_id=self.seed_post_id,
                    content=comment_body,
                )
                return (
                    result.get("id")
                    or result.get("comment_id")
                    or result.get("comment", {}).get("id")
                )
            else:
                print(f"   Posting to m/{community}...")
                result = self.platform.create_post(
                    title=title,
                    content=body,
                    community=community,
                    hypothesis=content.get("hypothesis", ""),
                    method=content.get("method", ""),
                    findings=content.get("findings", ""),
                )
                return (
                    result.get("id")
                    or result.get("post_id")
                    or result.get("post", {}).get("id")
                )
        except Exception as e:
            print(f"   Warning: Failed to post findings: {scrub(str(e))}")
            return None

    def _post_reaction_findings(self, children: List) -> None:
        """Post a consolidated finding for a batch of reaction artifacts."""
        try:
            from artifacts.reactor import summarise_reactions
            result_summary = summarise_reactions(children)
            session_id = self._get_or_create_reaction_session()
            if session_id:
                self.session_manager.post_finding(
                    session_id=session_id,
                    result=result_summary,
                    artifact_ids=[c.artifact_id for c in children],
                    confidence=0.7,
                )
        except Exception as e:
            print(f"   Warning: Failed to post reaction findings: {scrub(str(e))}")

    def _get_or_create_reaction_session(self) -> Optional[str]:
        """Return an active session_id to attach reaction findings to, or None."""
        try:
            sessions = self.session_manager.list_active_sessions()
            if sessions:
                return sessions[0]["id"]
        except Exception:
            pass
        return None

    def _synthesize_from_fulfillments(self, fulfillments: List) -> None:
        """
        Synthesize insights from a batch of fulfillment artifacts and post a
        comment on the original post if one can be identified.

        Steps:
        1. Bucket the new artifacts into papers / proteins / compounds based
           on their artifact_type.
        2. Call llm_reasoner.generate_insights() on the bucketed data.
        3. Emit a new synthesis artifact (with updated needs) to the artifact store.
        4. Post a comment on the original post that triggered the investigation,
           if the original post_id can be resolved from the parent investigation.

        Args:
            fulfillments: List of Artifact objects that have _fulfilled_need in
                their payload.
        """
        if not fulfillments:
            return
        if self.agent_profile.get("disable_llm"):
            return

        try:
            from autonomous.llm_reasoner import LLMScientificReasoner
            reasoner = LLMScientificReasoner(self.agent_name)
        except Exception as e:
            print(f"   Note: LLM reasoner unavailable for fulfillment synthesis ({scrub(str(e))})")
            return

        # --- Bucket artifacts by type ---
        papers: List[Dict[str, Any]] = []
        proteins: List[Dict[str, Any]] = []
        compounds: List[Dict[str, Any]] = []

        for art in fulfillments:
            atype = art.artifact_type
            payload = art.payload
            if atype == "pubmed_results":
                art_papers = payload.get("papers") or payload.get("articles") or []
                if isinstance(art_papers, list):
                    papers.extend(art_papers[:3])
                else:
                    papers.append({"title": str(art_papers)[:100]})
            elif atype in ("protein_data", "sequence_alignment", "structure_data"):
                name = (payload.get("protein_name") or payload.get("name") or
                        payload.get("primaryAccession") or payload.get("id", ""))
                info = payload.get("function") or payload.get("annotation") or ""
                proteins.append({"name": name, "info": str(info)[:200], "source": art.skill_used})
            elif atype in ("compound_data", "admet_prediction", "rdkit_properties", "drug_data"):
                name = payload.get("name") or payload.get("iupac_name") or payload.get("id", "")
                compounds.append({"name": name, "info": str(payload.get("smiles", ""))[:80],
                                  "source": art.skill_used})

        # Derive a shared topic from the fulfilled needs
        topics = []
        for art in fulfillments:
            fn = art.payload.get("_fulfilled_need", {})
            q = fn.get("query", "")
            if q:
                topics.append(q)
        synthesis_topic = "; ".join(topics[:2]) if topics else "fulfillment synthesis"

        inv_results: Dict[str, Any] = {
            "topic": synthesis_topic,
            "papers": papers,
            "proteins": proteins,
            "compounds": compounds,
            "tools_used": list({art.skill_used for art in fulfillments}),
            "insights": [],
        }

        # Generate insights from the bucketed data
        try:
            insights = reasoner.generate_insights(synthesis_topic, inv_results)
        except Exception as e:
            print(f"   Note: insight generation failed ({scrub(str(e))})")
            insights = []

        inv_results["insights"] = insights

        # Generate updated needs from the synthesized results
        try:
            new_needs = reasoner.generate_needs(synthesis_topic, inv_results)
        except Exception as e:
            print(f"   Note: needs generation failed ({scrub(str(e))})")
            new_needs = []

        # Emit a synthesis artifact with updated needs
        try:
            synthesis_payload = {
                "topic": synthesis_topic,
                "source": "fulfillment_synthesis",
                "fulfilled_artifact_ids": [art.artifact_id for art in fulfillments],
                "paper_count": len(papers),
                "protein_count": len(proteins),
                "compound_count": len(compounds),
                "insights": insights[:3],
                "query": synthesis_topic[:120],
            }
            # Use investigation_id from first fulfillment artifact if available
            inv_id = fulfillments[0].investigation_id if fulfillments else ""
            self._artifact_store.create_and_save(
                skill_used="_synthesis",
                payload=synthesis_payload,
                investigation_id=inv_id,
                needs=new_needs,
            )
            print(f"   Synthesis artifact emitted (needs={len(new_needs)})")
        except Exception as e:
            print(f"   Note: synthesis artifact save failed ({scrub(str(e))})")

        # Post a comment on the original post if we can identify it
        if not insights:
            return

        try:
            # Resolve original post_id from parent investigation via journal
            parent_artifact_ids = [
                art.payload.get("_fulfilled_need", {}).get("parent_artifact_id", "")
                for art in fulfillments
            ]
            # Look up parent investigation in journal for an associated post_id
            parent_post_id = None
            try:
                recent_entries = self.journal.search("", limit=200)
                for entry in reversed(recent_entries):
                    meta = entry.get("metadata", {})
                    for pid in parent_artifact_ids:
                        if pid and pid in str(meta.get("artifacts", "")):
                            parent_post_id = meta.get("post_id")
                            if parent_post_id:
                                break
                    if parent_post_id:
                        break
            except Exception:
                pass

            if not parent_post_id:
                # No original post found — skip comment
                return

            insight_text = "\n".join(f"- {ins}" for ins in insights[:3])
            comment_body = (
                f"**[{self.agent_name} — Fulfillment Synthesis]**\n\n"
                f"Following up on the investigation of *{synthesis_topic}*, "
                f"I retrieved {len(fulfillments)} requested artifact(s) and synthesised:\n\n"
                f"{insight_text}"
            )
            self.platform.create_comment(
                post_id=parent_post_id,
                content=comment_body,
            )
            print(f"   Comment posted on original post {parent_post_id[:12]}...")
        except Exception as e:
            print(f"   Note: fulfillment comment failed ({scrub(str(e))})")


# Test function for development
def test_loop_controller():
    """Test the autonomous loop controller with a sample profile."""
    
    sample_profile = {
        "name": "TestAgent",
        "bio": "Test agent for autonomous loop",
        "profile": "mixed",
        "interests": ["protein structure", "drug discovery"],
        "preferred_tools": ["blast", "pubmed", "tdc", "pubchem"],
        "curiosity_style": "systematic",
        "communication_style": "technical"
    }
    
    controller = AutonomousLoopController(sample_profile)
    
    print("\nTesting individual methods:\n")
    
    # Test observe_community
    print("1. Testing observe_community()...")
    gaps = controller.observe_community()
    print(f"   Found {len(gaps)} gaps\n")
    
    # Test generate_hypotheses
    if gaps:
        print("2. Testing generate_hypotheses()...")
        hypotheses = controller.generate_hypotheses(gaps[:2])
        print(f"   Generated {len(hypotheses)} hypotheses\n")
        
        # Test select_hypothesis
        if hypotheses:
            print("3. Testing select_hypothesis()...")
            selected = controller.select_hypothesis(hypotheses)
            print(f"   Selected: {selected}\n")
    
    print("✓ Loop controller test complete")


if __name__ == "__main__":
    test_loop_controller()
