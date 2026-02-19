#!/usr/bin/env python3
"""
Skill Usage Tracker - Prevent Repetitive Tool Usage

Tracks which skills an agent has used recently and encourages exploration
of the full 159 available skills instead of getting stuck in PubMed+UniProt rut.

NO HARDCODED CATEGORIES - just track actual skill usage patterns.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import Counter


class SkillUsageTracker:
    """
    Track skill usage to prevent repetitive patterns.

    Stored at: ~/.scienceclaw/skill_usage/{agent_name}.json
    """

    def __init__(self, agent_name: str):
        """Initialize tracker for an agent."""
        self.agent_name = agent_name
        self.usage_dir = Path.home() / ".scienceclaw" / "skill_usage"
        self.usage_dir.mkdir(parents=True, exist_ok=True)
        self.usage_file = self.usage_dir / f"{agent_name}.json"

        # Load or initialize usage history
        self.history = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load usage history from file."""
        if self.usage_file.exists():
            try:
                with open(self.usage_file) as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_history(self):
        """Save usage history to file."""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save skill usage: {e}")

    def record_usage(self, skills_used: List[str], topic: str):
        """
        Record skills used for a topic.

        Args:
            skills_used: List of skill names used
            topic: Research topic
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'topic': topic,
            'skills': skills_used,
            'skill_count': len(skills_used)
        }

        self.history.append(entry)

        # Keep last 100 entries
        if len(self.history) > 100:
            self.history = self.history[-100:]

        self._save_history()

    def get_recent_usage(self, window_size: int = 10) -> Dict[str, Any]:
        """
        Get skill usage statistics for recent posts.

        Args:
            window_size: Number of recent posts to analyze

        Returns:
            Dict with usage statistics
        """
        recent = self.history[-window_size:] if len(self.history) >= window_size else self.history

        if not recent:
            return {
                'total_posts': 0,
                'unique_skills_used': 0,
                'most_common_skills': [],
                'repetition_score': 0.0,
                'exploration_score': 1.0,
                'stuck_in_rut': False
            }

        # Count all skills used
        all_skills = []
        for entry in recent:
            all_skills.extend(entry.get('skills', []))

        skill_counts = Counter(all_skills)
        unique_skills = len(skill_counts)
        total_uses = len(all_skills)

        # Calculate repetition score (0 = very repetitive, 1 = very diverse)
        # If using same 2-3 skills repeatedly, score is low
        top_3_count = sum(count for skill, count in skill_counts.most_common(3))
        repetition_score = 1.0 - (top_3_count / max(total_uses, 1))

        # Exploration score (ratio of unique skills to total uses)
        exploration_score = unique_skills / max(total_uses, 1)

        # Stuck in rut detection
        # If last 5 posts all use same 2-3 skills, you're stuck
        stuck_in_rut = False
        if len(recent) >= 5:
            last_5_skills = []
            for entry in recent[-5:]:
                last_5_skills.extend(entry.get('skills', []))

            last_5_unique = len(set(last_5_skills))
            stuck_in_rut = last_5_unique <= 3

        return {
            'total_posts': len(recent),
            'total_skill_uses': total_uses,
            'unique_skills_used': unique_skills,
            'most_common_skills': skill_counts.most_common(5),
            'repetition_score': repetition_score,
            'exploration_score': exploration_score,
            'stuck_in_rut': stuck_in_rut,
            'rut_warning': 'Agent is stuck using same 2-3 skills repeatedly!' if stuck_in_rut else None
        }

    def get_underused_skills(self, available_skills: List[str], window_size: int = 20) -> List[str]:
        """
        Get skills that are available but haven't been used recently.

        Args:
            available_skills: All available skill names
            window_size: Look back window

        Returns:
            List of underused skill names
        """
        recent = self.history[-window_size:] if len(self.history) >= window_size else self.history

        # Get all skills used in window
        used_skills = set()
        for entry in recent:
            used_skills.update(entry.get('skills', []))

        # Find skills never or rarely used
        underused = [skill for skill in available_skills if skill not in used_skills]

        return underused

    def suggest_fresh_skills(
        self,
        available_skills: List[Dict[str, Any]],
        topic: str,
        max_suggestions: int = 10
    ) -> List[str]:
        """
        Suggest skills that are relevant to topic but haven't been overused.

        Args:
            available_skills: List of skill metadata dicts
            topic: Research topic
            max_suggestions: Max number to suggest

        Returns:
            List of skill names to try
        """
        stats = self.get_recent_usage(window_size=10)
        overused = {skill for skill, count in stats['most_common_skills']}

        # Filter to skills not in overused set
        fresh_skills = [
            s for s in available_skills
            if s.get('name') not in overused
        ]

        # Simple keyword matching (could be replaced with LLM)
        topic_lower = topic.lower()
        scored = []

        for skill in fresh_skills:
            score = 0
            name = skill.get('name', '').lower()
            desc = skill.get('description', '').lower()
            keywords = skill.get('keywords', [])

            # Score by topic relevance
            for word in topic_lower.split():
                if len(word) > 3:
                    if word in name:
                        score += 3
                    if word in desc:
                        score += 2
                    if any(word in kw for kw in keywords):
                        score += 1

            if score > 0:
                scored.append((score, skill.get('name')))

        # Sort by score and return top suggestions
        scored.sort(reverse=True, key=lambda x: x[0])
        return [name for score, name in scored[:max_suggestions]]

    def enhance_llm_prompt(self, topic: str, available_skills: List[Dict[str, Any]]) -> str:
        """
        Generate additional context for LLM to encourage skill diversity.

        Returns:
            String to add to LLM prompt
        """
        stats = self.get_recent_usage(window_size=10)

        if stats['total_posts'] == 0:
            return ""

        # Build warning if stuck in rut
        warning = ""
        if stats['stuck_in_rut']:
            overused = [skill for skill, count in stats['most_common_skills'][:3]]
            warning = f"""
⚠️ WARNING: You have been using the same {len(overused)} skills repeatedly.
Recent pattern: {', '.join(overused)}
CRITICAL: Try different tools this time! Explore the full skill catalog.
"""

        # Suggest fresh skills
        fresh = self.suggest_fresh_skills(available_skills, topic, max_suggestions=5)
        fresh_text = f"\n💡 Fresh skills to consider: {', '.join(fresh[:5])}" if fresh else ""

        # Build context
        context = f"""
📊 Your Recent Skill Usage (last {stats['total_posts']} posts):
- Unique skills used: {stats['unique_skills_used']}
- Exploration score: {stats['exploration_score']:.2f} (higher is better)
- Most used: {', '.join([s for s, c in stats['most_common_skills'][:3]])}
{warning}{fresh_text}

INSTRUCTION: Select skills you haven't used recently to explore different approaches.
Avoid defaulting to the same tools every time.
"""

        return context


def get_usage_tracker(agent_name: str) -> SkillUsageTracker:
    """Get skill usage tracker for an agent."""
    return SkillUsageTracker(agent_name)


# Test
if __name__ == "__main__":
    print("\n=== Testing Skill Usage Tracker ===\n")

    tracker = SkillUsageTracker("TestAgent")

    # Simulate repetitive usage
    print("Simulating repetitive usage pattern...")
    for i in range(10):
        tracker.record_usage(['pubmed', 'uniprot'], f"Topic {i}")

    stats = tracker.get_recent_usage(window_size=10)
    print(f"\nStats after repetitive usage:")
    print(f"  Unique skills: {stats['unique_skills_used']}")
    print(f"  Exploration score: {stats['exploration_score']:.2f}")
    print(f"  Stuck in rut: {stats['stuck_in_rut']}")
    print(f"  Most common: {stats['most_common_skills']}")

    # Simulate diverse usage
    print("\nSimulating diverse usage pattern...")
    diverse_skills = ['pubmed', 'tdc', 'blast', 'alphafold', 'rdkit', 'materials']
    for i, skill in enumerate(diverse_skills):
        tracker.record_usage([skill, 'websearch'], f"Diverse topic {i}")

    stats = tracker.get_recent_usage(window_size=10)
    print(f"\nStats after diverse usage:")
    print(f"  Unique skills: {stats['unique_skills_used']}")
    print(f"  Exploration score: {stats['exploration_score']:.2f}")
    print(f"  Stuck in rut: {stats['stuck_in_rut']}")

    print("\n✓ Skill usage tracker test complete")
