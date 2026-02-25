"""
Skill Executor - Universal execution engine for scientific skills

Handles execution of:
- Python scripts (existing ScienceClaw skills)
- Python packages (import and call directly)
- Database APIs (REST/GraphQL)
- CLI tools (command-line executables)

Returns standardized JSON results for chaining.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import sys


class SkillExecutor:
    """
    Universal executor for scientific skills.
    
    Provides unified interface to run any skill type and return structured results.
    """
    
    def __init__(self, scienceclaw_dir: Optional[Path] = None):
        """
        Initialize skill executor.
        
        Args:
            scienceclaw_dir: Root directory (auto-detected if None)
        """
        if scienceclaw_dir is None:
            scienceclaw_dir = Path(__file__).parent.parent
        
        self.scienceclaw_dir = Path(scienceclaw_dir)
    
    def execute_skill(self,
                     skill_name: str,
                     skill_metadata: Dict[str, Any],
                     parameters: Dict[str, Any],
                     timeout: int = 30) -> Dict[str, Any]:
        """
        Execute a skill with given parameters.
        
        Args:
            skill_name: Name of the skill
            skill_metadata: Skill metadata from registry
            parameters: Parameters to pass to skill
            timeout: Execution timeout in seconds
            
        Returns:
            Dict with execution results
        """
        skill_type = skill_metadata.get('type', 'tool')
        
        try:
            if skill_type == 'database':
                result = self._execute_database_skill(skill_metadata, parameters, timeout)
            elif skill_type == 'package':
                result = self._execute_package_skill(skill_metadata, parameters)
            elif skill_type in ['tool', 'integration']:
                result = self._execute_script_skill(skill_metadata, parameters, timeout)
            else:
                result = self._execute_generic_skill(skill_metadata, parameters, timeout)
            
            return {
                "status": "success",
                "skill": skill_name,
                "result": result
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "skill": skill_name,
                "error": f"Execution timeout ({timeout}s)"
            }
        except Exception as e:
            return {
                "status": "error",
                "skill": skill_name,
                "error": str(e)
            }
    
    def _execute_script_skill(self,
                             skill_metadata: Dict[str, Any],
                             parameters: Dict[str, Any],
                             timeout: int) -> Any:
        """
        Execute Python script-based skill.
        
        This is the current ScienceClaw skill format.
        """
        executables = skill_metadata.get('executables', [])
        
        if not executables:
            raise ValueError(f"No executables found for skill")
        
        # Use first executable
        script_path = executables[0]
        
        def _build_cmd(params: dict, with_format_json: bool) -> list:
            c = ["python3", script_path]
            for key, value in params.items():
                flag = f"--{key.replace('_', '-')}"
                if isinstance(value, list):
                    if value:
                        c.extend([flag] + [str(v) for v in value])
                elif isinstance(value, dict):
                    pass
                else:
                    c.extend([flag, str(value)])
            if with_format_json and "format" not in params:
                c.extend(["--format", "json"])
            return c

        def _run(cmd):
            return subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout, cwd=self.scienceclaw_dir
            )

        # First attempt: with --format json so output is parseable structured data
        result = _run(_build_cmd(parameters, with_format_json=True))

        if result.returncode != 0:
            # --format json may be unrecognised; retry without it
            result = _run(_build_cmd(parameters, with_format_json=False))

        if result.returncode != 0:
            # Try to recover by injecting topic as query when required args are missing
            needs_query = ("required" in result.stderr or
                           "unrecognized arguments" in result.stderr or
                           "invalid choice" in result.stderr)
            if needs_query:
                query_val = (parameters.get("query") or parameters.get("search")
                             or parameters.get("term") or parameters.get("keyword")
                             or parameters.get("topic", ""))
                if query_val:
                    minimal_params = {"query": str(query_val)}
                    if "limit" in parameters:
                        minimal_params["limit"] = str(parameters["limit"])
                    elif "max_results" in parameters:
                        minimal_params["limit"] = str(parameters["max_results"])
                    result = _run(_build_cmd(minimal_params, with_format_json=True))
                    if result.returncode != 0:
                        result = _run(_build_cmd(minimal_params, with_format_json=False))
                    if result.returncode != 0:
                        raise RuntimeError(f"Script failed: {result.stderr}")
                else:
                    raise RuntimeError(f"Script failed: {result.stderr}")
            else:
                raise RuntimeError(f"Script failed: {result.stderr}")

        # Try to parse JSON output — structured payloads enable artifact reactor matching
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            # Strip leading non-JSON lines (some skills print a status header before JSON)
            stdout = result.stdout
            for i, line in enumerate(stdout.splitlines()):
                try:
                    return json.loads("\n".join(stdout.splitlines()[i:]))
                except json.JSONDecodeError:
                    continue
            return {"output": stdout}
    
    def _execute_database_skill(self,
                                skill_metadata: Dict[str, Any],
                                parameters: Dict[str, Any],
                                timeout: int) -> Any:
        """Execute database/API skill."""
        # For now, treat like script skill
        # Future: Direct API calls without subprocess
        return self._execute_script_skill(skill_metadata, parameters, timeout)
    
    def _execute_package_skill(self,
                               skill_metadata: Dict[str, Any],
                               parameters: Dict[str, Any]) -> Any:
        """
        Execute Python package skill (direct import).
        
        Future enhancement: Import package and call directly instead of subprocess.
        """
        # For now, delegate to script execution
        return self._execute_script_skill(skill_metadata, parameters, timeout=30)
    
    def _execute_generic_skill(self,
                               skill_metadata: Dict[str, Any],
                               parameters: Dict[str, Any],
                               timeout: int) -> Any:
        """Execute generic skill."""
        return self._execute_script_skill(skill_metadata, parameters, timeout)
    
    def execute_skill_chain(self,
                           chain: List[Dict[str, Any]],
                           timeout_per_step: int = 30) -> List[Dict[str, Any]]:
        """
        Execute a chain of skills, passing results between them.
        
        Args:
            chain: List of skill execution configs:
                   [{"skill": "pubmed", "params": {...}, "pass_to_next": ["pmids"]}]
            timeout_per_step: Timeout for each step
            
        Returns:
            List of results from each step
        """
        results = []
        context = {}  # Shared context for passing data
        
        for i, step in enumerate(chain):
            skill_name = step['skill']
            params = step.get('params', {})
            
            # Inject context from previous steps
            if 'inject_from_context' in step:
                for key in step['inject_from_context']:
                    if key in context:
                        params[key] = context[key]
            
            # Execute step
            from core.skill_registry import get_registry
            registry = get_registry()
            skill_meta = registry.get_skill(skill_name)
            
            if not skill_meta:
                results.append({
                    "status": "error",
                    "skill": skill_name,
                    "error": f"Skill '{skill_name}' not found"
                })
                break
            
            result = self.execute_skill(skill_name, skill_meta, params, timeout_per_step)
            results.append(result)
            
            # Update context
            if result.get('status') == 'success' and 'pass_to_next' in step:
                for key in step['pass_to_next']:
                    if key in result.get('result', {}):
                        context[key] = result['result'][key]
        
        return results


# Global executor instance
_executor = None

def get_executor() -> SkillExecutor:
    """Get the global skill executor instance."""
    global _executor
    if _executor is None:
        _executor = SkillExecutor()
    return _executor
