# 7T10 structure-contact tensile mechanics

Evidence label: `imported_computational_surrogate, imported_real_structure`

## Scientific Hypothesis

A localized 7T10 contact hotspot pattern acts as a structural load anchor for a coarse-grained tensile response.

## Typed Artifact Schema

- inputs: structured artifact payloads, computational input files, mechanics sidecar
- transforms: deterministic mechanics descriptor extraction, model comparison, stress test or ablation
- observables: computed mechanics values, diagnostics, formal descriptors
- models: simple descriptor, richer explanatory mechanics model
- diagnostics: AIC/BIC-style gate or ablation score, R^2/RSS where applicable, robustness check
- claims: mechanics-language interpretation with stated limits

## Specific Problem Scope

- Specific question: Does the imported 7T10 peptide-receptor contact graph plus one coarse-grained force-extension trace support a contact-localized tensile mechanics claim?
- System boundary: PDB 7T10 peptide chain P against receptor chain R; hotspot residues [8, 9, 6, 7, 1, 11]; force-extension trace from 0.0 to 2.4 nm.
- Candidate scope: mean-force null model, linear force-extension model
- Input scope: 7T10.pdb, force_extension_7T10.csv, force_extension_7T10.json
- Observable scope: residue contact counts, contact entropy/Gini, peak force, pulling work, linear stiffness, AIC delta
- Out of scope: new SMD ensemble, mutation prediction, experimental binding mechanics, atomistic uncertainty quantification

## Mechanics Equations and Formal Descriptors

- Contact entropy: H = -sum_i p_i log(p_i), where p_i = c_i / sum_j c_j.
- Contact Gini: G = sum_i sum_j |c_i - c_j| / (2 n sum_i c_i).
- Force-extension gate: F(x) = k x + F0 compared against F(x) = mean(F).
- Work diagnostic: W = integral F dx, recorded from the imported computational surrogate trace.

## Candidate Models and Gate

- **7t10_M0_mean_force_null** / **mean-force null model**: `rejected`. It ignores extension-dependent tensile loading. Formal type: `ConstantForceDescriptor`. Inputs: `force_extension_7T10.json`.
- **7t10_M1_linear_tensile_response** / **linear force-extension model**: `accepted`. It explains the force trace with lower AIC and high R^2. Formal type: `AffineTensileResponseModel`. Inputs: `7T10.pdb, force_extension_7T10.csv, force_extension_7T10.json`.

Gate: `AIC model-selection gate`

{
  "accepted_model": "linear force-extension model",
  "decision": "accepted",
  "decision_rule": "Accept the model with lower AIC; require positive improvement over the simpler descriptor.",
  "gate_type": "AIC model-selection gate",
  "rejected_model": "mean-force null model",
  "scores": {
    "delta_rejected_minus_accepted": 69.496398,
    "linear force-extension model": 194.313107,
    "mean-force null model": 263.809505
  }
}

## Categorical Provenance Graph

- Graph file: `run_exports/formal_mechanics_runs/7t10_formal_extension/presentable_results/categorical_discovery_graph.json`
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
  "contact_entropy_nats": 1.777069,
  "contact_gini": 0.094595,
  "hotspot_load_anchor_index": 1.0,
  "peak_extension_nm": 2.4,
  "peak_force_pN": 766.98959,
  "pulling_work_pN_nm": 1141.29171,
  "stiffness_pN_per_nm": 253.068938
}

## Rejected Alternatives

- **contact-count-only claim**: Contact hotspots localize anchors but cannot by themselves predict tensile slope, peak force, or work.
- **mean-force descriptor**: It discards extension ordering and fails the AIC gate against the linear tensile descriptor.

## Stress Test or Ablation

{
  "accepted_model_advantage": "The accepted model couples structural anchoring to tensile-response diagnostics.",
  "name": "contact-only ablation",
  "result": "Removing the force-extension trace leaves hotspot localization but no stiffness/work/peak-force mechanics claim."
}

## Regime-Transition Audit

{
  "audit_claim": "The richer regime preserves the old descriptor artifacts and adds explanatory mechanics content that was not present in the simple regime.",
  "old_simple_descriptor_regime": "hotspot list plus force-trace summary",
  "residual_content_added_by_new_regime": [
    "entropy/Gini concentration",
    "load-anchor index",
    "AIC-gated tensile descriptor"
  ],
  "richer_explanatory_mechanics_regime": "contact concentration plus tensile model-selection regime",
  "transported_preserved_artifacts": [
    "PDB/contact artifact",
    "force-extension trace",
    "hotspot positions"
  ]
}

## Mechanics Claim

7T10 supports a contact-localized tensile mechanics interpretation: a small hotspot set concentrates structural anchoring while the force trace passes a linear tensile-response gate with measurable stiffness, work, and peak force.

## Limitations

The force trace is a single imported computational surrogate, not a measured ensemble or validated atomistic uncertainty estimate.
