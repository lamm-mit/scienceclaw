# Mechanobiology force-path mechanics

Evidence label: `synthetic_computational`

## Scientific Hypothesis

Mechanotransduction load routing is better represented by multivariable graph force-path structure than by adhesion strength alone.

## Typed Artifact Schema

- inputs: structured artifact payloads, computational input files, mechanics sidecar
- transforms: deterministic mechanics descriptor extraction, model comparison, stress test or ablation
- observables: computed mechanics values, diagnostics, formal descriptors
- models: simple descriptor, richer explanatory mechanics model
- diagnostics: AIC/BIC-style gate or ablation score, R^2/RSS where applicable, robustness check
- claims: mechanics-language interpretation with stated limits

## Specific Problem Scope

- Specific question: For the deterministic 12-path adhesion/cytoskeleton graph, does a four-feature force-path regression explain traction proxy better than an adhesion-only ablation?
- System boundary: Synthetic computational force-path table with 12 paths, adhesion score, cytoskeleton score, path length in um, displacement in um, traction proxy in Pa, and a path-adjacency graph.
- Candidate scope: adhesion-only traction model, full force-path regression
- Input scope: force_paths_synthetic.csv, adhesion_cytoskeleton_graph_synthetic.json
- Observable scope: degree centrality, load concentration, traction/path-length score, full regression coefficients, BIC delta, strongest-path removal mean score
- Out of scope: measured traction-force microscopy, cell-specific material calibration, time-dependent mechanotransduction, causal biological inference

## Mechanics Equations and Formal Descriptors

- Load-path score: L_i = traction_i / path_length_i.
- Adhesion ablation: T_i = beta0 + beta1 A_i.
- Full path model: T_i = beta0 + beta1 A_i + beta2 C_i + beta3 u_i + beta4 ell_i.
- Load concentration: max_i T_i / sum_i T_i.

## Candidate Models and Gate

- **mechbio_M0_adhesion_only_ablation** / **adhesion-only traction model**: `rejected`. It leaves cytoskeletal, displacement, and path-length structure outside the explanation. Formal type: `SinglePredictorTractionRegression`. Inputs: `force_paths_synthetic.csv`.
- **mechbio_M1_graph_conditioned_force_path_regression** / **full force-path regression**: `accepted`. It recovers the deterministic load-routing rule and improves the ablation score. Formal type: `MultifeatureLoadPathRegressionOnAdjacencyGraph`. Inputs: `force_paths_synthetic.csv, adhesion_cytoskeleton_graph_synthetic.json`.

Gate: `BIC model-selection gate`

{
  "accepted_model": "full force-path regression",
  "decision": "accepted",
  "decision_rule": "Accept the model with lower BIC; require positive improvement over the simpler descriptor.",
  "gate_type": "BIC model-selection gate",
  "rejected_model": "adhesion-only traction model",
  "scores": {
    "adhesion-only traction model": 48.953545,
    "delta_rejected_minus_accepted": 368.101265,
    "full force-path regression": -319.14772
  }
}

## Categorical Provenance Graph

- Graph file: `run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/categorical_discovery_graph.json`
- Objects: `7`
- Morphisms: `7`
- Artifacts: `7`

- `instantiate_mechanics_candidate_models`: `categorical_discovery_context` -> `MechanicsCandidateModelSet`
- `accept_mechanics_model`: `categorical_discovery_context` -> `MechanicsAcceptedModel`
- `reject_mechanics_model`: `categorical_discovery_context` -> `MechanicsRejectedModel`
- `apply_model_selection_gate`: `categorical_discovery_context` -> `MechanicsModelSelectionGate`
- `run_mechanics_stress_test`: `categorical_discovery_context` -> `MechanicsStressTest`
- `audit_mechanics_regime_transition`: `categorical_discovery_context` -> `MechanicsRegimeTransition`
- `synthesize_categorical_mechanics_claim`: `categorical_discovery_context` -> `MechanicsDiscoveryClaim`

## Deeper Mechanics Analysis

{
  "degree_centrality": {
    "path_1": 0.090909,
    "path_10": 0.181818,
    "path_11": 0.181818,
    "path_12": 0.090909,
    "path_2": 0.181818,
    "path_3": 0.181818,
    "path_4": 0.181818,
    "path_5": 0.181818,
    "path_6": 0.181818,
    "path_7": 0.181818,
    "path_8": 0.181818,
    "path_9": 0.181818
  },
  "full_model_coefficients": [
    -3.386667,
    34.73333,
    72.0,
    0.0,
    0.0
  ],
  "load_concentration": 0.102513,
  "mean_load_path_score_pa_per_um": 4.421814,
  "strongest_path_id": 12,
  "strongest_path_traction_pa": 72.886
}

## Rejected Alternatives

- **adhesion-only mechanobiology claim**: The ablation has lower explanatory power and omits path length, cytoskeletal score, and displacement.

## Stress Test or Ablation

{
  "after_removing_strongest_mean_load_score_pa_per_um": 4.471351,
  "baseline_mean_load_score_pa_per_um": 4.421814,
  "interpretation": "The ranked path field remains load-bearing after removing the strongest path, but the concentration diagnostic shows path 12 is the dominant route.",
  "name": "strongest-path removal robustness"
}

## Regime-Transition Audit

{
  "audit_claim": "The richer regime preserves the old descriptor artifacts and adds explanatory mechanics content that was not present in the simple regime.",
  "old_simple_descriptor_regime": "adhesion-vs-traction scalar association",
  "residual_content_added_by_new_regime": [
    "centrality",
    "load concentration",
    "full-vs-ablation regression gate",
    "strongest-path robustness"
  ],
  "richer_explanatory_mechanics_regime": "graph-conditioned force-path load-routing regime",
  "transported_preserved_artifacts": [
    "force-path feature table",
    "adhesion-cytoskeleton graph",
    "synthetic_computational label"
  ]
}

## Mechanics Claim

The mechanobiology run supports a graph-mediated load-routing claim: traction is best explained as a force-path property combining adhesion, cytoskeletal coupling, displacement, and path length, not as adhesion alone.

## Limitations

The force-path field is deterministic synthetic_computational input and must not be interpreted as measured cell traction.
