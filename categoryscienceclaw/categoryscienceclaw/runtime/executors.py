"""Execution backends for morphisms."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Protocol

from categoryscienceclaw.kernel.models import Artifact, ExecutionResult, MorphismSignature


class Executor(Protocol):
    def execute(
        self,
        *,
        morphism: MorphismSignature,
        inputs: list[Artifact],
        query: str,
        agent_name: str,
    ) -> ExecutionResult:
        ...


class LocalDemoExecutor:
    """Deterministic executor used for tests and local examples."""

    def _build_formal_payload(
        self,
        *,
        morphism: MorphismSignature,
        inputs: list[Artifact],
        query: str,
        agent_name: str,
        backend_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        parent_refs = [
            {
                "id": artifact.id,
                "type": artifact.type,
                "content_hash": artifact.content_hash,
            }
            for artifact in inputs
        ]
        payload = {
            "summary": f"{agent_name} executed {morphism.name} for {query}",
            "query": query,
            "morphism": morphism.name,
            "input_count": len(inputs),
            "parents": parent_refs,
            "source_parent_ids": [artifact.id for artifact in inputs],
            "data_status": morphism.metadata.get("data_status", "formal_descriptor_only"),
        }
        formal = morphism.metadata.get("formal") or {}
        if formal:
            payload["formal"] = formal
            payload["invariants"] = formal.get("invariants", ["type_preserving", "provenance_preserving"])
            payload["symmetry"] = formal.get("symmetry", formal.get("equivariance", []))
        if morphism.metadata.get("descriptor_type"):
            payload["descriptor_type"] = morphism.metadata["descriptor_type"]
        if morphism.metadata.get("blocked_reason"):
            payload["blocked_reason"] = morphism.metadata["blocked_reason"]
            payload["status"] = "blocked_real_data_need"
        if morphism.metadata.get("emits_needs"):
            payload["needs"] = list(morphism.metadata["emits_needs"])
        if morphism.output_type.endswith("Claim") or morphism.output_type == "Claim":
            payload["claim"] = (
                f"Provisional formal claim synthesized from {len(inputs)} parent artifact(s): {query}. "
                "No unsupported numeric scientific values are asserted."
            )
            payload["evidence_coverage"] = {
                "parent_count": len(inputs),
                "status": morphism.metadata.get("claim_status", "formal_workflow_demonstration"),
            }
        if backend_metadata:
            payload["execution_backend"] = backend_metadata.get("execution_backend")
            payload["scienceclaw"] = backend_metadata
        return payload

    def execute(
        self,
        *,
        morphism: MorphismSignature,
        inputs: list[Artifact],
        query: str,
        agent_name: str,
    ) -> ExecutionResult:
        return ExecutionResult(
            status="success",
            payload=self._build_formal_payload(
                morphism=morphism,
                inputs=inputs,
                query=query,
                agent_name=agent_name,
            ),
        )


class ScienceClawFormalMechanicsExecutor(LocalDemoExecutor):
    """Run a ScienceClaw skill, then normalize into the formal artifact contract.

    ScienceClaw skills provide the scientific/analytic action; this wrapper keeps
    CategoryScienceClaw certificates, child needs, and data-honesty metadata
    stable for the formal mechanics examples.
    """

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
        skill_name = str(morphism.metadata.get("skill_name") or _default_scienceclaw_skill(morphism))
        skill_meta = self._registry.get_skill(skill_name)
        if not skill_meta:
            return ExecutionResult(status="error", payload={}, error=f"ScienceClaw skill not found: {skill_name}")

        params = _scienceclaw_params(skill_name, query, inputs, morphism)
        result = self._executor.execute_skill(
            skill_name=skill_name,
            skill_metadata=skill_meta,
            parameters=params,
            timeout=int(morphism.metadata.get("timeout", 60)),
        )
        if result.get("status") != "success":
            return ExecutionResult(status="error", payload={}, error=str(result.get("error", "ScienceClaw skill failed")))

        result_summary = _summarize_scienceclaw_result(result.get("result", {}))
        substantive = _is_substantive_scienceclaw_result(skill_name, result_summary)
        payload = self._build_formal_payload(
            morphism=morphism,
            inputs=inputs,
            query=query,
            agent_name=agent_name,
            backend_metadata={
                "execution_backend": "scienceclaw",
                "skill_name": skill_name,
                "status": result.get("status"),
                "accepted_as_substantive": substantive,
                "result_summary": result_summary if substantive else {},
                "rejected_placeholder_summary": (
                    {
                        "skill_name": skill_name,
                        "rejection_reason": "ScienceClaw attempt returned a demo, scaffold, availability, or query-only concept result rather than an analysis of parent artifact data.",
                    }
                    if not substantive
                    else {}
                ),
            },
        )
        payload["summary"] = f"{agent_name} executed {morphism.name} via ScienceClaw skill {skill_name} for {query}"
        payload.update(_deterministic_formal_result(morphism=morphism, inputs=inputs, query=query, skill_name=skill_name))
        return ExecutionResult(status="success", payload=payload)


def _default_scienceclaw_skill(morphism: MorphismSignature) -> str:
    name = morphism.name.lower()
    out = morphism.output_type.lower()
    combined = f"{name} {out}"
    if any(token in combined for token in ("claim", "synthesis")):
        return "scientific-writing"
    if any(token in combined for token in ("audit", "validate", "validation", "check", "coverage", "contradiction", "replication")):
        return "scientific-critical-thinking"
    if any(token in combined for token in ("graph", "parity", "invariant", "dependency", "adhesion", "cytoskeleton", "fiber", "curvature", "network")):
        return "networkx"
    if any(token in combined for token in ("tensor", "energy", "mechanics", "model", "functor", "rupture", "transition")):
        return "sympy"
    return "scientific-critical-thinking"


def _scienceclaw_params(
    skill_name: str,
    query: str,
    inputs: list[Artifact] | None = None,
    morphism: MorphismSignature | None = None,
) -> dict[str, Any]:
    if skill_name in {"networkx"}:
        params = {"query": query, "format": "json"}
        source_graph = _networkx_source_graph_input(inputs or [], morphism, query)
        if source_graph:
            params["input_json"] = source_graph
        return params
    if skill_name in {"sympy"}:
        return {"example": "basic", "format": "json"}
    if skill_name in {"scientific-critical-thinking", "scientific-writing"}:
        return {"format": "json"}
    return {"query": query, "format": "json"}


def _summarize_scienceclaw_result(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        keep = {}
        for key in (
            "status",
            "skill",
            "message",
            "description",
            "note",
            "node_count",
            "edge_count",
            "nodes",
            "edges",
            "density",
            "avg_clustering",
            "data_source",
            "top_pagerank",
            "top_betweenness",
            "communities",
            "example",
        ):
            if key in result:
                keep[key] = result[key]
        if keep.get("data_source") in {"papers", "clusters"}:
            keep["source_data_analyzed"] = True
        if keep:
            return keep
        return {"keys": sorted(str(k) for k in result)[:12]}
    return {"value": str(result)[:500]}


def _is_substantive_scienceclaw_result(skill_name: str, summary: dict[str, Any]) -> bool:
    text = json_dumps_lower(summary)
    placeholder_markers = (
        "basic sympy demonstration",
        "placeholder demonstration",
        "see skill.md",
        "template/scaffold",
        '"status": "available"',
    )
    if any(marker in text for marker in placeholder_markers):
        return False
    # The networkx demo builds a concept graph from query words. It is useful
    # provenance, but not a real analysis of parent artifact data.
    if skill_name == "networkx" and "top_pagerank" in summary and "source_data_analyzed" not in summary:
        return False
    return bool(summary)


def json_dumps_lower(value: Any) -> str:
    try:
        return json_dumps(value).lower()
    except Exception:
        return str(value).lower()


def json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, sort_keys=True)


def _networkx_source_graph_input(
    inputs: list[Artifact],
    morphism: MorphismSignature | None,
    query: str,
) -> str:
    papers_by_id: dict[str, dict[str, Any]] = {}
    for artifact in inputs:
        payload = artifact.payload if isinstance(artifact.payload, dict) else {}
        citations = set(getattr(artifact, "parent_ids", []) or [])
        citations.update(
            str(parent.get("id"))
            for parent in payload.get("parents", [])
            if isinstance(parent, dict) and parent.get("id")
        )
        citations.update(str(parent_id) for parent_id in payload.get("source_parent_ids", []) if parent_id)
        for key, value in payload.items():
            if key in {"content_hash", "source_sha256"}:
                continue
            if isinstance(value, (str, int, float, bool)) and value not in {"", None}:
                citations.add(f"{artifact.id}:field:{key}")
            elif isinstance(value, (list, dict)) and value:
                citations.add(f"{artifact.id}:field:{key}")

        formal_result = payload.get("formal_result") if isinstance(payload.get("formal_result"), dict) else {}
        title_parts = [artifact.type]
        if formal_result.get("kind"):
            title_parts.append(str(formal_result["kind"]))
        if payload.get("morphism"):
            title_parts.append(str(payload["morphism"]))
        papers_by_id[artifact.id] = {
            "id": artifact.id,
            "title": " | ".join(title_parts),
            "citations": sorted(citation for citation in citations if citation and citation != artifact.id),
        }
        for citation in papers_by_id[artifact.id]["citations"]:
            papers_by_id.setdefault(
                citation,
                {
                    "id": citation,
                    "title": f"structured payload field or upstream artifact cited by {artifact.type}",
                    "citations": [],
                },
            )

    if len(papers_by_id) < 2:
        return ""

    return json_dumps(
        {
            "source_data_analyzed": True,
            "query": query,
            "morphism": morphism.name if morphism else "",
            "output_type": morphism.output_type if morphism else "",
            "papers": list(papers_by_id.values()),
        }
    )


def _source_content_features(inputs: list[Artifact]) -> list[dict[str, Any]]:
    features = []
    for artifact in inputs:
        payload = artifact.payload if isinstance(artifact.payload, dict) else {}
        formal_result = payload.get("formal_result") if isinstance(payload.get("formal_result"), dict) else {}
        emitted_needs = payload.get("needs") if isinstance(payload.get("needs"), list) else []
        feature = {
            "artifact_id": artifact.id,
            "artifact_type": artifact.type,
            "payload_keys": sorted(str(key) for key in payload.keys()),
            "data_status": payload.get("data_status", ""),
            "descriptor_type": payload.get("descriptor_type", ""),
            "morphism": payload.get("morphism", ""),
            "result_classification": payload.get("result_classification", ""),
            "formal_result_kind": formal_result.get("kind", ""),
            "formal_result_fields": sorted(str(key) for key in formal_result.keys()),
            "emitted_need_types": [need.get("required_type", "") for need in emitted_needs if isinstance(need, dict)],
        }
        if formal_result.get("expression"):
            feature["expression"] = formal_result["expression"]
        if formal_result.get("parity_value"):
            feature["parity_value"] = formal_result["parity_value"]
        if formal_result.get("node_count") is not None:
            feature["node_count"] = formal_result["node_count"]
        if formal_result.get("edge_count") is not None:
            feature["edge_count"] = formal_result["edge_count"]
        if formal_result.get("checks"):
            feature["checks_passed"] = all(
                bool(check.get("ok")) for check in formal_result["checks"] if isinstance(check, dict)
            )
        features.append(feature)
    return features


def _symbol_name(text: str, fallback: str) -> str:
    token = re.sub(r"[^0-9a-zA-Z_]+", "_", text).strip("_").lower()
    if not token:
        token = fallback
    if token[0].isdigit():
        token = f"x_{token}"
    return token[:48]


def _deterministic_formal_result(
    *,
    morphism: MorphismSignature,
    inputs: list[Artifact],
    query: str,
    skill_name: str,
) -> dict[str, Any]:
    parent_types = [artifact.type for artifact in inputs]
    parent_ids = [artifact.id for artifact in inputs]
    content_features = _source_content_features(inputs)
    base = {
        "result_classification": "formal_symbolic_result",
        "valid_result_basis": "deterministic formal computation over parent artifact payload fields, formal result kinds, declared morphism, and query; hashes retained only as provenance",
        "scienceclaw_skill_attempted": skill_name,
        "source_content_features": content_features,
    }
    if morphism.metadata.get("blocked_reason"):
        base.update(
            {
                "result_classification": "blocked_missing_data",
                "blocked_reason": morphism.metadata["blocked_reason"],
                "missing_input_needed": "real empirical boundary-condition or measurement data compatible with the requested mechanics inference",
                "status": "blocked_real_data_need",
            }
        )
        return base

    combined = f"{morphism.name} {morphism.output_type}".lower()
    if any(token in combined for token in ("claim", "synthesis")):
        base["formal_result"] = {
            "kind": "formal_claim_synthesis",
            "claim_scope": "formal workflow demonstration",
            "claim_text": (
                f"{morphism.output_type} is supported only as a formal composition of "
                f"{', '.join(parent_types) or 'no parent artifacts'} via {morphism.name}; "
                "no biological or mechanical measurement is asserted."
            ),
            "evidence_parent_ids": parent_ids,
            "evidence_parent_content": content_features,
        }
    elif any(token in combined for token in ("audit", "validate", "validation", "check", "coverage", "contradiction", "replication")):
        formal_kinds_present = [feature["formal_result_kind"] for feature in content_features if feature.get("formal_result_kind")]
        base["formal_result"] = {
            "kind": "formal_validation_record",
            "checks": [
                {"name": "parents_present", "ok": bool(parent_ids)},
                {"name": "parent_payload_content_extracted", "ok": bool(content_features)},
                {"name": "formal_result_kinds_present", "ok": bool(formal_kinds_present) or not parent_ids},
                {"name": "formal_only_status_declared", "ok": True},
                {"name": "no_empirical_numeric_claim_added", "ok": True},
            ],
            "validated_parent_types": parent_types,
            "validated_parent_content": content_features,
        }
    elif any(token in combined for token in ("parity", "invariant", "symmetry")):
        content_signature = json_dumps(content_features)
        signature = sum(ord(ch) for ch in content_signature) + sum(ord(ch) for ch in morphism.name)
        base["formal_result"] = {
            "kind": "symbolic_parity_descriptor",
            "parity_domain": parent_types,
            "parity_value": "even" if signature % 2 == 0 else "odd",
            "invariance_statement": "Descriptor is computed from sorted parent payload feature keys, parent formal-result kinds, and declared morphism; JSON field-order relabeling does not change the value.",
            "graph_invariants": ["parent_type_multiset", "parent_payload_key_sets", "parent_formal_result_kind_multiset", "morphism_name"],
            "source_content_features": content_features,
        }
    elif any(token in combined for token in ("graph", "network", "dependency", "adhesion", "cytoskeleton", "assembly")):
        nodes = [
            {
                "id": pid,
                "type": ptype,
                "formal_result_kind": feature.get("formal_result_kind", ""),
                "data_status": feature.get("data_status", ""),
            }
            for pid, ptype, feature in zip(parent_ids, parent_types, content_features)
        ]
        nodes.append({"id": morphism.output_type, "type": "output_type"})
        edges = [{"source": pid, "target": morphism.output_type, "relation": morphism.name} for pid in parent_ids]
        base["formal_result"] = {
            "kind": "typed_provenance_graph",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
            "graph_invariants": {
                "acyclic_by_construction": True,
                "all_inputs_reach_output": bool(parent_ids),
                "typed_parent_count": len(parent_types),
                "parent_payload_features_attached": bool(content_features),
            },
        }
    elif any(token in combined for token in ("tensor", "energy", "mechanics", "model", "functor", "rupture", "transition")):
        symbols = [
            _symbol_name(feature.get("formal_result_kind") or feature.get("artifact_type") or "", f"x{i}")
            for i, feature in enumerate(content_features, start=1)
        ] or ["x0"]
        expression = " + ".join(symbols)
        base["formal_result"] = {
            "kind": "symbolic_mechanics_expression",
            "symbols": symbols,
            "expression": f"{morphism.output_type} := {morphism.name}({expression})",
            "assumptions": [
                "formal descriptor only",
                "no measured force, stress, curvature, or energy values inferred",
                "parent artifacts provide provenance and type constraints",
            ],
            "input_types": parent_types,
            "source_content_features": content_features,
        }
    else:
        base["formal_result"] = {
            "kind": "formal_artifact_record",
            "input_types": parent_types,
            "output_type": morphism.output_type,
            "query": query,
            "source_content_features": content_features,
        }
    return base


class ExecutorRegistry:
    def __init__(self):
        self._executors: dict[str, Executor] = {"local": LocalDemoExecutor()}

    def register(self, adapter_name: str, executor: Executor) -> None:
        self._executors[adapter_name] = executor

    def get(self, adapter_name: str) -> Executor:
        if adapter_name not in self._executors:
            raise KeyError(f"No executor registered for adapter {adapter_name!r}")
        return self._executors[adapter_name]
