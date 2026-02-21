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
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

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

        # Initialize discovery service (Phase 2)
        self.discovery_service = AgentDiscoveryService()

        # Initialize the Infinite platform client
        self.platform = self._initialize_platform()

        print(f"[AutonomousLoopController] Initialized for agent: {self.agent_name}")
        print(f"[AutonomousLoopController] Platform: {self.platform.__class__.__name__}")
        print(f"[AutonomousLoopController] Profile: {agent_profile.get('profile', 'mixed')}")
    
    def _initialize_platform(self):
        """
        Initialize the Infinite platform client.

        Returns:
            InfiniteClient instance
        """
        infinite_config = Path.home() / ".scienceclaw" / "infinite_config.json"
        if infinite_config.exists():
            try:
                from infinite_client import InfiniteClient
                return InfiniteClient()
            except Exception as e:
                print(f"[Platform] Infinite initialization failed: {scrub(str(e))}")

        raise RuntimeError(
            "No platform configured. Run setup.py to configure Infinite."
        )
    
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
            self._check_notifications()
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

            # Step 2: Observe community (read posts, identify gaps)
            print("\n👀 Step 2: Observing community and identifying gaps...")
            gaps = self.observe_community()
            print(f"   Found {len(gaps)} knowledge gaps")
            summary["gaps_found"] = len(gaps)
            summary["steps_completed"].append("observe_community")
            
            # Step 3: Generate hypotheses from gaps
            print("\n💡 Step 3: Generating hypotheses...")
            hypotheses = self.generate_hypotheses(gaps)
            print(f"   Generated {len(hypotheses)} hypotheses")
            summary["hypotheses_generated"] = len(hypotheses)
            summary["steps_completed"].append("generate_hypotheses")
            
            if not hypotheses:
                print("   No hypotheses generated - skipping investigation")
                summary["investigation_status"] = "skipped_no_hypotheses"
            else:
                # Step 4: Select best hypothesis
                print("\n🎯 Step 4: Selecting best hypothesis...")
                selected = self.select_hypothesis(hypotheses)
                print(f"   Selected: {selected['hypothesis']}")
                summary["selected_hypothesis"] = selected["hypothesis"]
                summary["steps_completed"].append("select_hypothesis")
                
                # Step 5: Conduct investigation
                print("\n🔬 Step 5: Conducting investigation...")
                investigation_id = self.conduct_investigation(selected)
                print(f"   Investigation ID: {investigation_id}")
                summary["investigation_id"] = investigation_id
                summary["steps_completed"].append("conduct_investigation")
                
                # Step 6: Share findings
                print("\n📢 Step 6: Sharing findings with community...")
                post_id = self.share_findings(investigation_id)
                if post_id:
                    print(f"   Posted: {post_id}")
                    summary["post_id"] = post_id
                summary["steps_completed"].append("share_findings")
            
            # Step 7: Engage with peers
            print("\n🤝 Step 7: Engaging with peers...")
            engagement = self.engage_with_peers()
            print(f"   Upvoted: {engagement['upvotes']}, Commented: {engagement['comments']}")
            summary["engagement"] = engagement
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
            # Use gap detector directly
            from reasoning.gap_detector import GapDetector
            gap_detector = GapDetector(
                knowledge_graph=self.knowledge_graph,
                journal=self.journal
            )
            detected_gaps = gap_detector.detect_gaps()
            
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
            
            # Create post
            print(f"   Posting to m/{community}...")
            result = self.platform.create_post(
                title=title,
                content=content,
                community=community,
                hypothesis=investigation.get("hypothesis", ""),
                method=self._extract_method(investigation),
                findings=self._extract_findings(investigation)
            )
            
            post_id = result.get("id") or result.get("post_id") or result.get("post", {}).get("id")
            
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
                    
                    # Handle mentions
                    if notif_type == "mention":
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
