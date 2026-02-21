"""
LLM-Powered Skill Selector

Uses the agent's LLM to intelligently select which skills to use for a research topic.

Instead of hardcoding "use PubMed for literature", the LLM decides:
- Which skills are relevant
- In what order to use them
- What parameters to pass
- How to chain results

This makes the system truly adaptive and intelligent.
"""

import subprocess
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field


class SelectedSkill(BaseModel):
    """A skill selected by the LLM for investigation."""
    name: str = Field(description="Skill name")
    reason: str = Field(description="Why this skill is needed for this topic")
    suggested_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Suggested parameters for executing this skill"
    )
    category: Optional[str] = Field(default=None, description="Skill category")
    description: Optional[str] = Field(default=None, description="Skill description")


class SkillSelection(BaseModel):
    """LLM-selected skills for a research investigation."""
    topic: str = Field(description="Research topic")
    selected_skills: List[SelectedSkill] = Field(description="Selected skills")
    reasoning: str = Field(default="", description="Overall reasoning for this selection")
    total_skills: int = Field(default=0, description="Total number of skills selected")
    
    def model_post_init(self, __context):
        """Set total_skills after initialization."""
        if self.total_skills == 0:
            self.total_skills = len(self.selected_skills)


class LLMSkillSelector:
    """
    Uses LLM to select and orchestrate scientific skills.
    
    Implements intelligent skill selection:
    - Analyzes research topic
    - Queries skill registry
    - Determines optimal skill chain
    - Generates execution plan
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize skill selector.
        
        Args:
            agent_name: Name of the agent (for LLM context)
        """
        self.agent_name = agent_name
    
    def select_skills(self,
                     topic: str,
                     available_skills: List[Dict[str, Any]],
                     max_skills: int = 5) -> SkillSelection:
        """
        Use LLM to select which skills to use for a topic.
        
        Args:
            topic: Research topic
            available_skills: List of all available skills from registry
            max_skills: Maximum skills to select
            
        Returns:
            List of selected skills with suggested parameters
        """
        # Build skill catalog for LLM with specific skill names
        skill_catalog = self._build_skill_catalog(available_skills)
        
        prompt = f"""You are {self.agent_name}, planning a scientific investigation of: "{topic}"

AVAILABLE SKILLS ({len(available_skills)} total):
{skill_catalog}

TASK: Select 3-{max_skills} most relevant skills from the list above for investigating this topic.
Use multiple skills—do not select only one. Pick skill names exactly as they appear in the list.

CRITICAL GUIDANCE FOR SKILL SELECTION:

For ORGANIC/SYNTHETIC CHEMISTRY topics (reactions, synthesis, catalysis, coupling):
- AVOID: pubmed-database (it's for biomedical literature, not chemistry)
- PREFER: openalex-database, arxiv, biorxiv-database (chemistry literature)
- INCLUDE: chembl-database, pubchem-database, zinc-database (compounds)
- INCLUDE: nistwebbook, cas (chemistry reference data)

For BIOMEDICAL topics (drugs, diseases, proteins):
- USE: pubmed-database (appropriate for biomedical)

For DRUG DISCOVERY topics:
- USE: pubmed-database, chembl-database, drugbank-database, uniprot, pytdc

For MATERIALS SCIENCE / CRITICAL MINERALS topics (minerals, separation, extraction, rare earth, materials discovery, supply chain):
- PREFER: corpus-search (local critical minerals corpus), openalex-database (240M+ scholarly works), osti-database (DOE reports)
- INCLUDE: minerals-data (structured CSV data), materials (Materials Project), websearch (industry data)
- INCLUDE: rdkit, pubchem-database, nistwebbook (chemistry reference data)
- AVOID: pubmed-database, biorxiv-database, blast, alphafold-database, uniprot (biomedical)

For each selected skill, specify:
SKILL: exact_skill_name
REASON: Why this skill is needed for this topic
PARAMS: {{"param1": "value1", "param2": "value2"}}

SKILL: next_skill_name
REASON: Why this skill is needed
PARAMS: {{"param": "value"}}

Select 3-5 skills now:"""
        
        response = self._call_llm(prompt, max_tokens=800)
        
        # Parse LLM response - use whatever the LLM returns, no fallback
        selected = self._parse_skill_selection(response, available_skills)
        
        # Return structured SkillSelection
        return SkillSelection(
            topic=topic,
            selected_skills=selected[:max_skills],
            reasoning="LLM-powered skill selection" if response else "Keyword-based fallback"
        )
    
    def plan_investigation(self,
                          topic: str,
                          selected_skills: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate an investigation plan using selected skills.
        
        Args:
            topic: Research topic
            selected_skills: Skills selected by LLM
            
        Returns:
            Investigation plan with skill chain and execution order
        """
        skills_summary = '\n'.join([
            f"- {s['name']}: {s.get('reason', 'Selected')}"
            for s in selected_skills
        ])
        
        prompt = f"""You are {self.agent_name} planning an investigation of: "{topic}"

SELECTED SKILLS:
{skills_summary}

TASK: Create an investigation plan that:
1. Orders skills logically (e.g., literature search before entity lookup)
2. Explains how results flow between skills
3. Identifies what insights to extract from each

Format:
STEP 1: [skill_name]
ACTION: [What this skill will do]
OUTPUT: [What data it produces]
FEEDS_INTO: [Which later steps use this output]

STEP 2: [next_skill]
...

Create the plan:"""
        
        response = self._call_llm(prompt, max_tokens=800)
        
        return {
            "topic": topic,
            "plan": response,
            "skills": selected_skills
        }
    
    def _build_skill_catalog(self, skills: List[Dict[str, Any]]) -> str:
        """Build human-readable skill catalog for LLM."""
        catalog_lines = []
        
        # Group by category
        by_category = {}
        for skill in skills:
            cat = skill.get('category', 'general')
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(skill)
        
        # Format each category
        for category, cat_skills in sorted(by_category.items()):
            catalog_lines.append(f"\n{category.upper()}:")
            for skill in cat_skills[:15]:  # Limit per category to avoid overwhelming LLM
                name = skill.get('name', 'unknown')
                desc = skill.get('description', 'No description')[:80]
                catalog_lines.append(f"  - {name}: {desc}")
        
        return '\n'.join(catalog_lines)
    
    def _call_llm(self, prompt: str, max_tokens: int = 600) -> str:
        """Call LLM via unified client."""
        try:
            from core.llm_client import get_llm_client
            client = get_llm_client(agent_name=self.agent_name)
            return client.call(
                prompt=prompt,
                max_tokens=max_tokens,
                session_id=f"skill_selection_{self.agent_name}"
            )
        except Exception as e:
            # Fallback silently
            return ""
    
    def _parse_skill_selection(self,
                               response: str,
                               available_skills: List[Dict[str, Any]]) -> List[SelectedSkill]:
        """Parse LLM's skill selection response into Pydantic models."""
        selected = []
        
        # Create lookup dict
        skill_lookup = {s['name']: s for s in available_skills}
        
        # Parse response
        current_skill = None
        current_reason = ""
        current_params = {}
        
        for line in response.split('\n'):
            line_stripped = line.strip()
            
            if line_stripped.startswith('SKILL:'):
                # Save previous skill
                if current_skill and current_skill in skill_lookup:
                    skill_meta = skill_lookup[current_skill]
                    selected.append(SelectedSkill(
                        name=current_skill,
                        reason=current_reason,
                        suggested_params=current_params,
                        category=skill_meta.get('category'),
                        description=skill_meta.get('description')
                    ))
                
                # Start new skill
                current_skill = line_stripped.replace('SKILL:', '').strip()
                current_reason = ""
                current_params = {}
            
            elif line_stripped.startswith('REASON:'):
                current_reason = line_stripped.replace('REASON:', '').strip()
            
            elif line_stripped.startswith('PARAMS:'):
                params_str = line_stripped.replace('PARAMS:', '').strip()
                try:
                    current_params = json.loads(params_str)
                except json.JSONDecodeError:
                    current_params = {}
        
        # Save last skill
        if current_skill and current_skill in skill_lookup:
            skill_meta = skill_lookup[current_skill]
            selected.append(SelectedSkill(
                name=current_skill,
                reason=current_reason,
                suggested_params=current_params,
                category=skill_meta.get('category'),
                description=skill_meta.get('description')
            ))
        
        return selected
    
    def _fallback_selection(self,
                           topic: str,
                           available_skills: List[Dict[str, Any]],
                           max_skills: int) -> List[SelectedSkill]:
        """
        LLM-powered fallback: Ask LLM to suggest skills based on topic analysis.
        
        No hardcoded keywords or domain logic - let the LLM decide everything.
        """
        # Use topic analyzer to get LLM classification
        from core.topic_analyzer import get_analyzer
        analyzer = get_analyzer(self.agent_name)
        
        # Analyze topic to get investigation type and recommended categories
        analysis = analyzer.analyze_topic(topic)
        
        # Build skill catalog
        skill_catalog = self._build_skill_catalog(available_skills)
        
        # Ask LLM which skills match the analyzed topic
        prompt = f"""Based on this research analysis, select the most relevant skills:

TOPIC: {topic}
INVESTIGATION TYPE: {analysis.investigation_type}
KEY CONCEPTS: {', '.join(analysis.key_concepts)}
RECOMMENDED CATEGORIES: {', '.join(analysis.recommended_skill_categories)}
ENTITIES EXPECTED: {', '.join(f"{k}={'yes' if v else 'no'}" for k, v in analysis.entities_expected.items())}

AVAILABLE SKILLS:
{skill_catalog}

Select 3-5 specific skill names that best match this topic and analysis.
Format each as:
SKILL: skill_name
REASON: Why this skill matches the topic and analysis

Select now:"""
        
        response = self._call_llm(prompt, max_tokens=600)
        
        # Parse LLM response
        if response:
            selected = self._parse_skill_selection(response, available_skills)
            if selected:
                return selected[:max_skills]
        
        # If LLM fallback fails, just return empty and let caller handle it
        return []


# Global selector instance
_selector = None

def get_selector(agent_name: str) -> LLMSkillSelector:
    """Get skill selector instance."""
    global _selector
    if _selector is None or _selector.agent_name != agent_name:
        _selector = LLMSkillSelector(agent_name)
    return _selector
