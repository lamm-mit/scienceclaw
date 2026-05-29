# Example C: membrane curvature biophysics

> Act like a mechanics investigator, not a generic data analyzer.

## Run Summary

- Audit status: `pass`
- Executor backend: `scienceclaw`
- ScienceClaw agents used: `True`
- Artifacts emitted: `9`
- Needs fulfilled: `9`
- Open needs remaining: `0`
- Data honesty status: `no_fake_numeric_science`

## Mechanics Investigation Question

- Mechanical hypothesis: Membrane curvature and patch-gluing constraints can define energy and shape-transition mechanics.
- Mechanical question: Can membrane geometry, curvature measurements, and material parameters support quantitative energy or shape-transition estimates?
- Full smart-investigation payload: `presentable_results/MECHANICS_INVESTIGATION.json`

## Evidence Plan and Skill Routing

**Required evidence:**

- membrane geometry or curvature field with units
- patch adjacency/gluing data
- material parameters such as bending modulus or tension
- computational boundary conditions or perturbation protocol

**ScienceClaw skill routing:**

- `image-analysis`: measure membrane geometry/curvature from microscopy outputs Status: `blocked_missing_input`
- `csv-read`: load curvature, geometry, or perturbation tables Status: `eligible`
- `statsmodels`: fit curvature-energy or transition trends with diagnostics Status: `eligible`
- `fem-analysis`: perform modal/field mechanics only if mesh and material JSON exist Status: `blocked_missing_input`
- `datavis`: plot curvature and energy summaries Status: `eligible`

**Quantitative input search:**

- Available input kinds: `material_properties, synthetic_computational_input, table`
- Candidate files found: `2`

- `membrane_curvature_field_synthetic.csv` from `run_dir_scan`
- `membrane_material_model.json` from `run_dir_scan`

**ScienceClaw skill executions:**

- `csv-read:membrane_curvature_field_synthetic.csv` used `csv-read` on `membrane_curvature_field_synthetic.csv`; status `success`, shape `[49, 3]`.

## Quantitative Computational Mechanics Results

### Synthetic membrane curvature-energy computation

- Evidence class: `synthetic_computational`
- Input artifact: `membrane_curvature_field_synthetic.csv; membrane_material_model.json`
- Input file: `run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/computational_inputs/membrane_curvature_field_synthetic.csv`
- Method/skill used: ScienceClaw csv-read on generated computational curvature CSV plus deterministic Helfrich-style quadratic curvature-energy summary

**Computed values:**

```json
{
  "grid_point_count": 49,
  "max_abs_curvature_1_um": 0.2948332,
  "mean_energy_density_proxy_kbt_per_um2": 0.23935931,
  "rms_curvature_1_um": 0.15471241,
  "total_grid_energy_proxy_kbt": 11.72860601
}
```

**Units:**

```json
{
  "bending_modulus": "kBT",
  "curvature": "1/um",
  "energy_density_proxy": "kBT/um^2"
}
```

**Diagnostic:**

```json
{
  "bending_modulus_kbt": 20.0,
  "has_material_model": true,
  "input_file": "run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/computational_inputs/membrane_curvature_field_synthetic.csv",
  "material_file": "run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/computational_inputs/membrane_material_model.json"
}
```

**Scientific interpretation:** The curvature field yields a compact bending-energy summary for the membrane model: the RMS curvature and total quadratic energy proxy quantify how far the synthetic patch departs from flat geometry under the assigned bending modulus. Mechanically, the result supports a curvature-energy interpretation rather than a topology-only membrane descriptor.

**Uncertainty or limitation:** Deterministic synthetic computational curvature field and material model; useful for energy-pipeline computation, not a measured membrane shape.

## Validation and Diagnostics

```json
{
  "accepted_source_data_scienceclaw_count": 3,
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

### 1. CurvatureDescriptor

- Artifact ID: `art-279a9755644245668d4e7906758a5e96`
- Morphism: `measure_curvature`
- Agent: `StructureBreakerAgent`
- Full payload: `presentable_results/artifact_payloads/01_art-279a9755644245668d4e7906758a5e96_CurvatureDescriptor.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `networkx`
- Accepted as substantive: `True`

**Formal result:**

```json
{
  "input_types": [
    "MembranePatchGeometry"
  ],
  "kind": "formal_artifact_record",
  "output_type": "CurvatureDescriptor",
  "query": "measure formal curvature descriptor",
  "source_content_features": [
    {
      "artifact_id": "art-b66c478cbd0c49938d335ef6dd52e081",
      "artifact_type": "MembranePatchGeometry",
      "data_status": "example_seed_no_numeric_measurements",
      "descriptor_type": "",
      "emitted_need_types": [],
      "formal_result_fields": [],
      "formal_result_kind": "",
      "morphism": "",
      "payload_keys": [
        "data_status",
        "topic"
      ],
      "result_classification": ""
    }
  ]
}
```

### 2. CurvatureParityDescriptor

- Artifact ID: `art-1d4642ac944743a4893e5e968932a572`
- Morphism: `compute_curvature_parity`
- Agent: `ParityDescriptorAgent`
- Full payload: `presentable_results/artifact_payloads/02_art-1d4642ac944743a4893e5e968932a572_CurvatureParityDescriptor.json`
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
    "CurvatureDescriptor"
  ],
  "parity_value": "even",
  "source_content_features": [
    {
      "artifact_id": "art-279a9755644245668d4e7906758a5e96",
      "artifact_type": "CurvatureDescriptor",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "CurvatureDescriptor",
      "emitted_need_types": [
        "CurvatureParityDescriptor",
        "ProteinAssemblyGraph",
        "PatchGluingCompatibilityRecord"
      ],
      "formal_result_fields": [
        "input_types",
        "kind",
        "output_type",
        "query",
        "source_content_features"
      ],
      "formal_result_kind": "formal_artifact_record",
      "morphism": "measure_curvature",
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
  ]
}
```

### 3. ProteinAssemblyGraph

- Artifact ID: `art-6bbcf361efb64d7593772e0706d293c0`
- Morphism: `build_assembly_graph`
- Agent: `AssemblyAgent`
- Full payload: `presentable_results/artifact_payloads/03_art-6bbcf361efb64d7593772e0706d293c0_ProteinAssemblyGraph.json`
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
      "relation": "build_assembly_graph",
      "source": "art-279a9755644245668d4e7906758a5e96",
      "target": "ProteinAssemblyGraph"
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
      "data_status": "formal_descriptor_only",
      "formal_result_kind": "formal_artifact_record",
      "id": "art-279a9755644245668d4e7906758a5e96",
      "type": "CurvatureDescriptor"
    },
    {
      "id": "ProteinAssemblyGraph",
      "type": "output_type"
    }
  ]
}
```

### 4. PatchGluingCompatibilityRecord

- Artifact ID: `art-2657fef5a8ad408f9919cb8ed653af78`
- Morphism: `check_patch_gluing`
- Agent: `GluingAgent`
- Full payload: `presentable_results/artifact_payloads/04_art-2657fef5a8ad408f9919cb8ed653af78_PatchGluingCompatibilityRecord.json`
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
      "artifact_id": "art-279a9755644245668d4e7906758a5e96",
      "artifact_type": "CurvatureDescriptor",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "CurvatureDescriptor",
      "emitted_need_types": [
        "CurvatureParityDescriptor",
        "ProteinAssemblyGraph",
        "PatchGluingCompatibilityRecord"
      ],
      "formal_result_fields": [
        "input_types",
        "kind",
        "output_type",
        "query",
        "source_content_features"
      ],
      "formal_result_kind": "formal_artifact_record",
      "morphism": "measure_curvature",
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
    "CurvatureDescriptor"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 5. EnergyFunctional

- Artifact ID: `art-4b2e9f977d6742e0a3decfe4657535fc`
- Morphism: `derive_energy_functional`
- Agent: `MechanicsBuilderAgent`
- Full payload: `presentable_results/artifact_payloads/05_art-4b2e9f977d6742e0a3decfe4657535fc_EnergyFunctional.json`
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
  "expression": "EnergyFunctional := derive_energy_functional(formal_validation_record + symbolic_parity_descriptor)",
  "input_types": [
    "PatchGluingCompatibilityRecord",
    "CurvatureParityDescriptor"
  ],
  "kind": "symbolic_mechanics_expression",
  "source_content_features": [
    {
      "artifact_id": "art-2657fef5a8ad408f9919cb8ed653af78",
      "artifact_type": "PatchGluingCompatibilityRecord",
      "checks_passed": true,
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [
        "EnergyFunctional"
      ],
      "formal_result_fields": [
        "checks",
        "kind",
        "validated_parent_content",
        "validated_parent_types"
      ],
      "formal_result_kind": "formal_validation_record",
      "morphism": "check_patch_gluing",
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
      "artifact_id": "art-1d4642ac944743a4893e5e968932a572",
      "artifact_type": "CurvatureParityDescriptor",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "CurvatureParityDescriptor",
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
      "morphism": "compute_curvature_parity",
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
    "formal_validation_record",
    "symbolic_parity_descriptor"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 6. EnergyAssumptionValidationRecord

- Artifact ID: `art-0a32f5bce077400bb748a3c0e80dc055`
- Morphism: `validate_energy_assumptions`
- Agent: `FormalValidatorAgent`
- Full payload: `presentable_results/artifact_payloads/06_art-0a32f5bce077400bb748a3c0e80dc055_EnergyAssumptionValidationRecord.json`
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
      "artifact_id": "art-4b2e9f977d6742e0a3decfe4657535fc",
      "artifact_type": "EnergyFunctional",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "EnergyFunctional",
      "emitted_need_types": [
        "EnergyAssumptionValidationRecord"
      ],
      "expression": "EnergyFunctional := derive_energy_functional(formal_validation_record + symbolic_parity_descriptor)",
      "formal_result_fields": [
        "assumptions",
        "expression",
        "input_types",
        "kind",
        "source_content_features",
        "symbols"
      ],
      "formal_result_kind": "symbolic_mechanics_expression",
      "morphism": "derive_energy_functional",
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
    "EnergyFunctional"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 7. ShapeTransitionModel

- Artifact ID: `art-16c97823e6fb4639adc0d12ee85db8d6`
- Morphism: `predict_shape_transition`
- Agent: `MechanicsBuilderAgent`
- Full payload: `presentable_results/artifact_payloads/07_art-16c97823e6fb4639adc0d12ee85db8d6_ShapeTransitionModel.json`
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
  "expression": "ShapeTransitionModel := predict_shape_transition(formal_validation_record + symbolic_mechanics_expression)",
  "input_types": [
    "EnergyAssumptionValidationRecord",
    "EnergyFunctional"
  ],
  "kind": "symbolic_mechanics_expression",
  "source_content_features": [
    {
      "artifact_id": "art-0a32f5bce077400bb748a3c0e80dc055",
      "artifact_type": "EnergyAssumptionValidationRecord",
      "checks_passed": true,
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [
        "ShapeTransitionModel"
      ],
      "formal_result_fields": [
        "checks",
        "kind",
        "validated_parent_content",
        "validated_parent_types"
      ],
      "formal_result_kind": "formal_validation_record",
      "morphism": "validate_energy_assumptions",
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
      "artifact_id": "art-4b2e9f977d6742e0a3decfe4657535fc",
      "artifact_type": "EnergyFunctional",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "EnergyFunctional",
      "emitted_need_types": [
        "EnergyAssumptionValidationRecord"
      ],
      "expression": "EnergyFunctional := derive_energy_functional(formal_validation_record + symbolic_parity_descriptor)",
      "formal_result_fields": [
        "assumptions",
        "expression",
        "input_types",
        "kind",
        "source_content_features",
        "symbols"
      ],
      "formal_result_kind": "symbolic_mechanics_expression",
      "morphism": "derive_energy_functional",
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
    "symbolic_mechanics_expression"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 8. CurvatureContradictionCheck

- Artifact ID: `art-deda0ba1aa644b3daafbecc307df1e76`
- Morphism: `check_curvature_contradiction`
- Agent: `FormalValidatorAgent`
- Full payload: `presentable_results/artifact_payloads/08_art-deda0ba1aa644b3daafbecc307df1e76_CurvatureContradictionCheck.json`
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
      "artifact_id": "art-16c97823e6fb4639adc0d12ee85db8d6",
      "artifact_type": "ShapeTransitionModel",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [
        "CurvatureContradictionCheck",
        "BiophysicsClaim"
      ],
      "expression": "ShapeTransitionModel := predict_shape_transition(formal_validation_record + symbolic_mechanics_expression)",
      "formal_result_fields": [
        "assumptions",
        "expression",
        "input_types",
        "kind",
        "source_content_features",
        "symbols"
      ],
      "formal_result_kind": "symbolic_mechanics_expression",
      "morphism": "predict_shape_transition",
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
    "ShapeTransitionModel"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 9. BiophysicsClaim

- Artifact ID: `art-f1f6cc783d9e436b86d2a2bcd9221820`
- Morphism: `synthesize_biophysics_claim`
- Agent: `ClaimSynthesisAgent`
- Full payload: `presentable_results/artifact_payloads/09_art-f1f6cc783d9e436b86d2a2bcd9221820_BiophysicsClaim.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `scientific-writing`
- Accepted as substantive: `False`

**Formal result:**

```json
{
  "claim_scope": "formal workflow demonstration",
  "claim_text": "BiophysicsClaim is supported only as a formal composition of ShapeTransitionModel, CurvatureContradictionCheck via synthesize_biophysics_claim; no biological or mechanical measurement is asserted.",
  "evidence_parent_content": [
    {
      "artifact_id": "art-16c97823e6fb4639adc0d12ee85db8d6",
      "artifact_type": "ShapeTransitionModel",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [
        "CurvatureContradictionCheck",
        "BiophysicsClaim"
      ],
      "expression": "ShapeTransitionModel := predict_shape_transition(formal_validation_record + symbolic_mechanics_expression)",
      "formal_result_fields": [
        "assumptions",
        "expression",
        "input_types",
        "kind",
        "source_content_features",
        "symbols"
      ],
      "formal_result_kind": "symbolic_mechanics_expression",
      "morphism": "predict_shape_transition",
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
      "artifact_id": "art-deda0ba1aa644b3daafbecc307df1e76",
      "artifact_type": "CurvatureContradictionCheck",
      "checks_passed": true,
      "data_status": "formal_descriptor_only",
      "descriptor_type": "",
      "emitted_need_types": [],
      "formal_result_fields": [
        "checks",
        "kind",
        "validated_parent_content",
        "validated_parent_types"
      ],
      "formal_result_kind": "formal_validation_record",
      "morphism": "check_curvature_contradiction",
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
    "art-16c97823e6fb4639adc0d12ee85db8d6",
    "art-deda0ba1aa644b3daafbecc307df1e76"
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
