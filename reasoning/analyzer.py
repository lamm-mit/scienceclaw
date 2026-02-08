"""
Result Analyzer - Analyze experiment results against hypotheses

Determines if results support/refute hypothesis, calculates confidence
"""

from typing import Dict, Any, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from memory import KnowledgeGraph, AgentJournal


class ResultAnalyzer:
    """Analyzes experiment results and draws scientific conclusions."""
    
    def __init__(self, knowledge_graph: KnowledgeGraph, journal: AgentJournal):
        """
        Initialize result analyzer.
        
        Args:
            knowledge_graph: Agent's knowledge graph
            journal: Agent's journal
        """
        self.kg = knowledge_graph
        self.journal = journal
    
    def analyze_results(self, hypothesis: Dict[str, Any], 
                       experiment_plan: Dict[str, Any],
                       experiment_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze experiment results against hypothesis.
        
        Args:
            hypothesis: Hypothesis dict
            experiment_plan: Experiment plan
            experiment_result: Experiment result from Executor
            
        Returns:
            Analysis dict with support level, confidence, conclusion
        """
        # Check if experiment succeeded
        if experiment_result.get("status") != "success":
            return {
                "sufficient_evidence": False,
                "status": "experiment_failed",
                "error": experiment_result.get("error", "Unknown error"),
                "next_steps": ["Retry experiment", "Try alternative tool"]
            }
        
        tool = experiment_result.get("tool", "unknown")
        output = experiment_result.get("output", {})
        
        # Tool-specific analysis
        if tool == "pubmed":
            analysis = self._analyze_literature_results(hypothesis, output)
        elif tool in ["blast", "uniprot", "pdb"]:
            analysis = self._analyze_biology_results(hypothesis, output)
        elif tool in ["pubchem", "chembl", "tdc"]:
            analysis = self._analyze_chemistry_results(hypothesis, output)
        elif tool == "materials":
            analysis = self._analyze_materials_results(hypothesis, output)
        else:
            analysis = self._analyze_generic_results(hypothesis, output)
        
        # Add metadata
        analysis["tool"] = tool
        analysis["hypothesis"] = hypothesis["statement"]
        
        # Determine if sufficient for conclusion
        analysis["sufficient_evidence"] = self._is_sufficient(analysis)
        
        # Generate conclusion if sufficient
        if analysis["sufficient_evidence"]:
            analysis["conclusion"] = self._draw_conclusion(hypothesis, analysis)
        else:
            analysis["next_steps"] = self._suggest_next_steps(hypothesis, analysis)
        
        return analysis
    
    def _analyze_literature_results(self, hypothesis: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze PubMed literature search results."""
        papers = output.get("papers", output.get("results", []))
        
        if not papers:
            return {
                "support": "inconclusive",
                "confidence": "low",
                "reasoning": "No papers found",
                "evidence_count": 0
            }
        
        # Simple analysis: assume some papers are relevant
        evidence_count = len(papers)
        
        if evidence_count >= 5:
            support = "supported"
            confidence = "medium"
            reasoning = f"Found {evidence_count} papers providing evidence"
        elif evidence_count >= 2:
            support = "partially_supported"
            confidence = "low"
            reasoning = f"Found {evidence_count} papers, limited evidence"
        else:
            support = "inconclusive"
            confidence = "low"
            reasoning = "Insufficient papers found"
        
        return {
            "support": support,
            "confidence": confidence,
            "reasoning": reasoning,
            "evidence_count": evidence_count,
            "papers": [p.get("title", "")[:100] for p in papers[:3]]
        }
    
    def _analyze_biology_results(self, hypothesis: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze biology tool results (BLAST, UniProt, PDB)."""
        # Check for hits/matches
        has_results = bool(
            output.get("hits") or 
            output.get("entry") or 
            output.get("structures")
        )
        
        if has_results:
            return {
                "support": "supported",
                "confidence": "medium",
                "reasoning": "Biological data found matching hypothesis",
                "evidence_count": 1
            }
        else:
            return {
                "support": "refuted",
                "confidence": "medium",
                "reasoning": "No matching biological data found",
                "evidence_count": 0
            }
    
    def _analyze_chemistry_results(self, hypothesis: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze chemistry tool results (PubChem, ChEMBL, TDC)."""
        has_results = bool(
            output.get("compound") or 
            output.get("activities") or 
            output.get("predictions")
        )
        
        if has_results:
            # Check predictions if available
            predictions = output.get("predictions", {})
            if predictions:
                # Analyze prediction values
                return {
                    "support": "supported",
                    "confidence": "medium",
                    "reasoning": f"Computational predictions obtained: {predictions}",
                    "evidence_count": 1,
                    "predictions": predictions
                }
            
            return {
                "support": "supported",
                "confidence": "medium",
                "reasoning": "Chemical data found",
                "evidence_count": 1
            }
        else:
            return {
                "support": "inconclusive",
                "confidence": "low",
                "reasoning": "No chemical data found",
                "evidence_count": 0
            }
    
    def _analyze_materials_results(self, hypothesis: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Materials Project results."""
        has_material = bool(output.get("material"))
        
        if has_material:
            return {
                "support": "supported",
                "confidence": "medium",
                "reasoning": "Material properties obtained",
                "evidence_count": 1
            }
        else:
            return {
                "support": "inconclusive",
                "confidence": "low",
                "reasoning": "Material not found",
                "evidence_count": 0
            }
    
    def _analyze_generic_results(self, hypothesis: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
        """Generic analysis for unknown tools."""
        has_data = bool(output and len(output) > 0)
        
        if has_data:
            return {
                "support": "partially_supported",
                "confidence": "low",
                "reasoning": "Data obtained, requires manual review",
                "evidence_count": 1
            }
        else:
            return {
                "support": "inconclusive",
                "confidence": "low",
                "reasoning": "No data obtained",
                "evidence_count": 0
            }
    
    def _is_sufficient(self, analysis: Dict[str, Any]) -> bool:
        """Determine if evidence is sufficient for conclusion."""
        support = analysis.get("support", "inconclusive")
        confidence = analysis.get("confidence", "low")
        evidence_count = analysis.get("evidence_count", 0)
        
        # Need at least medium confidence and some evidence
        if confidence == "low" or evidence_count == 0:
            return False
        
        # Supported or refuted with medium+ confidence is sufficient
        if support in ["supported", "refuted"] and confidence in ["medium", "high"]:
            return True
        
        return False
    
    def _draw_conclusion(self, hypothesis: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Draw scientific conclusion from analysis."""
        support = analysis.get("support", "inconclusive")
        confidence = analysis.get("confidence", "low")
        reasoning = analysis.get("reasoning", "")
        
        if support == "supported":
            statement = f"Evidence supports the hypothesis: {hypothesis['statement']}"
        elif support == "refuted":
            statement = f"Evidence refutes the hypothesis: {hypothesis['statement']}"
        elif support == "partially_supported":
            statement = f"Partial evidence for hypothesis: {hypothesis['statement']}"
        else:
            statement = f"Inconclusive results for hypothesis: {hypothesis['statement']}"
        
        # Extract concepts for knowledge graph
        concepts = []
        # Simple extraction - in production, GPT would do this
        words = hypothesis["statement"].split()
        for word in words:
            if word[0].isupper() and len(word) > 3:
                concepts.append({"name": word, "type": "concept"})
        
        return {
            "statement": statement,
            "confidence": confidence,
            "reasoning": reasoning,
            "support_level": support,
            "concepts": concepts[:5],  # Limit to 5
            "relationships": [],  # Would extract from hypothesis
            "next_steps": self._suggest_follow_ups(hypothesis, support)
        }
    
    def _suggest_next_steps(self, hypothesis: Dict[str, Any], analysis: Dict[str, Any]) -> List[str]:
        """Suggest next experimental steps."""
        support = analysis.get("support", "inconclusive")
        tool = analysis.get("tool", "unknown")
        
        steps = []
        
        if support == "inconclusive":
            steps.append(f"Try alternative tool or approach")
            steps.append("Gather more data from different sources")
        
        if tool == "pubmed":
            steps.append("Conduct experimental validation")
        
        # Add tool-specific next steps
        planned = hypothesis.get("planned_tools", [])
        if len(planned) > 1:
            steps.append(f"Continue with next planned tool: {planned[1]}")
        
        if not steps:
            steps.append("Review results and refine hypothesis")
        
        return steps
    
    def _suggest_follow_ups(self, hypothesis: Dict[str, Any], support: str) -> List[str]:
        """Suggest follow-up investigations."""
        follow_ups = []
        
        if support == "supported":
            follow_ups.append("Test hypothesis in different contexts")
            follow_ups.append("Explore mechanisms underlying the finding")
        elif support == "refuted":
            follow_ups.append("Investigate why hypothesis was incorrect")
            follow_ups.append("Formulate alternative hypothesis")
        elif support == "partially_supported":
            follow_ups.append("Identify conditions where hypothesis holds")
            follow_ups.append("Gather more evidence")
        
        return follow_ups
