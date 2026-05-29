# CategoryScienceClaw Formal Methods Examples Implementation Plan

> For Hermes: Use subagent-driven-development skill to implement this plan task-by-task if execution is requested later. Do not commit unless boss explicitly asks.

Goal: Add several scientifically credible CategoryScienceClaw example cases that demonstrate formal, compositional, category-theoretic agent coordination for mechanics/biophysics problems suitable for an Extreme Mechanics Letters-style presentation.

Architecture: Extend `/home/fiona/LAMM/categoryscienceclaw` with example schemas, agents, deterministic local executors, tests, and documentation that formalize decentralized ScienceClaw workflows as typed objects, morphisms, monoidal compositions, parity/symmetry descriptors, invariants, and proof certificates. Keep the package compatible with the existing ScienceClaw repository layout and adapter model, while preserving decentralized coordination through open needs and worker heartbeats.

Tech Stack: Python 3.10+, stdlib dataclasses/JSON, pytest, existing `categoryscienceclaw` CLI/runtime, optional ScienceClaw adapter to `/home/fiona/LAMM/scienceclaw`, markdown documentation, Mermaid diagrams.

---

## Context From Read-Only Inspection

Repository inspected: `/home/fiona/LAMM/categoryscienceclaw`

Current state:

- `README.md` describes CategoryScienceClaw as a minimal proof-carrying execution runtime for decentralized ScienceClaw-style agents.
- Core categorical structures are in `categoryscienceclaw/kernel/models.py`:
  - `ObjectType`
  - `MorphismSignature`
  - `Artifact`
  - `Need`
  - `AgentProfile`
  - `CategoricalState`
- Current default schema in `categoryscienceclaw/defaults.py` has four objects:
  - `ResearchQuestion`
  - `LiteratureEvidence`
  - `ComputationalAnalysis`
  - `Claim`
- Current default morphisms are:
  - `literature_search: ResearchQuestion -> LiteratureEvidence`
  - `computational_analysis: LiteratureEvidence -> ComputationalAnalysis`
  - `synthesize_claim: (ComputationalAnalysis, LiteratureEvidence) -> Claim`
- Runtime coordination is decentralized in `categoryscienceclaw/runtime/worker.py`:
  - each worker scans open needs,
  - chooses a compatible morphism,
  - claims the need,
  - executes it,
  - emits an artifact,
  - closes the need,
  - writes a certificate.
- CLI entry points are in `categoryscienceclaw/cli.py`:
  - `init`
  - `worker`
  - `run`
  - `audit`
  - `replay`
  - `formalize-actual-run`
- Current tests in `tests/test_runtime.py` already validate decentralized run, single-claim locking, certificate type mismatch detection, and content-hash audit failures.
- Existing post-run formalization in `categoryscienceclaw/formalize.py` already has mechanics-relevant object names:
  - `StructureMetadata`
  - `ContactGraph`
  - `SequenceDescriptor`
  - `MDTrajectory`
  - `ForceExtensionTrace`
  - `MechanicsModel`
  - `AtomisticStructure`
  - `Claim`
  - `ValidationMetric`
  - `ValidationRecord`

Existing example that must not be repeated:

- `/home/fiona/LAMM/categoryscienceclaw/run_exports/structure_contact_7T10_formalized_20260528` is already a rich formalized ScienceClaw actual run, not a blank slate.
- Its topic is: “Which peptide residues form the strongest protein-contact hotspots in PDB 7T10?”
- It already contains a full contact/mechanics branch:
  - `ResearchQuestion -> OpenNeed -> AgentProposal -> StructureMetadata -> ContactGraph -> SequenceDescriptor -> Claim`
  - `ContactGraph -> MDTrajectory -> ForceExtensionTrace -> Claim`
  - `AgentProposal -> AtomisticStructure -> MDTrajectory -> ForceExtensionTrace -> Claim`
  - `Claim -> ValidationRecord -> DiscoursePost`
- It already has typed objects/morphisms for:
  - `PreparedAtomisticComplex`
  - `AtomisticSMDEnsemble`
  - `MutationMechanicsComparison`
  - `RupturePathwayGraph`
  - `MechanisticClaim`
  - `ExperimentalReference`
- It already advertises six open downstream needs:
  1. `PreparedAtomisticComplex` for receptor-bound 7T10 peptide-receptor preparation.
  2. `AtomisticSMDEnsemble` for receptor-bound steered-MD replicates.
  3. `MutationMechanicsComparison` for W8/K9/F6/F7 hotspot perturbations.
  4. `RupturePathwayGraph` for time-resolved contact rupture order.
  5. `ExperimentalReference` for SSTR2/somatostatin-14 supporting or contradicting evidence.
  6. `MechanisticClaim` for integrated synthesis after the above evidence exists.
- Therefore, the new plan should not recreate “7T10 contact hotspots” or another generic contact-graph/force-extension demo as if it does not exist. It should treat 7T10 as an existing baseline/case study and either:
  - extend it with formal category-theoretic descriptors, parity, and composition audits, or
  - add orthogonal examples at different biological/mechanical scales.

Important user constraints:

- Boss wants examples under `/home/fiona/LAMM/categoryscienceclaw`.
- Examples should show formal methods with category theory.
- Examples should be suitable for Extreme Mechanics Letters-style work: protein mechanics, biomechanics, biophysics, and related mechanics cases.
- Agents should be formalized to use mathematical descriptors, parity/symmetry, and compositional reasoning.
- Try several cases to decide what is best to present.
- Reference boss’s paper section about the “breaker/builder” example when implementing, but do not fabricate citation details. Use a placeholder until the exact paper/source file is identified.
- Maintain compatibility with the existing ScienceClaw repo: https://github.com/lamm-mit/scienceclaw
- Preserve decentralized coordination; do not convert the system into a central planner.
- No hardcoded or fake scientific conclusions.

---

## Proposed Example Suite

Implement a small suite of candidate examples, but treat the existing 7T10 formalized run as the baseline to extend rather than a case to repeat. Evaluate which 1-2 are best for a paper/demo narrative.

### Example A: 7T10 Formal Descriptor Extension — Reuse Existing Run, Do Not Repeat It

Scientific theme:

- Extend the already formalized PDB 7T10 contact/mechanics run with category-theoretic descriptors, parity/symmetry fields, and composition audits.
- This is not a new “find contact hotspots” example; the existing run already did that.

Existing source to reuse:

- `/home/fiona/LAMM/categoryscienceclaw/run_exports/structure_contact_7T10_formalized_20260528`

What already exists:

- Contact hotspot claim for PDB 7T10.
- Coarse-grained contact-derived force-extension descriptor.
- Atomistic villin SMD validation branch.
- Validation records and discourse posts.
- Open downstream needs for receptor-bound preparation, SMD ensemble, hotspot mutation mechanics, rupture pathway graph, experimental anchors, and integrated synthesis.

New formal-methods contribution:

- Add a post-run enrichment pass that reads the existing 7T10 artifacts and emits only new formal descriptor artifacts/certificates, such as:
  - `ContactParityDescriptor`
  - `RupturePathwayFormalization`
  - `CompositionAuditRecord`
  - `MechanicsFunctorDescriptor`
  - `OpenNeedDependencyGraph`
- Add morphisms that operate on existing artifacts:
  - `compute_7t10_contact_parity: ContactGraph -> ContactParityDescriptor`
  - `formalize_rupture_need: OpenNeed -> RupturePathwayFormalization`
  - `audit_mechanics_composition: (ContactGraph, ForceExtensionTrace, Claim) -> CompositionAuditRecord`
  - `derive_mechanics_functor_descriptor: (StructureMetadata, ContactGraph, ForceExtensionTrace) -> MechanicsFunctorDescriptor`
  - `build_open_need_dependency_graph: (OpenNeed, AgentProposal) -> OpenNeedDependencyGraph`

Formal descriptors:

- graph degree parity,
- contact order parity,
- signed contact orientation where source data supports it,
- chain-index involution or reversal symmetry,
- explicit functor-like projection from structure metadata/contact graph to mechanics descriptors,
- dependency graph for downstream needs as a compositional research program.

Why this should be the strongest first example:

- It uses real existing ScienceClaw outputs and hashes.
- It avoids duplicating work that already exists.
- It turns the current 7T10 run into a mathematically stronger demonstration by adding formal descriptors and proof obligations.
- It supports the breaker/builder story: the previous run already broke structure into artifacts and built claims; the extension adds categorical audits of those compositions.

### Example B: Biomechanics — Collagen/Fiber Network Anisotropy

Scientific theme:

- Fiber network mechanics, collagen alignment, anisotropy, and load-bearing paths in tissue.

Extreme Mechanics Letters fit:

- Strong biomechanics angle.
- Category theory naturally models multiscale maps: image/geometry -> network -> tensor descriptor -> mechanical prediction.

Categorical framing:

- Objects:
  - `TissueImageOrGeometry`
  - `FiberNetworkGraph`
  - `OrientationDistribution`
  - `AnisotropyTensor`
  - `BoundaryCondition`
  - `NetworkMechanicsModel`
  - `BiomechanicsClaim`
- Morphisms:
  - `extract_fiber_network: TissueImageOrGeometry -> FiberNetworkGraph`
  - `compute_orientation_distribution: FiberNetworkGraph -> OrientationDistribution`
  - `compute_anisotropy_tensor: OrientationDistribution -> AnisotropyTensor`
  - `apply_boundary_conditions: (FiberNetworkGraph, BoundaryCondition) -> NetworkMechanicsModel`
  - `validate_anisotropy_mechanics: (AnisotropyTensor, NetworkMechanicsModel) -> BiomechanicsClaim`
- Formal descriptors:
  - tensor parity under reflection,
  - orientation distribution modulo pi,
  - monoidal composition of sub-network patches,
  - invariance under relabeling of graph nodes,
  - functor from geometric fiber network to coarse anisotropy object.

Why it is useful:

- Demonstrates formal descriptors beyond proteins.
- Strong category-theoretic compositionality: local patches combine into a tissue-scale object.

### Example C: Biophysics — Membrane Curvature and Protein Assembly

Scientific theme:

- Membrane curvature, curvature-generating proteins, local-to-global assembly, and energetic descriptors.

Extreme Mechanics Letters fit:

- Biophysical mechanics with geometry and energy.
- Compositional maps from local curvature modules to global membrane shape are naturally categorical.

Categorical framing:

- Objects:
  - `MembranePatchGeometry`
  - `CurvatureDescriptor`
  - `ProteinAssemblyGraph`
  - `EnergyFunctional`
  - `ShapeTransitionModel`
  - `BiophysicsClaim`
- Morphisms:
  - `measure_curvature: MembranePatchGeometry -> CurvatureDescriptor`
  - `build_assembly_graph: MembranePatchGeometry -> ProteinAssemblyGraph`
  - `derive_energy_functional: (CurvatureDescriptor, ProteinAssemblyGraph) -> EnergyFunctional`
  - `predict_shape_transition: EnergyFunctional -> ShapeTransitionModel`
  - `synthesize_biophysics_claim: ShapeTransitionModel -> BiophysicsClaim`
- Formal descriptors:
  - orientation/parity of curvature sign,
  - invariance under patch relabeling,
  - gluing of local charts as categorical pushout-like composition,
  - functor from geometric surface data to an energy functional.

Why it is useful:

- Provides strong mathematical language for local-to-global composition.
- Good backup case if protein mechanics is too data-specific.

### Example D: Mechanobiology — Cell Adhesion / Cytoskeleton Force Transmission

Scientific theme:

- Force chains through focal adhesions, cytoskeletal network mechanics, and mechanotransduction paths.

Extreme Mechanics Letters fit:

- Biomechanics/biophysics crossover.
- Natural network and path-based mechanics descriptors.

Categorical framing:

- Objects:
  - `CellGeometry`
  - `AdhesionGraph`
  - `CytoskeletonNetwork`
  - `ForcePathDescriptor`
  - `MechanotransductionModel`
  - `MechanobiologyClaim`
- Morphisms:
  - `extract_adhesion_graph: CellGeometry -> AdhesionGraph`
  - `infer_cytoskeleton_network: CellGeometry -> CytoskeletonNetwork`
  - `compute_force_paths: (AdhesionGraph, CytoskeletonNetwork) -> ForcePathDescriptor`
  - `build_mechanotransduction_model: ForcePathDescriptor -> MechanotransductionModel`
  - `synthesize_mechanobiology_claim: MechanotransductionModel -> MechanobiologyClaim`
- Formal descriptors:
  - path parity,
  - signed load paths,
  - network centrality invariants,
  - monoidal composition of subcellular modules,
  - invariance under graph isomorphism.

Why it is useful:

- Very agent-friendly: different agents can independently work on geometry, adhesions, cytoskeleton, and synthesis.
- Good demonstration of decentralized coordination.

---

## Core Formal Grounding To Add

### 1. Categorical schema layer

Add explicit math metadata to object and morphism definitions without breaking current dataclasses.

Use existing `metadata: dict[str, Any]` on `MorphismSignature` and `ObjectType.description` first. Avoid schema-breaking changes unless tests prove they are needed.

Recommended metadata keys:

```python
metadata={
    "formal": {
        "domain_object": "ProteinStructure",
        "codomain_object": "ContactGraph",
        "categorical_role": "functorial_projection",
        "invariants": ["node_relabeling_invariant", "contact_order_parity"],
        "equivariance": ["chain_reversal"],
        "composition_laws": ["extract_contacts_then_compute_parity"],
        "proof_obligations": [
            "input_type_matches_domain",
            "output_type_matches_codomain",
            "parent_hash_preserved",
            "invariant_fields_present",
        ],
    }
}
```

### 2. Parity/symmetry descriptors

Add a lightweight descriptor convention:

```json
{
  "descriptor_type": "ContactParityDescriptor",
  "parity_vector": [0, 1, 1, 0],
  "symmetry_group": "C2_chain_reversal",
  "invariants": {
    "node_relabeling_invariant": true,
    "chain_reversal_equivariant": true
  },
  "source_artifact_hash": "..."
}
```

Do not claim the descriptor is physically meaningful unless computed from real data or clearly labeled as a formal demonstration descriptor.

### 3. Decentralized proof-carrying agent coordination

Keep the existing runtime pattern:

- Agents own morphism capabilities.
- Needs specify required output object types and allowed morphisms.
- Workers independently claim needs.
- Certificates prove type/provenance validity.
- Audit validates certificates and content hashes.

Extend certificates, if necessary, to include formal obligations:

- type correctness,
- arity correctness,
- provenance correctness,
- content hash correctness,
- invariant field presence,
- composition path validity.

### 4. Breaker/builder narrative

Use boss’s breaker/builder paper section as the conceptual framing:

- Breaker agents decompose raw scientific objects into typed formal descriptors.
- Builder agents compose descriptors into models/claims.
- Validator agents check type, provenance, parity/symmetry, and composition obligations.

Implementation should include a placeholder citation block in docs:

```markdown
TODO: Replace this placeholder with the exact citation/section from boss’s breaker/builder paper.
This example follows the breaker/builder pattern: breaker morphisms decompose structures into certified descriptors; builder morphisms compose certified descriptors into mechanics claims.
```

Do not invent paper details.

---

## Implementation Plan

### Task 1: Create an examples package layout

Objective: Add a clear location for formal mechanics example definitions without modifying runtime behavior.

Files:

- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/README.md`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/7t10_formal_extension.schema.json`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/biomechanics_fiber_network.schema.json`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/membrane_biophysics.schema.json`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/mechanobiology_force_paths.schema.json`

Plan:

1. Add a README explaining the purpose of the example suite.
2. Add one JSON schema file per candidate example.
3. Keep files data-only at first.
4. Do not wire anything into CLI yet.

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m json.tool examples/formal_mechanics/7t10_formal_extension.schema.json >/tmp/7t10_formal_extension_schema.json
python3 -m json.tool examples/formal_mechanics/biomechanics_fiber_network.schema.json >/tmp/fiber_schema.json
python3 -m json.tool examples/formal_mechanics/membrane_biophysics.schema.json >/tmp/membrane_schema.json
python3 -m json.tool examples/formal_mechanics/mechanobiology_force_paths.schema.json >/tmp/mechanobio_schema.json
```

Expected: all commands exit 0.

### Task 2: Add formal mechanics agent profiles

Objective: Provide decentralized agents for breaker, builder, and validator roles.

Files:

- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/agents.json`

Suggested agents:

```json
{
  "agents": [
    {
      "name": "StructureBreakerAgent",
      "morphisms": ["extract_contacts", "extract_fiber_network", "measure_curvature", "extract_adhesion_graph"],
      "preferred_types": ["ContactGraph", "FiberNetworkGraph", "CurvatureDescriptor", "AdhesionGraph"],
      "metadata": {"role": "breaker"}
    },
    {
      "name": "ParityDescriptorAgent",
      "morphisms": ["compute_contact_parity", "compute_orientation_parity", "compute_curvature_parity", "compute_force_path_parity"],
      "preferred_types": ["ContactParityDescriptor", "OrientationParityDescriptor", "CurvatureParityDescriptor", "ForcePathDescriptor"],
      "metadata": {"role": "formal_descriptor"}
    },
    {
      "name": "MechanicsBuilderAgent",
      "morphisms": ["infer_rupture_pathway", "build_network_mechanics_model", "derive_energy_functional", "build_mechanotransduction_model"],
      "preferred_types": ["RupturePathway", "NetworkMechanicsModel", "EnergyFunctional", "MechanotransductionModel"],
      "metadata": {"role": "builder"}
    },
    {
      "name": "ClaimSynthesisAgent",
      "morphisms": ["synthesize_mechanics_claim", "synthesize_biomechanics_claim", "synthesize_biophysics_claim", "synthesize_mechanobiology_claim"],
      "preferred_types": ["MechanicsClaim", "BiomechanicsClaim", "BiophysicsClaim", "MechanobiologyClaim"],
      "metadata": {"role": "synthesis"}
    },
    {
      "name": "FormalValidatorAgent",
      "morphisms": ["validate_formal_obligations"],
      "preferred_types": ["FormalValidationRecord"],
      "metadata": {"role": "validator"}
    }
  ]
}
```

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m json.tool examples/formal_mechanics/agents.json >/tmp/formal_agents.json
```

Expected: exits 0.

### Task 3: Add a schema loader for example files

Objective: Load example object/morphism schemas into the existing runtime without changing default behavior.

Files:

- Create: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/examples.py`
- Modify: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/cli.py`
- Test: `/home/fiona/LAMM/categoryscienceclaw/tests/test_formal_mechanics_examples.py`

Implementation design:

- Add a function:

```python
def load_schema_file(path: str | Path) -> tuple[list[ObjectType], list[MorphismSignature], str]:
    ...
```

Expected JSON shape:

```json
{
  "topic": "formal protein mechanics",
  "objects": [
    {"name": "ProteinStructure", "kind": "artifact", "description": "..."}
  ],
  "morphisms": [
    {
      "name": "extract_contacts",
      "input_types": ["ProteinStructure"],
      "output_type": "ContactGraph",
      "kind": "breaker",
      "adapter": "local",
      "description": "...",
      "metadata": {"formal": {}}
    }
  ]
}
```

CLI extension:

- Add optional `--schema` to `categoryscienceclaw init`.
- If `--schema` is omitted, preserve current `default_objects()` and `default_morphisms()` behavior.
- If `--schema` is provided, use objects/morphisms/topic from the schema file, while still using CLI `--topic` as the seed research question text.

Test cases:

- `load_schema_file()` returns expected object/morphism names.
- `categoryscienceclaw init --schema examples/formal_mechanics/protein_mechanics.schema.json` writes the custom schema.
- Existing `test_decentralized_run_produces_claim_and_audits` still passes without `--schema`.

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest tests/test_runtime.py tests/test_formal_mechanics_examples.py -q
```

Expected: all tests pass.

### Task 4: Support example-specific seed artifact type

Objective: Allow examples to start from `ProteinStructure`, `TissueImageOrGeometry`, `MembranePatchGeometry`, or `CellGeometry` instead of always `ResearchQuestion`.

Files:

- Modify: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/examples.py`
- Modify: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/cli.py`
- Test: `/home/fiona/LAMM/categoryscienceclaw/tests/test_formal_mechanics_examples.py`

Design:

Add schema fields:

```json
{
  "seed": {
    "artifact_type": "ProteinStructure",
    "payload": {
      "source": "example",
      "description": "Protein structure input for formal mechanics demo"
    },
    "initial_need": {
      "required_type": "ContactGraph",
      "query": "extract a contact graph for formal mechanics analysis",
      "allowed_morphisms": ["extract_contacts"]
    }
  }
}
```

Important:

- The seed payload must not fake scientific values.
- It can identify a real source artifact if available, e.g. an existing run export or a PDB ID, but should not invent measurements.
- For tests, use minimal formal payloads labeled as example inputs.

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest tests/test_formal_mechanics_examples.py::test_schema_seed_controls_initial_artifact -q
```

Expected: custom initial artifact and initial need are present.

### Task 5: Implement formal local executor behavior

Objective: Make deterministic local examples produce formal descriptors and needs, not generic summaries.

Files:

- Modify: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/runtime/executors.py`
- Test: `/home/fiona/LAMM/categoryscienceclaw/tests/test_formal_mechanics_examples.py`

Design:

Keep `LocalDemoExecutor` deterministic, but add a dispatch table for formal mechanics morphisms:

```python
FORMAL_DEMO_PAYLOADS = {
    "extract_contacts": _extract_contacts_payload,
    "compute_contact_parity": _compute_contact_parity_payload,
    "infer_rupture_pathway": _infer_rupture_pathway_payload,
    ...
}
```

Payload rules:

- Include `morphism`, `query`, `input_count`, and `parents` as current executor does.
- Add `formal_descriptor` fields when appropriate.
- Add `invariants` and `symmetry` fields for descriptor morphisms.
- Add `needs` from morphism metadata as the current executor already supports.
- Avoid fake physical measurements. Use symbolic/descriptive descriptors unless derived from real parent payload fields.

Example payload for `compute_contact_parity`:

```python
{
    "summary": "Computed symbolic contact parity descriptor from parent ContactGraph artifact.",
    "descriptor_type": "ContactParityDescriptor",
    "parity_basis": "contact_order_mod_2",
    "symmetry": {"candidate_group": "C2_chain_reversal", "status": "formal_descriptor_only"},
    "invariants": {
        "node_relabeling_invariant": True,
        "requires_empirical_validation": True
    },
    "source_parent_ids": [...]
}
```

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest tests/test_formal_mechanics_examples.py::test_formal_executor_emits_parity_descriptor -q
```

Expected: parity descriptor artifact contains formal descriptor fields and no invented force/energy values.

### Task 6: Add formal proof obligations to certificates

Objective: Validate more than types/provenance for formal examples.

Files:

- Modify: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/proofs/certificates.py`
- Modify: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/audit.py`, only if audit needs to surface new obligation failures.
- Test: `/home/fiona/LAMM/categoryscienceclaw/tests/test_formal_proof_obligations.py`

Read first:

- `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/proofs/certificates.py`
- `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/audit.py`

Design:

- If a morphism has `metadata.formal.proof_obligations`, include those obligations in the certificate.
- Start with simple obligations:
  - `formal_metadata_present`
  - `invariants_present`
  - `symmetry_descriptor_present`
  - `source_parent_ids_present`
- Keep failures explicit and auditable.
- Do not introduce a theorem prover dependency yet. This is a proof-carrying runtime certificate, not a full formal proof assistant integration.

Test cases:

- Certificate passes when required descriptor fields are present.
- Certificate fails when a morphism declares `invariants_present` but output payload lacks `invariants`.
- Existing certificate tests still pass.

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest tests/test_runtime.py tests/test_formal_proof_obligations.py -q
```

Expected: all tests pass.

### Task 7: Implement Example A end-to-end: 7T10 formal descriptor extension

Objective: Extend the existing formalized 7T10 run with new mathematical/category-theoretic descriptors without recreating the original contact-hotspot or mechanics workflow.

Files:

- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/7t10_formal_extension.schema.json`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/7t10_formal_extension.md`
- Create: `/home/fiona/LAMM/categoryscienceclaw/tests/test_7t10_formal_extension.py`
- Possibly create: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/enrich_existing_run.py`
- Possibly modify: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/cli.py`

Existing input run:

```text
/home/fiona/LAMM/categoryscienceclaw/run_exports/structure_contact_7T10_formalized_20260528
```

Do not repeat:

```text
ResearchQuestion -> OpenNeed -> AgentProposal -> StructureMetadata -> ContactGraph -> SequenceDescriptor -> Claim
ContactGraph -> MDTrajectory -> ForceExtensionTrace -> Claim
AgentProposal -> AtomisticStructure -> MDTrajectory -> ForceExtensionTrace -> Claim
```

New extension chain:

```text
Existing ContactGraph
  --compute_7t10_contact_parity-->
ContactParityDescriptor

Existing StructureMetadata + Existing ContactGraph + Existing ForceExtensionTrace
  --derive_mechanics_functor_descriptor-->
MechanicsFunctorDescriptor

Existing ContactGraph + Existing ForceExtensionTrace + Existing mechanics Claim
  --audit_mechanics_composition-->
CompositionAuditRecord

Existing OpenNeed + Existing AgentProposal
  --build_open_need_dependency_graph-->
OpenNeedDependencyGraph

Existing rupture-pathway OpenNeed
  --formalize_rupture_need-->
RupturePathwayFormalization
```

Implementation notes:

- The extension should read existing artifacts from `artifacts.jsonl` and `needs.index.jsonl`.
- It should produce a separate output run directory, for example:

```text
/tmp/csc-7t10-formal-extension
```

- The output must preserve parent IDs/hashes from the existing run in metadata.
- It must never overwrite the existing run export.
- It must not invent new contact hotspots, peak forces, or biological conclusions.
- Numeric values may only be copied/derived from existing source artifacts and must retain source hashes.

Test assertions:

- The extension reads the existing run and finds `contact_graph_7T10`, `force_extension_7T10`, and `mechanics_claim_7T10`.
- The extension emits at least one `ContactParityDescriptor`.
- The extension emits a `CompositionAuditRecord` whose parents include existing 7T10 artifact IDs.
- The extension emits an `OpenNeedDependencyGraph` based on the six existing open downstream needs.
- Audit passes for the new extension run.
- No duplicated `contact_claim_7T10` or new fake 7T10 hotspot claim is emitted.

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest tests/test_7t10_formal_extension.py -q
```

Manual command, if a CLI is added:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
rm -rf /tmp/csc-7t10-formal-extension
categoryscienceclaw enrich-existing-run \
  /home/fiona/LAMM/categoryscienceclaw/run_exports/structure_contact_7T10_formalized_20260528 \
  /tmp/csc-7t10-formal-extension \
  --schema examples/formal_mechanics/7t10_formal_extension.schema.json
categoryscienceclaw audit /tmp/csc-7t10-formal-extension
categoryscienceclaw replay /tmp/csc-7t10-formal-extension
```

Expected: audit passes; replay shows only new formal-enrichment artifacts/certificates, not a duplicate original 7T10 workflow.

### Task 8: Implement Example B end-to-end: fiber-network biomechanics

Objective: Demonstrate compositional multiscale mechanics and tensor/parity descriptors.

Files:

- Update: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/biomechanics_fiber_network.schema.json`
- Create: `/home/fiona/LAMM/categoryscienceclaw/tests/test_biomechanics_fiber_network_example.py`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/biomechanics_fiber_network.md`

Expected chain:

```text
TissueImageOrGeometry
  --extract_fiber_network-->
FiberNetworkGraph
  --compute_orientation_parity-->
OrientationParityDescriptor
  --compute_anisotropy_tensor-->
AnisotropyTensor
  --build_network_mechanics_model-->
NetworkMechanicsModel
  --synthesize_biomechanics_claim-->
BiomechanicsClaim
```

Formal emphasis:

- monoidal composition of subnetwork patches,
- reflection parity of orientation descriptors,
- graph-isomorphism invariance,
- functor from network graph to tensor descriptor.

Test assertions:

- Run produces `OrientationParityDescriptor`.
- If `AnisotropyTensor` is symbolic, it must be labeled symbolic.
- Audit passes.
- Final artifact lineage contains at least 4 morphism steps.

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest tests/test_biomechanics_fiber_network_example.py -q
```

### Task 9: Implement Example C end-to-end: membrane curvature biophysics

Objective: Demonstrate local-to-global categorical composition through curvature and energy descriptors.

Files:

- Update: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/membrane_biophysics.schema.json`
- Create: `/home/fiona/LAMM/categoryscienceclaw/tests/test_membrane_biophysics_example.py`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/membrane_biophysics.md`

Expected chain:

```text
MembranePatchGeometry
  --measure_curvature-->
CurvatureDescriptor
  --build_assembly_graph-->
ProteinAssemblyGraph
  --derive_energy_functional-->
EnergyFunctional
  --predict_shape_transition-->
ShapeTransitionModel
  --synthesize_biophysics_claim-->
BiophysicsClaim
```

Formal emphasis:

- curvature sign parity,
- gluing local patches as pushout-like composition,
- functor from geometry to energy functional,
- descriptor invariance under patch relabeling.

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest tests/test_membrane_biophysics_example.py -q
```

### Task 10: Implement Example D end-to-end: mechanobiology force paths

Objective: Demonstrate path-parity and force-chain reasoning in a decentralized graph mechanics example.

Files:

- Update: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/mechanobiology_force_paths.schema.json`
- Create: `/home/fiona/LAMM/categoryscienceclaw/tests/test_mechanobiology_force_paths_example.py`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/mechanobiology_force_paths.md`

Expected chain:

```text
CellGeometry
  --extract_adhesion_graph-->
AdhesionGraph
  --infer_cytoskeleton_network-->
CytoskeletonNetwork
  --compute_force_path_parity-->
ForcePathDescriptor
  --build_mechanotransduction_model-->
MechanotransductionModel
  --synthesize_mechanobiology_claim-->
MechanobiologyClaim
```

Formal emphasis:

- path parity,
- signed force-chain descriptors,
- graph invariants,
- monoidal composition of cell subregions.

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest tests/test_mechanobiology_force_paths_example.py -q
```

### Task 11: Add example scoring/ranking script

Objective: Compare the examples and identify the best one to present.

Files:

- Create: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/example_scoring.py`
- Create: `/home/fiona/LAMM/categoryscienceclaw/tests/test_example_scoring.py`
- Modify: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/cli.py`

CLI idea:

```bash
categoryscienceclaw score-examples examples/formal_mechanics
```

Scoring criteria:

- mechanics relevance,
- category-theoretic clarity,
- decentralized coordination depth,
- proof/certificate richness,
- ScienceClaw compatibility,
- data honesty/no fake claims,
- paper/demo visual clarity.

Output shape:

```json
{
  "ranked_examples": [
    {
      "name": "protein_mechanics",
      "score": 94,
      "strengths": ["strong mechanics fit", "existing artifact vocabulary", "clear breaker/builder story"],
      "risks": ["needs real force-extension input for full physical claim"]
    }
  ]
}
```

Important:

- The score can be rule-based and transparent.
- Do not use the score to claim scientific truth; it only ranks presentation suitability.

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest tests/test_example_scoring.py -q
```

### Task 12: Add ScienceClaw compatibility checks

Objective: Ensure the new examples remain compatible with the existing ScienceClaw repository and adapter model.

Files:

- Modify or create: `/home/fiona/LAMM/categoryscienceclaw/tests/test_scienceclaw_compatibility.py`
- Possibly modify: `/home/fiona/LAMM/categoryscienceclaw/categoryscienceclaw/adapters/scienceclaw/executor.py`

Compatibility checks:

- CategoryScienceClaw remains dependency-free by default.
- `categoryscienceclaw run ...` works without `/home/fiona/LAMM/scienceclaw`.
- `categoryscienceclaw run ... --scienceclaw` only uses the adapter if ScienceClaw is available.
- Object/morphism schemas can map to ScienceClaw artifact types and skills through metadata, not hardcoded imports.
- Existing tests still pass.

Suggested metadata bridge:

```json
{
  "scienceclaw": {
    "compatible_artifact_type": "ContactGraph",
    "candidate_skills": ["structure-contact-analysis", "scientific-visualization"],
    "adapter_mode": "optional"
  }
}
```

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest tests/test_runtime.py tests/test_scienceclaw_compatibility.py -q
```

Optional local adapter smoke test, only if ScienceClaw environment is ready:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
categoryscienceclaw run /tmp/csc-protein-mechanics --agents examples/formal_mechanics/agents.json --cycles 2 --scienceclaw
```

### Task 13: Add diagrams and paper-facing docs

Objective: Make the examples presentable for a paper/demo pitch.

Files:

- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/diagrams/protein_mechanics.mmd`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/diagrams/fiber_network.mmd`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/diagrams/membrane_biophysics.mmd`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/diagrams/mechanobiology_force_paths.mmd`
- Create: `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/paper_positioning.md`

Paper positioning should include:

- Extreme Mechanics Letters-style motivation.
- The categorical/decentralized agent contribution.
- Breaker/builder framing with placeholder for boss’s exact paper citation.
- Honest statement of what is formalized:
  - type/provenance/category-inspired composition,
  - not full mechanistic proof of biology unless real data is supplied.
- Recommended examples to present, probably:
  1. protein mechanics as primary,
  2. fiber-network biomechanics as secondary.

Verification:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest -q
```

Expected: docs do not break tests.

---

## Recommended Presentation Strategy

Primary example to develop first:

1. 7T10 Formal Descriptor Extension

Reason:

- It reuses the existing formalized actual run instead of duplicating it.
- It already has real ScienceClaw outputs, source hashes, force-extension traces, validation records, publications, and open downstream needs.
- The new contribution can be purely formal/category-theoretic: parity descriptors, functor-like mechanics projections, composition audits, and open-need dependency graphs.
- This is the most honest way to connect formal methods to the existing ScienceClaw evidence base.

Secondary example:

2. Fiber-Network Biomechanics

Reason:

- Strong compositional mechanics story at a different biological scale.
- Monoidal patch composition and tensor descriptors make category theory more explicit.
- It avoids repeating the protein-contact/force-extension path already present in 7T10.

Optional third example:

3. Membrane Curvature Biophysics

Reason:

- Strong geometry/category-theory story through local-to-global gluing.
- Useful if the paper narrative needs a surface/continuum biophysics case.

Keep mechanobiology force paths exploratory until the first two are stable.

---

## Tests / Validation Summary

Run after each implementation phase:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest -q
```

Focused test groups:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
python3 -m pytest tests/test_runtime.py -q
python3 -m pytest tests/test_formal_mechanics_examples.py -q
python3 -m pytest tests/test_formal_proof_obligations.py -q
python3 -m pytest tests/test_7t10_formal_extension.py -q
python3 -m pytest tests/test_biomechanics_fiber_network_example.py -q
python3 -m pytest tests/test_scienceclaw_compatibility.py -q
```

Manual 7T10 formal extension run:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
rm -rf /tmp/csc-7t10-formal-extension
categoryscienceclaw enrich-existing-run \
  /home/fiona/LAMM/categoryscienceclaw/run_exports/structure_contact_7T10_formalized_20260528 \
  /tmp/csc-7t10-formal-extension \
  --schema examples/formal_mechanics/7t10_formal_extension.schema.json
categoryscienceclaw audit /tmp/csc-7t10-formal-extension
categoryscienceclaw replay /tmp/csc-7t10-formal-extension
```

Manual example ranking:

```bash
cd /home/fiona/LAMM/categoryscienceclaw
categoryscienceclaw score-examples examples/formal_mechanics
```

---

## Risks and Mitigations

Risk: Examples become fake science.

Mitigation:

- Symbolic descriptors must be labeled as formal descriptors.
- Do not invent numeric mechanical values.
- If real input data is missing, emit an open need instead of a false claim.

Risk: Category theory is superficial.

Mitigation:

- Put categorical roles directly into morphism metadata.
- Validate composition paths and invariants through certificates.
- Include diagrams showing objects, morphisms, and agent roles.

Risk: Runtime becomes centrally planned.

Mitigation:

- Keep worker heartbeat and open-need mechanism unchanged.
- Use schemas and metadata to guide decentralized agents, not a central orchestrator.

Risk: Breaks existing examples/tests.

Mitigation:

- Keep default schema behavior unchanged when `--schema` is omitted.
- Add compatibility tests around `tests/test_runtime.py`.

Risk: ScienceClaw adapter coupling becomes brittle.

Mitigation:

- Store ScienceClaw links in metadata.
- Keep ScienceClaw integration optional.
- Do not import ScienceClaw modules at package import time.

Risk: Boss’s breaker/builder paper is referenced incorrectly.

Mitigation:

- Use a TODO placeholder until the exact paper source/citation is provided or found.
- Do not fabricate citation details.

---

## Open Questions For Boss

1. Which exact paper/source contains the breaker/builder example, and what citation wording should be used?
2. Should the primary example use existing `structure_contact_7T10` exports, or should it start from a new real protein mechanics run?
3. Should the formal descriptors remain symbolic for the first demo, or should we connect them to real computed graph/trajectory data immediately?
4. Is the target output a paper figure, a runnable CLI demo, or both?
5. Should the examples include optional real ScienceClaw skill execution, or stay deterministic/offline for reproducibility?

---

## Definition of Done

- `/home/fiona/LAMM/categoryscienceclaw/examples/formal_mechanics/` contains the 7T10 formal extension schema plus at least three orthogonal candidate formal mechanics example schemas.
- The 7T10 extension reuses `/home/fiona/LAMM/categoryscienceclaw/run_exports/structure_contact_7T10_formalized_20260528` and does not duplicate the existing contact-hotspot or force-extension workflow.
- At least one non-7T10 example runs end-to-end through decentralized agents and produces auditable certificates.
- 7T10 formal extension is strong enough for an Extreme Mechanics Letters-style narrative as the primary evidence-backed case.
- Examples explicitly encode categorical objects, morphisms, composition, invariants, and parity/symmetry descriptors.
- Formal certificates validate type/provenance plus basic formal descriptor obligations.
- ScienceClaw compatibility remains optional and non-breaking.
- Existing CategoryScienceClaw tests still pass.
- No hardcoded or fake scientific conclusions are introduced.
- Documentation clearly explains the breaker/builder framing and marks the boss-paper citation as TODO until confirmed.
