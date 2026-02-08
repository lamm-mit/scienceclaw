"""
Experiment Executor - Execute designed experiments using scientific tools

Runs bash commands for tool scripts, collects JSON outputs
"""

import subprocess
import json
import os
from typing import Dict, Any
from pathlib import Path


class ExperimentExecutor:
    """Executes scientific experiments using tool scripts."""
    
    def __init__(self, agent_name: str):
        """
        Initialize experiment executor.
        
        Args:
            agent_name: Name of the agent
        """
        self.agent_name = agent_name
        self.scienceclaw_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def execute_experiment(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an experiment plan.
        
        Args:
            plan: Experiment plan from ExperimentDesigner
            
        Returns:
            Experiment result dict with output, status, errors
        """
        script_path = plan.get("script_path")
        parameters = plan.get("parameters", {})
        tool = plan.get("tool", "unknown")
        
        if not script_path or not os.path.exists(script_path):
            return {
                "status": "error",
                "error": f"Script not found: {script_path}",
                "tool": tool
            }
        
        # Build command
        cmd = ["python3", script_path]
        
        # Add parameters as arguments
        for key, value in parameters.items():
            cmd.append(f"--{key}")
            cmd.append(str(value))
        
        try:
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                cwd=self.scienceclaw_root
            )
            
            if result.returncode == 0:
                # Try to parse JSON output
                try:
                    output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    output = {"raw_output": result.stdout}
                
                return {
                    "status": "success",
                    "tool": tool,
                    "output": output,
                    "summary": self._summarize_output(output, tool),
                    "command": " ".join(cmd)
                }
            else:
                return {
                    "status": "error",
                    "tool": tool,
                    "error": result.stderr or result.stdout,
                    "return_code": result.returncode,
                    "command": " ".join(cmd)
                }
        
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "tool": tool,
                "error": "Command timed out after 120 seconds",
                "command": " ".join(cmd)
            }
        
        except Exception as e:
            return {
                "status": "error",
                "tool": tool,
                "error": str(e),
                "command": " ".join(cmd)
            }
    
    def _summarize_output(self, output: Dict[str, Any], tool: str) -> str:
        """
        Create human-readable summary of tool output.
        
        Args:
            output: Tool output dict
            tool: Tool name
            
        Returns:
            Summary string
        """
        if tool == "pubmed":
            papers = output.get("papers", output.get("results", []))
            return f"Found {len(papers)} papers"
        
        elif tool == "blast":
            hits = output.get("hits", [])
            return f"Found {len(hits)} sequence matches"
        
        elif tool == "uniprot":
            if "entry" in output:
                return f"Retrieved protein: {output['entry'].get('id', 'unknown')}"
            return "Protein data retrieved"
        
        elif tool == "pubchem":
            if "compound" in output:
                return f"Found compound: {output['compound'].get('name', 'unknown')}"
            return "Compound data retrieved"
        
        elif tool == "chembl":
            activities = output.get("activities", [])
            return f"Found {len(activities)} bioactivity records"
        
        elif tool == "tdc":
            predictions = output.get("predictions", {})
            return f"Predictions: {predictions}"
        
        elif tool == "pdb":
            structures = output.get("structures", [])
            return f"Found {len(structures)} structures"
        
        elif tool == "materials":
            if "material" in output:
                return f"Material: {output['material'].get('formula', 'unknown')}"
            return "Material data retrieved"
        
        elif tool == "websearch":
            results = output.get("results", [])
            return f"Found {len(results)} web results"
        
        else:
            # Generic summary
            if isinstance(output, dict):
                return f"Retrieved {len(output)} data fields"
            return "Experiment completed"
    
    def execute_chain(self, plans: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """
        Execute a chain of experiments, passing outputs as inputs.
        
        Args:
            plans: List of experiment plans
            
        Returns:
            List of results
        """
        results = []
        context = {}
        
        for plan in plans:
            # Merge context into parameters
            plan["parameters"].update(context)
            
            result = self.execute_experiment(plan)
            results.append(result)
            
            # Extract key outputs for next step
            if result["status"] == "success":
                output = result.get("output", {})
                
                # Extract common outputs
                if "smiles" in output:
                    context["smiles"] = output["smiles"]
                if "sequence" in output:
                    context["sequence"] = output["sequence"]
                if "pdb_id" in output:
                    context["pdb_id"] = output["pdb_id"]
        
        return results
    
    def validate_tool_available(self, tool_name: str) -> bool:
        """
        Check if a tool is available.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if tool script exists
        """
        tool_scripts = {
            "pubmed": "skills/pubmed/scripts/pubmed_search.py",
            "blast": "skills/blast/scripts/blast_search.py",
            "uniprot": "skills/uniprot/scripts/uniprot_fetch.py",
            "pubchem": "skills/pubchem/scripts/pubchem_search.py",
            "chembl": "skills/chembl/scripts/chembl_search.py",
            "tdc": "skills/tdc/scripts/tdc_predict.py",
            "pdb": "skills/pdb/scripts/pdb_search.py",
            "materials": "skills/materials/scripts/materials_lookup.py",
            "websearch": "skills/websearch/scripts/web_search.py"
        }
        
        script = tool_scripts.get(tool_name)
        if not script:
            return False
        
        full_path = os.path.join(self.scienceclaw_root, script)
        return os.path.exists(full_path)
