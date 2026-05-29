# Example D: mechanobiology force paths

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

- Mechanical hypothesis: Adhesion and cytoskeleton graph structure constrain mechanotransduction force paths.
- Mechanical question: Can cell geometry, adhesion maps, and traction/cytoskeleton measurements support quantitative force-path inference?
- Full smart-investigation payload: `presentable_results/MECHANICS_INVESTIGATION.json`

## Evidence Plan and Skill Routing

**Required evidence:**

- cell geometry or computational segmentation
- adhesion and cytoskeleton measurements
- traction-force or simulated displacement fields
- computational boundary conditions and material model metadata

**ScienceClaw skill routing:**

- `image-analysis`: extract cell, adhesion, and cytoskeleton measurements from microscopy outputs Status: `blocked_missing_input`
- `csv-read`: load traction/displacement/trajectory tables Status: `eligible`
- `statsmodels`: fit mechanotransduction or force-path associations with diagnostics Status: `eligible`
- `fem-analysis`: compute mechanics fields only with a mesh, material model, and boundary conditions Status: `blocked_missing_input`
- `datavis`: plot force-path and graph-mechanics summaries Status: `eligible`

**Quantitative input search:**

- Available input kinds: `synthetic_computational_input, table`
- Candidate files found: `2`

- `adhesion_cytoskeleton_graph_synthetic.json` from `run_dir_scan`
- `force_paths_synthetic.csv` from `run_dir_scan`

**ScienceClaw skill executions:**

- `csv-read:force_paths_synthetic.csv` used `csv-read` on `force_paths_synthetic.csv`; status `success`, shape `[12, 6]`.
- `statsmodels:force_paths_synthetic.csv` used `statsmodels` on `force_paths_synthetic.csv`; status `success`, shape `[]`.

## Quantitative Computational Mechanics Results

### Synthetic mechanobiology force-path load score computation

- Evidence class: `synthetic_computational`
- Input artifact: `force_paths_synthetic.csv; adhesion_cytoskeleton_graph_synthetic.json`
- Input file: `run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/computational_inputs/force_paths_synthetic.csv`
- Method/skill used: ScienceClaw csv-read on generated computational CSV plus deterministic force-path scoring and statsmodels traction-vs-adhesion fit

**Computed values:**

```json
{
  "adhesion_traction_intercept_pa": 38.191375,
  "adhesion_traction_slope_pa_per_score": 32.775291,
  "max_traction_pa": 72.886,
  "max_traction_path_id": 12,
  "mean_load_path_score_pa_per_um": 4.421814,
  "path_count": 12
}
```

**Units:**

```json
{
  "displacement": "um",
  "load_path_score": "Pa/um",
  "path_length": "um",
  "traction": "Pa"
}
```

**Diagnostic:**

```json
{
  "graph_file": "run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/computational_inputs/adhesion_cytoskeleton_graph_synthetic.json",
  "input_file": "run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/computational_inputs/force_paths_synthetic.csv",
  "linear_fit_r_squared": 0.398862,
  "linear_fit_slope_p_value": 0.027611134124137217
}
```

**Scientific interpretation:** The synthetic force-path computation converts adhesion, cytoskeletal score, displacement, and path length into a traction-proxy load-path ranking. The strongest path is path 12, while the moderate adhesion-traction fit shows that adhesion alone does not explain the load distribution in this computational graph.

**Uncertainty or limitation:** Deterministic synthetic computational force-path field; useful for testing quantitative mechanobiology logic, not a measured cell traction map.

## Validation and Diagnostics

```json
{
  "accepted_source_data_scienceclaw_count": 5,
  "computational_input_need_count": 0,
  "formal_result_count": 10,
  "quantitative_result_count": 1,
  "unsupported_quantitative_claims_blocked": false
}
```

## Computational Input Needs

None.

## Valid Results

None.

## Formal/Symbolic Results

### 1. CytoskeletonNetwork

- Artifact ID: `art-8ce9ac06dce44cb0948782c15994b805`
- Morphism: `infer_cytoskeleton_network`
- Agent: `StructureBreakerAgent`
- Full payload: `presentable_results/artifact_payloads/01_art-8ce9ac06dce44cb0948782c15994b805_CytoskeletonNetwork.json`
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
      "relation": "infer_cytoskeleton_network",
      "source": "art-82917f504c6648ad8ef211eea31fadd9",
      "target": "CytoskeletonNetwork"
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
      "id": "art-82917f504c6648ad8ef211eea31fadd9",
      "type": "CellGeometry"
    },
    {
      "id": "CytoskeletonNetwork",
      "type": "output_type"
    }
  ]
}
```

### 2. CytoskeletonInvariantDescriptor

- Artifact ID: `art-eabf0aa30aa3443c9a3770f7bd7513d8`
- Morphism: `compute_cytoskeleton_invariants`
- Agent: `GraphInvariantAgent`
- Full payload: `presentable_results/artifact_payloads/02_art-eabf0aa30aa3443c9a3770f7bd7513d8_CytoskeletonInvariantDescriptor.json`
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
    "CytoskeletonNetwork"
  ],
  "parity_value": "even",
  "source_content_features": [
    {
      "artifact_id": "art-8ce9ac06dce44cb0948782c15994b805",
      "artifact_type": "CytoskeletonNetwork",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "edge_count": 1,
      "emitted_need_types": [
        "CytoskeletonInvariantDescriptor"
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
      "morphism": "infer_cytoskeleton_network",
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

### 3. AdhesionGraph

- Artifact ID: `art-606f916fa3f24ac1b30791f57ac7fa7d`
- Morphism: `extract_adhesion_graph`
- Agent: `StructureBreakerAgent`
- Full payload: `presentable_results/artifact_payloads/03_art-606f916fa3f24ac1b30791f57ac7fa7d_AdhesionGraph.json`
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
      "relation": "extract_adhesion_graph",
      "source": "art-82917f504c6648ad8ef211eea31fadd9",
      "target": "AdhesionGraph"
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
      "id": "art-82917f504c6648ad8ef211eea31fadd9",
      "type": "CellGeometry"
    },
    {
      "id": "AdhesionGraph",
      "type": "output_type"
    }
  ]
}
```

### 4. AdhesionInvariantDescriptor

- Artifact ID: `art-ded35013e7004d6680a25aa1cc604a24`
- Morphism: `compute_adhesion_invariants`
- Agent: `GraphInvariantAgent`
- Full payload: `presentable_results/artifact_payloads/04_art-ded35013e7004d6680a25aa1cc604a24_AdhesionInvariantDescriptor.json`
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
    "AdhesionGraph"
  ],
  "parity_value": "odd",
  "source_content_features": [
    {
      "artifact_id": "art-606f916fa3f24ac1b30791f57ac7fa7d",
      "artifact_type": "AdhesionGraph",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "edge_count": 1,
      "emitted_need_types": [
        "AdhesionInvariantDescriptor"
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
      "morphism": "extract_adhesion_graph",
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

### 5. ForcePathDescriptor

- Artifact ID: `art-aa6ba65b9e1e4b08bc31152761026f51`
- Morphism: `compute_force_path_parity`
- Agent: `ParityDescriptorAgent`
- Full payload: `presentable_results/artifact_payloads/05_art-aa6ba65b9e1e4b08bc31152761026f51_ForcePathDescriptor.json`
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
    "CytoskeletonInvariantDescriptor",
    "AdhesionInvariantDescriptor"
  ],
  "parity_value": "odd",
  "source_content_features": [
    {
      "artifact_id": "art-eabf0aa30aa3443c9a3770f7bd7513d8",
      "artifact_type": "CytoskeletonInvariantDescriptor",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [
        "ForcePathDescriptor"
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
      "morphism": "compute_cytoskeleton_invariants",
      "parity_value": "even",
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
      "artifact_id": "art-ded35013e7004d6680a25aa1cc604a24",
      "artifact_type": "AdhesionInvariantDescriptor",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
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
      "morphism": "compute_adhesion_invariants",
      "parity_value": "odd",
      "payload_keys": [
        "data_status",
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
  ]
}
```

### 6. PathParityValidationRecord

- Artifact ID: `art-fa4ced7c368249d6936d8b10f3e19ca5`
- Morphism: `validate_path_parity`
- Agent: `FormalValidatorAgent`
- Full payload: `presentable_results/artifact_payloads/06_art-fa4ced7c368249d6936d8b10f3e19ca5_PathParityValidationRecord.json`
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
      "artifact_id": "art-aa6ba65b9e1e4b08bc31152761026f51",
      "artifact_type": "ForcePathDescriptor",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "ForcePathDescriptor",
      "emitted_need_types": [
        "PathParityValidationRecord"
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
      "morphism": "compute_force_path_parity",
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
    }
  ],
  "validated_parent_types": [
    "ForcePathDescriptor"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 7. MechanotransductionModel

- Artifact ID: `art-63d470a3ab0b417992ee36ee76d9101b`
- Morphism: `build_mechanotransduction_model`
- Agent: `MechanicsBuilderAgent`
- Full payload: `presentable_results/artifact_payloads/07_art-63d470a3ab0b417992ee36ee76d9101b_MechanotransductionModel.json`
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
  "expression": "MechanotransductionModel := build_mechanotransduction_model(formal_validation_record + symbolic_parity_descriptor)",
  "input_types": [
    "PathParityValidationRecord",
    "ForcePathDescriptor"
  ],
  "kind": "symbolic_mechanics_expression",
  "source_content_features": [
    {
      "artifact_id": "art-fa4ced7c368249d6936d8b10f3e19ca5",
      "artifact_type": "PathParityValidationRecord",
      "checks_passed": true,
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [
        "MechanotransductionModel"
      ],
      "formal_result_fields": [
        "checks",
        "kind",
        "validated_parent_content",
        "validated_parent_types"
      ],
      "formal_result_kind": "formal_validation_record",
      "morphism": "validate_path_parity",
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
      "artifact_id": "art-aa6ba65b9e1e4b08bc31152761026f51",
      "artifact_type": "ForcePathDescriptor",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "ForcePathDescriptor",
      "emitted_need_types": [
        "PathParityValidationRecord"
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
      "morphism": "compute_force_path_parity",
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
    }
  ],
  "symbols": [
    "formal_validation_record",
    "symbolic_parity_descriptor"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 8. AlternativeForcePathModel

- Artifact ID: `art-ca9e4b7672584c378635e5c05f9cf88a`
- Morphism: `build_alternative_force_path_model`
- Agent: `MechanicsBuilderAgent`
- Full payload: `presentable_results/artifact_payloads/08_art-ca9e4b7672584c378635e5c05f9cf88a_AlternativeForcePathModel.json`
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
  "expression": "AlternativeForcePathModel := build_alternative_force_path_model(symbolic_mechanics_expression)",
  "input_types": [
    "MechanotransductionModel"
  ],
  "kind": "symbolic_mechanics_expression",
  "source_content_features": [
    {
      "artifact_id": "art-63d470a3ab0b417992ee36ee76d9101b",
      "artifact_type": "MechanotransductionModel",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [
        "AlternativeForcePathModel",
        "ForcePathContradictionRecord"
      ],
      "expression": "MechanotransductionModel := build_mechanotransduction_model(formal_validation_record + symbolic_parity_descriptor)",
      "formal_result_fields": [
        "assumptions",
        "expression",
        "input_types",
        "kind",
        "source_content_features",
        "symbols"
      ],
      "formal_result_kind": "symbolic_mechanics_expression",
      "morphism": "build_mechanotransduction_model",
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
  "symbols": [
    "symbolic_mechanics_expression"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 9. ForcePathContradictionRecord

- Artifact ID: `art-99e1f915e5344039afa2ca9239bb86e7`
- Morphism: `check_force_path_contradiction`
- Agent: `FormalValidatorAgent`
- Full payload: `presentable_results/artifact_payloads/09_art-99e1f915e5344039afa2ca9239bb86e7_ForcePathContradictionRecord.json`
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
      "artifact_id": "art-63d470a3ab0b417992ee36ee76d9101b",
      "artifact_type": "MechanotransductionModel",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [
        "AlternativeForcePathModel",
        "ForcePathContradictionRecord"
      ],
      "expression": "MechanotransductionModel := build_mechanotransduction_model(formal_validation_record + symbolic_parity_descriptor)",
      "formal_result_fields": [
        "assumptions",
        "expression",
        "input_types",
        "kind",
        "source_content_features",
        "symbols"
      ],
      "formal_result_kind": "symbolic_mechanics_expression",
      "morphism": "build_mechanotransduction_model",
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
      "artifact_id": "art-ca9e4b7672584c378635e5c05f9cf88a",
      "artifact_type": "AlternativeForcePathModel",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [],
      "expression": "AlternativeForcePathModel := build_alternative_force_path_model(symbolic_mechanics_expression)",
      "formal_result_fields": [
        "assumptions",
        "expression",
        "input_types",
        "kind",
        "source_content_features",
        "symbols"
      ],
      "formal_result_kind": "symbolic_mechanics_expression",
      "morphism": "build_alternative_force_path_model",
      "payload_keys": [
        "data_status",
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
  "validated_parent_types": [
    "MechanotransductionModel",
    "AlternativeForcePathModel"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 10. MechanobiologyClaim

- Artifact ID: `art-b34a76dc8bbb47c9a3f1841d81fa3a4a`
- Morphism: `synthesize_mechanobiology_claim`
- Agent: `ClaimSynthesisAgent`
- Full payload: `presentable_results/artifact_payloads/10_art-b34a76dc8bbb47c9a3f1841d81fa3a4a_MechanobiologyClaim.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `scientific-writing`
- Accepted as substantive: `False`

**Formal result:**

```json
{
  "claim_scope": "formal workflow demonstration",
  "claim_text": "MechanobiologyClaim is supported only as a formal composition of ForcePathContradictionRecord, AlternativeForcePathModel via synthesize_mechanobiology_claim; no biological or mechanical measurement is asserted.",
  "evidence_parent_content": [
    {
      "artifact_id": "art-99e1f915e5344039afa2ca9239bb86e7",
      "artifact_type": "ForcePathContradictionRecord",
      "checks_passed": true,
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [
        "MechanobiologyClaim"
      ],
      "formal_result_fields": [
        "checks",
        "kind",
        "validated_parent_content",
        "validated_parent_types"
      ],
      "formal_result_kind": "formal_validation_record",
      "morphism": "check_force_path_contradiction",
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
      "artifact_id": "art-ca9e4b7672584c378635e5c05f9cf88a",
      "artifact_type": "AlternativeForcePathModel",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [],
      "expression": "AlternativeForcePathModel := build_alternative_force_path_model(symbolic_mechanics_expression)",
      "formal_result_fields": [
        "assumptions",
        "expression",
        "input_types",
        "kind",
        "source_content_features",
        "symbols"
      ],
      "formal_result_kind": "symbolic_mechanics_expression",
      "morphism": "build_alternative_force_path_model",
      "payload_keys": [
        "data_status",
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
    "art-99e1f915e5344039afa2ca9239bb86e7",
    "art-ca9e4b7672584c378635e5c05f9cf88a"
  ],
  "kind": "formal_claim_synthesis"
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

## Blocked or Missing Data

None.

## Rejected Placeholder Outputs

None. Placeholder ScienceClaw outputs were rejected at runtime and replaced with formal results or blocked records.
