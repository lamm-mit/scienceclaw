#!/usr/bin/env python3
"""
Dynamic Role Manager - Intelligent Role Assignment

Assigns complementary roles to agents based on:
- Skills (what tools they have)
- Personality (curiosity style, communication style)
- Session needs (what roles are already filled)
- Agent expertise (domain knowledge)

Roles: investigator, validator, critic, synthesizer, screener

Author: ScienceClaw Team
"""

from typing import Dict, List, Any, Optional, Set
from enum import Enum


class AgentRole(Enum):
    """Available roles in collaborative sessions."""
    INVESTIGATOR = "investigator"
    VALIDATOR = "validator"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"
    SCREENER = "screener"


class RoleManager:
    """
    Assigns dynamic roles to agents based on skills and personality.

    Roles define how agents contribute to collaborative sessions:
    - Investigator: Conducts primary research, explores hypotheses
    - Validator: Independently verifies findings via different methods
    - Critic: Challenges findings, proposes alternatives
    - Synthesizer: Integrates findings into coherent narrative
    - Screener: Runs parallel high-throughput tasks
    """

    # Role definitions: requirements and responsibilities
    ROLES = {
        AgentRole.INVESTIGATOR: {
            "description": "Primary investigation and hypothesis testing",
            "skills_needed": ["pubmed", "uniprot", "pubchem"],  # Recommended, not required
            "personality_match": ["explorer", "deep-diver"],
            "responsibilities": [
                "Conduct primary investigation",
                "Generate and test hypotheses",
                "Post findings with full evidence",
                "Identify knowledge gaps"
            ],
            "priority": 1  # First role to assign
        },
        AgentRole.VALIDATOR: {
            "description": "Independent verification and replication",
            "skills_needed": ["alphafold", "chai", "tdc"],
            "personality_match": ["systematic", "skeptic"],
            "responsibilities": [
                "Independently verify findings",
                "Use different tools/methods than original investigator",
                "Assess confidence levels",
                "Validate mechanistic claims"
            ],
            "priority": 2
        },
        AgentRole.CRITIC: {
            "description": "Challenge findings, identify flaws, propose alternatives",
            "skills_needed": ["pubmed", "arxiv"],
            "personality_match": ["skeptic", "connector"],
            "responsibilities": [
                "Critically examine findings",
                "Identify logical flaws or missing evidence",
                "Propose alternative hypotheses",
                "Question assumptions"
            ],
            "priority": 3
        },
        AgentRole.SYNTHESIZER: {
            "description": "Integrate findings into coherent narrative",
            "skills_needed": ["datavis", "websearch"],
            "personality_match": ["connector", "deep-diver"],
            "responsibilities": [
                "Synthesize findings from all agents",
                "Create coherent narrative",
                "Highlight consensus and disagreements",
                "Identify open questions for future work"
            ],
            "priority": 4
        },
        AgentRole.SCREENER: {
            "description": "Parallel high-throughput task execution",
            "skills_needed": ["tdc", "pubchem", "chembl"],
            "personality_match": ["systematic", "explorer"],
            "responsibilities": [
                "Execute parallel similar tasks",
                "Screen compounds/sequences",
                "Aggregate results",
                "Report summary statistics"
            ],
            "priority": 5
        }
    }

    def __init__(self):
        """Initialize role manager."""
        print(f"[RoleManager] Initialized with {len(self.ROLES)} roles")

    def suggest_role(
        self,
        agent_profile: Dict[str, Any],
        session_info: Optional[Dict[str, Any]] = None
    ) -> tuple:
        """
        Suggest a role for an agent based on profile and session needs.

        Args:
            agent_profile: Agent profile with:
                - preferred_tools: List of tool names (skills)
                - curiosity_style: "explorer", "deep-diver", "connector", "skeptic"
                - domain: "biology", "chemistry", "mixed"
                - interests: List of research interests
            session_info: Optional session state to check filled roles

        Returns:
            (role_name, score, reasoning) tuple
        """
        agent_skills = set(agent_profile.get("preferred_tools", []))
        curiosity = agent_profile.get("curiosity_style", "explorer")
        domain = agent_profile.get("domain", "mixed")

        # Score each role
        scored_roles = []

        for role, requirements in self.ROLES.items():
            score = 0.0
            reasons = []

            # Skill match (0-2 points)
            needed_skills = set(requirements["skills_needed"])
            skill_overlap = len(agent_skills & needed_skills)
            if skill_overlap > 0:
                score += min(2.0, skill_overlap / len(needed_skills) * 2)
                reasons.append(f"Skills: {skill_overlap}/{len(needed_skills)} match")
            else:
                reasons.append("Skills: No direct match")

            # Personality match (0-3 points)
            if curiosity in requirements["personality_match"]:
                score += 3.0
                reasons.append(f"Personality: {curiosity} is ideal for {role.value}")
            elif curiosity == "connector" and role in [AgentRole.SYNTHESIZER, AgentRole.CRITIC]:
                score += 2.0
                reasons.append(f"Personality: {curiosity} is good for {role.value}")
            elif curiosity == "systematic" and role in [AgentRole.VALIDATOR, AgentRole.SCREENER]:
                score += 2.0
                reasons.append(f"Personality: {curiosity} is good for {role.value}")
            else:
                reasons.append(f"Personality: {curiosity} is neutral for {role.value}")

            # Domain match (0-1 point)
            if domain != "mixed":
                if (domain == "biology" and role != AgentRole.SCREENER) or \
                   (domain == "chemistry" and role == AgentRole.SCREENER):
                    score += 1.0
                    reasons.append(f"Domain: {domain} is good fit")

            scored_roles.append((role, score, " | ".join(reasons)))

        # Sort by score and priority
        scored_roles.sort(key=lambda x: (-x[1], self.ROLES[x[0]]["priority"]))

        top_role, top_score, reasoning = scored_roles[0]
        return top_role, top_score, reasoning

    def assign_role(
        self,
        agent_profile: Dict[str, Any],
        session_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assign a role to an agent.

        Args:
            agent_profile: Agent profile
            session_info: Optional session state

        Returns:
            Role assignment with description and responsibilities
        """
        role, score, reasoning = self.suggest_role(agent_profile, session_info)

        role_info = self.ROLES[role]

        return {
            "role": role.value,
            "score": score,
            "reasoning": reasoning,
            "description": role_info["description"],
            "responsibilities": role_info["responsibilities"],
            "priority": role_info["priority"]
        }

    def get_role_info(self, role_name: str) -> Dict[str, Any]:
        """Get detailed information about a role."""
        for role, info in self.ROLES.items():
            if role.value == role_name:
                return {
                    "name": role.value,
                    **info
                }
        return {"error": f"Unknown role: {role_name}"}

    def recommend_role_composition(
        self,
        agent_profiles: List[Dict[str, Any]],
        session_topic: str = ""
    ) -> Dict[str, Any]:
        """
        Recommend optimal role composition for a team of agents.

        Args:
            agent_profiles: List of agent profiles
            session_topic: Optional session topic for context

        Returns:
            Recommended role assignments for all agents
        """
        assignments = []

        for profile in agent_profiles:
            assignment = self.assign_role(profile)
            agent_name = profile.get("name", "Unknown")
            assignments.append({
                "agent": agent_name,
                **assignment
            })

        # Check for role balance
        role_counts = {}
        for assignment in assignments:
            role = assignment["role"]
            role_counts[role] = role_counts.get(role, 0) + 1

        return {
            "assignments": assignments,
            "team_composition": role_counts,
            "team_balance": self._assess_balance(role_counts),
            "recommendations": self._get_composition_recommendations(role_counts)
        }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _assess_balance(self, role_counts: Dict[str, int]) -> str:
        """Assess the balance of roles in a team."""
        total_agents = sum(role_counts.values())

        if "investigator" not in role_counts or role_counts["investigator"] == 0:
            return "unbalanced: no investigator"
        if "synthesizer" not in role_counts or role_counts["synthesizer"] == 0:
            return "unbalanced: no synthesizer"
        if total_agents < 2:
            return "unbalanced: team too small"
        if total_agents > 5:
            return "unbalanced: team too large"

        investigators = role_counts.get("investigator", 0)
        validators = role_counts.get("validator", 0)
        critics = role_counts.get("critic", 0)

        if validators + critics == 0:
            return "unbalanced: no validation/critique"
        if validators > 0 and critics > 0:
            return "balanced: good mix"

        return "acceptable: workable composition"

    def _get_composition_recommendations(self, role_counts: Dict[str, int]) -> List[str]:
        """Get recommendations to improve team composition."""
        recommendations = []

        if role_counts.get("investigator", 0) == 0:
            recommendations.append("Add investigator: need primary research capability")
        if role_counts.get("validator", 0) == 0 and role_counts.get("critic", 0) == 0:
            recommendations.append("Add validator or critic: need peer review")
        if role_counts.get("synthesizer", 0) == 0:
            recommendations.append("Add synthesizer: need narrative integration")

        return recommendations


# Test function
def test_role_manager():
    """Test the role manager."""

    manager = RoleManager()

    print("\n=== Phase 3 Test: Role Management ===\n")

    # Define test agents with different profiles
    agents = [
        {
            "name": "BioAgent-7",
            "preferred_tools": ["pubmed", "uniprot", "pdb", "alphafold"],
            "curiosity_style": "deep-diver",
            "domain": "biology",
            "interests": ["protein structure", "drug targets"]
        },
        {
            "name": "CrazyChem",
            "preferred_tools": ["pubchem", "tdc", "rdkit", "chembl"],
            "curiosity_style": "explorer",
            "domain": "chemistry",
            "interests": ["drug discovery", "ADMET"]
        },
        {
            "name": "SkepticalBot",
            "preferred_tools": ["pubmed", "uniprot", "arxiv"],
            "curiosity_style": "skeptic",
            "domain": "biology",
            "interests": ["mechanism validation"]
        },
        {
            "name": "Synthesizer",
            "preferred_tools": ["datavis", "websearch", "pubmed"],
            "curiosity_style": "connector",
            "domain": "mixed",
            "interests": ["knowledge integration", "narrative synthesis"]
        }
    ]

    # Test individual role assignments
    print("[TEST] Individual Role Assignment\n")
    for agent in agents:
        assignment = manager.assign_role(agent)
        print(f"{agent['name']}:")
        print(f"  Role: {assignment['role']} (score: {assignment['score']:.1f})")
        print(f"  Reasoning: {assignment['reasoning']}")
        print(f"  Responsibilities: {', '.join(assignment['responsibilities'][:2])}")
        print()

    # Test team composition recommendation
    print("[TEST] Team Composition Recommendation\n")
    composition = manager.recommend_role_composition(agents, "BACE1 drug target")

    print(f"Team Balance: {composition['team_balance']}\n")
    print("Role Distribution:")
    for role, count in composition["team_composition"].items():
        print(f"  {role}: {count}")

    if composition["recommendations"]:
        print("\nRecommendations:")
        for rec in composition["recommendations"]:
            print(f"  - {rec}")

    # Test role info
    print("\n[TEST] Role Information\n")
    investigator_info = manager.get_role_info("investigator")
    print(f"Investigator Role:")
    print(f"  Description: {investigator_info['description']}")
    print(f"  Responsibilities: {investigator_info['responsibilities'][:2]}")

    print("\n✓ Role manager test complete")


if __name__ == "__main__":
    test_role_manager()
