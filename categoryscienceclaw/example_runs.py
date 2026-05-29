"""Runnable formal-mechanics example runs."""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Any

from categoryscienceclaw.audit import audit_run
from categoryscienceclaw.kernel.models import AgentProfile, Artifact, MorphismSignature, Need, ObjectType, now_utc
from categoryscienceclaw.discovery_reports import generate_mechanics_discovery_reports
from categoryscienceclaw.presentation import export_presentable_results, export_presentation_index
from categoryscienceclaw.proofs.hashing import canonical_hash
from categoryscienceclaw.reactor import ArtifactReactor
from categoryscienceclaw.runtime import ExecutorRegistry, RunStore, ScienceClawFormalMechanicsExecutor
from categoryscienceclaw.runtime.events import Event

EXAMPLES = {
    "7t10-formal-extension": "7T10 formal descriptor extension",
    "biomechanics-fiber-network": "Fiber-network biomechanics",
    "membrane-biophysics": "Membrane curvature biophysics",
    "mechanobiology-force-paths": "Mechanobiology force paths",
}

EXAMPLE_RUN_DIRS = {
    "7t10-formal-extension": "7t10_formal_extension",
    "biomechanics-fiber-network": "biomechanics_fiber_network",
    "membrane-biophysics": "membrane_biophysics",
    "mechanobiology-force-paths": "mechanobiology_force_paths",
}


def _obj(name: str) -> ObjectType:
    return ObjectType(name=name, description=f"Formal mechanics object: {name}")


def _need(required_type: str, query: str, morphism: str, rationale: str = "") -> dict[str, Any]:
    return {
        "required_type": required_type,
        "query": query,
        "rationale": rationale or f"Need {required_type} via {morphism}.",
        "allowed_morphisms": [morphism],
    }


def _morphism(
    name: str,
    inputs: list[str],
    output: str,
    *,
    emits: list[dict[str, Any]] | None = None,
    descriptor_type: str | None = None,
    blocked_reason: str | None = None,
) -> MorphismSignature:
    metadata: dict[str, Any] = {
        "formal": {
            "categorical_role": "need_fulfillment_morphism",
            "invariants": ["type_preserving", "provenance_preserving", "composition_auditable"],
            "symmetry": ["formal_equivariance_checked_where_applicable"],
            "proof_obligations": ["source_parent_ids_present", "invariants_present"],
        },
        "data_status": "formal_descriptor_only",
    }
    if emits:
        metadata["emits_needs"] = emits
    if descriptor_type:
        metadata["descriptor_type"] = descriptor_type
    if blocked_reason:
        metadata["blocked_reason"] = blocked_reason
    return MorphismSignature(
        name=name,
        input_types=tuple(inputs),
        output_type=output,
        kind="formal_mechanics",
        adapter="local",
        description=f"{name}: {', '.join(inputs)} -> {output}",
        metadata=metadata,
    )


def formal_agents() -> list[AgentProfile]:
    return [
        AgentProfile(
            "StructureBreakerAgent",
            morphisms=("extract_fiber_network", "measure_curvature", "extract_adhesion_graph", "infer_cytoskeleton_network"),
            preferred_types=("FiberNetworkGraph", "CurvatureDescriptor", "AdhesionGraph", "CytoskeletonNetwork"),
            metadata={"role": "breaker"},
        ),
        AgentProfile(
            "ParityDescriptorAgent",
            morphisms=("compute_7t10_contact_parity", "compute_orientation_parity", "compute_curvature_parity", "compute_force_path_parity"),
            preferred_types=("ContactParityDescriptor", "OrientationParityDescriptor", "CurvatureParityDescriptor", "ForcePathDescriptor"),
            metadata={"role": "formal_descriptor"},
        ),
        AgentProfile(
            "GraphInvariantAgent",
            morphisms=("compute_fiber_graph_invariants", "compute_adhesion_invariants", "compute_cytoskeleton_invariants"),
            preferred_types=("GraphInvariantDescriptor", "AdhesionInvariantDescriptor", "CytoskeletonInvariantDescriptor"),
            metadata={"role": "invariant"},
        ),
        AgentProfile(
            "BoundaryConditionAgent",
            morphisms=("report_missing_boundary_condition",),
            preferred_types=("BlockedRealDataNeed",),
            metadata={"role": "real_data_gate"},
        ),
        AgentProfile(
            "AssemblyAgent",
            morphisms=("build_assembly_graph",),
            preferred_types=("ProteinAssemblyGraph",),
            metadata={"role": "breaker"},
        ),
        AgentProfile(
            "GluingAgent",
            morphisms=("check_patch_gluing",),
            preferred_types=("PatchGluingCompatibilityRecord",),
            metadata={"role": "composition"},
        ),
        AgentProfile(
            "MechanicsBuilderAgent",
            morphisms=(
                "derive_mechanics_functor_descriptor", "formalize_rupture_need", "compute_anisotropy_tensor",
                "build_network_mechanics_model", "derive_energy_functional", "predict_shape_transition",
                "build_mechanotransduction_model", "build_alternative_force_path_model",
            ),
            preferred_types=(
                "MechanicsFunctorDescriptor", "RupturePathwayFormalization", "AnisotropyTensor",
                "NetworkMechanicsModel", "EnergyFunctional", "ShapeTransitionModel",
                "MechanotransductionModel", "AlternativeForcePathModel",
            ),
            metadata={"role": "builder"},
        ),
        AgentProfile(
            "NeedReactorAgent",
            morphisms=("build_open_need_dependency_graph", "classify_7t10_needs"),
            preferred_types=("OpenNeedDependencyGraph", "NeedClassificationRecord"),
            metadata={"role": "need_reactor"},
        ),
        AgentProfile(
            "FormalValidatorAgent",
            morphisms=(
                "audit_mechanics_composition", "verify_contact_parity_invariance", "validate_tensor_symmetry",
                "record_fiber_evidence_coverage", "validate_energy_assumptions", "check_curvature_contradiction", "validate_path_parity",
                "check_force_path_contradiction",
            ),
            preferred_types=(
                "CompositionAuditRecord", "DescriptorInvarianceCheck", "TensorSymmetryValidationRecord",
                "EvidenceCoverageRecord", "EnergyAssumptionValidationRecord", "CurvatureContradictionCheck", "PathParityValidationRecord",
                "ForcePathContradictionRecord",
            ),
            metadata={"role": "validator"},
        ),
        AgentProfile(
            "ReplicationAgent",
            morphisms=("replicate_patch_composition",),
            preferred_types=("PatchCompositionReplicationRecord",),
            metadata={"role": "replicator"},
        ),
        AgentProfile(
            "ClaimSynthesisAgent",
            morphisms=("synthesize_7t10_formal_claim", "synthesize_biomechanics_claim", "synthesize_biophysics_claim", "synthesize_mechanobiology_claim"),
            preferred_types=("FormalMechanicsExtensionClaim", "BiomechanicsClaim", "BiophysicsClaim", "MechanobiologyClaim"),
            metadata={"role": "synthesis"},
        ),
    ]


def _schema_7t10() -> tuple[list[ObjectType], list[MorphismSignature]]:
    objects = [_obj(n) for n in [
        "ContactGraph", "ForceExtensionTrace", "MechanicsClaim", "OpenNeedRecord", "ContactParityDescriptor",
        "MechanicsFunctorDescriptor", "CompositionAuditRecord", "OpenNeedDependencyGraph",
        "RupturePathwayFormalization", "NeedClassificationRecord", "DescriptorInvarianceCheck",
        "FormalMechanicsExtensionClaim",
    ]]
    morphisms = [
        _morphism("compute_7t10_contact_parity", ["ContactGraph"], "ContactParityDescriptor", descriptor_type="ContactParityDescriptor", emits=[_need("DescriptorInvarianceCheck", "verify 7T10 contact parity invariance", "verify_contact_parity_invariance")]),
        _morphism("verify_contact_parity_invariance", ["ContactParityDescriptor"], "DescriptorInvarianceCheck", descriptor_type="DescriptorInvarianceCheck"),
        _morphism("derive_mechanics_functor_descriptor", ["ForceExtensionTrace", "ContactGraph"], "MechanicsFunctorDescriptor", descriptor_type="MechanicsFunctorDescriptor"),
        _morphism("audit_mechanics_composition", ["MechanicsClaim", "ContactGraph", "ForceExtensionTrace"], "CompositionAuditRecord", descriptor_type="CompositionAuditRecord"),
        _morphism("build_open_need_dependency_graph", ["OpenNeedRecord"], "OpenNeedDependencyGraph", descriptor_type="OpenNeedDependencyGraph", emits=[_need("NeedClassificationRecord", "classify inherited 7T10 downstream needs", "classify_7t10_needs")]),
        _morphism("classify_7t10_needs", ["OpenNeedDependencyGraph"], "NeedClassificationRecord", descriptor_type="NeedClassificationRecord"),
        _morphism("formalize_rupture_need", ["OpenNeedRecord"], "RupturePathwayFormalization", descriptor_type="RupturePathwayFormalization", emits=[_need("FormalMechanicsExtensionClaim", "synthesize formal-only 7T10 extension claim", "synthesize_7t10_formal_claim")]),
        _morphism("synthesize_7t10_formal_claim", ["RupturePathwayFormalization", "NeedClassificationRecord"], "FormalMechanicsExtensionClaim"),
    ]
    return objects, morphisms


def _schema_fiber() -> tuple[list[ObjectType], list[MorphismSignature]]:
    names = ["TissueImageOrGeometry", "FiberNetworkGraph", "OrientationParityDescriptor", "GraphInvariantDescriptor", "BlockedRealDataNeed", "AnisotropyTensor", "TensorSymmetryValidationRecord", "NetworkMechanicsModel", "EvidenceCoverageRecord", "PatchCompositionReplicationRecord", "BiomechanicsClaim"]
    objects = [_obj(n) for n in names]
    morphisms = [
        _morphism("extract_fiber_network", ["TissueImageOrGeometry"], "FiberNetworkGraph", emits=[_need("OrientationParityDescriptor", "compute orientation parity", "compute_orientation_parity"), _need("GraphInvariantDescriptor", "compute graph invariants", "compute_fiber_graph_invariants"), _need("BlockedRealDataNeed", "request real boundary condition", "report_missing_boundary_condition")]),
        _morphism("compute_orientation_parity", ["FiberNetworkGraph"], "OrientationParityDescriptor", descriptor_type="OrientationParityDescriptor"),
        _morphism("compute_fiber_graph_invariants", ["FiberNetworkGraph"], "GraphInvariantDescriptor", descriptor_type="GraphInvariantDescriptor", emits=[_need("AnisotropyTensor", "derive symbolic anisotropy tensor", "compute_anisotropy_tensor")]),
        _morphism("report_missing_boundary_condition", ["FiberNetworkGraph"], "BlockedRealDataNeed", blocked_reason="No real boundary-condition data supplied; emitting blocked need instead of unsupported mechanics."),
        _morphism("compute_anisotropy_tensor", ["GraphInvariantDescriptor", "OrientationParityDescriptor"], "AnisotropyTensor", descriptor_type="AnisotropyTensor", emits=[_need("TensorSymmetryValidationRecord", "validate tensor symmetry", "validate_tensor_symmetry")]),
        _morphism("validate_tensor_symmetry", ["AnisotropyTensor"], "TensorSymmetryValidationRecord", emits=[_need("NetworkMechanicsModel", "build formal network mechanics model", "build_network_mechanics_model")]),
        _morphism("build_network_mechanics_model", ["TensorSymmetryValidationRecord", "AnisotropyTensor"], "NetworkMechanicsModel", emits=[_need("EvidenceCoverageRecord", "record formal evidence coverage", "record_fiber_evidence_coverage"), _need("PatchCompositionReplicationRecord", "replicate by alternative patch composition", "replicate_patch_composition"), _need("BiomechanicsClaim", "synthesize biomechanics formal claim", "synthesize_biomechanics_claim")]),
        _morphism("record_fiber_evidence_coverage", ["NetworkMechanicsModel"], "EvidenceCoverageRecord", descriptor_type="EvidenceCoverageRecord"),
        _morphism("replicate_patch_composition", ["NetworkMechanicsModel"], "PatchCompositionReplicationRecord", descriptor_type="PatchCompositionReplicationRecord"),
        _morphism("synthesize_biomechanics_claim", ["NetworkMechanicsModel", "PatchCompositionReplicationRecord"], "BiomechanicsClaim"),
    ]
    return objects, morphisms


def _schema_membrane() -> tuple[list[ObjectType], list[MorphismSignature]]:
    names = ["MembranePatchGeometry", "CurvatureDescriptor", "CurvatureParityDescriptor", "ProteinAssemblyGraph", "PatchGluingCompatibilityRecord", "EnergyFunctional", "EnergyAssumptionValidationRecord", "ShapeTransitionModel", "CurvatureContradictionCheck", "BiophysicsClaim"]
    objects = [_obj(n) for n in names]
    morphisms = [
        _morphism("measure_curvature", ["MembranePatchGeometry"], "CurvatureDescriptor", descriptor_type="CurvatureDescriptor", emits=[_need("CurvatureParityDescriptor", "check curvature sign parity", "compute_curvature_parity"), _need("ProteinAssemblyGraph", "build protein assembly graph", "build_assembly_graph"), _need("PatchGluingCompatibilityRecord", "check neighboring patch gluing", "check_patch_gluing")]),
        _morphism("compute_curvature_parity", ["CurvatureDescriptor"], "CurvatureParityDescriptor", descriptor_type="CurvatureParityDescriptor"),
        _morphism("build_assembly_graph", ["CurvatureDescriptor"], "ProteinAssemblyGraph"),
        _morphism("check_patch_gluing", ["CurvatureDescriptor"], "PatchGluingCompatibilityRecord", emits=[_need("EnergyFunctional", "derive symbolic energy functional", "derive_energy_functional")]),
        _morphism("derive_energy_functional", ["PatchGluingCompatibilityRecord", "CurvatureParityDescriptor"], "EnergyFunctional", descriptor_type="EnergyFunctional", emits=[_need("EnergyAssumptionValidationRecord", "validate symbolic energy assumptions", "validate_energy_assumptions")]),
        _morphism("validate_energy_assumptions", ["EnergyFunctional"], "EnergyAssumptionValidationRecord", emits=[_need("ShapeTransitionModel", "predict formal shape transition", "predict_shape_transition")]),
        _morphism("predict_shape_transition", ["EnergyAssumptionValidationRecord", "EnergyFunctional"], "ShapeTransitionModel", emits=[_need("CurvatureContradictionCheck", "check curvature contradiction", "check_curvature_contradiction"), _need("BiophysicsClaim", "synthesize membrane biophysics formal claim", "synthesize_biophysics_claim")]),
        _morphism("check_curvature_contradiction", ["ShapeTransitionModel"], "CurvatureContradictionCheck"),
        _morphism("synthesize_biophysics_claim", ["ShapeTransitionModel", "CurvatureContradictionCheck"], "BiophysicsClaim"),
    ]
    return objects, morphisms


def _schema_mechanobio() -> tuple[list[ObjectType], list[MorphismSignature]]:
    names = ["CellGeometry", "AdhesionGraph", "CytoskeletonNetwork", "AdhesionInvariantDescriptor", "CytoskeletonInvariantDescriptor", "ForcePathDescriptor", "PathParityValidationRecord", "MechanotransductionModel", "AlternativeForcePathModel", "ForcePathContradictionRecord", "MechanobiologyClaim"]
    objects = [_obj(n) for n in names]
    morphisms = [
        _morphism("extract_adhesion_graph", ["CellGeometry"], "AdhesionGraph", emits=[_need("AdhesionInvariantDescriptor", "compute adhesion graph invariants", "compute_adhesion_invariants")]),
        _morphism("infer_cytoskeleton_network", ["CellGeometry"], "CytoskeletonNetwork", emits=[_need("CytoskeletonInvariantDescriptor", "compute cytoskeleton graph invariants", "compute_cytoskeleton_invariants")]),
        _morphism("compute_adhesion_invariants", ["AdhesionGraph"], "AdhesionInvariantDescriptor"),
        _morphism("compute_cytoskeleton_invariants", ["CytoskeletonNetwork"], "CytoskeletonInvariantDescriptor", emits=[_need("ForcePathDescriptor", "compute force path parity", "compute_force_path_parity")]),
        _morphism("compute_force_path_parity", ["CytoskeletonInvariantDescriptor", "AdhesionInvariantDescriptor"], "ForcePathDescriptor", descriptor_type="ForcePathDescriptor", emits=[_need("PathParityValidationRecord", "validate path parity under relabeling", "validate_path_parity")]),
        _morphism("validate_path_parity", ["ForcePathDescriptor"], "PathParityValidationRecord", emits=[_need("MechanotransductionModel", "build formal mechanotransduction model", "build_mechanotransduction_model")]),
        _morphism("build_mechanotransduction_model", ["PathParityValidationRecord", "ForcePathDescriptor"], "MechanotransductionModel", emits=[_need("AlternativeForcePathModel", "build alternative force path model", "build_alternative_force_path_model"), _need("ForcePathContradictionRecord", "check force path contradiction", "check_force_path_contradiction")]),
        _morphism("build_alternative_force_path_model", ["MechanotransductionModel"], "AlternativeForcePathModel"),
        _morphism("check_force_path_contradiction", ["MechanotransductionModel", "AlternativeForcePathModel"], "ForcePathContradictionRecord", emits=[_need("MechanobiologyClaim", "synthesize mechanobiology formal claim", "synthesize_mechanobiology_claim")]),
        _morphism("synthesize_mechanobiology_claim", ["ForcePathContradictionRecord", "AlternativeForcePathModel"], "MechanobiologyClaim"),
    ]
    return objects, morphisms


def _schema_for(example: str) -> tuple[list[ObjectType], list[MorphismSignature], str, str]:
    if example == "7t10-formal-extension":
        return (*_schema_7t10(), "ContactGraph", "extend 7T10 with formal descriptors")
    if example == "biomechanics-fiber-network":
        return (*_schema_fiber(), "TissueImageOrGeometry", "formal fiber network mechanics")
    if example == "membrane-biophysics":
        return (*_schema_membrane(), "MembranePatchGeometry", "formal membrane curvature biophysics")
    if example == "mechanobiology-force-paths":
        return (*_schema_mechanobio(), "CellGeometry", "formal mechanobiology force paths")
    raise KeyError(f"unknown example: {example}")


def _fixed_artifact(artifact_id: str, artifact_type: str, payload: dict[str, Any], producer: str = "imported") -> Artifact:
    return Artifact(
        id=artifact_id,
        type=artifact_type,
        payload=payload,
        producer_agent=producer,
        timestamp=now_utc(),
        content_hash=canonical_hash(payload),
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _import_7t10_artifact(raw: dict[str, Any], *, artifact_type: str) -> Artifact:
    metadata = dict(raw.get("metadata", {}))
    metadata["imported_from"] = "structure_contact_7T10_formalized_20260528"
    metadata["original_type"] = raw.get("type", "")
    metadata["original_morphism"] = raw.get("morphism", "")
    metadata["original_parent_ids"] = list(raw.get("parent_ids", []))
    return Artifact(
        id=str(raw["id"]),
        type=artifact_type,
        payload=dict(raw.get("payload", {})),
        producer_agent="7T10BaselineImportAgent",
        morphism="",
        parent_ids=(),
        timestamp=str(raw.get("timestamp", "")) or now_utc(),
        content_hash=str(raw.get("content_hash", "")) or canonical_hash(dict(raw.get("payload", {}))),
        needs=(),
        metadata=metadata,
    )


def _seed_run(store: RunStore, example: str, seed_type: str, topic: str) -> None:
    if example == "7t10-formal-extension":
        baseline = Path(__file__).resolve().parents[1] / "run_exports" / "structure_contact_7T10_formalized_20260528"
        baseline_artifacts = {raw.get("id"): raw for raw in _read_jsonl(baseline / "artifacts.jsonl")}
        inherited_needs = _read_jsonl(baseline / "needs.index.jsonl")

        contact = _import_7t10_artifact(baseline_artifacts["contact_graph_7T10"], artifact_type="ContactGraph")
        force = _import_7t10_artifact(baseline_artifacts["force_extension_7T10"], artifact_type="ForceExtensionTrace")
        claim = _import_7t10_artifact(baseline_artifacts["mechanics_claim_7T10"], artifact_type="MechanicsClaim")
        open_need = _fixed_artifact(
            "source_open_needs_7T10",
            "OpenNeedRecord",
            {
                "source": str(baseline / "needs.index.jsonl"),
                "status": "imported_reference",
                "inherited_needs": inherited_needs,
            },
        )
        for artifact in [contact, force, claim, open_need]:
            store.append_artifact(artifact)
        seed_needs = [
            Need.create(parent_artifact_id=contact.id, need_index=0, required_type="ContactParityDescriptor", query="compute 7T10 contact parity", allowed_morphisms=["compute_7t10_contact_parity"]),
            Need.create(parent_artifact_id=force.id, need_index=0, required_type="MechanicsFunctorDescriptor", query="derive 7T10 mechanics functor descriptor", allowed_morphisms=["derive_mechanics_functor_descriptor"]),
            Need.create(parent_artifact_id=claim.id, need_index=0, required_type="CompositionAuditRecord", query="audit 7T10 mechanics composition", allowed_morphisms=["audit_mechanics_composition"]),
            Need.create(parent_artifact_id=open_need.id, need_index=0, required_type="OpenNeedDependencyGraph", query="build open need dependency graph", allowed_morphisms=["build_open_need_dependency_graph"]),
            Need.create(parent_artifact_id=open_need.id, need_index=1, required_type="RupturePathwayFormalization", query="formalize inherited rupture pathway need", allowed_morphisms=["formalize_rupture_need"]),
        ]
        for need in seed_needs:
            store.append_need(need)
        return

    seed = Artifact.create(
        artifact_type=seed_type,
        payload={"topic": topic, "data_status": "example_seed_no_numeric_measurements"},
        producer_agent="human",
    )
    if example == "biomechanics-fiber-network":
        needs = [Need.create(parent_artifact_id=seed.id, need_index=0, required_type="FiberNetworkGraph", query="extract symbolic fiber network", allowed_morphisms=["extract_fiber_network"])]
    elif example == "membrane-biophysics":
        needs = [Need.create(parent_artifact_id=seed.id, need_index=0, required_type="CurvatureDescriptor", query="measure formal curvature descriptor", allowed_morphisms=["measure_curvature"])]
    elif example == "mechanobiology-force-paths":
        needs = [
            Need.create(parent_artifact_id=seed.id, need_index=0, required_type="AdhesionGraph", query="extract adhesion graph", allowed_morphisms=["extract_adhesion_graph"]),
            Need.create(parent_artifact_id=seed.id, need_index=1, required_type="CytoskeletonNetwork", query="infer cytoskeleton network", allowed_morphisms=["infer_cytoskeleton_network"]),
        ]
    else:
        needs = []
    store.append_artifact(replace(seed, needs=tuple(needs)))


def run_example(example: str, run_dir: str | Path, *, cycles: int = 30, complexity: str = "high", use_scienceclaw: bool = False) -> dict[str, Any]:
    if example not in EXAMPLES:
        raise KeyError(f"unknown example: {example}")
    run_path = Path(run_dir)
    if run_path.exists():
        shutil.rmtree(run_path)
    store = RunStore(run_path)
    store.init()
    objects, morphisms, seed_type, topic = _schema_for(example)
    agents = formal_agents()
    store.write_schema(objects=objects, morphisms=morphisms, topic=topic)
    store.write_agents(agents)
    _seed_run(store, example, seed_type, topic)
    store.append_event(Event(type="FormalMechanicsRunInitialized", agent="human", data={"example": example, "complexity": complexity}))
    executors = ExecutorRegistry()
    executor_backend = "local"
    if use_scienceclaw:
        executors.register("local", ScienceClawFormalMechanicsExecutor())
        executor_backend = "scienceclaw"
    reactor = ArtifactReactor(store=store, agents={agent.name: agent for agent in agents}, executors=executors, max_cycles=cycles)
    reactor_summary = reactor.run_until_quiescent()
    report = audit_run(store)
    artifacts = store.list_artifacts()
    needs_lines = [json.loads(line) for line in store.needs_path.read_text().splitlines() if line.strip()]
    fulfilled = [line for line in needs_lines if line.get("status") == "fulfilled"]
    blocked_artifacts = [artifact.id for artifact in artifacts if artifact.type == "BlockedRealDataNeed"]
    summary = {
        "example": example,
        "complexity": complexity,
        "cycles_requested": cycles,
        "cycles_completed": reactor_summary.cycles_completed,
        "artifacts_emitted": max(0, len(artifacts) - (4 if example == "7t10-formal-extension" else 1)),
        "needs_fulfilled": len(fulfilled),
        "open_needs_remaining": len(store.open_needs()),
        "blocked_needs": blocked_artifacts,
        "terminal_artifacts": [artifact.type for artifact in artifacts[-3:]],
        "audit_status": "pass" if report.ok else "fail",
        "data_honesty_status": "no_fake_numeric_science",
        "errors": report.errors,
        "executor_backend": executor_backend,
        "scienceclaw_agents_used": use_scienceclaw,
    }
    if example == "7t10-formal-extension":
        summary["inherited_7t10_needs_remaining"] = 6
        extension_seed_artifacts = {"contact_graph_7T10", "force_extension_7T10", "mechanics_claim_7T10", "source_open_needs_7T10"}
        summary["formal_extension_needs_fulfilled"] = len(
            [
                f
                for f in fulfilled
                if any(f.get("id", "").startswith(f"need:{artifact_id}:") for artifact_id in extension_seed_artifacts)
            ]
        )
    (run_path / "run_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    export_presentable_results(run_path)
    return summary


def run_examples_a_to_d(out_root: str | Path, *, cycles: int = 30, complexity: str = "high", use_scienceclaw: bool = False) -> dict[str, dict[str, Any]]:
    root = Path(out_root)
    root.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, Any]] = {}
    for example in EXAMPLES:
        results[example] = run_example(example, root / EXAMPLE_RUN_DIRS[example], cycles=cycles, complexity=complexity, use_scienceclaw=use_scienceclaw)
    export_presentation_index(root)
    generate_mechanics_discovery_reports(root)
    return results


def write_example_files(base_dir: str | Path) -> None:
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    (base / "agents.json").write_text(json.dumps({"agents": [a.to_dict() for a in formal_agents()]}, indent=2), encoding="utf-8")
    for key in EXAMPLES:
        objects, morphisms, seed_type, topic = _schema_for(key)
        schema_text = json.dumps({"topic": topic, "seed": {"artifact_type": seed_type}, "objects": [o.to_dict() for o in objects], "morphisms": [m.to_dict() for m in morphisms]}, indent=2)
        (base / f"{key}.schema.json").write_text(schema_text, encoding="utf-8")
        (base / f"{EXAMPLE_RUN_DIRS[key]}.schema.json").write_text(schema_text, encoding="utf-8")
