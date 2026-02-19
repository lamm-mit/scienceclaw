"""
Contextual Role Adoption - Dynamic roles based on conversation needs.

Instead of static role assignment (investigator, validator, etc.), agents
determine their role based on what each specific conversation needs at that moment.
Roles emerge from context, not pre-assignment.

Example:
- Discussion needs validation → Agent becomes validator
- Discussion needs synthesis → Agent becomes synthesizer
- Discussion needs critical review → Agent becomes critic
- Discussion needs new direction → Agent becomes explorer

An agent might be a validator in one thread and a synthesizer in another,
based on what's most helpful.
"""

import json
from typing import Dict, List, Optional
from pathlib import Path


class ContextualRoleAdopter:
    """Determines agent's role based on conversation context."""

    # Role definitions with indicators
    ROLES = {
        'validator': {
            'indicators': [
                'needs validation', 'unverified', 'preliminary', 'claimed',
                'no data shown', 'source needed', 'citation needed'
            ],
            'capabilities': ['validation_skills', 'experimental_design'],
            'threshold': 0.7
        },
        'synthesizer': {
            'indicators': [
                'multiple findings', 'several approaches', 'different papers',
                'contradictory', 'conflicting', 'needs integration', 'scattered'
            ],
            'capabilities': ['synthesis_skills', 'big_picture_thinking'],
            'threshold': 0.7
        },
        'critic': {
            'indicators': [
                'assumes', 'overlooks', 'doesn\'t consider', 'ignores',
                'flawed', 'incomplete', 'oversimplified', 'bias'
            ],
            'capabilities': ['domain_expertise', 'critical_thinking'],
            'threshold': 0.8
        },
        'investigator': {
            'indicators': [
                'need more data', 'should test', 'run experiment',
                'analyze', 'investigate', 'explore', 'dig deeper'
            ],
            'capabilities': ['tool_proficiency', 'experimental_skills'],
            'threshold': 0.6
        },
        'explainer': {
            'indicators': [
                'don\'t understand', 'confusing', 'unclear', 'how does',
                'why does', 'can you explain', 'what does'
            ],
            'capabilities': ['communication_skills', 'teaching'],
            'threshold': 0.6
        },
        'contributor': {
            'indicators': [],  # Default role
            'capabilities': ['general_expertise'],
            'threshold': 0.0
        }
    }

    def __init__(self, agent_profile: Dict):
        """
        Initialize role adopter.

        Args:
            agent_profile: Agent's profile with skills and expertise
        """
        self.agent_profile = agent_profile
        self.preferred_tools = agent_profile.get('preferred_tools', [])
        self.interests = agent_profile.get('interests', [])
        self.expertise = agent_profile.get('expertise', 'mixed')

    def determine_role(self, conversation_context: Dict) -> str:
        """
        Determine what role agent should play in THIS conversation.

        Args:
            conversation_context: Dict with post, comments, thread structure

        Returns:
            Role name (validator, synthesizer, critic, etc.)
        """
        # Analyze what the conversation needs
        needs = self._analyze_conversation_needs(conversation_context)

        # Assess agent's capabilities for each role
        my_capabilities = self._assess_my_capabilities(needs)

        # Match role to needs + capabilities
        best_role = 'contributor'  # Default
        best_score = 0.0

        for role_name, role_def in self.ROLES.items():
            # Check if conversation needs this role
            need_score = needs.get(role_name + '_needed', 0.0)

            # Check if agent can fulfill this role
            capability_score = my_capabilities.get(role_name, 0.5)

            # Combined score
            combined = need_score * capability_score

            if combined > best_score and capability_score >= role_def['threshold']:
                best_score = combined
                best_role = role_name

        return best_role

    def _analyze_conversation_needs(self, context: Dict) -> Dict[str, float]:
        """
        Analyze what the conversation needs next.

        Uses keyword matching and heuristics to identify:
        - Need for validation
        - Need for synthesis
        - Need for critical review
        - Need for new investigation
        - Need for explanation
        """
        needs = {}

        # Get all text from conversation
        post = context.get('post', {})
        comments = context.get('comments', [])

        all_text = (
            post.get('title', '') + ' ' +
            post.get('content', '') + ' ' +
            ' '.join([c.get('content', '') for c in comments])
        ).lower()

        # Check for each role's indicators
        for role_name, role_def in self.ROLES.items():
            indicators = role_def['indicators']
            if not indicators:
                needs[role_name + '_needed'] = 0.0
                continue

            # Count indicator matches
            matches = sum(1 for indicator in indicators if indicator in all_text)
            need_score = min(1.0, matches / len(indicators) * 2)  # Scale up

            needs[role_name + '_needed'] = need_score

        # Additional heuristics

        # Validation needed if post has bold claims but few citations
        citation_indicators = ['pmid:', 'doi:', 'et al.', 'reference']
        citation_count = sum(1 for ind in citation_indicators if ind in all_text)
        claim_indicators = ['demonstrates', 'proves', 'shows', 'reveals', 'confirms']
        claim_count = sum(1 for ind in claim_indicators if ind in all_text)

        if claim_count > 2 and citation_count < 2:
            needs['validator_needed'] = max(needs.get('validator_needed', 0), 0.7)

        # Synthesis needed if multiple papers/findings mentioned
        paper_count = all_text.count('paper') + all_text.count('study') + all_text.count('finding')
        if paper_count >= 3:
            needs['synthesizer_needed'] = max(needs.get('synthesizer_needed', 0), 0.6)

        # Investigation needed if open questions present
        question_count = all_text.count('?')
        if question_count >= 2:
            needs['investigator_needed'] = max(needs.get('investigator_needed', 0), 0.5)

        return needs

    def _assess_my_capabilities(self, needs: Dict) -> Dict[str, float]:
        """
        Assess agent's capability to fulfill each role.

        Returns:
            Dict mapping role name to capability score (0.0 to 1.0)
        """
        capabilities = {}

        # Validator - can validate if has relevant tools
        validation_tools = ['blast', 'uniprot', 'pdb', 'alphafold', 'tdc']
        validation_skill = sum(1 for tool in validation_tools if tool in self.preferred_tools) / len(validation_tools)
        capabilities['validator'] = validation_skill

        # Synthesizer - can synthesize if has broad expertise
        synthesis_skill = len(self.preferred_tools) / 10.0  # More tools = better synthesis
        capabilities['synthesizer'] = min(1.0, synthesis_skill)

        # Critic - can critique if has domain expertise
        expertise_levels = {
            'biology': 0.8,
            'chemistry': 0.8,
            'mixed': 0.9  # Mixed agents can critique both domains
        }
        critic_skill = expertise_levels.get(self.expertise, 0.6)
        capabilities['critic'] = critic_skill

        # Investigator - can investigate if has tools
        investigator_skill = min(1.0, len(self.preferred_tools) / 5.0)
        capabilities['investigator'] = investigator_skill

        # Explainer - can explain if has communication focus
        explainer_skill = 0.6  # Baseline for all agents
        capabilities['explainer'] = explainer_skill

        # Contributor - default
        capabilities['contributor'] = 0.5

        return capabilities

    def get_role_guidance(self, role: str) -> str:
        """
        Get guidance for how to act in a given role.

        Returns:
            String describing role behavior
        """
        guidance = {
            'validator': """Act as a validator:
- Request specific data/sources for claims
- Suggest validation experiments
- Check methodology rigor
- Verify citations
- Point out missing controls""",

            'synthesizer': """Act as a synthesizer:
- Integrate multiple findings
- Identify common themes
- Reconcile contradictions
- Build unified model
- Connect disparate pieces""",

            'critic': """Act as a critic:
- Question assumptions
- Identify gaps in logic
- Point out alternative explanations
- Challenge oversimplifications
- Highlight confounding factors""",

            'investigator': """Act as an investigator:
- Propose new experiments
- Suggest tools/approaches
- Offer to run analyses
- Identify next steps
- Design follow-up studies""",

            'explainer': """Act as an explainer:
- Clarify complex concepts
- Provide background context
- Use analogies
- Break down mechanisms
- Answer questions clearly""",

            'contributor': """Act as a contributor:
- Share relevant knowledge
- Add complementary perspectives
- Build on others' ideas
- Offer constructive feedback
- Support collaborative progress"""
        }

        return guidance.get(role, guidance['contributor'])

    def format_comment_with_role(self, role: str, comment_content: str) -> str:
        """
        Format comment to indicate role (optional - for transparency).

        Args:
            role: Role name
            comment_content: Raw comment text

        Returns:
            Formatted comment
        """
        # Optional: Add subtle role indicator
        # Most of the time, let role emerge naturally without explicit labeling

        # Only label if role is very specific (critic, validator)
        if role in ['validator', 'critic']:
            return f"[{role.title()} perspective]\n\n{comment_content}"

        return comment_content
