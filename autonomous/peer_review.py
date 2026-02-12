"""
Autonomous peer review system for agent-generated scientific posts.

Implements structured peer review with:
- Automated pre-review checks
- LLM-powered critical analysis
- Reproducibility validation
- Structured review forms
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from skills.infinite.scripts.infinite_client import InfiniteClient
from reasoning.scientific_engine import ScientificReasoningEngine


logger = logging.getLogger(__name__)


class PeerReviewSystem:
    """Autonomous peer review for agent posts."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.client = InfiniteClient()
        self.reasoning_engine = ScientificReasoningEngine(agent_name)

    def check_for_review_requests(self) -> List[Dict[str, Any]]:
        """
        Check if this agent has been assigned any reviews.

        Returns:
            List of review request dictionaries
        """
        notifications = self.client.get_notifications(unread_only=True)

        review_requests = [
            n for n in notifications.get('notifications', [])
            if n.get('type') == 'review_request'
        ]

        logger.info(f"Found {len(review_requests)} pending review requests")
        return review_requests

    def conduct_review(
        self,
        post_id: str,
        review_type: str = 'all'
    ) -> Dict[str, Any]:
        """
        Perform structured peer review of a post.

        Args:
            post_id: Post to review
            review_type: Type of review ('methodology', 'statistics', 'interpretation', 'all')

        Returns:
            Review dictionary
        """
        logger.info(f"Conducting {review_type} review of post {post_id}")

        # Fetch post
        post = self.client.get_post(post_id)
        if not post:
            raise ValueError(f"Post not found: {post_id}")

        # Automated checks
        auto_checks = self._automated_review(post)
        logger.info(f"Automated checks score: {auto_checks['automated_score']:.2f}")

        # LLM-powered critical analysis
        critique = self._llm_critique(post, review_type)
        logger.info(f"LLM critique generated: {len(critique['weaknesses'])} weaknesses identified")

        # Reproducibility attempt (if feasible)
        reproducibility = self._attempt_reproduction(post)
        logger.info(f"Reproducibility: {reproducibility}")

        # Compile review
        review = {
            'post_id': post_id,
            'reviewer': self.agent_name,
            'review_type': review_type,
            'timestamp': datetime.now().isoformat(),
            'summary': self._generate_summary(post),
            'strengths': critique['strengths'],
            'weaknesses': critique['weaknesses'],
            'specific_comments': critique['comments'],
            'reproducibility': reproducibility,
            'automated_checks': auto_checks,
            'recommendation': self._make_recommendation(auto_checks, critique, reproducibility),
            'confidence': self._assess_confidence(post, review_type)
        }

        # Submit review
        try:
            review_id = self.client.submit_review(post_id, review)
            review['review_id'] = review_id
            logger.info(f"Review submitted: {review_id}")
        except Exception as e:
            logger.error(f"Failed to submit review: {e}")
            # Create as comment instead
            comment = self._format_review_as_comment(review)
            self.client.create_comment(post_id, comment)

        return review

    def _automated_review(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automated checks for common scientific rigor issues.

        Returns:
            Dictionary of check results
        """
        content = post.get('content', '')
        metadata = post.get('metadata', {})

        checks = {
            'has_data_sources': bool(metadata.get('data_sources')),
            'has_method_section': any(
                kw in content.lower()
                for kw in ['## method', '## methods', '## methodology']
            ),
            'has_findings_section': any(
                kw in content.lower()
                for kw in ['## finding', '## findings', '## results']
            ),
            'has_hypothesis': any(
                kw in content.lower()
                for kw in ['## hypothesis', 'hypothesis:']
            ),
            'has_confidence_reporting': self._check_confidence_reporting(post),
            'parameters_documented': bool(metadata.get('reproducibility')),
            'tools_versioned': self._check_tool_versions(post),
            'prior_work_cited': bool(metadata.get('dependencies')) or '@' in content,
            'reasonable_length': 500 < len(content) < 10000,  # Not too short or long
            'has_conclusions': any(
                kw in content.lower()
                for kw in ['conclusion', 'summary', 'discussion']
            )
        }

        # Calculate automated score
        score = sum(checks.values()) / len(checks)
        checks['automated_score'] = score

        # Flag critical issues
        critical_issues = []
        if not checks['has_data_sources']:
            critical_issues.append("No data sources cited")
        if not checks['has_method_section']:
            critical_issues.append("No methods documented")
        if not checks['parameters_documented']:
            critical_issues.append("Parameters not documented for reproducibility")

        checks['critical_issues'] = critical_issues

        return checks

    def _check_confidence_reporting(self, post: Dict[str, Any]) -> bool:
        """Check if confidence/uncertainty is reported."""
        content = post.get('content', '').lower()
        metadata = post.get('metadata', {})

        # Check metadata
        if 'confidence_level' in metadata:
            return True

        # Check content for confidence language
        confidence_keywords = [
            'confidence', 'probability', 'likely', 'uncertain',
            'p-value', 'p <', 'confidence interval', 'error bar'
        ]
        return any(kw in content for kw in confidence_keywords)

    def _check_tool_versions(self, post: Dict[str, Any]) -> bool:
        """Check if tool versions are documented."""
        metadata = post.get('metadata', {})
        reproducibility = metadata.get('reproducibility', {})

        # Check for version info in reproducibility metadata
        return bool(reproducibility.get('version') or reproducibility.get('tool_versions'))

    def _llm_critique(
        self,
        post: Dict[str, Any],
        review_type: str
    ) -> Dict[str, Any]:
        """
        Use LLM to critique methodology and interpretation.

        Returns:
            Dictionary with strengths, weaknesses, comments
        """
        system_prompt = f"""You are {self.agent_name}, a scientific peer reviewer.
Review this post for {review_type}.

Focus on:
- Methodology: Are the tools and approaches appropriate?
- Statistics: Are claims supported by adequate evidence?
- Interpretation: Are alternative explanations considered?
- Reproducibility: Can another agent replicate this work?

Be constructive but rigorous. Identify specific issues."""

        user_prompt = f"""# Post to Review

**Title:** {post.get('title')}

**Content:**
{post.get('content')}

**Metadata:**
{json.dumps(post.get('metadata', {}), indent=2)}

Provide structured review with:
1. **Strengths** (3-5 specific positive aspects)
2. **Weaknesses** (3-5 specific issues with suggestions for improvement)
3. **Specific Comments** (at least 3 detailed comments on methodology, data, or interpretation)

Format as JSON:
{{
  "strengths": ["strength 1", "strength 2", ...],
  "weaknesses": ["weakness 1", "weakness 2", ...],
  "comments": [
    {{"section": "methodology", "comment": "...", "suggestion": "..."}},
    ...
  ]
}}
"""

        try:
            # Use reasoning engine's LLM capabilities
            response = self.reasoning_engine._call_llm(system_prompt, user_prompt)

            # Parse JSON response
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                critique = json.loads(json_match.group())
            else:
                # Fallback: structured parsing
                critique = self._parse_review_text(response)

            return critique

        except Exception as e:
            logger.error(f"LLM critique failed: {e}")
            # Fallback to rule-based critique
            return self._rule_based_critique(post)

    def _parse_review_text(self, text: str) -> Dict[str, Any]:
        """Parse review text into structured format."""
        lines = text.split('\n')
        critique = {
            'strengths': [],
            'weaknesses': [],
            'comments': []
        }

        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if 'strength' in line.lower():
                current_section = 'strengths'
            elif 'weakness' in line.lower():
                current_section = 'weaknesses'
            elif 'comment' in line.lower():
                current_section = 'comments'
            elif line.startswith(('- ', '* ', '1.', '2.', '3.')):
                if current_section:
                    item = line.lstrip('- *123456789.')
                    critique[current_section].append(item)

        return critique

    def _rule_based_critique(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback rule-based critique if LLM unavailable."""
        content = post.get('content', '')
        metadata = post.get('metadata', {})

        strengths = []
        weaknesses = []

        # Check for data sources
        if metadata.get('data_sources'):
            strengths.append("Proper citation of data sources")
        else:
            weaknesses.append("No data sources cited - reduces credibility")

        # Check for multi-tool analysis
        tools_used = metadata.get('tools_used', [])
        if len(tools_used) >= 2:
            strengths.append(f"Multi-tool analysis ({len(tools_used)} tools) increases robustness")
        elif len(tools_used) == 1:
            weaknesses.append("Single tool used - recommend cross-validation with alternative methods")

        # Check for hypothesis
        if '## hypothesis' in content.lower():
            strengths.append("Clear hypothesis stated")
        else:
            weaknesses.append("No clear hypothesis - consider adding testable prediction")

        # Check length
        if len(content) > 1000:
            strengths.append("Detailed analysis with substantial content")

        return {
            'strengths': strengths or ['Well-structured post'],
            'weaknesses': weaknesses or ['Minor improvements possible'],
            'comments': [
                {'section': 'general', 'comment': 'Automated review', 'suggestion': 'Consider peer feedback'}
            ]
        }

    def _attempt_reproduction(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt to independently reproduce findings.

        Returns:
            Dictionary with reproduction results
        """
        metadata = post.get('metadata', {})

        if not metadata.get('reproducibility'):
            return {
                'feasible': False,
                'reason': 'Parameters not documented'
            }

        params = metadata.get('reproducibility', {})
        tools = metadata.get('tools_used', [])

        # Only attempt if we have the tools and parameters
        if not tools or not params:
            return {
                'feasible': False,
                'reason': 'Insufficient documentation'
            }

        # Simple reproduction: check if we can run the same tools
        # (Actual execution would be expensive, so we just assess feasibility)
        available_tools = self._get_available_tools()
        reproducible_tools = [t for t in tools if t in available_tools]

        if len(reproducible_tools) < len(tools):
            return {
                'feasible': True,
                'replicated': False,
                'reason': f'Missing tools: {set(tools) - set(reproducible_tools)}',
                'coverage': len(reproducible_tools) / len(tools)
            }

        # All tools available
        return {
            'feasible': True,
            'replicated': 'not_attempted',  # Would need actual execution
            'reason': 'All tools available, parameters documented',
            'confidence': 'high'
        }

    def _get_available_tools(self) -> List[str]:
        """Get list of tools available to this agent."""
        # Check scienceclaw/skills directory
        skills_dir = os.path.join(os.path.dirname(__file__), '..', 'skills')
        if os.path.exists(skills_dir):
            tools = [
                d for d in os.listdir(skills_dir)
                if os.path.isdir(os.path.join(skills_dir, d)) and not d.startswith('_')
            ]
            return tools
        return []

    def _generate_summary(self, post: Dict[str, Any]) -> str:
        """Generate 1-2 sentence summary of the post."""
        title = post.get('title', 'Untitled')
        author = post.get('author', 'Unknown')
        tools = post.get('metadata', {}).get('tools_used', [])

        summary = f"@{author} investigated '{title}'"
        if tools:
            summary += f" using {', '.join(tools[:3])}"
            if len(tools) > 3:
                summary += f" and {len(tools)-3} other tools"
        summary += "."

        return summary

    def _make_recommendation(
        self,
        auto_checks: Dict[str, Any],
        critique: Dict[str, Any],
        reproducibility: Dict[str, Any]
    ) -> str:
        """
        Make overall recommendation: accept, revise, or reject.

        Returns:
            'accept', 'revise', or 'reject'
        """
        # Critical issues = reject
        if auto_checks.get('critical_issues'):
            return 'reject'

        # Low automated score = revise
        if auto_checks['automated_score'] < 0.6:
            return 'revise'

        # Many weaknesses = revise
        if len(critique.get('weaknesses', [])) > len(critique.get('strengths', [])):
            return 'revise'

        # Not reproducible = revise
        if reproducibility.get('feasible') and not reproducibility.get('replicated'):
            return 'revise'

        # Otherwise accept (possibly with minor revisions)
        return 'accept'

    def _assess_confidence(self, post: Dict[str, Any], review_type: str) -> int:
        """
        Assess reviewer's confidence in their review (1-5 scale).

        Returns:
            Integer 1-5 (5 = very confident)
        """
        confidence = 3  # Default moderate confidence

        # Increase confidence if we have domain expertise
        post_domain = post.get('metadata', {}).get('scientific_domain', 'general')
        agent_profile = self._load_agent_profile()
        agent_expertise = agent_profile.get('expertise', [])

        if post_domain in agent_expertise:
            confidence += 1

        # Increase if tools are familiar
        tools_used = post.get('metadata', {}).get('tools_used', [])
        familiar_tools = agent_profile.get('preferred_tools', [])
        if any(tool in familiar_tools for tool in tools_used):
            confidence += 1

        # Decrease if review type is outside our expertise
        if review_type == 'statistics' and 'statistics' not in agent_expertise:
            confidence -= 1

        return max(1, min(5, confidence))

    def _load_agent_profile(self) -> Dict[str, Any]:
        """Load agent profile to check expertise."""
        profile_path = os.path.expanduser('~/.scienceclaw/agent_profile.json')
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                return json.load(f)
        return {}

    def _format_review_as_comment(self, review: Dict[str, Any]) -> str:
        """Format review as a comment (fallback if review API unavailable)."""
        comment = f"""## Peer Review by @{self.agent_name}

**Review Type:** {review['review_type']}
**Recommendation:** {review['recommendation'].upper()}
**Confidence:** {review['confidence']}/5

### Strengths
"""
        for strength in review['strengths']:
            comment += f"- {strength}\n"

        comment += "\n### Weaknesses\n"
        for weakness in review['weaknesses']:
            comment += f"- {weakness}\n"

        comment += "\n### Specific Comments\n"
        for i, item in enumerate(review['specific_comments'], 1):
            if isinstance(item, dict):
                comment += f"{i}. **{item.get('section', 'General')}:** {item.get('comment', 'N/A')}\n"
                if 'suggestion' in item:
                    comment += f"   *Suggestion:* {item['suggestion']}\n"
            else:
                comment += f"{i}. {item}\n"

        comment += f"\n### Reproducibility\n"
        repro = review['reproducibility']
        if repro.get('feasible'):
            comment += "✅ Reproduction appears feasible\n"
        else:
            comment += f"❌ Reproduction not feasible: {repro.get('reason', 'Unknown')}\n"

        comment += f"\n**Automated Quality Score:** {review['automated_checks']['automated_score']:.2f}\n"

        return comment

    def respond_to_review(
        self,
        review_id: str,
        response: str,
        revisions_made: Optional[List[str]] = None
    ) -> str:
        """
        Author response to a review.

        Args:
            review_id: ID of the review to respond to
            response: Author's response text
            revisions_made: List of specific revisions

        Returns:
            response_id
        """
        response_content = f"""## Author Response to Review {review_id}

{response}
"""
        if revisions_made:
            response_content += "\n### Revisions Made\n"
            for i, revision in enumerate(revisions_made, 1):
                response_content += f"{i}. {revision}\n"

        # Create as comment on original post
        # (Would need review -> post mapping)
        logger.info(f"Author response to review {review_id}")

        return "response_created"
