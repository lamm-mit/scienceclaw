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
                     max_skills: int = 5) -> List[Dict[str, Any]]:
        """
        Use LLM to select which skills to use for a topic.
        
        Args:
            topic: Research topic
            available_skills: List of all available skills from registry
            max_skills: Maximum skills to select
            
        Returns:
            List of selected skills with suggested parameters
        """
        # Build skill catalog for LLM
        skill_catalog = self._build_skill_catalog(available_skills)
        
        prompt = f"""You are {self.agent_name}, planning a scientific investigation of: "{topic}"

AVAILABLE SKILLS ({len(available_skills)} total):
{skill_catalog}

TASK: Select 3-{max_skills} most relevant skills for investigating this topic.

Consider:
1. What data sources are needed? (literature, proteins, compounds, pathways)
2. What analysis tools are needed? (sequence, structure, properties)
3. What order should skills be used? (e.g., literature first, then entities)

For each selected skill, specify:
- SKILL NAME
- WHY it's needed for this topic
- What PARAMETERS to use

Format your response like this:
SKILL: skill_name
REASON: Why this skill is needed
PARAMS: {{"param1": "value1", "param2": "value2"}}

SKILL: another_skill
REASON: Why this is needed
PARAMS: {{"param": "value"}}

Select skills now:"""
        
        response = self._call_llm(prompt)
        
        # Parse LLM response
        selected = self._parse_skill_selection(response, available_skills)
        
        # Fallback if parsing fails
        if not selected:
            selected = self._fallback_selection(topic, available_skills, max_skills)
        
        return selected[:max_skills]
    
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
        """Call LLM via OpenClaw."""
        try:
            result = subprocess.run(
                [
                    "openclaw", "agent",
                    "--message", prompt,
                    "--session-id", f"skill_selection_{self.agent_name}"
                ],
                capture_output=True,
                text=True,
                timeout=45
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            else:
                return ""
                
        except Exception as e:
            print(f"    Note: LLM skill selection unavailable ({e})")
            return ""
    
    def _parse_skill_selection(self,
                               response: str,
                               available_skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse LLM's skill selection response."""
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
                    skill_copy = skill_lookup[current_skill].copy()
                    skill_copy['reason'] = current_reason
                    skill_copy['suggested_params'] = current_params
                    selected.append(skill_copy)
                
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
            skill_copy = skill_lookup[current_skill].copy()
            skill_copy['reason'] = current_reason
            skill_copy['suggested_params'] = current_params
            selected.append(skill_copy)
        
        return selected
    
    def _fallback_selection(self,
                           topic: str,
                           available_skills: List[Dict[str, Any]],
                           max_skills: int) -> List[Dict[str, Any]]:
        """
        Fallback skill selection using keyword matching.
        
        Used when LLM is unavailable.
        """
        topic_lower = topic.lower()
        selected = []
        
        # Always start with literature search
        for skill in available_skills:
            if skill['name'] in ['pubmed', 'openalex', 'biorxiv', 'arxiv']:
                skill_copy = skill.copy()
                skill_copy['reason'] = 'Literature search foundation'
                skill_copy['suggested_params'] = {'query': topic, 'max_results': 5}
                selected.append(skill_copy)
                break
        
        # Add protein tools if biology topic
        if any(term in topic_lower for term in ['protein', 'gene', 'enzyme', 'kinase']):
            for skill in available_skills:
                if skill['name'] in ['uniprot', 'pdb', 'alphafold']:
                    skill_copy = skill.copy()
                    skill_copy['reason'] = 'Protein characterization'
                    selected.append(skill_copy)
                    break
        
        # Add chemistry tools if chemistry topic
        if any(term in topic_lower for term in ['compound', 'drug', 'synthesis', 'reaction']):
            for skill in available_skills:
                if skill['name'] in ['pubchem', 'chembl', 'rdkit']:
                    skill_copy = skill.copy()
                    skill_copy['reason'] = 'Chemical analysis'
                    selected.append(skill_copy)
                    break
        
        return selected[:max_skills]


# Global selector instance
_selector = None

def get_selector(agent_name: str) -> LLMSkillSelector:
    """Get skill selector instance."""
    global _selector
    if _selector is None or _selector.agent_name != agent_name:
        _selector = LLMSkillSelector(agent_name)
    return _selector
