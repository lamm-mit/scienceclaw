"""Optional adapter to the existing ScienceClaw skill runtime."""

from __future__ import annotations

import sys
from pathlib import Path

from categoryscienceclaw.kernel.models import Artifact, ExecutionResult, MorphismSignature


class ScienceClawSkillExecutor:
    """Wrap ScienceClaw's SkillExecutor without making it a hard dependency."""

    def __init__(self, scienceclaw_dir: str | Path = "/home/fiona/LAMM/scienceclaw"):
        self.scienceclaw_dir = Path(scienceclaw_dir)
        if str(self.scienceclaw_dir) not in sys.path:
            sys.path.insert(0, str(self.scienceclaw_dir))
        from core.skill_executor import SkillExecutor
        from core.skill_registry import get_registry

        self._executor = SkillExecutor(self.scienceclaw_dir)
        self._registry = get_registry()

    def execute(
        self,
        *,
        morphism: MorphismSignature,
        inputs: list[Artifact],
        query: str,
        agent_name: str,
    ) -> ExecutionResult:
        del agent_name
        skill_name = str(morphism.metadata.get("skill_name") or morphism.name)
        skill_meta = self._registry.get_skill(skill_name)
        if not skill_meta:
            return ExecutionResult(status="error", payload={}, error=f"ScienceClaw skill not found: {skill_name}")

        params = dict(morphism.metadata.get("params", {}))
        params.setdefault("query", query)
        for artifact in inputs:
            for key, value in artifact.payload.items():
                params.setdefault(key, value)

        result = self._executor.execute_skill(
            skill_name=skill_name,
            skill_metadata=skill_meta,
            parameters=params,
            timeout=int(morphism.metadata.get("timeout", 45)),
        )
        if result.get("status") != "success":
            return ExecutionResult(status="error", payload={}, error=str(result.get("error", "skill failed")))
        payload = result.get("result", {})
        if not isinstance(payload, dict):
            payload = {"output": payload}
        return ExecutionResult(status="success", payload=payload)
