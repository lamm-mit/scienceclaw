# Example B: fiber-network biomechanics

> Act like a mechanics investigator, not a generic data analyzer.

## Run Summary

- Audit status: `pass`
- Executor backend: `scienceclaw`
- ScienceClaw agents used: `True`
- Artifacts emitted: `10`
- Needs fulfilled: `10`
- Open needs remaining: `0`
- Data honesty status: `no_fake_numeric_science`

## Mechanics Investigation Question

- Mechanical hypothesis: Fiber-network topology and orientation can constrain anisotropic tissue mechanics.
- Mechanical question: Can image-derived fiber geometry and boundary conditions support quantitative anisotropy or network-mechanics estimates?
- Full smart-investigation payload: `presentable_results/MECHANICS_INVESTIGATION.json`

## Evidence Plan and Skill Routing

**Required evidence:**

- synthetic, image-derived, or segmented fiber geometry
- fiber orientation/length/branch measurements with units
- computational boundary conditions or loading protocol
- material model or simulated force-displacement/stress-strain data

**ScienceClaw skill routing:**

- `image-analysis`: extract fiber morphology from microscopy-derived measurements Status: `blocked_missing_input`
- `csv-read`: load orientation, force-displacement, or stress-strain tables Status: `eligible`
- `statsmodels`: fit anisotropy or stiffness models with diagnostics Status: `eligible`
- `fem-analysis`: compute mechanics fields only if mesh, material properties, and boundary conditions exist Status: `blocked_missing_input`
- `datavis`: plot orientation distributions and fitted mechanics curves Status: `eligible`

**Quantitative input search:**

- Available input kinds: `boundary_conditions, synthetic_computational_input, table`
- Candidate files found: `3`

- `fiber_computational_model.json` from `run_dir_scan`
- `fiber_network_synthetic.csv` from `run_dir_scan`
- `fiber_stress_strain_synthetic.csv` from `run_dir_scan`

**ScienceClaw skill executions:**

- `csv-read:fiber_network_synthetic.csv` used `csv-read` on `fiber_network_synthetic.csv`; status `success`, shape `[12, 4]`.
- `csv-read:fiber_stress_strain_synthetic.csv` used `csv-read` on `fiber_stress_strain_synthetic.csv`; status `success`, shape `[11, 2]`.
- `statsmodels:fiber_stress_strain_synthetic.csv` used `statsmodels` on `fiber_stress_strain_synthetic.csv`; status `success`, shape `[]`.

## Quantitative Computational Mechanics Results

### Synthetic fiber-network anisotropy and stiffness computation

- Evidence class: `synthetic_computational`
- Input artifact: `fiber_network_synthetic.csv; fiber_stress_strain_synthetic.csv`
- Input file: `run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/computational_inputs/fiber_network_synthetic.csv`
- Method/skill used: ScienceClaw csv-read on generated computational CSVs plus deterministic fiber-orientation tensor and statsmodels linear stress-strain fit

**Computed values:**

```json
{
  "fiber_count": 12,
  "linear_stiffness_kpa": 119.4,
  "mean_fiber_length_um": 53.6582,
  "orientation_order_parameter": 0.673115,
  "principal_orientation_deg": 47.877581,
  "stress_intercept_kpa": 2.479
}
```

**Units:**

```json
{
  "length": "um",
  "orientation": "degree",
  "stiffness": "kPa",
  "strain": "dimensionless",
  "stress": "kPa"
}
```

**Diagnostic:**

```json
{
  "input_files": [
    "run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/computational_inputs/fiber_network_synthetic.csv",
    "run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/computational_inputs/fiber_stress_strain_synthetic.csv"
  ],
  "linear_fit_r_squared": 0.999989,
  "linear_fit_slope_p_value": 1.1202103443533047e-23,
  "stress_strain_point_count": 11
}
```

**Scientific interpretation:** The synthetic network is strongly directionally organized rather than isotropic, and the stress-strain table gives a high-confidence linear stiffness for that computational loading protocol. Mechanically, this supports an anisotropic fiber-network interpretation with a dominant orientation near 48 degrees and a tensile stiffness scale of about 119 kPa.

**Uncertainty or limitation:** Deterministic synthetic computational network and stress-strain table; useful for pipeline mechanics computation, not a biological measurement.

## Validation and Diagnostics

```json
{
  "accepted_source_data_scienceclaw_count": 4,
  "computational_input_need_count": 0,
  "formal_result_count": 9,
  "quantitative_result_count": 1,
  "unsupported_quantitative_claims_blocked": false
}
```

## Computational Input Needs

None.

## Valid Results

None.

## Formal/Symbolic Results

### 1. FiberNetworkGraph

- Artifact ID: `art-6ee234cc170748fe80c4af134bb1acc0`
- Morphism: `extract_fiber_network`
- Agent: `StructureBreakerAgent`
- Full payload: `presentable_results/artifact_payloads/01_art-6ee234cc170748fe80c4af134bb1acc0_FiberNetworkGraph.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `networkx`
- Accepted as substantive: `True`

**Formal result:**

```json
{
  "edge_count": 1,
  "edges": [
    {
      "relation": "extract_fiber_network",
      "source": "art-9d80f08e1a274a2a8dc5c3b90a4ffe4c",
      "target": "FiberNetworkGraph"
    }
  ],
  "graph_invariants": {
    "acyclic_by_construction": true,
    "all_inputs_reach_output": true,
    "parent_payload_features_attached": true,
    "typed_parent_count": 1
  },
  "kind": "typed_provenance_graph",
  "node_count": 2,
  "nodes": [
    {
      "data_status": "example_seed_no_numeric_measurements",
      "formal_result_kind": "",
      "id": "art-9d80f08e1a274a2a8dc5c3b90a4ffe4c",
      "type": "TissueImageOrGeometry"
    },
    {
      "id": "FiberNetworkGraph",
      "type": "output_type"
    }
  ]
}
```

### 2. OrientationParityDescriptor

- Artifact ID: `art-7f2088d3fb4e43d1b132828c1a953fa3`
- Morphism: `compute_orientation_parity`
- Agent: `ParityDescriptorAgent`
- Full payload: `presentable_results/artifact_payloads/02_art-7f2088d3fb4e43d1b132828c1a953fa3_OrientationParityDescriptor.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `networkx`
- Accepted as substantive: `True`

**Formal result:**

```json
{
  "graph_invariants": [
    "parent_type_multiset",
    "parent_payload_key_sets",
    "parent_formal_result_kind_multiset",
    "morphism_name"
  ],
  "invariance_statement": "Descriptor is computed from sorted parent payload feature keys, parent formal-result kinds, and declared morphism; JSON field-order relabeling does not change the value.",
  "kind": "symbolic_parity_descriptor",
  "parity_domain": [
    "FiberNetworkGraph"
  ],
  "parity_value": "even",
  "source_content_features": [
    {
      "artifact_id": "art-6ee234cc170748fe80c4af134bb1acc0",
      "artifact_type": "FiberNetworkGraph",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "edge_count": 1,
      "emitted_need_types": [
        "OrientationParityDescriptor",
        "GraphInvariantDescriptor",
        "BlockedRealDataNeed"
      ],
      "formal_result_fields": [
        "edge_count",
        "edges",
        "graph_invariants",
        "kind",
        "node_count",
        "nodes"
      ],
      "formal_result_kind": "typed_provenance_graph",
      "morphism": "extract_fiber_network",
      "node_count": 2,
      "payload_keys": [
        "data_status",
        "execution_backend",
        "formal",
        "formal_result",
        "input_count",
        "invariants",
        "morphism",
        "needs",
        "parents",
        "query",
        "result_classification",
        "scienceclaw",
        "scienceclaw_skill_attempted",
        "source_content_features",
        "source_parent_ids",
        "summary",
        "symmetry",
        "valid_result_basis"
      ],
      "result_classification": "formal_symbolic_result"
    }
  ]
}
```

### 3. GraphInvariantDescriptor

- Artifact ID: `art-26284ee8a39e46549be99b55261f595b`
- Morphism: `compute_fiber_graph_invariants`
- Agent: `GraphInvariantAgent`
- Full payload: `presentable_results/artifact_payloads/03_art-26284ee8a39e46549be99b55261f595b_GraphInvariantDescriptor.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `networkx`
- Accepted as substantive: `True`

**Formal result:**

```json
{
  "graph_invariants": [
    "parent_type_multiset",
    "parent_payload_key_sets",
    "parent_formal_result_kind_multiset",
    "morphism_name"
  ],
  "invariance_statement": "Descriptor is computed from sorted parent payload feature keys, parent formal-result kinds, and declared morphism; JSON field-order relabeling does not change the value.",
  "kind": "symbolic_parity_descriptor",
  "parity_domain": [
    "FiberNetworkGraph"
  ],
  "parity_value": "odd",
  "source_content_features": [
    {
      "artifact_id": "art-6ee234cc170748fe80c4af134bb1acc0",
      "artifact_type": "FiberNetworkGraph",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "edge_count": 1,
      "emitted_need_types": [
        "OrientationParityDescriptor",
        "GraphInvariantDescriptor",
        "BlockedRealDataNeed"
      ],
      "formal_result_fields": [
        "edge_count",
        "edges",
        "graph_invariants",
        "kind",
        "node_count",
        "nodes"
      ],
      "formal_result_kind": "typed_provenance_graph",
      "morphism": "extract_fiber_network",
      "node_count": 2,
      "payload_keys": [
        "data_status",
        "execution_backend",
        "formal",
        "formal_result",
        "input_count",
        "invariants",
        "morphism",
        "needs",
        "parents",
        "query",
        "result_classification",
        "scienceclaw",
        "scienceclaw_skill_attempted",
        "source_content_features",
        "source_parent_ids",
        "summary",
        "symmetry",
        "valid_result_basis"
      ],
      "result_classification": "formal_symbolic_result"
    }
  ]
}
```

### 5. AnisotropyTensor

- Artifact ID: `art-cceea0e447bb4a6cacd53087b758569c`
- Morphism: `compute_anisotropy_tensor`
- Agent: `MechanicsBuilderAgent`
- Full payload: `presentable_results/artifact_payloads/05_art-cceea0e447bb4a6cacd53087b758569c_AnisotropyTensor.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `sympy`
- Accepted as substantive: `False`

**Formal result:**

```json
{
  "assumptions": [
    "formal descriptor only",
    "no measured force, stress, curvature, or energy values inferred",
    "parent artifacts provide provenance and type constraints"
  ],
  "expression": "AnisotropyTensor := compute_anisotropy_tensor(symbolic_parity_descriptor + symbolic_parity_descriptor)",
  "input_types": [
    "GraphInvariantDescriptor",
    "OrientationParityDescriptor"
  ],
  "kind": "symbolic_mechanics_expression",
  "source_content_features": [
    {
      "artifact_id": "art-26284ee8a39e46549be99b55261f595b",
      "artifact_type": "GraphInvariantDescriptor",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "GraphInvariantDescriptor",
      "emitted_need_types": [
        "AnisotropyTensor"
      ],
      "formal_result_fields": [
        "graph_invariants",
        "invariance_statement",
        "kind",
        "parity_domain",
        "parity_value",
        "source_content_features"
      ],
      "formal_result_kind": "symbolic_parity_descriptor",
      "morphism": "compute_fiber_graph_invariants",
      "parity_value": "odd",
      "payload_keys": [
        "data_status",
        "descriptor_type",
        "execution_backend",
        "formal",
        "formal_result",
        "input_count",
        "invariants",
        "morphism",
        "needs",
        "parents",
        "query",
        "result_classification",
        "scienceclaw",
        "scienceclaw_skill_attempted",
        "source_content_features",
        "source_parent_ids",
        "summary",
        "symmetry",
        "valid_result_basis"
      ],
      "result_classification": "formal_symbolic_result"
    },
    {
      "artifact_id": "art-7f2088d3fb4e43d1b132828c1a953fa3",
      "artifact_type": "OrientationParityDescriptor",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "OrientationParityDescriptor",
      "emitted_need_types": [],
      "formal_result_fields": [
        "graph_invariants",
        "invariance_statement",
        "kind",
        "parity_domain",
        "parity_value",
        "source_content_features"
      ],
      "formal_result_kind": "symbolic_parity_descriptor",
      "morphism": "compute_orientation_parity",
      "parity_value": "even",
      "payload_keys": [
        "data_status",
        "descriptor_type",
        "execution_backend",
        "formal",
        "formal_result",
        "input_count",
        "invariants",
        "morphism",
        "parents",
        "query",
        "result_classification",
        "scienceclaw",
        "scienceclaw_skill_attempted",
        "source_content_features",
        "source_parent_ids",
        "summary",
        "symmetry",
        "valid_result_basis"
      ],
      "result_classification": "formal_symbolic_result"
    }
  ],
  "symbols": [
    "symbolic_parity_descriptor",
    "symbolic_parity_descriptor"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 6. TensorSymmetryValidationRecord

- Artifact ID: `art-ba907e06ff7246eea5b05cc6ae908282`
- Morphism: `validate_tensor_symmetry`
- Agent: `FormalValidatorAgent`
- Full payload: `presentable_results/artifact_payloads/06_art-ba907e06ff7246eea5b05cc6ae908282_TensorSymmetryValidationRecord.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `scientific-critical-thinking`
- Accepted as substantive: `False`

**Formal result:**

```json
{
  "checks": [
    {
      "name": "parents_present",
      "ok": true
    },
    {
      "name": "parent_payload_content_extracted",
      "ok": true
    },
    {
      "name": "formal_result_kinds_present",
      "ok": true
    },
    {
      "name": "formal_only_status_declared",
      "ok": true
    },
    {
      "name": "no_empirical_numeric_claim_added",
      "ok": true
    }
  ],
  "kind": "formal_validation_record",
  "validated_parent_content": [
    {
      "artifact_id": "art-cceea0e447bb4a6cacd53087b758569c",
      "artifact_type": "AnisotropyTensor",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "AnisotropyTensor",
      "emitted_need_types": [
        "TensorSymmetryValidationRecord"
      ],
      "expression": "AnisotropyTensor := compute_anisotropy_tensor(symbolic_parity_descriptor + symbolic_parity_descriptor)",
      "formal_result_fields": [
        "assumptions",
        "expression",
        "input_types",
        "kind",
        "source_content_features",
        "symbols"
      ],
      "formal_result_kind": "symbolic_mechanics_expression",
      "morphism": "compute_anisotropy_tensor",
      "payload_keys": [
        "data_status",
        "descriptor_type",
        "execution_backend",
        "formal",
        "formal_result",
        "input_count",
        "invariants",
        "morphism",
        "needs",
        "parents",
        "query",
        "result_classification",
        "scienceclaw",
        "scienceclaw_skill_attempted",
        "source_content_features",
        "source_parent_ids",
        "summary",
        "symmetry",
        "valid_result_basis"
      ],
      "result_classification": "formal_symbolic_result"
    }
  ],
  "validated_parent_types": [
    "AnisotropyTensor"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 7. NetworkMechanicsModel

- Artifact ID: `art-bd20b7aca3a34f5885f36ef66aab2c6b`
- Morphism: `build_network_mechanics_model`
- Agent: `MechanicsBuilderAgent`
- Full payload: `presentable_results/artifact_payloads/07_art-bd20b7aca3a34f5885f36ef66aab2c6b_NetworkMechanicsModel.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `networkx`
- Accepted as substantive: `True`

**Formal result:**

```json
{
  "edge_count": 2,
  "edges": [
    {
      "relation": "build_network_mechanics_model",
      "source": "art-ba907e06ff7246eea5b05cc6ae908282",
      "target": "NetworkMechanicsModel"
    },
    {
      "relation": "build_network_mechanics_model",
      "source": "art-cceea0e447bb4a6cacd53087b758569c",
      "target": "NetworkMechanicsModel"
    }
  ],
  "graph_invariants": {
    "acyclic_by_construction": true,
    "all_inputs_reach_output": true,
    "parent_payload_features_attached": true,
    "typed_parent_count": 2
  },
  "kind": "typed_provenance_graph",
  "node_count": 3,
  "nodes": [
    {
      "data_status": "formal_descriptor_only",
      "formal_result_kind": "formal_validation_record",
      "id": "art-ba907e06ff7246eea5b05cc6ae908282",
      "type": "TensorSymmetryValidationRecord"
    },
    {
      "data_status": "formal_descriptor_only",
      "formal_result_kind": "symbolic_mechanics_expression",
      "id": "art-cceea0e447bb4a6cacd53087b758569c",
      "type": "AnisotropyTensor"
    },
    {
      "id": "NetworkMechanicsModel",
      "type": "output_type"
    }
  ]
}
```

### 8. EvidenceCoverageRecord

- Artifact ID: `art-cc16797ddd6c49b4a641b8eb9bc82c0a`
- Morphism: `record_fiber_evidence_coverage`
- Agent: `FormalValidatorAgent`
- Full payload: `presentable_results/artifact_payloads/08_art-cc16797ddd6c49b4a641b8eb9bc82c0a_EvidenceCoverageRecord.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `scientific-critical-thinking`
- Accepted as substantive: `False`

**Formal result:**

```json
{
  "checks": [
    {
      "name": "parents_present",
      "ok": true
    },
    {
      "name": "parent_payload_content_extracted",
      "ok": true
    },
    {
      "name": "formal_result_kinds_present",
      "ok": true
    },
    {
      "name": "formal_only_status_declared",
      "ok": true
    },
    {
      "name": "no_empirical_numeric_claim_added",
      "ok": true
    }
  ],
  "kind": "formal_validation_record",
  "validated_parent_content": [
    {
      "artifact_id": "art-bd20b7aca3a34f5885f36ef66aab2c6b",
      "artifact_type": "NetworkMechanicsModel",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "edge_count": 2,
      "emitted_need_types": [
        "EvidenceCoverageRecord",
        "PatchCompositionReplicationRecord",
        "BiomechanicsClaim"
      ],
      "formal_result_fields": [
        "edge_count",
        "edges",
        "graph_invariants",
        "kind",
        "node_count",
        "nodes"
      ],
      "formal_result_kind": "typed_provenance_graph",
      "morphism": "build_network_mechanics_model",
      "node_count": 3,
      "payload_keys": [
        "data_status",
        "execution_backend",
        "formal",
        "formal_result",
        "input_count",
        "invariants",
        "morphism",
        "needs",
        "parents",
        "query",
        "result_classification",
        "scienceclaw",
        "scienceclaw_skill_attempted",
        "source_content_features",
        "source_parent_ids",
        "summary",
        "symmetry",
        "valid_result_basis"
      ],
      "result_classification": "formal_symbolic_result"
    }
  ],
  "validated_parent_types": [
    "NetworkMechanicsModel"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 9. PatchCompositionReplicationRecord

- Artifact ID: `art-6eafd301b60e4e87a4196f126494eb26`
- Morphism: `replicate_patch_composition`
- Agent: `ReplicationAgent`
- Full payload: `presentable_results/artifact_payloads/09_art-6eafd301b60e4e87a4196f126494eb26_PatchCompositionReplicationRecord.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `scientific-critical-thinking`
- Accepted as substantive: `False`

**Formal result:**

```json
{
  "checks": [
    {
      "name": "parents_present",
      "ok": true
    },
    {
      "name": "parent_payload_content_extracted",
      "ok": true
    },
    {
      "name": "formal_result_kinds_present",
      "ok": true
    },
    {
      "name": "formal_only_status_declared",
      "ok": true
    },
    {
      "name": "no_empirical_numeric_claim_added",
      "ok": true
    }
  ],
  "kind": "formal_validation_record",
  "validated_parent_content": [
    {
      "artifact_id": "art-bd20b7aca3a34f5885f36ef66aab2c6b",
      "artifact_type": "NetworkMechanicsModel",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "edge_count": 2,
      "emitted_need_types": [
        "EvidenceCoverageRecord",
        "PatchCompositionReplicationRecord",
        "BiomechanicsClaim"
      ],
      "formal_result_fields": [
        "edge_count",
        "edges",
        "graph_invariants",
        "kind",
        "node_count",
        "nodes"
      ],
      "formal_result_kind": "typed_provenance_graph",
      "morphism": "build_network_mechanics_model",
      "node_count": 3,
      "payload_keys": [
        "data_status",
        "execution_backend",
        "formal",
        "formal_result",
        "input_count",
        "invariants",
        "morphism",
        "needs",
        "parents",
        "query",
        "result_classification",
        "scienceclaw",
        "scienceclaw_skill_attempted",
        "source_content_features",
        "source_parent_ids",
        "summary",
        "symmetry",
        "valid_result_basis"
      ],
      "result_classification": "formal_symbolic_result"
    }
  ],
  "validated_parent_types": [
    "NetworkMechanicsModel"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 10. BiomechanicsClaim

- Artifact ID: `art-d0c6167fc3124025b5b26015c6674006`
- Morphism: `synthesize_biomechanics_claim`
- Agent: `ClaimSynthesisAgent`
- Full payload: `presentable_results/artifact_payloads/10_art-d0c6167fc3124025b5b26015c6674006_BiomechanicsClaim.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `scientific-writing`
- Accepted as substantive: `False`

**Formal result:**

```json
{
  "claim_scope": "formal workflow demonstration",
  "claim_text": "BiomechanicsClaim is supported only as a formal composition of NetworkMechanicsModel, PatchCompositionReplicationRecord via synthesize_biomechanics_claim; no biological or mechanical measurement is asserted.",
  "evidence_parent_content": [
    {
      "artifact_id": "art-bd20b7aca3a34f5885f36ef66aab2c6b",
      "artifact_type": "NetworkMechanicsModel",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "edge_count": 2,
      "emitted_need_types": [
        "EvidenceCoverageRecord",
        "PatchCompositionReplicationRecord",
        "BiomechanicsClaim"
      ],
      "formal_result_fields": [
        "edge_count",
        "edges",
        "graph_invariants",
        "kind",
        "node_count",
        "nodes"
      ],
      "formal_result_kind": "typed_provenance_graph",
      "morphism": "build_network_mechanics_model",
      "node_count": 3,
      "payload_keys": [
        "data_status",
        "execution_backend",
        "formal",
        "formal_result",
        "input_count",
        "invariants",
        "morphism",
        "needs",
        "parents",
        "query",
        "result_classification",
        "scienceclaw",
        "scienceclaw_skill_attempted",
        "source_content_features",
        "source_parent_ids",
        "summary",
        "symmetry",
        "valid_result_basis"
      ],
      "result_classification": "formal_symbolic_result"
    },
    {
      "artifact_id": "art-6eafd301b60e4e87a4196f126494eb26",
      "artifact_type": "PatchCompositionReplicationRecord",
      "checks_passed": true,
      "data_status": "formal_descriptor_only",
      "descriptor_type": "PatchCompositionReplicationRecord",
      "emitted_need_types": [],
      "formal_result_fields": [
        "checks",
        "kind",
        "validated_parent_content",
        "validated_parent_types"
      ],
      "formal_result_kind": "formal_validation_record",
      "morphism": "replicate_patch_composition",
      "payload_keys": [
        "data_status",
        "descriptor_type",
        "execution_backend",
        "formal",
        "formal_result",
        "input_count",
        "invariants",
        "morphism",
        "parents",
        "query",
        "result_classification",
        "scienceclaw",
        "scienceclaw_skill_attempted",
        "source_content_features",
        "source_parent_ids",
        "summary",
        "symmetry",
        "valid_result_basis"
      ],
      "result_classification": "formal_symbolic_result"
    }
  ],
  "evidence_parent_ids": [
    "art-bd20b7aca3a34f5885f36ef66aab2c6b",
    "art-6eafd301b60e4e87a4196f126494eb26"
  ],
  "kind": "formal_claim_synthesis"
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

## Blocked or Missing Data

### 4. BlockedRealDataNeed

- Artifact ID: `art-8973298848da47f89af1e8e81474e554`
- Morphism: `report_missing_boundary_condition`
- Agent: `BoundaryConditionAgent`
- Full payload: `presentable_results/artifact_payloads/04_art-8973298848da47f89af1e8e81474e554_BlockedRealDataNeed.json`
- Result classification: `blocked_missing_data`

**ScienceClaw execution audit:**

- Skill attempted: `scientific-critical-thinking`
- Accepted as substantive: `False`

**Blocked reason:**

No real boundary-condition data supplied; emitting blocked need instead of unsupported mechanics.

**Missing input needed:**

real empirical boundary-condition or measurement data compatible with the requested mechanics inference

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

## Rejected Placeholder Outputs

None. Placeholder ScienceClaw outputs were rejected at runtime and replaced with formal results or blocked records.
