"""
Natural Agent Discovery - Organic collaboration through community observation.

Agents discover collaboration opportunities by reading posts and comments,
not through pre-scripted matchmaking. This creates emergent, context-driven
team formation.

Key Components:
- OpportunityScanner: Finds where agent can contribute
- CapabilityAnnouncer: Posts "I can help with X"
- HelpSeeker: Posts questions when needs expertise
- TeamFormationDetector: Identifies emerging collaborations
"""

import json
import re
from typing import Dict, List, Optional
from pathlib import Path


class OpportunityScanner:
    """Scans community for opportunities to contribute."""

    def __init__(self, agent_name: str, agent_profile: Dict, platform, collaboration_memory=None):
        """
        Initialize scanner.

        Args:
            agent_name: Agent's name
            agent_profile: Agent's profile with skills/interests
            platform: Platform client (InfiniteClient)
            collaboration_memory: Optional CollaborationMemory instance for learning
        """
        self.agent_name = agent_name
        self.agent_profile = agent_profile
        self.platform = platform
        self.collaboration_memory = collaboration_memory
        self.preferred_tools = agent_profile.get('preferred_tools', [])
        self.interests = agent_profile.get('interests', [])

    def scan_for_opportunities(self, limit: int = 20) -> List[Dict]:
        """
        Scan community posts for opportunities to contribute.

        Returns:
            List of opportunities with confidence scores
        """
        try:
            posts = self.platform.get_feed(limit=limit)
        except Exception as e:
            print(f"  ⚠️  Failed to fetch feed: {e}")
            return []

        opportunities = []

        for post in posts:
            # Skip own posts
            if post.get('author') == self.agent_name:
                continue

            # Detect help requests
            if self._is_help_request(post):
                needed_skills = self._extract_needed_skills(post)
                if self._can_help(needed_skills):
                    confidence = self._assess_match(needed_skills)
                    opportunities.append({
                        'post_id': post.get('id'),
                        'author': post.get('author'),
                        'type': 'help_request',
                        'title': post.get('title', '')[:100],
                        'skills_needed': needed_skills,
                        'confidence': confidence,
                        'priority': 'high' if confidence > 0.7 else 'medium'
                    })

            # Check for unanswered questions in comments
            try:
                comments = self.platform.get_comments(post.get('id'))
                for comment in comments:
                    if self._is_unanswered_question(comment, comments) and self._can_answer(comment):
                        opportunities.append({
                            'post_id': post.get('id'),
                            'comment_id': comment.get('id'),
                            'author': post.get('author'),
                            'type': 'unanswered_question',
                            'title': post.get('title', '')[:100],
                            'question': comment.get('content', '')[:200],
                            'confidence': 0.6,
                            'priority': 'medium'
                        })
            except Exception as e:
                # Skip if comments unavailable
                pass

            # Detect complementary investigations
            if self._is_complementary_investigation(post):
                opportunities.append({
                    'post_id': post.get('id'),
                    'author': post.get('author'),
                    'type': 'complementary_investigation',
                    'title': post.get('title', '')[:100],
                    'confidence': 0.7,
                    'priority': 'medium',
                    'reason': 'Overlaps with your expertise'
                })

        # Prioritize opportunities with successful past collaborators
        if self.collaboration_memory:
            patterns = self.collaboration_memory.get_collaboration_patterns()
            successful_partners = patterns.get('successful_partners', {})

            for opp in opportunities:
                author = opp.get('author')
                if author in successful_partners:
                    partner_stats = successful_partners[author]
                    if partner_stats['success_rate'] >= 0.7:
                        # Boost priority and confidence for successful partners
                        opp['priority'] = 'high'
                        opp['confidence'] = min(1.0, opp['confidence'] * 1.2)
                        opp['reason'] = opp.get('reason', '') + f" (past success: {int(partner_stats['success_rate']*100)}%)"

        return sorted(opportunities, key=lambda x: x['confidence'], reverse=True)

    def _is_help_request(self, post: Dict) -> bool:
        """Detect if post is requesting help."""
        content = (post.get('title', '') + ' ' + post.get('content', '')).lower()

        help_indicators = [
            'need help', 'looking for', 'anyone have', 'can someone',
            'seeking', 'need expertise', 'could use', 'wondering if',
            'any suggestions', 'how to', 'struggling with'
        ]

        return any(indicator in content for indicator in help_indicators)

    def _extract_needed_skills(self, post: Dict) -> List[str]:
        """Extract what skills/tools are needed from post."""
        content = (post.get('title', '') + ' ' + post.get('content', '')).lower()

        # Tool mentions
        tool_keywords = {
            'blast': ['blast', 'sequence alignment', 'homology'],
            'pubmed': ['pubmed', 'literature', 'papers', 'publications'],
            'uniprot': ['uniprot', 'protein', 'sequence'],
            'pdb': ['pdb', 'structure', 'crystal'],
            'pubchem': ['pubchem', 'compound', 'chemical'],
            'chembl': ['chembl', 'drug', 'bioactivity'],
            'tdc': ['tdc', 'admet', 'bbb', 'permeability'],
            'rdkit': ['rdkit', 'molecular descriptor', 'fingerprint'],
            'alphafold': ['alphafold', 'structure prediction', 'af2'],
            'materials': ['materials', 'bandgap', 'dft'],
        }

        needed = []
        for tool, keywords in tool_keywords.items():
            if any(kw in content for kw in keywords):
                needed.append(tool)

        return needed

    def _can_help(self, needed_skills: List[str]) -> bool:
        """Check if agent has skills to help."""
        if not needed_skills:
            return False

        # Check if any needed skill matches agent's tools
        return any(skill in self.preferred_tools for skill in needed_skills)

    def _assess_match(self, needed_skills: List[str]) -> float:
        """Assess how well agent can help (0.0 to 1.0)."""
        if not needed_skills:
            return 0.0

        matches = sum(1 for skill in needed_skills if skill in self.preferred_tools)
        return min(1.0, matches / len(needed_skills))

    def _is_unanswered_question(self, comment: Dict, all_comments: List[Dict]) -> bool:
        """Check if comment is an unanswered question."""
        content = comment.get('content', '')

        # Is it a question?
        if '?' not in content:
            return False

        # Has it been answered?
        comment_id = comment.get('id')
        has_reply = any(
            c.get('parentId') == comment_id
            for c in all_comments
        )

        return not has_reply

    def _can_answer(self, comment: Dict) -> bool:
        """Check if agent can answer the question."""
        content = comment.get('content', '').lower()

        # Simple heuristic: check for tool/domain mentions
        keywords = self.interests + self.preferred_tools
        return any(keyword.lower() in content for keyword in keywords)

    def _is_complementary_investigation(self, post: Dict) -> bool:
        """Check if post's investigation complements agent's expertise."""
        content = (post.get('title', '') + ' ' + post.get('content', '')).lower()

        # Check for topic overlap with agent interests
        interest_overlap = sum(
            1 for interest in self.interests
            if interest.lower() in content
        )

        return interest_overlap >= 2


class CapabilityAnnouncer:
    """Posts announcements about agent's capabilities."""

    def __init__(self, agent_name: str, agent_profile: Dict, platform):
        self.agent_name = agent_name
        self.agent_profile = agent_profile
        self.platform = platform

    def announce_capabilities(self, looking_for: Optional[str] = None) -> Dict:
        """
        Post announcement about what agent can help with.

        Args:
            looking_for: Optional description of what agent seeks

        Returns:
            Post creation result
        """
        tools = self.agent_profile.get('preferred_tools', [])[:5]
        interests = self.agent_profile.get('interests', [])[:3]

        title = f"Offering: {', '.join(interests)} expertise"

        content = f"""I'm {self.agent_name}, specializing in {', '.join(interests)}.

**Tools I work with:**
{chr(10).join([f'- {tool}' for tool in tools])}

**Looking to collaborate on:**
"""

        if looking_for:
            content += f"- {looking_for}\n"
        else:
            content += f"- {interests[0]} investigations\n"
            if len(interests) > 1:
                content += f"- {interests[1]} projects\n"

        content += "\nFeel free to tag me if you need these capabilities!"

        try:
            result = self.platform.create_post(
                title=title,
                content=content,
                community='scienceclaw'
            )
            return result
        except Exception as e:
            print(f"  ⚠️  Failed to announce capabilities: {e}")
            return {'error': str(e)}


class HelpSeeker:
    """Posts questions when agent needs expertise."""

    def __init__(self, agent_name: str, platform):
        self.agent_name = agent_name
        self.platform = platform

    def seek_help(self, topic: str, needed_expertise: str, context: str) -> Dict:
        """
        Post a help request.

        Args:
            topic: What agent is investigating
            needed_expertise: What expertise is needed
            context: Background/context for the help request

        Returns:
            Post creation result
        """
        title = f"Seeking help: {needed_expertise} for {topic}"

        content = f"""I'm investigating {topic} and could use expertise in {needed_expertise}.

**Context:**
{context}

**Specifically looking for:**
- {needed_expertise} analysis
- Tool recommendations
- Interpretation guidance

If you have experience with this, please comment or DM!
"""

        try:
            result = self.platform.create_post(
                title=title,
                content=content,
                community='scienceclaw',
                hypothesis=f"Collaborative investigation of {topic}",
                method=f"Seeking {needed_expertise} expertise from community"
            )
            return result
        except Exception as e:
            print(f"  ⚠️  Failed to seek help: {e}")
            return {'error': str(e)}


class TeamFormationDetector:
    """Detects emerging collaborations in comment threads."""

    def __init__(self, agent_name: str, platform):
        self.agent_name = agent_name
        self.platform = platform

    def detect_team_formation(self, post_id: str) -> Dict:
        """
        Analyze comment thread to detect if team is forming.

        Returns:
            Dict with team_formed (bool), participants (list), signals (list)
        """
        try:
            comments = self.platform.get_comments(post_id)
        except Exception as e:
            return {'team_formed': False, 'error': str(e)}

        # Signals of team formation
        collaboration_signals = []
        participants = set([self.agent_name])

        for comment in comments:
            author = comment.get('author', '')
            content = comment.get('content', '').lower()

            participants.add(author)

            # Detect collaboration signals
            if any(phrase in content for phrase in [
                'i can help', "i'll investigate", 'let me', 'i could',
                'happy to', 'i have', 'i will', "i'd be glad"
            ]):
                collaboration_signals.append({
                    'type': 'offer_to_help',
                    'author': author
                })

            if any(phrase in content for phrase in [
                'great idea', 'that would be', 'yes please', 'sounds good',
                'let\'s collaborate', 'let\'s work', 'together'
            ]):
                collaboration_signals.append({
                    'type': 'acceptance',
                    'author': author
                })

            if any(phrase in content for phrase in [
                'you could', 'maybe', 'suggest', 'how about', 'what if'
            ]):
                collaboration_signals.append({
                    'type': 'suggestion',
                    'author': author
                })

        # Team is forming if:
        # - 2+ participants beyond post author
        # - 2+ collaboration signals (offer + acceptance, or multiple offers)
        team_formed = (
            len(participants) >= 3 and
            len(collaboration_signals) >= 2 and
            any(s['type'] == 'offer_to_help' for s in collaboration_signals)
        )

        return {
            'team_formed': team_formed,
            'participants': list(participants),
            'signal_count': len(collaboration_signals),
            'signals': collaboration_signals
        }
