"""
Gap Detector - Identify knowledge gaps from posts and memory

Detects:
- Unanswered open questions from posts
- Contradictory findings
- Missing experimental validations
- Unexplored parameter spaces
"""

from typing import Dict, List, Optional, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from memory import KnowledgeGraph, AgentJournal


class GapDetector:
    """Detects knowledge gaps from community posts and agent memory."""
    
    def __init__(self, knowledge_graph: KnowledgeGraph, journal: AgentJournal):
        """
        Initialize gap detector.
        
        Args:
            knowledge_graph: Agent's knowledge graph
            journal: Agent's journal for checking investigated topics
        """
        self.kg = knowledge_graph
        self.journal = journal
    
    def detect_gaps(self, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Detect knowledge gaps from context and memory.
        
        Args:
            context: Dictionary containing posts, recent observations, etc.
            
        Returns:
            List of knowledge gaps ordered by priority
        """
        gaps = []
        
        # 1. Check for contradictions in knowledge graph
        contradictions = self.kg.find_contradictions()
        for contr in contradictions:
            gaps.append({
                "type": "contradiction",
                "description": f"Conflicting findings: '{contr['finding_a']['name']}' vs '{contr['finding_b']['name']}'",
                "priority": "high",
                "findings": [contr['finding_a'], contr['finding_b']],
                "requires_resolution": True
            })
        
        # 2. Extract open questions from posts
        if context and "posts" in context:
            for post in context["posts"]:
                open_questions = post.get("openQuestions", post.get("open_questions", []))
                for question in open_questions:
                    # Check if already investigated
                    topics = self.journal.get_investigated_topics()
                    if not any(topic.lower() in question.lower() for topic in topics):
                        gaps.append({
                            "type": "open_question",
                            "description": question,
                            "priority": "medium",
                            "source_post": post.get("id"),
                            "context": post.get("title", "")
                        })
        
        # 3. Detect missing experimental validations
        # Find hypotheses in journal without corresponding conclusions
        hypotheses = self.journal.search("", entry_types=["hypothesis"], limit=20)
        conclusions = self.journal.search("", entry_types=["conclusion"], limit=20)
        conclusion_contents = [c["content"].lower() for c in conclusions]
        
        for hyp in hypotheses:
            hyp_content = hyp["content"].lower()
            # Simple check: if hypothesis keywords not in any conclusion
            if not any(word in " ".join(conclusion_contents) 
                      for word in hyp_content.split()[:5]):
                gaps.append({
                    "type": "unvalidated_hypothesis",
                    "description": f"Hypothesis needs validation: {hyp['content']}",
                    "priority": "medium",
                    "hypothesis_timestamp": hyp["timestamp"]
                })
        
        # 4. Detect unexplored parameter spaces
        # Look for findings with specific parameters that could be varied
        findings = self.kg.search_nodes("", node_types=["finding"])
        for finding in findings:
            props = finding.get("properties", {})
            # If finding mentions specific parameters, suggest exploring variations
            if any(key in str(props).lower() for key in ["concentration", "temperature", "ratio", "dose"]):
                gaps.append({
                    "type": "parameter_space",
                    "description": f"Explore parameter variations for: {finding['name'][:100]}",
                    "priority": "low",
                    "finding_id": finding["id"]
                })
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 1))
        
        return gaps
    
    def extract_open_questions(self, posts: List[Dict[str, Any]]) -> List[str]:
        """Extract all open questions from posts."""
        questions = []
        for post in posts:
            open_qs = post.get("openQuestions", post.get("open_questions", []))
            questions.extend(open_qs)
        return questions
    
    def find_contradictions(self) -> List[Dict[str, Any]]:
        """Find contradictory findings in knowledge graph."""
        return self.kg.find_contradictions()
    
    def identify_missing_validations(self) -> List[Dict[str, Any]]:
        """Identify hypotheses that lack experimental validation."""
        missing = []
        
        hypotheses = self.journal.search("", entry_types=["hypothesis"], limit=50)
        
        for hyp in hypotheses:
            # Check if there are experiments linked to this hypothesis
            experiments = self.journal.search(
                hyp["timestamp"],
                entry_types=["experiment"],
                limit=10
            )
            
            if not experiments:
                missing.append({
                    "hypothesis": hyp["content"],
                    "timestamp": hyp["timestamp"],
                    "reason": "No experiments conducted"
                })
        
        return missing
    
    def find_unexplored_spaces(self) -> List[Dict[str, Any]]:
        """Find unexplored parameter spaces from existing findings."""
        unexplored = []
        
        # Get all findings from knowledge graph
        findings = self.kg.search_nodes("", node_types=["finding"])
        
        for finding in findings:
            # Look for numeric parameters that could be varied
            props = finding.get("properties", {})
            
            # Simple heuristic: if mentions specific values, suggest exploring range
            content = finding.get("name", "") + " " + str(props)
            
            if any(indicator in content.lower() for indicator in [
                "mol%", "concentration", "temperature", "ratio", "dose", "at "
            ]):
                unexplored.append({
                    "finding": finding["name"],
                    "suggestion": "Explore parameter variations",
                    "finding_id": finding["id"]
                })
        
        return unexplored
