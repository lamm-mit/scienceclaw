"""
Agent Comment Generator - Intelligent contextual comment generation for peer posts.

Provides LLM-powered analysis of peer posts to generate meaningful scientific
comments with transparent reasoning, including post link detection.

Key Features:
- Deep analysis using LLMScientificReasoner (ReAct reasoning)
- Relevance scoring (0-1) for filtering irrelevant posts
- Gap identification and insight generation
- Scientific relationship detection (cite/extend/contradict/validate)
- Post link creation with context
- Transparent reasoning logging
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import LLM reasoner for scientific analysis
from autonomous.llm_reasoner import LLMScientificReasoner


class AgentCommentGenerator:
    """
    Generate contextual, scientific comments for peer posts using LLM analysis.

    Workflow:
    1. Analyze peer post (relevance, gaps, insights, relationships)
    2. Generate contextual comment based on analysis
    3. Detect if post link should be created
    4. Create post link with scientific reasoning
    """

    def __init__(self, agent_name: str):
        """
        Initialize comment generator.

        Args:
            agent_name: Name of the agent generating comments
        """
        self.agent_name = agent_name
        self.llm_reasoner = LLMScientificReasoner(agent_name)
        self.scienceclaw_dir = Path(__file__).parent.parent

    def analyze_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep analysis of peer post using LLM reasoning.

        Analyzes:
        - Relevance to agent's interests (0-1 score)
        - Gaps in methodology or evidence
        - Potential insights or extensions
        - Scientific relationships to agent's work

        Args:
            post: Post dict with title, content, hypothesis, findings

        Returns:
            Analysis dict with:
            - relevance_score: float 0-1
            - gaps_identified: List[str]
            - insights_generated: List[str]
            - relationship_type: str or None (cite/extend/contradict/validate)
            - reasoning: str (transparent thought process)
        """
        try:
            # Build analysis prompt for LLM
            post_summary = f"""
Title: {post.get('title', 'Untitled')}
Hypothesis: {post.get('hypothesis', 'Not specified')}
Method: {post.get('method', 'Not specified')}
Findings: {post.get('findings', 'Not specified')}
"""

            # Get agent's interests for relevance scoring
            agent_config_path = Path.home() / ".scienceclaw" / "agent_profile.json"
            interests = []
            if agent_config_path.exists():
                try:
                    with open(agent_config_path) as f:
                        config = json.load(f)
                        interests = config.get("interests", [])
                except Exception:
                    pass

            interests_str = ", ".join(interests) if interests else "general science"

            # Create analysis prompt
            analysis_prompt = f"""
Analyze this scientific post for an agent with interests in: {interests_str}

POST CONTENT:
{post_summary}

Provide analysis in JSON format with these keys:
1. relevance_score (0-1): How relevant is this to the agent's interests?
2. gaps_identified (list): What gaps or limitations in methodology/evidence?
3. insights_generated (list): What new insights could extend this work?
4. relationship_type (str or null): Is this cite/extend/contradict/validate of related work?
5. reasoning (str): Transparent explanation of the analysis

Be specific and scientific. Return ONLY valid JSON.
"""

            # Get LLM analysis
            llm_response = self.llm_reasoner._call_llm(
                prompt=analysis_prompt,
                max_tokens=800
            )

            # Parse LLM response
            try:
                analysis = json.loads(llm_response)
            except json.JSONDecodeError:
                # Fallback: extract JSON from response if wrapped in markdown
                try:
                    json_start = llm_response.find('{')
                    json_end = llm_response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        analysis = json.loads(llm_response[json_start:json_end])
                    else:
                        raise ValueError("No JSON found in response")
                except Exception:
                    # Default analysis if LLM fails
                    analysis = {
                        "relevance_score": 0.5,
                        "gaps_identified": [],
                        "insights_generated": [],
                        "relationship_type": None,
                        "reasoning": "Analysis unavailable"
                    }

            # Validate structure
            if not isinstance(analysis.get("relevance_score"), (int, float)):
                analysis["relevance_score"] = float(analysis.get("relevance_score", 0.5))

            if not isinstance(analysis.get("gaps_identified"), list):
                analysis["gaps_identified"] = []

            if not isinstance(analysis.get("insights_generated"), list):
                analysis["insights_generated"] = []

            if analysis.get("relationship_type") not in ["cite", "extend", "contradict", "validate", None]:
                analysis["relationship_type"] = None

            if not isinstance(analysis.get("reasoning"), str):
                analysis["reasoning"] = "Analysis complete"

            return analysis

        except Exception as e:
            print(f"    Warning: Post analysis failed: {e}")
            # Return safe default analysis
            return {
                "relevance_score": 0.3,
                "gaps_identified": [],
                "insights_generated": [],
                "relationship_type": None,
                "reasoning": f"Analysis attempted but failed: {str(e)[:50]}"
            }

    def generate_comment(self, post: Dict[str, Any], analysis: Dict[str, Any], comments: List[Dict] = None) -> Optional[str]:
        """
        Generate contextual scientific comment based on analysis and conversation needs.

        Uses contextual role adoption to determine what the conversation needs:
        - Validator if claims need verification
        - Synthesizer if multiple findings need integration
        - Critic if assumptions need questioning
        - Investigator if next steps are unclear
        - Explainer if concepts are confusing

        Only generates comments for posts with relevance >= 0.5

        Args:
            post: Original post dict
            analysis: Analysis dict from analyze_post()
            comments: Optional list of existing comments for context

        Returns:
            Comment text or None if not relevant enough
        """
        # Filter by relevance
        if analysis.get("relevance_score", 0) < 0.5:
            return None

        # Determine contextual role based on conversation needs
        from autonomous.contextual_roles import ContextualRoleAdopter
        from pathlib import Path
        import json

        # Load agent profile
        agent_config_path = Path.home() / ".scienceclaw" / "agent_profile.json"
        agent_profile = {}
        if agent_config_path.exists():
            try:
                with open(agent_config_path) as f:
                    agent_profile = json.load(f)
            except Exception:
                pass

        # Build conversation context
        conversation_context = {
            'post': post,
            'comments': comments or []
        }

        # Determine appropriate role
        role_adopter = ContextualRoleAdopter(agent_profile)
        role = role_adopter.determine_role(conversation_context)

        print(f"   🎭 Adopting role: {role} for this discussion")

        # Get role-specific guidance
        role_guidance = role_adopter.get_role_guidance(role)

        try:
            # Build comment generation prompt
            gaps_text = ""
            if analysis.get("gaps_identified"):
                gaps_text = "Potential gaps: " + "; ".join(
                    analysis["gaps_identified"][:2]  # Top 2 gaps
                )

            insights_text = ""
            if analysis.get("insights_generated"):
                insights_text = "Extension ideas: " + "; ".join(
                    analysis["insights_generated"][:2]  # Top 2 insights
                )

            comment_prompt = f"""
Generate a brief, scientific comment on this post for an AI research agent.

POST TITLE: {post.get('title', 'Untitled')}
POST FINDINGS: {post.get('findings', '')[:200]}

ANALYSIS:
Relevance: {analysis.get('relevance_score', 0):.1f}/1.0
{gaps_text}
{insights_text}

YOUR ROLE IN THIS DISCUSSION: {role}
{role_guidance}

REQUIREMENTS:
1. Be specific and scientific (not generic praise)
2. Reference specific parts of their methodology/findings
3. Ask follow-up questions or suggest alternatives
4. Keep to 1-2 sentences maximum
5. Show genuine engagement with their work
6. Avoid templates and generic comments
7. **Act according to your role** - what does this conversation need right now?

Relationship type: {analysis.get('relationship_type', 'none')}
- If cite: mention your related work
- If extend: suggest extensions
- If contradict: respectfully present alternative view
- If validate: propose validation approach

Generate ONLY the comment text, no metadata.
"""

            # Get LLM comment
            comment = self.llm_reasoner._call_llm(
                prompt=comment_prompt,
                max_tokens=200
            )

            if not comment or len(comment.strip()) < 20:
                return None

            return comment.strip()

        except Exception as e:
            print(f"    Warning: Comment generation failed: {e}")
            return None

    def should_create_link(self, analysis: Dict[str, Any]) -> bool:
        """
        Determine if post link should be created based on analysis.

        Creates links only when:
        - A clear relationship is identified (cite/extend/contradict/validate)
        - Relevance is high (>= 0.6)

        Args:
            analysis: Analysis dict from analyze_post()

        Returns:
            True if link should be created
        """
        relationship = analysis.get("relationship_type")
        relevance = analysis.get("relevance_score", 0)

        # Only create links for strong relationships and high relevance
        has_relationship = relationship in ["cite", "extend", "contradict", "validate"]
        has_good_relevance = relevance >= 0.6

        return has_relationship and has_good_relevance

    def find_related_posts(self) -> List[Dict[str, Any]]:
        """
        Find agent's recent posts that might relate to peer work.

        Uses memory system to retrieve agent's recent investigations
        and posts, ranked by recency.

        Returns:
            List of post dicts with id, title, topic
        """
        try:
            from memory import AgentJournal

            journal = AgentJournal(self.agent_name)

            # Get recent investigations from journal
            recent_entries = journal.get_recent_entries(
                entry_type="investigation",
                limit=10
            )

            # Extract topics and convert to post-like structures
            related_posts = []
            for entry in recent_entries:
                content = entry.get("content", {})
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        continue

                # Try to extract post ID if available
                post_id = entry.get("metadata", {}).get("post_id")
                if post_id:
                    related_posts.append({
                        "id": post_id,
                        "title": content.get("topic", ""),
                        "topic": content.get("topic", "")
                    })

            return related_posts[:5]  # Return top 5 recent posts

        except Exception as e:
            print(f"    Warning: Could not retrieve related posts: {e}")
            return []

    def create_post_link(
        self,
        from_post_id: str,
        to_post_id: str,
        analysis: Dict[str, Any],
        platform: Any
    ) -> bool:
        """
        Create post link based on scientific relationship.

        Args:
            from_post_id: Agent's post ID
            to_post_id: Peer's post ID
            analysis: Analysis dict with relationship_type and reasoning
            platform: Platform client (for API call)

        Returns:
            True if link created successfully
        """
        try:
            link_type = analysis.get("relationship_type")
            if not link_type:
                return False

            # Generate context based on relationship
            reasoning = analysis.get("reasoning", "")
            insights = analysis.get("insights_generated", [])

            if link_type == "cite":
                context = f"Cited for: {reasoning[:100]}"
            elif link_type == "extend":
                if insights:
                    context = f"Extended with: {insights[0][:100]}"
                else:
                    context = f"Extended the findings on: {reasoning[:100]}"
            elif link_type == "contradict":
                context = f"Alternative perspective: {reasoning[:100]}"
            elif link_type == "validate":
                context = f"Validation approach: {reasoning[:100]}"
            else:
                context = reasoning[:100]

            # Create link via platform
            result = platform.link_post(
                from_post_id=from_post_id,
                to_post_id=to_post_id,
                link_type=link_type,
                context=context
            )

            if "error" not in result:
                print(f"    🔗 Created '{link_type}' link: {from_post_id[:8]} → {to_post_id[:8]}")
                return True
            else:
                print(f"    Warning: Link creation failed: {result.get('error')}")
                return False

        except Exception as e:
            print(f"    Warning: Could not create post link: {e}")
            return False

    def log_analysis(self, post_id: str, analysis: Dict[str, Any], action: str):
        """
        Log analysis reasoning for transparency.

        Saves to: ~/.scienceclaw/logs/{agent_name}/analysis.jsonl

        Args:
            post_id: ID of analyzed post
            analysis: Analysis dict
            action: Action taken (commented, linked, ignored)
        """
        try:
            log_dir = Path.home() / ".scienceclaw" / "logs" / self.agent_name
            log_dir.mkdir(parents=True, exist_ok=True)

            log_file = log_dir / "analysis.jsonl"

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "post_id": post_id,
                "relevance_score": analysis.get("relevance_score", 0),
                "gaps_identified": analysis.get("gaps_identified", []),
                "insights_generated": analysis.get("insights_generated", []),
                "relationship_type": analysis.get("relationship_type"),
                "reasoning": analysis.get("reasoning", ""),
                "action": action
            }

            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        except Exception as e:
            print(f"    Warning: Could not log analysis: {e}")
