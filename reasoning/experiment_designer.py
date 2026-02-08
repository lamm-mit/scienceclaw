"""
Experiment Designer - Design experiments to test hypotheses

Selects appropriate tools, defines parameters, creates execution plan
"""

from typing import Dict, List, Optional, Any
import os


class ExperimentDesigner:
    """Designs experiments to test scientific hypotheses."""
    
    # Available tools and their capabilities
    TOOLS = {
        "pubmed": {
            "description": "Search biomedical literature",
            "input": "search query",
            "output": "list of papers with abstracts",
            "script": "skills/pubmed/scripts/pubmed_search.py"
        },
        "blast": {
            "description": "Sequence homology search",
            "input": "protein/DNA sequence",
            "output": "similar sequences with alignment scores",
            "script": "skills/blast/scripts/blast_search.py"
        },
        "uniprot": {
            "description": "Protein information retrieval",
            "input": "protein ID or name",
            "output": "protein annotations, sequence, function",
            "script": "skills/uniprot/scripts/uniprot_fetch.py"
        },
        "pubchem": {
            "description": "Chemical compound search",
            "input": "compound name or SMILES",
            "output": "compound properties, SMILES, identifiers",
            "script": "skills/pubchem/scripts/pubchem_search.py"
        },
        "chembl": {
            "description": "Bioactivity database search",
            "input": "compound or target",
            "output": "bioactivity data, IC50 values",
            "script": "skills/chembl/scripts/chembl_search.py"
        },
        "tdc": {
            "description": "ADMET property prediction",
            "input": "SMILES string",
            "output": "predicted properties (BBB, toxicity, etc.)",
            "script": "skills/tdc/scripts/tdc_predict.py"
        },
        "pdb": {
            "description": "Protein structure database",
            "input": "PDB ID or protein name",
            "output": "structure file, metadata",
            "script": "skills/pdb/scripts/pdb_search.py"
        },
        "materials": {
            "description": "Materials Project database",
            "input": "material formula or ID",
            "output": "crystal structure, properties",
            "script": "skills/materials/scripts/materials_lookup.py"
        },
        "websearch": {
            "description": "General web search",
            "input": "search query",
            "output": "web results with summaries",
            "script": "skills/websearch/scripts/web_search.py"
        }
    }
    
    def __init__(self, agent_name: str):
        """
        Initialize experiment designer.
        
        Args:
            agent_name: Name of the agent (for script paths)
        """
        self.agent_name = agent_name
        self.scienceclaw_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def design_experiment(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Design an experiment to test a hypothesis.
        
        Args:
            hypothesis: Hypothesis dict from HypothesisGenerator
            
        Returns:
            Experiment plan dict with tool, parameters, expected output
        """
        # Get planned tools from hypothesis
        planned_tools = hypothesis.get("planned_tools", ["pubmed"])
        
        # Select first tool (sequential execution)
        tool_name = planned_tools[0] if planned_tools else "pubmed"
        
        # Get tool info
        tool_info = self.TOOLS.get(tool_name, self.TOOLS["pubmed"])
        
        # Generate parameters based on hypothesis and tool
        parameters = self._generate_parameters(hypothesis, tool_name)
        
        # Create experiment plan
        plan = {
            "hypothesis": hypothesis["statement"],
            "tool": tool_name,
            "tool_description": tool_info["description"],
            "script_path": os.path.join(self.scienceclaw_root, tool_info["script"]),
            "parameters": parameters,
            "expected_output": tool_info["output"],
            "description": f"Use {tool_name} to investigate: {hypothesis['statement'][:100]}",
            "success_criteria": hypothesis.get("success_criteria", "Gather relevant data"),
            "validation_method": self._determine_validation_method(hypothesis, tool_name)
        }
        
        return plan
    
    def _generate_parameters(self, hypothesis: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
        """
        Generate parameters for tool execution based on hypothesis.
        
        This is simplified - in production, GPT would generate these.
        """
        hyp_statement = hypothesis["statement"].lower()
        
        if tool_name == "pubmed":
            # Extract key terms for search
            query = self._extract_search_terms(hypothesis["statement"])
            return {
                "query": query,
                "max_results": 10
            }
        
        elif tool_name == "blast":
            # Would need sequence from hypothesis
            return {
                "query": hypothesis.get("sequence", ""),
                "program": "blastp"
            }
        
        elif tool_name == "uniprot":
            # Extract protein name
            return {
                "query": self._extract_protein_name(hypothesis["statement"])
            }
        
        elif tool_name == "pubchem":
            # Extract compound name
            return {
                "query": self._extract_compound_name(hypothesis["statement"]),
                "format": "json"
            }
        
        elif tool_name == "chembl":
            return {
                "query": self._extract_compound_name(hypothesis["statement"])
            }
        
        elif tool_name == "tdc":
            # Would need SMILES from previous step
            return {
                "smiles": hypothesis.get("smiles", "CCO"),  # Placeholder
                "model": "BBB_Martins-AttentiveFP"
            }
        
        elif tool_name == "pdb":
            return {
                "query": self._extract_protein_name(hypothesis["statement"])
            }
        
        elif tool_name == "materials":
            return {
                "formula": self._extract_material_formula(hypothesis["statement"])
            }
        
        elif tool_name == "websearch":
            return {
                "query": hypothesis["statement"][:200]
            }
        
        else:
            # Generic fallback
            return {"query": hypothesis["statement"][:200]}
    
    def _extract_search_terms(self, text: str) -> str:
        """Extract key search terms from text."""
        # Simple extraction - remove common words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "can", "will", "does"}
        words = text.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        return " ".join(keywords[:10])
    
    def _extract_protein_name(self, text: str) -> str:
        """Extract protein name from text (simple heuristic)."""
        # Look for capitalized words or known patterns
        words = text.split()
        for word in words:
            if word[0].isupper() and len(word) > 3:
                return word
        return "protein"
    
    def _extract_compound_name(self, text: str) -> str:
        """Extract compound name from text."""
        # Look for chemical-sounding terms
        words = text.split()
        for word in words:
            if any(x in word.lower() for x in ["lin-", "peg-", "dma", "acid"]):
                return word
        return "compound"
    
    def _extract_material_formula(self, text: str) -> str:
        """Extract material formula from text."""
        # Look for chemical formulas
        words = text.split()
        for word in words:
            if any(c.isdigit() for c in word) and any(c.isupper() for c in word):
                return word
        return "Fe2O3"  # Default
    
    def _determine_validation_method(self, hypothesis: Dict[str, Any], tool_name: str) -> str:
        """Determine how to validate experiment results."""
        if tool_name == "pubmed":
            return "Count papers supporting vs contradicting hypothesis"
        elif tool_name in ["blast", "uniprot"]:
            return "Check if results match expected proteins/sequences"
        elif tool_name in ["pubchem", "chembl"]:
            return "Verify compound properties match predictions"
        elif tool_name == "tdc":
            return "Compare predicted values to known data"
        else:
            return "Qualitative assessment of results"
    
    def chain_experiments(self, hypotheses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Design a chain of experiments for complex investigations.
        
        Args:
            hypotheses: List of related hypotheses
            
        Returns:
            List of experiment plans in execution order
        """
        plans = []
        for hyp in hypotheses:
            plan = self.design_experiment(hyp)
            plans.append(plan)
        return plans
