"""
LLM-Powered Topic Analyzer

Uses the agent's LLM to intelligently analyze research topics and determine:
- Investigation type (biology, chemistry, materials, interdisciplinary)
- Key concepts and entities
- Recommended skill categories
- Reasoning for classification

Replaces hardcoded keyword matching with intelligent reasoning.
"""

import subprocess
import json
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


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
        """Call LLM via OpenClaw."""
        try:
            result = subprocess.run(
                [
                    "openclaw", "agent",
                    "--message", prompt,
                    "--session-id", f"topic_analysis_{self.agent_name}"
                ],
                capture_output=True,
                text=True,
                timeout=45  # Increased timeout - LLM may need time
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            else:
                return ""
                
        except subprocess.TimeoutExpired:
            # LLM timeout - that's ok, fallback will work
            return ""
        except FileNotFoundError:
            # openclaw not found - skip LLM, use fallback
            return ""
        except Exception as e:
            # Other errors - use fallback silently
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
        mat_keywords = ['material', 'crystal', 'polymer', 'alloy', 'nanoparticle']
        
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
