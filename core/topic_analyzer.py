"""
LLM-Powered Topic Analyzer

Uses the agent's LLM to analyze research topics and select skills.
- Investigation type (Infinite community)
- Key concepts, entities, skill categories
- Specific skill selection (when combined with skill catalog)

Set DEBUG_LLM_TOPIC=1 to log LLM responses and parsing for debugging.
"""

import os
import subprocess
import json
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, field_validator

DEBUG = os.environ.get("DEBUG_LLM_TOPIC", "").lower() in ("1", "true", "yes")


def _get_infinite_communities() -> List[str]:
    """Get community names available on Infinite server. No fallback."""
    try:
        from skills.infinite.scripts.infinite_client import InfiniteClient
        client = InfiniteClient()
        return client.list_communities()
    except Exception:
        return []


class SelectedSkillItem(BaseModel):
    """A single skill selected by the LLM."""
    name: str = Field(min_length=1)
    reason: str = Field(default="")
    suggested_params: Dict[str, Any] = Field(default_factory=dict)


class TopicAndSkillResponse(BaseModel):
    """Strict Pydantic model for combined topic analysis + skill selection."""
    investigation_type: str = Field(description="Infinite community name")
    key_concepts: List[str] = Field(default_factory=list, max_length=10)
    entities_expected: Dict[str, bool] = Field(default_factory=dict)
    skill_categories: List[str] = Field(default_factory=list, max_length=6)
    reasoning: str = Field(default="")
    selected_skills: List[SelectedSkillItem] = Field(default_factory=list, max_length=5)

    @field_validator("investigation_type", mode="before")
    @classmethod
    def validate_investigation_type(cls, v: str, info) -> str:
        communities = _get_infinite_communities()
        v_lower = (v or "").strip().lower()
        for c in communities:
            if c.lower() == v_lower:
                return c
        return v_lower or (communities[0] if communities else "")


class TopicAnalysis(BaseModel):
    """Structured output from topic analysis."""
    investigation_type: str = Field(
        description="Primary investigation type: 'biology', 'chemistry', 'materials', 'interdisciplinary'"
    )
    key_concepts: List[str] = Field(
        description="Main scientific concepts in this topic (2-5 items)",
        default_factory=list
    )
    entities_expected: Dict[str, bool] = Field(
        description="What entities to look for: proteins, compounds, genes, reactions, materials",
        default_factory=dict
    )
    recommended_skill_categories: List[str] = Field(
        description="Skill categories to use: literature, proteins, compounds, pathways, bioinformatics, etc.",
        default_factory=list
    )
    reasoning: str = Field(
        description="Brief explanation of classification",
        default=""
    )


class InvestigationPlan(BaseModel):
    """Plan for conducting a multi-tool investigation."""
    topic: str = Field(description="Research topic")
    analysis: TopicAnalysis = Field(description="Topic analysis results")
    investigation_steps: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Ordered steps for investigation"
    )
    expected_outputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Expected data outputs from investigation"
    )
    
    class Config:
        arbitrary_types_allowed = True


class LLMTopicAnalyzer:
    """
    Uses LLM to analyze research topics and recommend tools.
    
    This replaces hardcoded keyword matching with intelligent reasoning.
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize topic analyzer.
        
        Args:
            agent_name: Name of the agent (for LLM context)
        """
        self.agent_name = agent_name
    
    def analyze_and_select_skills(self,
                                  topic: str,
                                  available_skills: List[Dict[str, Any]],
                                  max_skills: int = 5,
                                  agent_profile: Optional[Dict[str, Any]] = None) -> Tuple[TopicAnalysis, List[Dict[str, Any]]]:
        """
        Analyze topic AND select specific skills in one LLM call.
        
        Returns:
            (TopicAnalysis, list of selected skill dicts with name, reason, suggested_params)
        """
        skill_catalog = self._build_skill_catalog(available_skills)
        skill_lookup = {s['name']: s for s in available_skills}
        communities = _get_infinite_communities()
        inv_type_hint = f"[{'|'.join(communities)}]" if communities else "[community name]"
        
        role_context = ""
        if agent_profile:
            bio = agent_profile.get("bio", "")
            interests = agent_profile.get("research", {}).get("interests", [])
            role = agent_profile.get("role", "")
            if bio or interests or role:
                parts = []
                if role:
                    parts.append(f"Role: {role}")
                if bio:
                    parts.append(f"Bio: {bio}")
                if interests:
                    parts.append(f"Interests: {', '.join(interests[:5])}")
                role_context = "\n".join(parts) + "\n\n"
        
        prompt = f"""You are {self.agent_name}, planning a scientific investigation of: "{topic}"
{role_context}AVAILABLE SKILLS ({len(available_skills)} total):
{skill_catalog}

TASK: In one response, do BOTH:
1. Analyze the topic (investigation type = Infinite community, concepts, entities)
2. Select 3-{max_skills} specific skills from the list above

Respond in this EXACT format:
INVESTIGATION_TYPE: {inv_type_hint}
KEY_CONCEPTS: concept1, concept2, concept3
ENTITIES_EXPECTED: proteins=yes/no, compounds=yes/no, genes=yes/no, reactions=yes/no, materials=yes/no
SKILL_CATEGORIES: category1, category2
REASONING: [1-2 sentence explanation]

SKILL: exact_skill_name_from_list
REASON: Why this skill is needed
PARAMS: {{}}

SKILL: next_skill_name
REASON: Why needed
PARAMS: {{}}

Select 3-{max_skills} skills now (use exact names from the list):"""
        
        response = self._call_llm(prompt)
        
        if not response:
            if DEBUG:
                print("    [DEBUG] LLM returned empty response")
            return (self._fallback_analysis(topic), [])
        
        if DEBUG:
            preview = response[:500] + "..." if len(response) > 500 else response
            print(f"    [DEBUG] LLM response ({len(response)} chars): {preview!r}")
        
        # Parse combined response
        analysis = self._parse_analysis(response)
        selected = self._parse_skill_selection(response, skill_lookup)
        
        if DEBUG and not selected:
            print(f"    [DEBUG] Parser extracted 0 skills. Raw response lines with SKILL: {[l for l in response.split(chr(10)) if 'SKILL' in l.upper()]!r}")
        
        return (analysis, selected)
    
    def _build_skill_catalog(self, skills: List[Dict[str, Any]]) -> str:
        """Build human-readable skill catalog for LLM."""
        lines = []
        by_cat = {}
        for s in skills:
            cat = s.get('category', 'general')
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(s)
        for cat, items in sorted(by_cat.items()):
            lines.append(f"\n{cat.upper()}:")
            for s in items[:12]:
                name = s.get('name', 'unknown')
                desc = (s.get('description') or '')[:70]
                lines.append(f"  - {name}: {desc}")
        return '\n'.join(lines)
    
    def _parse_skill_selection(self, response: str, skill_lookup: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """Parse SKILL/REASON/PARAMS blocks from LLM response. Case-insensitive skill name matching."""
        selected = []
        current_skill, current_reason, current_params = None, "", {}
        name_lower_to_orig = {k.lower(): k for k in skill_lookup}
        
        def _resolve_skill(name: str) -> Optional[str]:
            """Resolve skill name (case-insensitive) to canonical form in skill_lookup."""
            if not name:
                return None
            return name_lower_to_orig.get(name.strip().lower())
        
        for line in response.split('\n'):
            line_stripped = line.strip()
            if line_stripped.upper().startswith('SKILL') and ':' in line_stripped:
                # Extract skill name after colon
                skill_name = line_stripped.split(':', 1)[1].strip()
                if current_skill:
                    canon = _resolve_skill(current_skill)
                    if canon:
                        selected.append({
                            "name": canon,
                            "reason": current_reason,
                            "suggested_params": current_params,
                            "category": skill_lookup[canon].get('category'),
                            "description": skill_lookup[canon].get('description')
                        })
                current_skill = skill_name
                current_reason = ""
                current_params = {}
            elif line_stripped.upper().startswith('REASON') and ':' in line_stripped:
                current_reason = line_stripped.split(':', 1)[1].strip()
            elif line_stripped.upper().startswith('PARAMS') and ':' in line_stripped:
                try:
                    params_str = line_stripped.split(':', 1)[1].strip() or '{}'
                    current_params = json.loads(params_str)
                except json.JSONDecodeError:
                    current_params = {}
        
        if current_skill:
            canon = _resolve_skill(current_skill)
            if canon:
                selected.append({
                    "name": canon,
                    "reason": current_reason,
                    "suggested_params": current_params,
                    "category": skill_lookup[canon].get('category'),
                    "description": skill_lookup[canon].get('description')
                })
        
        return selected[:5]
    
    def analyze_topic(self, topic: str) -> TopicAnalysis:
        """
        Analyze a research topic using LLM.
        
        Args:
            topic: Research topic to analyze
            
        Returns:
            TopicAnalysis with classification and recommendations
        """
        prompt = f"""You are {self.agent_name}, a scientific researcher. Analyze this research topic and classify it:

TOPIC: "{topic}"

Determine:
1. **Investigation Type**: Is this primarily biology, chemistry, materials, or interdisciplinary?
   - Biology: proteins, genes, cells, organisms, molecular biology
   - Chemistry: reactions, synthesis, compounds, organic/inorganic chemistry
   - Materials: crystals, polymers, metals, materials science
   - Interdisciplinary: crosses multiple domains (e.g., drug discovery = biology + chemistry)

2. **Key Concepts**: What are the 2-5 main scientific concepts?

3. **Entities Expected**: What should we look for?
   - proteins: yes/no
   - compounds: yes/no
   - genes: yes/no
   - reactions: yes/no
   - materials: yes/no

4. **Recommended Skill Categories**: Which tool categories are most relevant?
   - literature (papers, articles)
   - proteins (UniProt, PDB, AlphaFold)
   - compounds (PubChem, ChEMBL, DrugBank)
   - pathways (KEGG, Reactome)
   - bioinformatics (BLAST, sequence analysis)
   - clinical (ClinVar, clinical trials)
   - materials (Materials Project)

Respond in this EXACT format:
INVESTIGATION_TYPE: [biology|chemistry|materials|interdisciplinary]
KEY_CONCEPTS: concept1, concept2, concept3
ENTITIES_EXPECTED: proteins=yes/no, compounds=yes/no, genes=yes/no, reactions=yes/no, materials=yes/no
SKILL_CATEGORIES: category1, category2, category3
REASONING: [1-2 sentence explanation]

Analyze now:"""
        
        response = self._call_llm(prompt)
        
        if response:
            try:
                analysis = self._parse_analysis(response)
                return analysis
            except Exception as e:
                print(f"    Note: Could not parse LLM analysis ({e}), using fallback")
        
        # Fallback to keyword-based analysis
        return self._fallback_analysis(topic)
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM via unified client."""
        try:
            from core.llm_client import get_llm_client
            client = get_llm_client(agent_name=self.agent_name)
            out = client.call(
                prompt=prompt,
                max_tokens=600,
                session_id=f"topic_analysis_{self.agent_name}"
            )
            if DEBUG and not out:
                print("    [DEBUG] LLM client returned empty (no exception)")
            return out or ""
        except Exception as e:
            if DEBUG:
                import traceback
                print(f"    [DEBUG] LLM call failed: {e}")
                traceback.print_exc()
            return ""
    
    def _parse_analysis(self, response: str) -> TopicAnalysis:
        """Parse LLM response into structured analysis."""
        lines = response.split('\n')
        
        investigation_type = "interdisciplinary"
        key_concepts = []
        entities_expected = {}
        skill_categories = []
        reasoning = ""
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('INVESTIGATION_TYPE:'):
                inv_type = line.split(':', 1)[1].strip().lower()
                if inv_type in ['biology', 'chemistry', 'materials', 'interdisciplinary']:
                    investigation_type = inv_type
            
            elif line.startswith('KEY_CONCEPTS:'):
                concepts_str = line.split(':', 1)[1].strip()
                key_concepts = [c.strip() for c in concepts_str.split(',') if c.strip()]
            
            elif line.startswith('ENTITIES_EXPECTED:'):
                entities_str = line.split(':', 1)[1].strip()
                for pair in entities_str.split(','):
                    if '=' in pair:
                        key, val = pair.split('=')
                        entities_expected[key.strip()] = val.strip().lower() == 'yes'
            
            elif line.startswith('SKILL_CATEGORIES:'):
                categories_str = line.split(':', 1)[1].strip()
                skill_categories = [c.strip() for c in categories_str.split(',') if c.strip()]
            
            elif line.startswith('REASONING:'):
                reasoning = line.split(':', 1)[1].strip()
        
        return TopicAnalysis(
            investigation_type=investigation_type,
            key_concepts=key_concepts,
            entities_expected=entities_expected,
            recommended_skill_categories=skill_categories,
            reasoning=reasoning
        )
    
    def _fallback_analysis(self, topic: str) -> TopicAnalysis:
        """
        Fallback analysis using keyword matching.
        
        Used when LLM is unavailable.
        """
        topic_lower = topic.lower()
        
        # Simple keyword detection (general concepts, not specific reaction names)
        bio_keywords = ['protein', 'gene', 'cell', 'enzyme', 'antibody', 'dna', 'rna', 'kinase']
        chem_keywords = ['reaction', 'synthesis', 'compound', 'molecule', 'chemical', 'catalyst', 'coupling', 
                        'catalysis', 'organic', 'ligand', 'reagent', 'solvent']
        mat_keywords = ['material', 'crystal', 'polymer', 'alloy', 'nanoparticle', 'battery', 'batteries', 'electrode', 'cathode', 'anode', 'li-ion', 'lithium']
        
        bio_score = sum(1 for kw in bio_keywords if kw in topic_lower)
        chem_score = sum(1 for kw in chem_keywords if kw in topic_lower)
        mat_score = sum(1 for kw in mat_keywords if kw in topic_lower)
        
        # Determine type
        if mat_score > 0:
            inv_type = "materials"
        elif bio_score > 0 and chem_score > 0:
            inv_type = "interdisciplinary"
        elif chem_score > bio_score:
            inv_type = "chemistry"
        elif bio_score > 0:
            inv_type = "biology"
        else:
            inv_type = "interdisciplinary"
        
        # Determine entities
        entities = {
            "proteins": bio_score > 0,
            "compounds": chem_score > 0 or inv_type == "chemistry",
            "genes": bio_score > 0,
            "reactions": chem_score > 0,
            "materials": mat_score > 0
        }
        
        # Determine skill categories
        categories = ["literature"]  # Always include literature
        if inv_type in ["biology", "interdisciplinary"]:
            categories.extend(["proteins", "bioinformatics"])
        if inv_type in ["chemistry", "interdisciplinary"]:
            categories.extend(["compounds"])
        if inv_type == "materials":
            categories.append("materials")
        
        return TopicAnalysis(
            investigation_type=inv_type,
            key_concepts=[topic],
            entities_expected=entities,
            recommended_skill_categories=categories,
            reasoning=f"Keyword-based classification: {inv_type}"
        )


# Global analyzer instance
_analyzer = None

def get_analyzer(agent_name: str) -> LLMTopicAnalyzer:
    """Get topic analyzer instance."""
    global _analyzer
    if _analyzer is None or _analyzer.agent_name != agent_name:
        _analyzer = LLMTopicAnalyzer(agent_name)
    return _analyzer
