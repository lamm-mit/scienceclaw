"""
Discussion Manager - Track and participate in multi-turn scientific discussions.

Enables agents to:
- Monitor their own posts for incoming replies/mentions
- Respond contextually to peer comments and questions
- Participate in multi-turn scientific debates
- Track conversation history to avoid repetition

Key Features:
- Uses notifications API to detect replies and mentions
- Contextual reply generation using LLMScientificReasoner
- Thread state tracking to prevent redundant responses
- Conversation history analysis for informed responses
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from autonomous.llm_reasoner import LLMScientificReasoner


class DiscussionManager:
    """
    Manage multi-turn scientific discussions on peer posts.

    Workflow:
    1. Monitor own posts via notifications API
    2. Detect replies/mentions from peers
    3. Analyze parent context (original post + previous comments)
    4. Generate contextual response based on discussion
    5. Track conversation state to avoid repetition
    """

    def __init__(self, agent_name: str, platform: Any = None):
        """
        Initialize discussion manager.

        Args:
            agent_name: Name of the agent
            platform: Platform client for API calls (InfiniteClient)
        """
        self.agent_name = agent_name
        self.platform = platform
        self.llm_reasoner = LLMScientificReasoner(agent_name)
        self.scienceclaw_dir = Path(__file__).parent.parent

        # Track posts being monitored
        self._tracked_posts: Dict[str, Dict[str, Any]] = {}

    def track_own_posts(self, posts: List[Dict[str, Any]]) -> int:
        """
        Track agent's own posts for monitoring replies.

        Args:
            posts: List of agent's recent posts with id, title, content

        Returns:
            Number of posts now being tracked
        """
        try:
            for post in posts:
                post_id = post.get("id")
                if post_id and post_id not in self._tracked_posts:
                    self._tracked_posts[post_id] = {
                        "title": post.get("title", ""),
                        "last_checked": datetime.now().isoformat(),
                        "reply_count": 0,
                        "responded_to": set()
                    }

            return len(self._tracked_posts)

        except Exception as e:
            print(f"    Warning: Could not track posts: {e}")
            return 0

    def check_for_replies(self) -> List[Dict[str, Any]]:
        """
        Check for replies to agent's posts using notifications.

        Returns:
            List of reply dicts with:
            - post_id: Original post ID
            - comment_id: Reply comment ID
            - author: Who replied
            - content: Reply content
            - type: "reply" or "mention"
        """
        if not self.platform:
            return []

        try:
            # Get unread notifications
            notif_result = self.platform.get_notifications(unread_only=True, limit=20)

            if "error" in notif_result:
                return []

            notifications = notif_result.get("notifications", [])
            replies = []

            for notif in notifications:
                notif_type = notif.get("type")

                # Handle reply notifications
                if notif_type == "reply":
                    reply = {
                        "post_id": notif.get("post_id"),
                        "comment_id": notif.get("comment_id"),
                        "author": notif.get("author_name"),
                        "content": notif.get("content"),
                        "type": "reply",
                        "timestamp": notif.get("created_at")
                    }
                    replies.append(reply)

                # Handle mention notifications
                elif notif_type == "mention":
                    mention = {
                        "post_id": notif.get("post_id"),
                        "comment_id": notif.get("comment_id"),
                        "author": notif.get("author_name"),
                        "content": notif.get("content"),
                        "type": "mention",
                        "timestamp": notif.get("created_at")
                    }
                    replies.append(mention)

            return replies

        except Exception as e:
            print(f"    Warning: Could not check for replies: {e}")
            return []

    def respond_to_reply(
        self,
        reply: Dict[str, Any],
        parent_post: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Generate contextual response to a peer's reply.

        Analyzes:
        - The peer's comment (question, critique, suggestion)
        - The original post context
        - Previous discussion thread

        Generates response using LLM that:
        - Addresses specific points in peer's comment
        - Provides scientific explanation
        - Suggests follow-up experiments
        - Continues multi-turn scientific debate

        Args:
            reply: Reply dict from check_for_replies()
            parent_post: Original post being replied to

        Returns:
            Response text or None if unable to generate
        """
        try:
            if not self.platform:
                return None

            # Fetch parent post if not provided
            if not parent_post:
                post_id = reply.get("post_id")
                parent_result = self.platform.get_post(post_id)
                if "error" in parent_result:
                    return None
                parent_post = parent_result

            # Build response prompt
            peer_comment = reply.get("content", "")
            peer_author = reply.get("author", "Unknown")

            parent_hypothesis = parent_post.get("hypothesis", "")
            parent_findings = parent_post.get("findings", "")
            parent_method = parent_post.get("method", "")

            # Get previous discussion context
            thread_context = self._get_thread_context(
                post_id=reply.get("post_id"),
                comment_id=reply.get("comment_id")
            )

            response_prompt = f"""
You are {self.agent_name}, a scientific agent responding to a peer's comment.

ORIGINAL POST:
Hypothesis: {parent_hypothesis}
Method: {parent_method}
Findings: {parent_findings}

PEER'S COMMENT (from {peer_author}):
{peer_comment}

PREVIOUS DISCUSSION:
{thread_context}

Generate a contextual, scientific response that:
1. Directly addresses the peer's points
2. Provides mechanistic explanations or evidence
3. Suggests follow-up experiments or validation
4. Continues the scientific discussion productively
5. Is 1-2 sentences, specific and technical

Respond ONLY with the comment text (no metadata).
"""

            response = self.llm_reasoner._call_llm(
                prompt=response_prompt,
                max_tokens=250
            )

            if not response or len(response.strip()) < 20:
                return None

            return response.strip()

        except Exception as e:
            print(f"    Warning: Could not generate response: {e}")
            return None

    def _get_thread_context(
        self,
        post_id: str,
        comment_id: Optional[str] = None,
        limit: int = 5
    ) -> str:
        """
        Get previous discussion context for a thread.

        Retrieves up to `limit` previous comments in the thread.

        Args:
            post_id: Post ID
            comment_id: Specific comment ID (optional, for reply context)
            limit: Maximum comments to retrieve

        Returns:
            Formatted thread context string
        """
        if not self.platform:
            return "No previous discussion"

        try:
            # Get all comments for the post
            comments_result = self.platform.get_comments(post_id)

            if "error" in comments_result:
                return "No previous discussion"

            comments = comments_result.get("comments", [])

            # Build context string
            context_lines = []
            for comment in comments[-limit:]:  # Last 5 comments
                author = comment.get("author_name", "Unknown")
                content = comment.get("content", "")
                context_lines.append(f"- {author}: {content[:100]}...")

            if context_lines:
                return "\n".join(context_lines)
            else:
                return "No previous discussion"

        except Exception as e:
            print(f"    Warning: Could not get thread context: {e}")
            return "Error retrieving context"

    def follow_thread(self, post_id: str) -> List[Dict[str, Any]]:
        """
        Get complete discussion thread for a post.

        Args:
            post_id: Post ID to follow

        Returns:
            List of comment dicts with author and content
        """
        if not self.platform:
            return []

        try:
            comments_result = self.platform.get_comments(post_id)

            if "error" in comments_result:
                return []

            comments = comments_result.get("comments", [])

            # Format for return
            thread = []
            for comment in comments:
                thread.append({
                    "id": comment.get("id"),
                    "author": comment.get("author_name"),
                    "content": comment.get("content"),
                    "timestamp": comment.get("created_at"),
                    "depth": comment.get("depth", 0)
                })

            return thread

        except Exception as e:
            print(f"    Warning: Could not follow thread: {e}")
            return []

    def should_respond(self, reply: Dict[str, Any]) -> bool:
        """
        Determine if agent should respond to a reply.

        Don't respond if:
        - Already responded to this specific comment
        - Reply is off-topic or unhelpful

        Args:
            reply: Reply dict from check_for_replies()

        Returns:
            True if agent should respond
        """
        post_id = reply.get("post_id")
        comment_id = reply.get("comment_id")

        # Track responses to avoid repetition
        if post_id in self._tracked_posts:
            responded = self._tracked_posts[post_id].get("responded_to", set())

            # Don't respond twice to same comment
            if comment_id in responded:
                return False

            # Record that we're responding
            responded.add(comment_id)
            return True

        return True

    def record_response(self, post_id: str, comment_id: str):
        """Record that we've responded to a comment."""
        if post_id in self._tracked_posts:
            self._tracked_posts[post_id]["responded_to"].add(comment_id)

    def log_discussion(
        self,
        post_id: str,
        reply: Dict[str, Any],
        response: Optional[str],
        action: str
    ):
        """
        Log discussion activity for transparency.

        Saves to: ~/.scienceclaw/logs/{agent_name}/discussions.jsonl

        Args:
            post_id: Post ID
            reply: Reply dict
            response: Generated response (if any)
            action: Action taken (responded, ignored, etc.)
        """
        try:
            log_dir = Path.home() / ".scienceclaw" / "logs" / self.agent_name
            log_dir.mkdir(parents=True, exist_ok=True)

            log_file = log_dir / "discussions.jsonl"

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "post_id": post_id,
                "peer_author": reply.get("author"),
                "peer_comment": reply.get("content", "")[:200],
                "reply_type": reply.get("type"),
                "response_generated": response is not None,
                "response_length": len(response) if response else 0,
                "action": action
            }

            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        except Exception as e:
            print(f"    Warning: Could not log discussion: {e}")

    # ========== Enhanced Full-Context Discussion Methods (Phase 4) ==========

    def get_full_conversation_context(self, post_id: str) -> Dict[str, Any]:
        """
        Get ENTIRE conversation thread, not just last N comments.

        Builds complete conversation tree with:
        - Original post
        - All comments (unlimited)
        - Thread structure (parent-child relationships)
        - Discussion state analysis

        Args:
            post_id: Post ID to analyze

        Returns:
            Dict with 'post', 'thread', 'state' keys
        """
        if not self.platform:
            return {'post': {}, 'thread': [], 'state': {}}

        try:
            # Get original post
            post_result = self.platform.get_post(post_id)
            if "error" in post_result:
                return {'post': {}, 'thread': [], 'state': {}}

            post = post_result.get("post", {})

            # Get ALL comments (no limit!)
            comments_result = self.platform.get_comments(post_id)
            if "error" in comments_result:
                comments = []
            else:
                comments = comments_result.get("comments", [])

            # Build conversation tree
            thread = self._build_conversation_tree(comments)

            # Analyze discussion state
            state = self._analyze_discussion_state(post, thread)

            return {
                'post': post,
                'thread': thread,
                'state': state
            }

        except Exception as e:
            print(f"    Warning: Could not get full context: {e}")
            return {'post': {}, 'thread': [], 'state': {}}

    def _build_conversation_tree(self, comments: List[Dict]) -> List[Dict]:
        """
        Build hierarchical conversation tree from flat comment list.

        Args:
            comments: Flat list of comments

        Returns:
            List of comments with nested 'replies' field
        """
        # Index comments by ID
        comment_map = {c.get('id'): dict(c, replies=[]) for c in comments}

        # Build tree structure
        root_comments = []
        for comment in comments:
            parent_id = comment.get('parentId')
            if parent_id and parent_id in comment_map:
                # Add to parent's replies
                comment_map[parent_id]['replies'].append(comment_map[comment.get('id')])
            else:
                # Root level comment
                root_comments.append(comment_map[comment.get('id')])

        return root_comments

    def _analyze_discussion_state(self, post: Dict, thread: List[Dict]) -> Dict[str, Any]:
        """
        Analyze current state of discussion.

        Detects:
        - Original questions vs answered questions
        - Open questions remaining
        - Consensus areas
        - Disagreement areas
        - Collaboration signals
        - Stalled threads

        Args:
            post: Original post dict
            thread: Conversation tree

        Returns:
            State analysis dict
        """
        state = {
            'original_questions': [],
            'questions_addressed': [],
            'open_questions': [],
            'consensus_areas': [],
            'disagreement_areas': [],
            'collaboration_signals': [],
            'needs_attention': []
        }

        # Extract original questions from post
        open_questions_text = post.get('openQuestions', '') or post.get('content', '')
        if '?' in open_questions_text:
            state['original_questions'] = [
                q.strip() + '?' for q in open_questions_text.split('?') if q.strip()
            ][:5]

        # Analyze thread
        all_comments = self._flatten_thread(thread)

        # Track question patterns
        for comment in all_comments:
            content = comment.get('content', '').lower()

            # Open questions
            if '?' in content:
                state['open_questions'].extend([
                    q.strip() + '?' for q in content.split('?') if q.strip() and len(q) < 100
                ][:2])

            # Consensus signals
            consensus_keywords = ['agree', 'confirmed', 'validated', 'correct', 'exactly']
            if any(kw in content for kw in consensus_keywords):
                state['consensus_areas'].append(comment.get('content', '')[:100])

            # Disagreement signals
            disagreement_keywords = ['disagree', 'however', 'but', 'incorrect', 'wrong', 'not convinced']
            if any(kw in content for kw in disagreement_keywords):
                state['disagreement_areas'].append(comment.get('content', '')[:100])

            # Collaboration signals
            collab_keywords = ['let\'s', 'we could', 'collaborate', 'together', 'i can help']
            if any(kw in content for kw in collab_keywords):
                state['collaboration_signals'].append({
                    'author': comment.get('author'),
                    'signal': comment.get('content', '')[:100]
                })

        # Deduplicate and limit
        state['open_questions'] = list(set(state['open_questions']))[:5]
        state['consensus_areas'] = state['consensus_areas'][:3]
        state['disagreement_areas'] = state['disagreement_areas'][:3]

        return state

    def _flatten_thread(self, thread: List[Dict]) -> List[Dict]:
        """Flatten hierarchical thread to flat list of comments."""
        flat = []
        for comment in thread:
            flat.append(comment)
            if 'replies' in comment:
                flat.extend(self._flatten_thread(comment['replies']))
        return flat

    def should_continue_discussion(self, context: Dict) -> tuple[bool, str]:
        """
        Determine if discussion should continue based on natural exit criteria.

        Exit criteria:
        - All questions answered
        - Consensus reached
        - Discussion circular/repetitive
        - No new contributions in N comments

        Args:
            context: Full conversation context from get_full_conversation_context()

        Returns:
            (should_continue: bool, reason: str)
        """
        state = context.get('state', {})

        # Exit if all questions answered
        original_q = len(state.get('original_questions', []))
        open_q = len(state.get('open_questions', []))

        if original_q > 0 and open_q == 0:
            return False, "All original questions answered"

        # Exit if strong consensus reached
        consensus_count = len(state.get('consensus_areas', []))
        if consensus_count >= 3:
            return False, "Consensus reached"

        # Exit if circular discussion
        if self._is_repeating_points(context['thread']):
            return False, "Discussion becoming circular"

        # Exit if only disagreement remaining (stalemate)
        disagreement_count = len(state.get('disagreement_areas', []))
        if disagreement_count >= 3 and consensus_count == 0:
            return False, "Discussion reached stalemate"

        # Continue if productive engagement
        if open_q > 0 or len(state.get('collaboration_signals', [])) > 0:
            return True, "Productive discussion ongoing"

        # Default: continue if recent activity
        return True, "Discussion active"

    def _is_repeating_points(self, thread: List[Dict]) -> bool:
        """
        Detect if discussion is repeating same points (circular).

        Args:
            thread: Conversation tree

        Returns:
            True if circular, False otherwise
        """
        all_comments = self._flatten_thread(thread)

        if len(all_comments) < 4:
            return False

        # Get last 4 comments
        recent = all_comments[-4:]

        # Simple heuristic: check for repeated keywords
        keyword_sets = []
        for comment in recent:
            content = comment.get('content', '').lower()
            # Extract keywords (words > 4 chars)
            keywords = set([
                word for word in content.split()
                if len(word) > 4 and word.isalpha()
            ])
            keyword_sets.append(keywords)

        # Check overlap between consecutive comments
        overlaps = []
        for i in range(len(keyword_sets) - 1):
            if keyword_sets[i] and keyword_sets[i + 1]:
                overlap = len(keyword_sets[i] & keyword_sets[i + 1]) / len(keyword_sets[i] | keyword_sets[i + 1])
                overlaps.append(overlap)

        # If average overlap > 0.5, discussion is circular
        if overlaps:
            avg_overlap = sum(overlaps) / len(overlaps)
            return avg_overlap > 0.5

        return False
