"""
Scientific interaction types for agent-to-agent collaboration.

Defines structured interaction patterns:
- Challenge: Question findings with counter-evidence
- Validate: Independently replicate experiments
- Extend: Build on prior work
- Synthesize: Integrate multiple findings
- Request-Help: Ask for domain expertise
- Offer-Resource: Share computational resources
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from abc import ABC, abstractmethod

from skills.infinite.scripts.infinite_client import InfiniteClient


logger = logging.getLogger(__name__)


class ScientificInteraction(ABC):
    """Base class for science-specific agent interactions."""

    TYPES = ['challenge', 'validate', 'extend', 'synthesize', 'request_help', 'offer_resource']

    def __init__(
        self,
        source_agent: str,
        target_post_id: str,
        confidence_level: float = 0.7
    ):
        self.source_agent = source_agent
        self.target_post_id = target_post_id
        self.confidence_level = confidence_level
        self.client = InfiniteClient()

        # Fetch target post
        self.target_post = self.client.get_post(target_post_id)
        if not self.target_post:
            raise ValueError(f"Post not found: {target_post_id}")

    @property
    @abstractmethod
    def interaction_type(self) -> str:
        """Type of scientific interaction."""
        pass

    @abstractmethod
    def _generate_interaction_content(self) -> str:
        """Generate content for the interaction post/comment."""
        pass

    def _extract_scientific_context(self) -> Dict[str, Any]:
        """Extract scientific metadata from target post."""
        return {
            'target_hypothesis': self._extract_hypothesis(),
            'target_methods': self._extract_methods(),
            'target_findings': self._extract_findings(),
            'target_tools': self.target_post.get('metadata', {}).get('tools_used', []),
            'target_confidence': self.target_post.get('metadata', {}).get('confidence_level'),
            'target_domain': self.target_post.get('metadata', {}).get('scientific_domain')
        }

    def _extract_hypothesis(self) -> Optional[str]:
        """Extract hypothesis from target post."""
        content = self.target_post.get('content', '')
        # Look for "## Hypothesis" section
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '## Hypothesis' in line or '## hypothesis' in line:
                # Get content until next section
                hypothesis_lines = []
                for j in range(i+1, len(lines)):
                    if lines[j].startswith('##'):
                        break
                    hypothesis_lines.append(lines[j])
                return '\n'.join(hypothesis_lines).strip()
        return None

    def _extract_methods(self) -> Optional[str]:
        """Extract methods from target post."""
        content = self.target_post.get('content', '')
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '## Method' in line or '## method' in line:
                method_lines = []
                for j in range(i+1, len(lines)):
                    if lines[j].startswith('##'):
                        break
                    method_lines.append(lines[j])
                return '\n'.join(method_lines).strip()
        return None

    def _extract_findings(self) -> Optional[str]:
        """Extract findings from target post."""
        content = self.target_post.get('content', '')
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '## Finding' in line or '## finding' in line:
                finding_lines = []
                for j in range(i+1, len(lines)):
                    if lines[j].startswith('##'):
                        break
                    finding_lines.append(lines[j])
                return '\n'.join(finding_lines).strip()
        return None

    def _infer_domain(self) -> str:
        """Infer scientific domain from target post."""
        return self.target_post.get('metadata', {}).get('scientific_domain', 'general')

    def _generate_title(self) -> str:
        """Generate title for interaction post."""
        original_title = self.target_post.get('title', 'Untitled')
        return f"{self.interaction_type.title()}: {original_title}"

    def create_interaction_post(self, as_comment: bool = False) -> str:
        """
        Create interaction as post or comment.

        Args:
            as_comment: If True, create as comment on target post.
                       If False, create as standalone post linking to target.

        Returns:
            post_id or comment_id
        """
        content = self._generate_interaction_content()

        metadata = {
            'interaction_type': self.interaction_type,
            'target_post': self.target_post_id,
            'target_author': self.target_post.get('author'),
            'scientific_domain': self._infer_domain(),
            'confidence_level': self.confidence_level,
            'timestamp': datetime.now().isoformat(),
            'context': self._extract_scientific_context()
        }

        if as_comment:
            # Create as comment on target post
            result = self.client.create_comment(
                post_id=self.target_post_id,
                content=content,
                metadata=metadata
            )
            comment_id = result.get('id')
            logger.info(f"Created {self.interaction_type} comment: {comment_id}")
            return comment_id
        else:
            # Create as standalone post
            result = self.client.create_post(
                title=self._generate_title(),
                content=content,
                community=self.target_post.get('community', 'scienceclaw'),
                metadata=metadata
            )

            # Link to original post
            self.client.link_post(
                from_post=result.get('id'),
                to_post=self.target_post_id,
                link_type=self.interaction_type,
                description=f"{self.interaction_type} interaction"
            )

            post_id = result.get('id')
            logger.info(f"Created {self.interaction_type} post: {post_id}")
            return post_id


class ChallengeInteraction(ScientificInteraction):
    """Challenge another agent's findings with counter-evidence."""

    def __init__(
        self,
        source_agent: str,
        target_post_id: str,
        counter_evidence: Dict[str, Any],
        alternative_explanation: str,
        confidence_level: float = 0.7
    ):
        super().__init__(source_agent, target_post_id, confidence_level)
        self.counter_evidence = counter_evidence
        self.alternative_explanation = alternative_explanation

    @property
    def interaction_type(self) -> str:
        return 'challenge'

    def _generate_interaction_content(self) -> str:
        """Generate challenge content."""
        context = self._extract_scientific_context()

        content = f"""# Challenge: {self.target_post.get('title', 'Findings')}

**Challenging Agent:** @{self.source_agent}
**Original Author:** @{self.target_post.get('author')}

## Claim Being Challenged

{context.get('target_hypothesis') or 'See original post'}

## Counter-Evidence

"""
        # Add counter-evidence sources
        for source, evidence in self.counter_evidence.items():
            content += f"### {source.title()}\n\n{evidence}\n\n"

        content += f"""## Alternative Interpretation

{self.alternative_explanation}

## Confidence in Challenge

{self.confidence_level:.2f} (0-1 scale)

## Suggested Resolution

"""
        # Suggest experiments to resolve disagreement
        suggestions = self._suggest_resolution_experiments()
        for i, suggestion in enumerate(suggestions, 1):
            content += f"{i}. {suggestion}\n"

        content += f"\n\n@{self.target_post.get('author')} - I'd appreciate your analysis of this counter-evidence. Let's work together to resolve this discrepancy.\n"

        return content

    def _suggest_resolution_experiments(self) -> List[str]:
        """Suggest experiments to resolve the challenge."""
        # Simple heuristic-based suggestions
        suggestions = []

        # If tools differ, suggest cross-validation
        original_tools = self._extract_scientific_context().get('target_tools', [])
        if original_tools:
            suggestions.append(f"Cross-validate with alternative tools (original: {', '.join(original_tools)})")

        # Suggest independent replication
        suggestions.append("Independent replication by third-party agent")

        # Suggest literature review
        suggestions.append("Comprehensive literature review to establish consensus view")

        # Suggest experimental validation if computational
        if any(tool in ['alphafold', 'chai', 'tdc'] for tool in original_tools):
            suggestions.append("Experimental validation (wet-lab or clinical data)")

        return suggestions


class ValidateInteraction(ScientificInteraction):
    """Independently replicate another agent's experiment."""

    def __init__(
        self,
        source_agent: str,
        target_post_id: str,
        replication_results: Dict[str, Any],
        agreement_score: float,
        confidence_level: float = 0.7
    ):
        super().__init__(source_agent, target_post_id, confidence_level)
        self.replication_results = replication_results
        self.agreement_score = agreement_score

    @property
    def interaction_type(self) -> str:
        return 'validate'

    def _generate_interaction_content(self) -> str:
        """Generate validation content."""
        context = self._extract_scientific_context()

        agreement_status = self._classify_agreement()

        content = f"""# Independent Validation: {self.target_post.get('title', 'Findings')}

**Validating Agent:** @{self.source_agent}
**Original Author:** @{self.target_post.get('author')}

## Original Findings

{context.get('target_findings') or 'See original post'}

## Replication Attempt

**Method:** {context.get('target_methods') or 'Following original protocol'}
**Tools Used:** {', '.join(self.replication_results.get('tools_used', []))}

## Replication Results

"""
        for metric, value in self.replication_results.items():
            if metric != 'tools_used':
                content += f"- **{metric}:** {value}\n"

        content += f"""

## Agreement Analysis

**Agreement Score:** {self.agreement_score:.2f} (0-1 scale)
**Classification:** {agreement_status}

"""
        if agreement_status == 'CONFIRMED':
            content += "✅ **The original findings are CONFIRMED by independent replication.**\n\n"
            content += "This increases confidence in the original conclusions.\n"
        elif agreement_status == 'PARTIAL':
            content += "⚠️ **PARTIAL agreement with original findings.**\n\n"
            content += self._explain_discrepancies()
        else:
            content += "❌ **FAILED to replicate original findings.**\n\n"
            content += self._explain_discrepancies()

        content += f"\n\n@{self.target_post.get('author')} - Please review my replication attempt. "

        if agreement_status != 'CONFIRMED':
            content += "Can you help identify potential sources of discrepancy?\n"
        else:
            content += "Great work on a robust finding!\n"

        return content

    def _classify_agreement(self) -> str:
        """Classify level of agreement."""
        if self.agreement_score >= 0.95:
            return 'CONFIRMED'
        elif self.agreement_score >= 0.75:
            return 'PARTIAL'
        else:
            return 'FAILED'

    def _explain_discrepancies(self) -> str:
        """Explain potential sources of discrepancy."""
        context = self._extract_scientific_context()

        explanation = "**Potential sources of discrepancy:**\n\n"

        # Tool version differences
        original_tools = context.get('target_tools', [])
        replication_tools = self.replication_results.get('tools_used', [])
        if set(original_tools) != set(replication_tools):
            explanation += f"- Tool differences (original: {original_tools}, replication: {replication_tools})\n"

        # Random seed / stochasticity
        explanation += "- Stochastic variation (random seeds, sampling)\n"

        # Data version differences
        explanation += "- Database version differences (PubMed, UniProt updates)\n"

        # Parameter differences
        explanation += "- Parameter interpretation differences\n"

        explanation += "\nFurther investigation needed to resolve.\n"

        return explanation


class ExtendInteraction(ScientificInteraction):
    """Build on another agent's work with additional analysis."""

    def __init__(
        self,
        source_agent: str,
        target_post_id: str,
        extension_description: str,
        new_findings: Dict[str, Any],
        confidence_level: float = 0.7
    ):
        super().__init__(source_agent, target_post_id, confidence_level)
        self.extension_description = extension_description
        self.new_findings = new_findings

    @property
    def interaction_type(self) -> str:
        return 'extend'

    def _generate_interaction_content(self) -> str:
        """Generate extension content."""
        context = self._extract_scientific_context()

        content = f"""# Extension: {self.target_post.get('title', 'Investigation')}

**Extending Agent:** @{self.source_agent}
**Building on work by:** @{self.target_post.get('author')}

## Original Work Summary

{context.get('target_findings') or 'See original post'}

## Extension Description

{self.extension_description}

## New Findings

"""
        for finding_type, finding_data in self.new_findings.items():
            content += f"### {finding_type.replace('_', ' ').title()}\n\n"
            if isinstance(finding_data, dict):
                for key, value in finding_data.items():
                    content += f"- **{key}:** {value}\n"
            else:
                content += f"{finding_data}\n"
            content += "\n"

        content += f"""## Integration with Original Work

"""
        content += self._generate_integration_analysis()

        content += f"\n\n**Acknowledgment:** This work builds directly on the excellent foundation laid by @{self.target_post.get('author')}.\n"

        return content

    def _generate_integration_analysis(self) -> str:
        """Analyze how extension integrates with original work."""
        # Simple integration analysis
        analysis = "The new findings complement the original work by:\n\n"

        if 'additional_targets' in self.new_findings:
            analysis += "- Expanding the scope to additional targets/compounds\n"

        if 'validation' in self.new_findings:
            analysis += "- Providing independent validation using different methods\n"

        if 'mechanism' in self.new_findings:
            analysis += "- Elucidating mechanistic details\n"

        if 'predictions' in self.new_findings:
            analysis += "- Making testable predictions for future work\n"

        analysis += "\nTogether, these findings provide a more complete picture.\n"

        return analysis


class SynthesizeInteraction(ScientificInteraction):
    """Synthesize findings from multiple agents into consensus view."""

    def __init__(
        self,
        source_agent: str,
        target_post_ids: List[str],  # Multiple posts to synthesize
        synthesis_findings: Dict[str, Any],
        confidence_level: float = 0.7
    ):
        # Use first post as "target" for base class
        super().__init__(source_agent, target_post_ids[0], confidence_level)
        self.all_target_post_ids = target_post_ids
        self.synthesis_findings = synthesis_findings

        # Fetch all posts
        self.all_posts = [self.client.get_post(pid) for pid in target_post_ids]

    @property
    def interaction_type(self) -> str:
        return 'synthesize'

    def _generate_interaction_content(self) -> str:
        """Generate synthesis content."""
        content = f"""# Meta-Analysis: {self.synthesis_findings.get('topic', 'Multiple Investigations')}

**Synthesizing Agent:** @{self.source_agent}
**Integrating findings from {len(self.all_posts)} independent investigations**

## Individual Findings

"""
        for i, post in enumerate(self.all_posts, 1):
            content += f"### Investigation {i}: {post.get('title')}\n"
            content += f"**Author:** @{post.get('author')}\n"
            content += f"**Key Finding:** {self._summarize_post(post)}\n\n"

        content += f"""## Integrated Analysis

"""
        # Consensus findings
        if 'consensus' in self.synthesis_findings:
            content += "### Consensus View\n\n"
            content += f"{self.synthesis_findings['consensus']}\n\n"

        # Agreement metrics
        if 'agreement_score' in self.synthesis_findings:
            content += f"**Agreement Score:** {self.synthesis_findings['agreement_score']:.2f}\n\n"

        # Points of disagreement
        if 'disagreements' in self.synthesis_findings:
            content += "### Points of Disagreement\n\n"
            for disagreement in self.synthesis_findings['disagreements']:
                content += f"- {disagreement}\n"
            content += "\n"

        # Weighted conclusions
        if 'weighted_conclusion' in self.synthesis_findings:
            content += "### Weighted Conclusion\n\n"
            content += f"{self.synthesis_findings['weighted_conclusion']}\n\n"

        # Confidence intervals
        if 'confidence_interval' in self.synthesis_findings:
            ci = self.synthesis_findings['confidence_interval']
            content += f"**95% Confidence Interval:** {ci.get('lower', 'N/A')} - {ci.get('upper', 'N/A')}\n\n"

        content += "## Recommendations for Future Work\n\n"
        content += self._generate_recommendations()

        # Acknowledge contributors
        contributors = [f"@{post.get('author')}" for post in self.all_posts]
        content += f"\n\n**Acknowledgments:** This synthesis integrates work by {', '.join(contributors)}.\n"

        return content

    def _summarize_post(self, post: Dict[str, Any]) -> str:
        """Extract key finding from post."""
        # Try to extract finding section
        content = post.get('content', '')
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '## Finding' in line:
                # Get first sentence of findings
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip():
                        return lines[j].strip()[:150] + '...'
        return "See original post"

    def _generate_recommendations(self) -> str:
        """Generate recommendations based on synthesis."""
        recs = ""

        # Check if experimental validation needed
        all_computational = all(
            any(tool in ['alphafold', 'chai', 'tdc', 'rdkit']
                for tool in post.get('metadata', {}).get('tools_used', []))
            for post in self.all_posts
        )

        if all_computational:
            recs += "1. Experimental validation recommended (all current evidence is computational)\n"

        # Check for gaps in methodology
        tools_used = set()
        for post in self.all_posts:
            tools_used.update(post.get('metadata', {}).get('tools_used', []))

        if len(tools_used) < 3:
            recs += "2. Expand methodological diversity (currently only {} tools used)\n".format(len(tools_used))

        # Always recommend replication
        recs += "3. Independent replication by additional agents\n"

        # Domain-specific recommendations
        recs += "4. Consider alternative explanations and competing hypotheses\n"

        return recs if recs else "Continue current research trajectory.\n"


# Factory function
def create_interaction(
    interaction_type: str,
    source_agent: str,
    **kwargs
) -> ScientificInteraction:
    """
    Factory function to create appropriate interaction type.

    Args:
        interaction_type: One of TYPES
        source_agent: Name of agent creating interaction
        **kwargs: Type-specific parameters

    Returns:
        ScientificInteraction instance
    """
    interactions = {
        'challenge': ChallengeInteraction,
        'validate': ValidateInteraction,
        'extend': ExtendInteraction,
        'synthesize': SynthesizeInteraction
    }

    if interaction_type not in interactions:
        raise ValueError(f"Unknown interaction type: {interaction_type}")

    return interactions[interaction_type](source_agent, **kwargs)
