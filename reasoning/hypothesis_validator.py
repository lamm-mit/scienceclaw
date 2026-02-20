"""
Skills-Aware Hypothesis Validator

Validates whether a hypothesis is testable with the available skill catalog.
Each validator has a configurable personality that shapes its critique style.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class ValidationResult:
    score: float                          # 0.0–1.0
    is_valid: bool                        # score >= threshold
    critique: str
    refined_tools: List[str]             # better tool selections from live catalog
    refined_success_criteria: str
    missing_capabilities: List[str]
    validator_agent: str
    personality: str                      # skeptic / deep-diver / connector / explorer
    iteration: int


PERSONALITY_INSTRUCTIONS = {
    "skeptic": (
        "Challenge every vague claim. Demand quantitative success criteria. "
        "If the hypothesis cannot be falsified with the listed tools, score it low. "
        "Be direct and uncompromising — science requires precision."
    ),
    "deep-diver": (
        "Check whether the planned tool chain is complete end-to-end. "
        "Ask: can you get from raw input to a measurable conclusion with these tools alone? "
        "Identify any missing intermediate steps in the pipeline."
    ),
    "connector": (
        "Identify missing cross-domain tools that could enrich this hypothesis. "
        "Look for complementary skills from different fields (e.g., structural + computational). "
        "Suggest how connecting additional data sources would strengthen the evidence."
    ),
    "explorer": (
        "Suggest broader investigative directions the hypothesis overlooks. "
        "Ask: what adjacent questions would deepen understanding of this topic? "
        "Encourage widening the scope where the current framing is too narrow."
    ),
}


class HypothesisValidator:
    """
    Single validator agent with configurable personality.

    Loads the live SkillRegistry and calls the LLM to evaluate whether
    a hypothesis is testable with the available skills.
    """

    VALIDATION_THRESHOLD = 0.65

    def __init__(self, agent_name: str, personality: str = "skeptic"):
        self.agent_name = agent_name
        self.personality = personality
        self._registry = None
        self._reasoner = None

    # ------------------------------------------------------------------ #
    # Lazy-load heavy dependencies                                         #
    # ------------------------------------------------------------------ #

    @property
    def registry(self):
        if self._registry is None:
            from core.skill_registry import SkillRegistry
            self._registry = SkillRegistry()
        return self._registry

    @property
    def reasoner(self):
        if self._reasoner is None:
            from autonomous.llm_reasoner import LLMScientificReasoner
            self._reasoner = LLMScientificReasoner(agent_name=self.agent_name)
        return self._reasoner

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def validate(self, hypothesis: dict, iteration: int = 1) -> ValidationResult:
        """
        Evaluate hypothesis testability against the live skill catalog.

        Args:
            hypothesis: dict with keys statement, planned_tools, success_criteria
            iteration: which refinement round this is (for context)

        Returns:
            ValidationResult
        """
        statement = hypothesis.get("statement", "")
        planned_tools = hypothesis.get("planned_tools", [])
        success_criteria = hypothesis.get("success_criteria", "")

        # Build compact skill catalog (1 line per skill)
        catalog_lines = []
        for name, skill in self.registry.skills.items():
            desc = (skill.get("description") or "")[:80]
            category = skill.get("category", "general")
            catalog_lines.append(f"- {name} | {category} | {desc}")
        skill_catalog_text = "\n".join(catalog_lines) if catalog_lines else "(no skills available)"

        personality_instruction = PERSONALITY_INSTRUCTIONS.get(
            self.personality, PERSONALITY_INSTRUCTIONS["skeptic"]
        )

        prompt = f"""You are {self.agent_name}, a {self.personality} hypothesis validator.
{personality_instruction}

Given this hypothesis and the live skill catalog below, evaluate its testability.
Iteration: {iteration}

HYPOTHESIS: {statement}
PLANNED_TOOLS: {', '.join(planned_tools) if planned_tools else 'none'}
SUCCESS_CRITERIA: {success_criteria}

AVAILABLE SKILLS (name | category | description):
{skill_catalog_text}

Provide your evaluation in this EXACT format (no extra text):
SCORE: 0.XX
CRITIQUE: <one paragraph critique>
REFINED_TOOLS: tool1, tool2, tool3
REFINED_CRITERIA: <improved measurable success criteria>
MISSING: capability1, capability2
"""

        response = self._call_llm_safe(prompt)
        return self._parse_response(response, iteration)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _call_llm_safe(self, prompt: str) -> str:
        """Call LLM, return empty string on failure."""
        try:
            return self.reasoner._call_llm(prompt, max_tokens=600)
        except Exception as e:
            return f"SCORE: 0.30\nCRITIQUE: LLM unavailable ({e}). Defaulting to low score.\nREFINED_TOOLS: pubmed\nREFINED_CRITERIA: {{}}\nMISSING: llm_access"

    def _parse_response(self, response: str, iteration: int) -> ValidationResult:
        """Parse structured LLM output into ValidationResult."""
        lines = response.strip().splitlines()
        data = {}
        for line in lines:
            if ":" in line:
                key, _, val = line.partition(":")
                data[key.strip().upper()] = val.strip()

        # Score
        try:
            score = float(data.get("SCORE", "0.3"))
            score = max(0.0, min(1.0, score))
        except ValueError:
            score = 0.3

        # Critique
        critique = data.get("CRITIQUE", "No critique provided.")

        # Refined tools
        refined_tools_raw = data.get("REFINED_TOOLS", "")
        refined_tools = [t.strip() for t in refined_tools_raw.split(",") if t.strip()]

        # Refined criteria
        refined_success_criteria = data.get("REFINED_CRITERIA", "")

        # Missing capabilities
        missing_raw = data.get("MISSING", "")
        missing_capabilities = [m.strip() for m in missing_raw.split(",") if m.strip()]

        return ValidationResult(
            score=score,
            is_valid=score >= self.VALIDATION_THRESHOLD,
            critique=critique,
            refined_tools=refined_tools,
            refined_success_criteria=refined_success_criteria,
            missing_capabilities=missing_capabilities,
            validator_agent=self.agent_name,
            personality=self.personality,
            iteration=iteration,
        )
