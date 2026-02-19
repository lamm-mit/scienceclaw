"""
Collaboration Memory - Track and learn from multi-agent collaborations.

Logs collaboration events (help provided, teams formed, questions answered)
and extracts patterns to inform future collaboration decisions.

Key Features:
- JSONL event logging for all collaborations
- Pattern extraction (successful partners, productive topics, effective tools)
- Collaboration suggestions based on past success
- Learning from both successful and unproductive collaborations

Usage:
    from memory.collaboration_memory import CollaborationMemory

    memory = CollaborationMemory('AgentName')

    # Log collaboration
    memory.log_collaboration({
        'type': 'help_provided',
        'participants': ['AgentName', 'PeerAgent'],
        'outcome': 'successful',
        'tools_used': ['tdc', 'pubchem'],
        'post_id': 'post-123'
    })

    # Get patterns
    patterns = memory.get_collaboration_patterns()
    print(f"Successful partners: {patterns['successful_partners']}")

    # Get suggestions
    suggestions = memory.suggest_collaborators("ADMET analysis task")
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict


class CollaborationMemory:
    """Tracks collaboration outcomes and learns patterns."""

    def __init__(self, agent_name: str):
        """
        Initialize collaboration memory.

        Args:
            agent_name: Name of the agent
        """
        self.agent_name = agent_name
        self.memory_dir = Path.home() / ".scienceclaw" / "memory" / agent_name
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.memory_dir / "collaborations.jsonl"

    def log_collaboration(self, data: Dict[str, Any]) -> None:
        """
        Log a collaboration event.

        Args:
            data: Collaboration data with keys:
                - type: str ('help_provided', 'team_formed', 'question_answered', etc.)
                - participants: List[str] (agent names involved)
                - outcome: str ('successful', 'unproductive', 'ongoing')
                - tools_used: List[str] (optional)
                - post_id: str (optional)
                - thread_length: int (optional)
                - topic: str (optional)
        """
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'agent': self.agent_name,
            'type': data.get('type', 'unknown'),
            'participants': data.get('participants', []),
            'outcome': data.get('outcome', 'unknown'),
            'tools_used': data.get('tools_used', []),
            'post_id': data.get('post_id'),
            'thread_length': data.get('thread_length', 0),
            'topic': data.get('topic', ''),
            'context': data.get('context', {})
        }

        try:
            with open(self.memory_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            print(f"Warning: Could not log collaboration: {e}")

    def _load_all(self) -> List[Dict[str, Any]]:
        """Load all collaboration events from JSONL file."""
        if not self.memory_file.exists():
            return []

        events = []
        try:
            with open(self.memory_file, 'r') as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
        except Exception as e:
            print(f"Warning: Could not load collaborations: {e}")

        return events

    def get_collaboration_patterns(self) -> Dict[str, Any]:
        """
        Extract patterns from past collaborations.

        Returns:
            Dict with:
            - successful_partners: Dict[agent_name -> success_stats]
            - productive_topics: List[(topic, success_rate)]
            - effective_tools: List[(tool, usage_count, success_rate)]
            - role_preferences: Dict[role -> effectiveness]
        """
        events = self._load_all()

        if not events:
            return {
                'successful_partners': {},
                'productive_topics': [],
                'effective_tools': [],
                'role_preferences': {}
            }

        # Analyze successful partners
        successful_partners = self._identify_successful_partners(events)

        # Analyze productive topics
        productive_topics = self._identify_productive_topics(events)

        # Analyze effective tools
        effective_tools = self._identify_effective_tools(events)

        # Analyze role effectiveness
        role_preferences = self._identify_role_effectiveness(events)

        return {
            'successful_partners': successful_partners,
            'productive_topics': productive_topics,
            'effective_tools': effective_tools,
            'role_preferences': role_preferences
        }

    def _identify_successful_partners(self, events: List[Dict]) -> Dict[str, Dict]:
        """
        Identify agents with high collaboration success rate.

        Returns:
            Dict mapping agent name to success stats
        """
        partner_stats = defaultdict(lambda: {'total': 0, 'successful': 0, 'unproductive': 0})

        for event in events:
            participants = event.get('participants', [])
            outcome = event.get('outcome', 'unknown')

            # Get partners (excluding self)
            partners = [p for p in participants if p != self.agent_name]

            for partner in partners:
                partner_stats[partner]['total'] += 1
                if outcome == 'successful':
                    partner_stats[partner]['successful'] += 1
                elif outcome == 'unproductive':
                    partner_stats[partner]['unproductive'] += 1

        # Calculate success rates
        results = {}
        for partner, stats in partner_stats.items():
            if stats['total'] > 0:
                success_rate = stats['successful'] / stats['total']
                results[partner] = {
                    'total_collaborations': stats['total'],
                    'successful': stats['successful'],
                    'success_rate': success_rate
                }

        return results

    def _identify_productive_topics(self, events: List[Dict]) -> List[tuple]:
        """
        Identify topics with high collaboration success.

        Returns:
            List of (topic, success_rate, count) tuples
        """
        topic_stats = defaultdict(lambda: {'total': 0, 'successful': 0})

        for event in events:
            topic = event.get('topic', '').lower()
            if not topic:
                continue

            outcome = event.get('outcome', 'unknown')
            topic_stats[topic]['total'] += 1
            if outcome == 'successful':
                topic_stats[topic]['successful'] += 1

        # Calculate success rates
        results = []
        for topic, stats in topic_stats.items():
            if stats['total'] >= 2:  # Require at least 2 collaborations
                success_rate = stats['successful'] / stats['total']
                results.append((topic, success_rate, stats['total']))

        # Sort by success rate then count
        results.sort(key=lambda x: (x[1], x[2]), reverse=True)

        return results[:10]

    def _identify_effective_tools(self, events: List[Dict]) -> List[tuple]:
        """
        Identify tools with high collaboration success.

        Returns:
            List of (tool, usage_count, success_rate) tuples
        """
        tool_stats = defaultdict(lambda: {'total': 0, 'successful': 0})

        for event in events:
            tools = event.get('tools_used', [])
            outcome = event.get('outcome', 'unknown')

            for tool in tools:
                tool_stats[tool]['total'] += 1
                if outcome == 'successful':
                    tool_stats[tool]['successful'] += 1

        # Calculate success rates
        results = []
        for tool, stats in tool_stats.items():
            if stats['total'] > 0:
                success_rate = stats['successful'] / stats['total']
                results.append((tool, stats['total'], success_rate))

        # Sort by success rate then usage
        results.sort(key=lambda x: (x[2], x[1]), reverse=True)

        return results[:10]

    def _identify_role_effectiveness(self, events: List[Dict]) -> Dict[str, float]:
        """
        Identify which collaboration types are most effective.

        Returns:
            Dict mapping collaboration type to success rate
        """
        role_stats = defaultdict(lambda: {'total': 0, 'successful': 0})

        for event in events:
            collab_type = event.get('type', 'unknown')
            outcome = event.get('outcome', 'unknown')

            role_stats[collab_type]['total'] += 1
            if outcome == 'successful':
                role_stats[collab_type]['successful'] += 1

        # Calculate success rates
        results = {}
        for role, stats in role_stats.items():
            if stats['total'] > 0:
                results[role] = stats['successful'] / stats['total']

        return results

    def suggest_collaborators(self, task_description: str) -> List[Dict[str, Any]]:
        """
        Suggest collaborators based on past success.

        Args:
            task_description: Description of the task

        Returns:
            List of suggestions with agent, success_rate, reason
        """
        patterns = self.get_collaboration_patterns()
        suggestions = []

        # Get successful partners
        for agent, stats in patterns['successful_partners'].items():
            if stats['success_rate'] >= 0.7 and stats['total_collaborations'] >= 2:
                reason = self._explain_suggestion(agent, stats, task_description, patterns)
                suggestions.append({
                    'agent': agent,
                    'success_rate': stats['success_rate'],
                    'total_collaborations': stats['total_collaborations'],
                    'reason': reason,
                    'priority': 'high' if stats['success_rate'] >= 0.8 else 'medium'
                })

        # Sort by success rate
        suggestions.sort(key=lambda x: x['success_rate'], reverse=True)

        return suggestions[:5]

    def _explain_suggestion(
        self,
        agent: str,
        stats: Dict,
        task: str,
        patterns: Dict
    ) -> str:
        """
        Generate explanation for why agent is suggested.

        Args:
            agent: Agent name
            stats: Success statistics for this agent
            task: Task description
            patterns: All collaboration patterns

        Returns:
            Explanation string
        """
        reasons = []

        # Success rate
        success_pct = int(stats['success_rate'] * 100)
        reasons.append(f"{success_pct}% success rate over {stats['total_collaborations']} collaborations")

        # Check if agent was successful with specific tools mentioned in task
        task_lower = task.lower()
        for tool_info in patterns.get('effective_tools', []):
            tool, count, rate = tool_info
            if tool.lower() in task_lower and rate >= 0.7:
                reasons.append(f"successful with {tool}")

        if reasons:
            return "; ".join(reasons)
        else:
            return f"past success with {agent}"

    def get_recent_collaborations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent collaboration events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent collaboration events
        """
        events = self._load_all()
        return events[-limit:] if events else []

    def get_collaboration_count(self) -> int:
        """Get total number of collaborations logged."""
        events = self._load_all()
        return len(events)

    def get_success_rate(self) -> float:
        """
        Get overall collaboration success rate.

        Returns:
            Success rate (0.0 to 1.0)
        """
        events = self._load_all()
        if not events:
            return 0.0

        successful = sum(1 for e in events if e.get('outcome') == 'successful')
        return successful / len(events)
