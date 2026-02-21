"""
Scientific Reasoning Engine - Core orchestrator for autonomous scientific discovery

Integrates with:
- Memory system (AgentJournal, InvestigationTracker, KnowledgeGraph)
- LLM for reasoning
- 18 scientific tools for experiments

Implements the complete scientific method loop.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add parent directory to path for memory imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory import AgentJournal, InvestigationTracker, KnowledgeGraph
from reasoning.gap_detector import GapDetector
from reasoning.hypothesis_generator import HypothesisGenerator
from reasoning.experiment_designer import ExperimentDesigner
from reasoning.executor import ExperimentExecutor
from reasoning.analyzer import ResultAnalyzer


class ScientificReasoningEngine:
    """
    Core reasoning engine implementing autonomous scientific method.
    
    Uses LLM for scientific reasoning, with persistent memory
    for tracking investigations across cycles.
    """
    
    def __init__(self, agent_name: str, memory_base_dir: Optional[str] = None):
        """
        Initialize reasoning engine for an agent.
        
        Args:
            agent_name: Name of the agent (for memory system)
            memory_base_dir: Base dir for memory (default: ~/.scienceclaw). Use for isolated testing.
        """
        self.agent_name = agent_name
        
        # Initialize memory components
        if memory_base_dir:
            journal_dir = str(Path(memory_base_dir) / "journals")
            inv_dir = str(Path(memory_base_dir) / "investigations")
            kg_dir = str(Path(memory_base_dir) / "knowledge")
            self.journal = AgentJournal(agent_name, base_dir=journal_dir)
            self.tracker = InvestigationTracker(agent_name, base_dir=inv_dir)
            self.kg = KnowledgeGraph(agent_name, base_dir=kg_dir)
        else:
            self.journal = AgentJournal(agent_name)
            self.tracker = InvestigationTracker(agent_name)
            self.kg = KnowledgeGraph(agent_name)
        
        # Initialize reasoning components
        self.gap_detector = GapDetector(self.kg, self.journal)
        self.hypothesis_generator = HypothesisGenerator(self.kg, self.journal)
        self.experiment_designer = ExperimentDesigner(agent_name)
        self.executor = ExperimentExecutor(agent_name)
        self.analyzer = ResultAnalyzer(self.kg, self.journal)
    
    def run_scientific_cycle(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run one complete scientific method cycle.
        
        Steps:
        1. Check for active investigations
        2. If none, detect knowledge gaps
        3. Generate hypothesis from gap
        4. Design experiment
        5. Execute experiment
        6. Analyze results
        7. Draw conclusions
        8. Update memory
        
        Args:
            context: Optional context (posts from Infinite, etc.)
            
        Returns:
            Dictionary with cycle results and actions taken
        """
        cycle_log = {
            "agent": self.agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "actions": []
        }
        
        # Step 1: Check for active investigations
        active = self.tracker.get_active_investigations(priority="high")
        
        if active:
            # Continue existing investigation
            inv = active[0]
            cycle_log["mode"] = "continue_investigation"
            cycle_log["investigation_id"] = inv["id"]
            
            result = self._continue_investigation(inv)
            cycle_log["actions"].append(result)
            
            return cycle_log
        
        # Step 2: Detect knowledge gaps
        cycle_log["mode"] = "new_investigation"
        
        gaps = self.gap_detector.detect_gaps(context)
        
        if not gaps:
            cycle_log["status"] = "no_gaps_found"
            cycle_log["actions"].append("No knowledge gaps detected")
            return cycle_log
        
        # Select most interesting gap (first one for now)
        gap = gaps[0]
        cycle_log["gap"] = gap
        
        # Step 3: Generate hypothesis
        hypotheses = self.hypothesis_generator.generate_hypotheses(gap)
        
        if not hypotheses:
            cycle_log["status"] = "no_hypotheses"
            return cycle_log
        
        hypothesis = hypotheses[0]  # Select first/best hypothesis
        cycle_log["hypothesis"] = hypothesis
        
        # Log hypothesis to journal
        hyp_entry = self.journal.log_hypothesis(
            hypothesis=hypothesis["statement"],
            motivation=hypothesis.get("motivation", gap.get("description", "")),
            related_observations=hypothesis.get("related_observations", [])
        )
        
        # Step 4: Create investigation
        inv_id = self.tracker.create_investigation(
            hypothesis=hypothesis["statement"],
            goal=hypothesis.get("goal", "Test hypothesis"),
            planned_experiments=hypothesis.get("planned_tools", []),
            tags=hypothesis.get("tags", []),
            priority=hypothesis.get("priority", "medium")
        )
        
        cycle_log["investigation_id"] = inv_id
        cycle_log["actions"].append(f"Created investigation {inv_id[:8]}")
        
        # Step 5: Design first experiment
        experiment_plan = self.experiment_designer.design_experiment(hypothesis)
        cycle_log["experiment_plan"] = experiment_plan
        
        # Step 6: Execute experiment
        experiment_result = self.executor.execute_experiment(experiment_plan)
        cycle_log["experiment_result"] = experiment_result
        
        # Log experiment to journal
        self.journal.log_experiment(
            description=experiment_plan["description"],
            tool=experiment_plan["tool"],
            parameters=experiment_plan["parameters"],
            results=experiment_result,
            hypothesis_id=hyp_entry["timestamp"]
        )
        
        # Add to investigation tracker
        self.tracker.add_experiment(inv_id, {
            "tool": experiment_plan["tool"],
            "description": experiment_plan["description"],
            "results_summary": experiment_result.get("summary", ""),
            "status": experiment_result.get("status", "completed")
        })
        
        # Step 7: Analyze results
        analysis = self.analyzer.analyze_results(
            hypothesis=hypothesis,
            experiment_plan=experiment_plan,
            experiment_result=experiment_result
        )
        cycle_log["analysis"] = analysis
        
        # Step 8: Draw conclusions (if sufficient evidence)
        if analysis.get("sufficient_evidence", False):
            conclusion = analysis["conclusion"]
            
            # Log conclusion to journal
            self.journal.log_conclusion(
                conclusion=conclusion["statement"],
                evidence=[hyp_entry["timestamp"]],
                confidence=conclusion.get("confidence", "medium"),
                next_steps=conclusion.get("next_steps", [])
            )
            
            # Mark investigation complete
            self.tracker.mark_complete(
                investigation_id=inv_id,
                conclusion=conclusion["statement"],
                confidence=conclusion.get("confidence", "medium"),
                next_steps=conclusion.get("next_steps", [])
            )
            
            # Add to knowledge graph
            self.kg.add_finding(
                finding=conclusion["statement"],
                related_concepts=conclusion.get("concepts", []),
                relationships=conclusion.get("relationships", []),
                confidence=conclusion.get("confidence", "medium")
            )
            
            cycle_log["status"] = "investigation_completed"
            cycle_log["conclusion"] = conclusion
        else:
            # Need more experiments
            self.tracker.update_status(
                inv_id,
                "active",
                f"Initial experiment complete. {analysis.get('next_steps', 'Continue investigation')}"
            )
            cycle_log["status"] = "investigation_ongoing"
        
        return cycle_log
    
    def _continue_investigation(self, investigation: Dict[str, Any]) -> Dict[str, Any]:
        """Continue an existing investigation."""
        inv_id = investigation["id"]
        
        # Get progress
        progress = self.tracker.get_investigation_progress(inv_id)
        
        # Determine next experiment
        completed_tools = [
            exp.get("tool") for exp in investigation.get("experiments_completed", [])
        ]
        remaining = [
            tool for tool in investigation.get("planned_experiments", [])
            if tool not in completed_tools
        ]
        
        if not remaining:
            # All experiments done - need to conclude
            return {
                "action": "ready_to_conclude",
                "investigation_id": inv_id,
                "message": "All planned experiments completed"
            }
        
        # Design and execute next experiment
        next_tool = remaining[0]
        
        # Create minimal experiment plan
        experiment_plan = {
            "tool": next_tool,
            "description": f"Continue investigation using {next_tool}",
            "parameters": {},  # Would need to determine from context
            "hypothesis": investigation["hypothesis"]
        }
        
        # Execute
        result = self.executor.execute_experiment(experiment_plan)
        
        # Log
        self.journal.log_experiment(
            description=experiment_plan["description"],
            tool=next_tool,
            parameters=experiment_plan["parameters"],
            results=result
        )
        
        # Track
        self.tracker.add_experiment(inv_id, {
            "tool": next_tool,
            "description": experiment_plan["description"],
            "results_summary": result.get("summary", ""),
            "status": result.get("status", "completed")
        })
        
        return {
            "action": "continued_investigation",
            "investigation_id": inv_id,
            "tool_executed": next_tool,
            "result": result
        }
    
    def observe_knowledge_gaps(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Observe knowledge gaps from community posts.
        
        Wrapper around GapDetector for external use.
        """
        return self.gap_detector.detect_gaps({"posts": posts})
    
    def generate_hypotheses(self, gap: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate hypotheses for a knowledge gap."""
        return self.hypothesis_generator.generate_hypotheses(gap)
    
    def design_experiment(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """Design an experiment to test a hypothesis."""
        return self.experiment_designer.design_experiment(hypothesis)
    
    def execute_experiment(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an experiment plan."""
        return self.executor.execute_experiment(plan)
    
    def analyze_results(self, hypothesis: Dict[str, Any], 
                       plan: Dict[str, Any], 
                       result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze experiment results against hypothesis."""
        return self.analyzer.analyze_results(hypothesis, plan, result)
    
    def draw_conclusions(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Draw conclusions from analysis."""
        if not analysis.get("sufficient_evidence", False):
            return {
                "status": "insufficient_evidence",
                "message": "Need more experiments",
                "next_steps": analysis.get("next_steps", [])
            }
        
        return analysis.get("conclusion", {})
    
    def peer_review(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform peer review of a scientific post.
        
        Evaluates:
        - Hypothesis clarity
        - Method soundness
        - Evidence quality
        - Conclusions supported by data
        """
        review = {
            "post_id": post.get("id"),
            "timestamp": datetime.utcnow().isoformat(),
            "scores": {},
            "comments": [],
            "overall": "needs_review"
        }
        
        # Check hypothesis
        if post.get("hypothesis"):
            review["scores"]["hypothesis"] = "clear"
            review["comments"].append("Hypothesis is well-defined")
        else:
            review["scores"]["hypothesis"] = "missing"
            review["comments"].append("No hypothesis stated")
        
        # Check method
        if post.get("method"):
            review["scores"]["method"] = "described"
        else:
            review["scores"]["method"] = "missing"
            review["comments"].append("Method not described")
        
        # Check data sources
        if post.get("data_sources") or post.get("dataSources"):
            review["scores"]["data"] = "cited"
        else:
            review["scores"]["data"] = "missing"
            review["comments"].append("No data sources cited")
        
        # Overall assessment
        if all(score in ["clear", "described", "cited"] 
               for score in review["scores"].values()):
            review["overall"] = "rigorous"
        elif any(score == "missing" for score in review["scores"].values()):
            review["overall"] = "needs_improvement"
        
        return review
