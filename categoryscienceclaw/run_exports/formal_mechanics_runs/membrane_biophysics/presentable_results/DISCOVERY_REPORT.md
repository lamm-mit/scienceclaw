# Membrane curvature-energy mechanics

Evidence label: `synthetic_computational`

## Scientific Hypothesis

A membrane curvature field becomes mechanically interpretable only when transported into a curvature-energy regime with bending modulus dependence.

## Typed Artifact Schema

- inputs: structured artifact payloads, computational input files, mechanics sidecar
- transforms: deterministic mechanics descriptor extraction, model comparison, stress test or ablation
- observables: computed mechanics values, diagnostics, formal descriptors
- models: simple descriptor, richer explanatory mechanics model
- diagnostics: AIC/BIC-style gate or ablation score, R^2/RSS where applicable, robustness check
- claims: mechanics-language interpretation with stated limits

## Specific Problem Scope

- Specific question: For the deterministic 7x7 synthetic curvature field, does a Helfrich-style curvature-energy proxy add material mechanics beyond a curvature-only shape descriptor?
- System boundary: Synthetic computational membrane grid from -1.5 to 1.5 um in x/y, mean curvature in 1/um, bending modulus 20 kBT, tension metadata retained but not used in the quadratic proxy.
- Candidate scope: curvature-only shape descriptor, Helfrich-style curvature-energy proxy
- Input scope: membrane_curvature_field_synthetic.csv, membrane_material_model.json
- Observable scope: RMS curvature, max absolute curvature, quadratic energy proxy, top-10% energy localization, 0.5x/1x/2x bending-modulus sensitivity
- Out of scope: measured membrane surface reconstruction, spontaneous curvature fitting, thermal fluctuation spectrum, calibrated lipid composition

## Mechanics Equations and Formal Descriptors

- Helfrich-style proxy: e_i = 1/2 kappa H_i^2.
- Total grid energy: E = sum_i e_i.
- Energy localization: sum_top10%(e_i) / sum_i e_i.
- Bending-modulus sensitivity: E(alpha kappa) = alpha E(kappa).

## Candidate Models and Gate

- **membrane_M0_curvature_only_shape** / **curvature-only shape descriptor**: `rejected`. It reports geometry but has no material-energy scale. Formal type: `GeometryOnlyCurvatureDescriptor`. Inputs: `membrane_curvature_field_synthetic.csv`.
- **membrane_M1_helfrich_quadratic_energy_proxy** / **Helfrich-style curvature-energy proxy**: `accepted`. It converts geometry into material-dependent bending energy and localization. Formal type: `QuadraticCurvatureEnergyFunctional`. Inputs: `membrane_curvature_field_synthetic.csv, membrane_material_model.json`.

Gate: `explicit mechanics-regime criterion`

{
  "accepted_model": "Helfrich-style curvature-energy proxy",
  "decision": "accepted",
  "decision_rule": "Accept the model that maps curvature and bending modulus to energy with units and sensitivity diagnostics.",
  "gate_type": "explicit mechanics-regime criterion",
  "rejected_model": "curvature-only shape descriptor"
}

## Categorical Provenance Graph

- Graph file: `run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/categorical_discovery_graph.json`
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
  "bending_modulus_sensitivity": {
    "kappa_0.5x_total_kbt": 5.864303,
    "kappa_1x_total_kbt": 11.728606,
    "kappa_2x_total_kbt": 23.457212
  },
  "curvature_energy_localization_top10_fraction": 0.32692,
  "max_abs_curvature_1_um": 0.2948332,
  "mean_energy_density_proxy_kbt_per_um2": 0.23935931,
  "rms_curvature_1_um": 0.15471241,
  "total_grid_energy_proxy_kbt": 11.72860601
}

## Rejected Alternatives

- **topology-only or curvature-only membrane claim**: It cannot express bending-modulus sensitivity or energy localization.

## Stress Test or Ablation

{
  "interpretation": "Energy scales linearly with bending modulus, confirming that the accepted claim is an energy-regime claim rather than a geometry-only summary.",
  "name": "bending-modulus sensitivity",
  "result": {
    "kappa_0.5x_total_kbt": 5.864303,
    "kappa_1x_total_kbt": 11.728606,
    "kappa_2x_total_kbt": 23.457212
  }
}

## Regime-Transition Audit

{
  "audit_claim": "The richer regime preserves the old descriptor artifacts and adds explanatory mechanics content that was not present in the simple regime.",
  "old_simple_descriptor_regime": "curvature field descriptor",
  "residual_content_added_by_new_regime": [
    "energy map",
    "top-10% localization",
    "bending-modulus sensitivity"
  ],
  "richer_explanatory_mechanics_regime": "Helfrich-style curvature-energy mechanics regime",
  "transported_preserved_artifacts": [
    "curvature grid",
    "material model",
    "synthetic_computational label"
  ]
}

## Mechanics Claim

The membrane run supports a curvature-energy mechanics claim: the synthetic curvature field has localized bending-energy structure whose total magnitude is controlled by the assigned bending modulus.

## Limitations

The curvature field and material model are deterministic synthetic_computational inputs, not measured membrane geometry or calibrated biophysical parameters.
