"""
Hypothesis Generator - Generate testable hypotheses from knowledge gaps

Uses LLM for scientific reasoning patterns:
- "If A correlates with B, does C also correlate?"
- "If method M works for X, does it work for similar Y?"
- "If property P varies with Q, what are the boundary conditions?"
"""

from typing import Dict, List, Optional, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from memory import KnowledgeGraph, AgentJournal


class HypothesisGenerator:
    """Generates testable scientific hypotheses from knowledge gaps."""
    
    def __init__(self, knowledge_graph: KnowledgeGraph, journal: AgentJournal):
        """
        Initialize hypothesis generator.
        
        Args:
            knowledge_graph: Agent's knowledge graph for context
            journal: Agent's journal for checking past hypotheses
        """
        self.kg = knowledge_graph
        self.journal = journal
    
    def generate_hypotheses(self, gap: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate testable hypotheses for a knowledge gap.
        
        Args:
            gap: Knowledge gap dict from GapDetector
            
        Returns:
            List of hypothesis dicts with statement, rationale, test plan
        """
        gap_type = gap.get("type", "unknown")
        
        if gap_type == "contradiction":
            return self._generate_from_contradiction(gap)
        elif gap_type == "open_question":
            return self._generate_from_question(gap)
        elif gap_type == "unvalidated_hypothesis":
            return self._revive_hypothesis(gap)
        elif gap_type == "parameter_space":
            return self._generate_parameter_hypothesis(gap)
        else:
            return self._generate_generic(gap)
    
    def _generate_from_contradiction(self, gap: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate hypotheses to resolve contradictions."""
        finding_a = gap["findings"][0]
        finding_b = gap["findings"][1]
        
        hypotheses = [
            {
                "statement": f"The contradiction between '{finding_a['name'][:80]}...' and '{finding_b['name'][:80]}...' is due to different experimental conditions",
                "motivation": "Contradictory findings often result from methodological differences",
                "type": "resolution",
                "priority": "high",
                "testable": True,
                "success_criteria": "Identify specific experimental parameters that explain the difference",
                "planned_tools": ["pubmed", "comparison_analysis"],
                "related_observations": [finding_a.get("source"), finding_b.get("source")],
                "tags": ["contradiction", "validation"]
            },
            {
                "statement": f"One of the conflicting findings is incorrect due to experimental error or limited sample size",
                "motivation": "Alternative explanation for contradiction",
                "type": "resolution",
                "priority": "high",
                "testable": True,
                "success_criteria": "Find evidence supporting one finding over the other",
                "planned_tools": ["pubmed", "data_review"],
                "tags": ["contradiction", "validation"]
            }
        ]
        
        return hypotheses
    
    def _generate_from_question(self, gap: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate hypotheses from open questions."""
        question = gap["description"]
        
        # Simple transformation of question to hypothesis
        # In practice, LLM would do sophisticated reasoning here
        
        hypothesis = {
            "statement": self._question_to_hypothesis(question),
            "motivation": f"Addressing open question from community: {question}",
            "type": "exploratory",
            "priority": gap.get("priority", "medium"),
            "testable": True,
            "success_criteria": "Provide evidence-based answer to the question",
            "planned_tools": self._select_tools_for_question(question),
            "related_observations": [gap.get("source_post")],
            "tags": ["community_question", "exploration"]
        }
        
        return [hypothesis]
    
    def _revive_hypothesis(self, gap: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Revive an unvalidated hypothesis for testing."""
        return [{
            "statement": gap["description"].replace("Hypothesis needs validation: ", ""),
            "motivation": "Previously stated hypothesis that was never tested",
            "type": "validation",
            "priority": "medium",
            "testable": True,
            "success_criteria": "Complete experimental validation",
            "planned_tools": ["pubmed", "data_analysis"],
            "related_observations": [gap.get("hypothesis_timestamp")],
            "tags": ["validation", "follow_up"]
        }]
    
    def _generate_parameter_hypothesis(self, gap: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate hypothesis for exploring parameter space."""
        return [{
            "statement": gap["description"],
            "motivation": "Systematic parameter space exploration",
            "type": "optimization",
            "priority": "low",
            "testable": True,
            "success_criteria": "Identify optimal parameter range",
            "planned_tools": ["literature_search", "computational_prediction"],
            "related_observations": [gap.get("finding_id")],
            "tags": ["optimization", "parameter_sweep"]
        }]
    
    def _generate_generic(self, gap: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate generic hypothesis from untyped gap."""
        return [{
            "statement": f"Investigate: {gap.get('description', 'Unknown gap')}",
            "motivation": "Knowledge gap identified",
            "type": "exploratory",
            "priority": gap.get("priority", "medium"),
            "testable": True,
            "success_criteria": "Gather relevant data and form conclusions",
            "planned_tools": ["pubmed", "websearch"],
            "tags": ["exploration"]
        }]
    
    def _question_to_hypothesis(self, question: str) -> str:
        """
        Convert a question to a testable hypothesis.
        
        Simple rules for MVP - in production, GPT would handle this.
        """
        question = question.strip().rstrip("?")
        
        # Common patterns
        if question.lower().startswith("what"):
            return question.replace("What", "We can determine what", 1)
        elif question.lower().startswith("how"):
            return question.replace("How", "We can explain how", 1)
        elif question.lower().startswith("why"):
            return question.replace("Why", "We can determine why", 1)
        elif question.lower().startswith("does"):
            return question  # Already hypothesis-like
        elif question.lower().startswith("is"):
            return question  # Already hypothesis-like
        else:
            return f"Investigation of: {question}"
    
    def _select_tools_for_question(self, question: str) -> List[str]:
        """
        Select appropriate tools for investigating a question.
        
        Simple keyword matching for MVP - GPT would be better.
        """
        question_lower = question.lower()
        tools = []
        
        # Biology tools
        if any(word in question_lower for word in ["protein", "sequence", "gene", "blast"]):
            tools.extend(["blast", "uniprot", "pdb"])
        if any(word in question_lower for word in ["paper", "literature", "study", "research"]):
            tools.append("pubmed")
        
        # Chemistry tools
        if any(word in question_lower for word in ["compound", "molecule", "chemical", "drug", "smiles"]):
            tools.extend(["pubchem", "chembl"])
        if any(word in question_lower for word in ["admet", "toxicity", "solubility", "permeability"]):
            tools.append("tdc")
        
        # Materials
        if any(word in question_lower for word in ["material", "crystal", "band gap"]):
            tools.append("materials")
        
        # Default fallback
        if not tools:
            tools = ["pubmed", "websearch"]
        
        return tools[:3]  # Limit to 3 tools for initial investigation
    
    def generate_followup_hypothesis(self, conclusion: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate follow-up hypothesis from a conclusion.
        
        Args:
            conclusion: Conclusion dict from ResultAnalyzer
            
        Returns:
            Follow-up hypothesis or None
        """
        next_steps = conclusion.get("next_steps", [])
        
        if not next_steps:
            return None
        
        # Convert first next step to hypothesis
        next_step = next_steps[0]
        
        return {
            "statement": next_step,
            "motivation": f"Follow-up from conclusion: {conclusion['statement'][:100]}",
            "type": "follow_up",
            "priority": "medium",
            "testable": True,
            "success_criteria": "Extend understanding from previous investigation",
            "planned_tools": ["pubmed", "data_analysis"],
            "tags": ["follow_up", "extension"]
        }
