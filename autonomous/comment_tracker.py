#!/usr/bin/env python3
"""
Comment Tracker - Anti-Lazy Safeguards
Prevents consecutive commenting on same posts and enforces active commenting behavior.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Set
from datetime import datetime, timedelta


class CommentTracker:
    """
    Tracks comment history to prevent lazy/repetitive behavior.

    Safeguards:
    1. No consecutive commenting on same posts (within 24h cooldown)
    2. Minimum comment requirement per cycle (at least 1-2 comments)
    3. Diversification across different posts/topics
    """

    def __init__(self, agent_name: str):
        """
        Initialize comment tracker for agent.

        Args:
            agent_name: Name of the agent
        """
        self.agent_name = agent_name
        self.state_dir = Path.home() / ".scienceclaw" / "comment_state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / f"{agent_name}_comment_history.json"

        # Load existing state
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load comment history from disk."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)

        return {
            "commented_posts": {},  # post_id -> {timestamp, comment_count}
            "cycle_history": [],     # List of {cycle_time, comments_posted}
            "total_comments": 0
        }

    def _save_state(self):
        """Save comment history to disk."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def can_comment_on_post(self, post_id: str, cooldown_hours: int = 24) -> bool:
        """
        Check if agent can comment on this post (respects cooldown).

        Args:
            post_id: ID of the post
            cooldown_hours: Hours before can comment again (default: 24)

        Returns:
            True if can comment, False if in cooldown period
        """
        if post_id not in self.state["commented_posts"]:
            return True

        last_comment = self.state["commented_posts"][post_id]
        last_time = datetime.fromisoformat(last_comment["timestamp"])
        cooldown_end = last_time + timedelta(hours=cooldown_hours)

        return datetime.now() >= cooldown_end

    def record_comment(self, post_id: str, post_title: str = ""):
        """
        Record that agent commented on this post.

        Args:
            post_id: ID of the post commented on
            post_title: Optional title for tracking
        """
        if post_id not in self.state["commented_posts"]:
            self.state["commented_posts"][post_id] = {
                "timestamp": datetime.now().isoformat(),
                "comment_count": 1,
                "title": post_title
            }
        else:
            self.state["commented_posts"][post_id]["timestamp"] = datetime.now().isoformat()
            self.state["commented_posts"][post_id]["comment_count"] += 1

        self.state["total_comments"] += 1
        self._save_state()

    def start_cycle(self):
        """Mark the start of a new heartbeat cycle."""
        self.current_cycle = {
            "cycle_time": datetime.now().isoformat(),
            "comments_posted": 0,
            "posts_commented": []
        }

    def end_cycle(self):
        """
        End the current cycle and validate comment requirement.

        Returns:
            Dict with cycle summary and whether minimum was met
        """
        if not hasattr(self, 'current_cycle'):
            return {"error": "No active cycle"}

        # Add to history
        self.state["cycle_history"].append(self.current_cycle)

        # Keep only last 10 cycles
        if len(self.state["cycle_history"]) > 10:
            self.state["cycle_history"] = self.state["cycle_history"][-10:]

        self._save_state()

        summary = {
            "comments_posted": self.current_cycle["comments_posted"],
            "posts_commented": self.current_cycle["posts_commented"],
            "met_minimum": self.current_cycle["comments_posted"] >= 1,
            "diversity_score": len(set(self.current_cycle["posts_commented"]))
        }

        return summary

    def increment_cycle_comments(self, post_id: str):
        """Increment comment count for current cycle."""
        if hasattr(self, 'current_cycle'):
            self.current_cycle["comments_posted"] += 1
            self.current_cycle["posts_commented"].append(post_id)

    def get_recent_commented_posts(self, hours: int = 24) -> Set[str]:
        """
        Get set of post IDs commented on recently.

        Args:
            hours: Look back this many hours

        Returns:
            Set of post IDs
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_posts = set()

        for post_id, info in self.state["commented_posts"].items():
            comment_time = datetime.fromisoformat(info["timestamp"])
            if comment_time >= cutoff:
                recent_posts.add(post_id)

        return recent_posts

    def get_stats(self) -> Dict[str, Any]:
        """Get commenting statistics for the agent."""
        recent_cycles = self.state["cycle_history"][-5:] if self.state["cycle_history"] else []
        avg_comments = sum(c["comments_posted"] for c in recent_cycles) / len(recent_cycles) if recent_cycles else 0

        return {
            "total_comments": self.state["total_comments"],
            "unique_posts_commented": len(self.state["commented_posts"]),
            "recent_cycles": len(recent_cycles),
            "avg_comments_per_cycle": avg_comments,
            "last_cycle": recent_cycles[-1] if recent_cycles else None
        }

    def clean_old_history(self, days: int = 7):
        """Remove comment history older than N days."""
        cutoff = datetime.now() - timedelta(days=days)

        # Clean old posts
        old_posts = []
        for post_id, info in self.state["commented_posts"].items():
            comment_time = datetime.fromisoformat(info["timestamp"])
            if comment_time < cutoff:
                old_posts.append(post_id)

        for post_id in old_posts:
            del self.state["commented_posts"][post_id]

        # Clean old cycles
        self.state["cycle_history"] = [
            c for c in self.state["cycle_history"]
            if datetime.fromisoformat(c["cycle_time"]) >= cutoff
        ]

        self._save_state()
        return len(old_posts)
