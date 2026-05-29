# Example A: 7T10 formal descriptor extension

> Act like a mechanics investigator, not a generic data analyzer.

## Run Summary

- Audit status: `pass`
- Executor backend: `scienceclaw`
- ScienceClaw agents used: `True`
- Artifacts emitted: `8`
- Needs fulfilled: `8`
- Open needs remaining: `0`
- Data honesty status: `no_fake_numeric_science`

## Mechanics Investigation Question

- Mechanical hypothesis: 7T10 peptide-receptor contact topology can be connected to load-bearing force-extension behavior.
- Mechanical question: Which contact-supported peptide positions and coarse-grained force-extension features support a mechanics interpretation of PDB 7T10?
- Full smart-investigation payload: `presentable_results/MECHANICS_INVESTIGATION.json`

## Evidence Plan and Skill Routing

**Required evidence:**

- PDB/contact graph or local structure file
- force-extension trace with force and extension units
- mechanics claim tying contacts to force-extension behavior
- atomistic or coarse-grained simulation ensemble for stronger quantitative claims

**ScienceClaw skill routing:**

- `structure-contact-analysis`: derive peptide-protein contact hotspots from PDB/contact data Status: `eligible`
- `csv-read`: inspect force-extension CSV tables when present Status: `eligible`
- `statsmodels`: fit force-extension trends and diagnostics when replicate traces exist Status: `eligible`
- `datavis`: plot force-extension curves when tabular data exists Status: `eligible`
- `pdb-database`: retrieve/verify PDB structure metadata when structure identifiers are present Status: `eligible`

**Quantitative input search:**

- Available input kinds: `force_extension_trace, pdb_or_contact, table`
- Candidate files found: `4`

- `contact_graph_7T10.json` from `imported_artifact:contact_graph_7T10`
- `force_extension_7T10.csv` from `paired_csv_for:force_extension_7T10`
- `force_extension_7T10.json` from `imported_artifact:force_extension_7T10`
- `mechanics_claim_7T10.json` from `imported_artifact:mechanics_claim_7T10`

**ScienceClaw skill executions:**

- `structure-contact-analysis:7T10.pdb` used `structure-contact-analysis` on `7T10.pdb`; status `success`, shape `[]`.
- `csv-read:force_extension_7T10.csv` used `csv-read` on `force_extension_7T10.csv`; status `success`, shape `[25, 5]`.
- `statsmodels:force_extension_7T10.csv` used `statsmodels` on `force_extension_7T10.csv`; status `success`, shape `[]`.

## Quantitative Computational Mechanics Results

### 7T10 peptide-receptor contact hotspot mechanics anchor

- Evidence class: `structural_computational`
- Input artifact: `contact_graph_7T10`
- Input file: `/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/7T10.pdb`
- Method/skill used: ScienceClaw structure-contact-analysis on local 7T10 PDB file

**Computed values:**

```json
{
  "binding_hotspots": [
    {
      "aa": "W",
      "contacts": 8,
      "interacting_protein_residues": [
        "R:119MET",
        "R:177ILE",
        "R:208PHE",
        "R:212THR",
        "R:272PHE",
        "R:276ASN",
        "R:294PHE",
        "R:298VAL"
      ],
      "position": 8
    },
    {
      "aa": "K",
      "contacts": 7,
      "interacting_protein_residues": [
        "R:92PHE",
        "R:99LEU",
        "R:122ASP",
        "R:272PHE",
        "R:294PHE",
        "R:298VAL",
        "R:302TYR"
      ],
      "position": 9
    },
    {
      "aa": "F",
      "contacts": 6,
      "interacting_protein_residues": [
        "R:275PHE",
        "R:279SER",
        "R:286PRO",
        "R:290LEU",
        "R:291LYS",
        "R:294PHE"
      ],
      "position": 6
    },
    {
      "aa": "F",
      "contacts": 6,
      "interacting_protein_residues": [
        "R:197TRP",
        "R:205TYR",
        "R:208PHE",
        "R:209ILE",
        "R:276ASN",
        "R:294PHE"
      ],
      "position": 7
    },
    {
      "aa": "A",
      "contacts": 5,
      "interacting_protein_residues": [
        "R:184ARG",
        "R:196ASN",
        "R:197TRP",
        "R:200GLU",
        "R:205TYR"
      ],
      "position": 1
    },
    {
      "aa": "F",
      "contacts": 5,
      "interacting_protein_residues": [
        "R:102GLN",
        "R:192SER",
        "R:286PRO",
        "R:291LYS",
        "R:294PHE"
      ],
      "position": 11
    }
  ],
  "cutoff_angstrom": 4.5,
  "hotspot_positions": [
    8,
    9,
    6,
    7,
    1,
    11
  ],
  "peptide_chain": "P",
  "peptide_sequence": "AGCKNFFWKTFTSC",
  "protein_chain": "R"
}
```

**Units:**

```json
{
  "contact_count": "residue contacts",
  "distance_cutoff": "angstrom"
}
```

**Diagnostic:**

```json
{
  "hotspot_count": 6,
  "matches_imported_contact_claim": true,
  "protein_length": 287
}
```

**Scientific interpretation:** The contact graph identifies a localized mechanical anchoring motif on the peptide: positions 8, 9, 6, 7, 1, and 11 carry the largest contact counts under the cutoff and are therefore the residues most plausibly coupled to load transfer in this structural model.

**Uncertainty or limitation:** Contact counts identify structural anchoring positions under a 4.5 angstrom cutoff; they do not assign residue-resolved force without a validated mechanics model.

### 7T10 coarse-grained force-extension descriptor

- Evidence class: `computational_surrogate`
- Input artifact: `force_extension_7T10`
- Input file: `/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/force_extension_7T10.json`
- Method/skill used: ScienceClaw csv-read on force_extension_7T10.csv plus deterministic force-extension extraction from ScienceClaw-generated JSON

**Computed values:**

```json
{
  "linear_force_extension_intercept_pN": 168.844286,
  "linear_force_extension_slope_pN_per_nm": 253.068938,
  "max_force_pN": 766.98959,
  "mean_force_pN": 472.52701,
  "min_force_pN": 33.52676,
  "peak_extension_nm": 2.4,
  "peak_force_pN": 766.98959,
  "point_count": 25,
  "pulling_work_pN_nm": 1141.29171
}
```

**Units:**

```json
{
  "energy": "kJ/mol",
  "extension": "nm",
  "force": "pN"
}
```

**Diagnostic:**

```json
{
  "candidate_files_used": [
    "/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/force_extension_7T10.csv",
    "/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/force_extension_7T10.json"
  ],
  "extension_monotonic": true,
  "has_point_series": true,
  "has_units": true,
  "linear_fit_r_squared": 0.942723,
  "linear_fit_slope_p_value": 8.808244777987513e-16
}
```

**Scientific interpretation:** The monotonic force-extension trace and positive linear slope provide a coarse-grained tensile mechanics descriptor for the 7T10 model: the imported surrogate behaves as a load-bearing extension response with a high peak force, but not as a replicated experimental or atomistic stiffness estimate.

**Uncertainty or limitation:** Single coarse-grained OpenMM surrogate trace; no replicate simulation ensemble, confidence interval, or atomistic validation is present.

## Validation and Diagnostics

```json
{
  "accepted_source_data_scienceclaw_count": 2,
  "computational_input_need_count": 0,
  "formal_result_count": 8,
  "quantitative_result_count": 2,
  "unsupported_quantitative_claims_blocked": false
}
```

## Computational Input Needs

None.

## 7T10 Baseline Handling

- Formal extension needs fulfilled: `5`
- Inherited 7T10 science needs remaining: `6`
- Imported baseline artifacts: `contact_graph_7T10`, `force_extension_7T10`, `mechanics_claim_7T10`.
- The run does not rerun hotspot detection or force-extension simulation.

## Valid Results

None.

## Formal/Symbolic Results

### 1. ContactParityDescriptor

- Artifact ID: `art-aa190b6d7dc046bb88fcb8a1e79aa99b`
- Morphism: `compute_7t10_contact_parity`
- Agent: `ParityDescriptorAgent`
- Full payload: `presentable_results/artifact_payloads/01_art-aa190b6d7dc046bb88fcb8a1e79aa99b_ContactParityDescriptor.json`
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
    "ContactGraph"
  ],
  "parity_value": "odd",
  "source_content_features": [
    {
      "artifact_id": "contact_graph_7T10",
      "artifact_type": "ContactGraph",
      "data_status": "",
      "descriptor_type": "",
      "emitted_need_types": [],
      "formal_result_fields": [],
      "formal_result_kind": "",
      "morphism": "",
      "payload_keys": [
        "source_name",
        "source_sha256",
        "summary"
      ],
      "result_classification": ""
    }
  ]
}
```

### 2. RupturePathwayFormalization

- Artifact ID: `art-470351c53c11461099002ccbcfccc3cf`
- Morphism: `formalize_rupture_need`
- Agent: `MechanicsBuilderAgent`
- Full payload: `presentable_results/artifact_payloads/02_art-470351c53c11461099002ccbcfccc3cf_RupturePathwayFormalization.json`
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
  "expression": "RupturePathwayFormalization := formalize_rupture_need(openneedrecord)",
  "input_types": [
    "OpenNeedRecord"
  ],
  "kind": "symbolic_mechanics_expression",
  "source_content_features": [
    {
      "artifact_id": "source_open_needs_7T10",
      "artifact_type": "OpenNeedRecord",
      "data_status": "",
      "descriptor_type": "",
      "emitted_need_types": [],
      "formal_result_fields": [],
      "formal_result_kind": "",
      "morphism": "",
      "payload_keys": [
        "inherited_needs",
        "source",
        "status"
      ],
      "result_classification": ""
    }
  ],
  "symbols": [
    "openneedrecord"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 3. OpenNeedDependencyGraph

- Artifact ID: `art-f74cc6873b5b490092fcd85e8a1cad93`
- Morphism: `build_open_need_dependency_graph`
- Agent: `NeedReactorAgent`
- Full payload: `presentable_results/artifact_payloads/03_art-f74cc6873b5b490092fcd85e8a1cad93_OpenNeedDependencyGraph.json`
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
      "relation": "build_open_need_dependency_graph",
      "source": "source_open_needs_7T10",
      "target": "OpenNeedDependencyGraph"
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
      "data_status": "",
      "formal_result_kind": "",
      "id": "source_open_needs_7T10",
      "type": "OpenNeedRecord"
    },
    {
      "id": "OpenNeedDependencyGraph",
      "type": "output_type"
    }
  ]
}
```

### 4. CompositionAuditRecord

- Artifact ID: `art-e27d3f5180d94f36a921614560d7dea5`
- Morphism: `audit_mechanics_composition`
- Agent: `FormalValidatorAgent`
- Full payload: `presentable_results/artifact_payloads/04_art-e27d3f5180d94f36a921614560d7dea5_CompositionAuditRecord.json`
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
      "ok": false
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
      "artifact_id": "mechanics_claim_7T10",
      "artifact_type": "MechanicsClaim",
      "data_status": "",
      "descriptor_type": "",
      "emitted_need_types": [],
      "formal_result_fields": [],
      "formal_result_kind": "",
      "morphism": "",
      "payload_keys": [
        "source_name",
        "source_sha256",
        "summary"
      ],
      "result_classification": ""
    },
    {
      "artifact_id": "contact_graph_7T10",
      "artifact_type": "ContactGraph",
      "data_status": "",
      "descriptor_type": "",
      "emitted_need_types": [],
      "formal_result_fields": [],
      "formal_result_kind": "",
      "morphism": "",
      "payload_keys": [
        "source_name",
        "source_sha256",
        "summary"
      ],
      "result_classification": ""
    },
    {
      "artifact_id": "force_extension_7T10",
      "artifact_type": "ForceExtensionTrace",
      "data_status": "",
      "descriptor_type": "",
      "emitted_need_types": [],
      "formal_result_fields": [],
      "formal_result_kind": "",
      "morphism": "",
      "payload_keys": [
        "source_name",
        "source_sha256",
        "summary"
      ],
      "result_classification": ""
    }
  ],
  "validated_parent_types": [
    "MechanicsClaim",
    "ContactGraph",
    "ForceExtensionTrace"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 5. MechanicsFunctorDescriptor

- Artifact ID: `art-30898c4f51324e53b9284dbec8c01d05`
- Morphism: `derive_mechanics_functor_descriptor`
- Agent: `MechanicsBuilderAgent`
- Full payload: `presentable_results/artifact_payloads/05_art-30898c4f51324e53b9284dbec8c01d05_MechanicsFunctorDescriptor.json`
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
  "expression": "MechanicsFunctorDescriptor := derive_mechanics_functor_descriptor(forceextensiontrace + contactgraph)",
  "input_types": [
    "ForceExtensionTrace",
    "ContactGraph"
  ],
  "kind": "symbolic_mechanics_expression",
  "source_content_features": [
    {
      "artifact_id": "force_extension_7T10",
      "artifact_type": "ForceExtensionTrace",
      "data_status": "",
      "descriptor_type": "",
      "emitted_need_types": [],
      "formal_result_fields": [],
      "formal_result_kind": "",
      "morphism": "",
      "payload_keys": [
        "source_name",
        "source_sha256",
        "summary"
      ],
      "result_classification": ""
    },
    {
      "artifact_id": "contact_graph_7T10",
      "artifact_type": "ContactGraph",
      "data_status": "",
      "descriptor_type": "",
      "emitted_need_types": [],
      "formal_result_fields": [],
      "formal_result_kind": "",
      "morphism": "",
      "payload_keys": [
        "source_name",
        "source_sha256",
        "summary"
      ],
      "result_classification": ""
    }
  ],
  "symbols": [
    "forceextensiontrace",
    "contactgraph"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 6. NeedClassificationRecord

- Artifact ID: `art-91fc3930c58b45bcb62911e7a6df4f83`
- Morphism: `classify_7t10_needs`
- Agent: `NeedReactorAgent`
- Full payload: `presentable_results/artifact_payloads/06_art-91fc3930c58b45bcb62911e7a6df4f83_NeedClassificationRecord.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `scientific-critical-thinking`
- Accepted as substantive: `False`

**Formal result:**

```json
{
  "input_types": [
    "OpenNeedDependencyGraph"
  ],
  "kind": "formal_artifact_record",
  "output_type": "NeedClassificationRecord",
  "query": "classify inherited 7T10 downstream needs",
  "source_content_features": [
    {
      "artifact_id": "art-f74cc6873b5b490092fcd85e8a1cad93",
      "artifact_type": "OpenNeedDependencyGraph",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "OpenNeedDependencyGraph",
      "edge_count": 1,
      "emitted_need_types": [
        "NeedClassificationRecord"
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
      "morphism": "build_open_need_dependency_graph",
      "node_count": 2,
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

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 7. DescriptorInvarianceCheck

- Artifact ID: `art-4c5272bbf8734a419bc13b8896eebdb6`
- Morphism: `verify_contact_parity_invariance`
- Agent: `FormalValidatorAgent`
- Full payload: `presentable_results/artifact_payloads/07_art-4c5272bbf8734a419bc13b8896eebdb6_DescriptorInvarianceCheck.json`
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
      "artifact_id": "art-aa190b6d7dc046bb88fcb8a1e79aa99b",
      "artifact_type": "ContactParityDescriptor",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "ContactParityDescriptor",
      "emitted_need_types": [
        "DescriptorInvarianceCheck"
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
      "morphism": "compute_7t10_contact_parity",
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
    "ContactParityDescriptor"
  ]
}
```

**Rejected ScienceClaw output:**

The attempted ScienceClaw skill returned a placeholder/demo/scaffold response, so it is not presented as a valid result.

### 8. FormalMechanicsExtensionClaim

- Artifact ID: `art-fee8625446634bd1b587428a1cc60d18`
- Morphism: `synthesize_7t10_formal_claim`
- Agent: `ClaimSynthesisAgent`
- Full payload: `presentable_results/artifact_payloads/08_art-fee8625446634bd1b587428a1cc60d18_FormalMechanicsExtensionClaim.json`
- Result classification: `formal_symbolic_result`

**ScienceClaw execution audit:**

- Skill attempted: `scientific-writing`
- Accepted as substantive: `False`

**Formal result:**

```json
{
  "claim_scope": "formal workflow demonstration",
  "claim_text": "FormalMechanicsExtensionClaim is supported only as a formal composition of RupturePathwayFormalization, NeedClassificationRecord via synthesize_7t10_formal_claim; no biological or mechanical measurement is asserted.",
  "evidence_parent_content": [
    {
      "artifact_id": "art-470351c53c11461099002ccbcfccc3cf",
      "artifact_type": "RupturePathwayFormalization",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "RupturePathwayFormalization",
      "emitted_need_types": [
        "FormalMechanicsExtensionClaim"
      ],
      "expression": "RupturePathwayFormalization := formalize_rupture_need(openneedrecord)",
      "formal_result_fields": [
        "assumptions",
        "expression",
        "input_types",
        "kind",
        "source_content_features",
        "symbols"
      ],
      "formal_result_kind": "symbolic_mechanics_expression",
      "morphism": "formalize_rupture_need",
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
      "artifact_id": "art-91fc3930c58b45bcb62911e7a6df4f83",
      "artifact_type": "NeedClassificationRecord",
      "data_status": "formal_descriptor_only",
      "descriptor_type": "NeedClassificationRecord",
      "emitted_need_types": [],
      "formal_result_fields": [
        "input_types",
        "kind",
        "output_type",
        "query",
        "source_content_features"
      ],
      "formal_result_kind": "formal_artifact_record",
      "morphism": "classify_7t10_needs",
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
    "art-470351c53c11461099002ccbcfccc3cf",
    "art-91fc3930c58b45bcb62911e7a6df4f83"
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
