# Fiber-network anisotropic mechanics

Evidence label: `synthetic_computational`

## Scientific Hypothesis

The fiber network encodes anisotropic tensile mechanics through its orientation tensor rather than through an isotropic scalar fiber count.

## Typed Artifact Schema

- inputs: structured artifact payloads, computational input files, mechanics sidecar
- transforms: deterministic mechanics descriptor extraction, model comparison, stress test or ablation
- observables: computed mechanics values, diagnostics, formal descriptors
- models: simple descriptor, richer explanatory mechanics model
- diagnostics: AIC/BIC-style gate or ablation score, R^2/RSS where applicable, robustness check
- claims: mechanics-language interpretation with stated limits

## Specific Problem Scope

- Specific question: For the deterministic 12-fiber synthetic network, does an orientation-tensor anisotropic stiffness model explain the 11-point stress-strain table better than an isotropic scalar descriptor?
- System boundary: Synthetic computational fiber table with 12 fibers, orientations 12-93 degrees, length in um, branch degree 1-4, and uniaxial strain range 0.00-0.10.
- Candidate scope: isotropic fiber-count descriptor, orientation-tensor anisotropic stiffness surrogate
- Input scope: fiber_network_synthetic.csv, fiber_stress_strain_synthetic.csv, fiber_computational_model.json
- Observable scope: 2x2 orientation tensor, orientation eigenvalues/eigenvector, anisotropy ratio, linear stiffness kPa, AIC delta, perturbed order parameter
- Out of scope: real tissue segmentation, viscoelastic constitutive fitting, FEM boundary-value solution, biological calibration

## Mechanics Equations and Formal Descriptors

- Orientation tensor: A = <n tensor n>, n = (cos theta, sin theta).
- Nematic order: S = sqrt(<cos 2theta>^2 + <sin 2theta>^2).
- Stress-strain surrogate: sigma = E epsilon + sigma0.
- Anisotropy ratio: lambda_max(A) / lambda_min(A).

## Candidate Models and Gate

- **fiber_M0_isotropic_count_scalar** / **isotropic fiber-count descriptor**: `rejected`. It cannot represent dominant orientation or anisotropic stiffness direction. Formal type: `IsotropicScalarNetworkDescriptor`. Inputs: `fiber_network_synthetic.csv, fiber_stress_strain_synthetic.csv`.
- **fiber_M1_orientation_tensor_stiffness** / **orientation-tensor anisotropic stiffness surrogate**: `accepted`. It combines orientation eigenstructure with the stress-strain stiffness gate. Formal type: `SecondOrderOrientationTensorPlusLinearElasticSurrogate`. Inputs: `fiber_network_synthetic.csv, fiber_stress_strain_synthetic.csv, fiber_computational_model.json`.

Gate: `AIC model-selection gate`

{
  "accepted_model": "orientation-tensor anisotropic stiffness surrogate",
  "decision": "accepted",
  "decision_rule": "Accept the model with lower AIC; require positive improvement over the simpler descriptor.",
  "gate_type": "AIC model-selection gate",
  "rejected_model": "isotropic fiber-count descriptor",
  "scores": {
    "delta_rejected_minus_accepted": 123.873782,
    "isotropic fiber-count descriptor": 31.229352,
    "orientation-tensor anisotropic stiffness surrogate": -92.64443
  }
}

## Categorical Provenance Graph

- Graph file: `run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/categorical_discovery_graph.json`
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
  "anisotropy_ratio": 5.11836,
  "orientation_eigenvalues": [
    0.836558,
    0.163442
  ],
  "orientation_order_parameter": 0.673115,
  "orientation_tensor": [
    [
      0.466251,
      0.334861
    ],
    [
      0.334861,
      0.533749
    ]
  ],
  "principal_eigenvector": [
    0.670717,
    0.741713
  ],
  "stiffness_kpa": 119.4
}

## Rejected Alternatives

- **isotropic scalar stiffness only**: It fits stress but does not explain why the network has a dominant load-bearing direction.

## Stress Test or Ablation

{
  "baseline_order": 0.673115,
  "interpretation": "The order parameter remains nonzero under deterministic angle perturbation, so the anisotropic claim is not a single-angle artifact.",
  "name": "orientation perturbation stress test",
  "perturbed_order": 0.661231
}

## Regime-Transition Audit

{
  "audit_claim": "The richer regime preserves the old descriptor artifacts and adds explanatory mechanics content that was not present in the simple regime.",
  "old_simple_descriptor_regime": "fiber count and mean length descriptors",
  "residual_content_added_by_new_regime": [
    "tensor eigenstructure",
    "anisotropic stiffness surrogate",
    "perturbation robustness"
  ],
  "richer_explanatory_mechanics_regime": "orientation-tensor and anisotropic stiffness regime",
  "transported_preserved_artifacts": [
    "fiber geometry table",
    "stress-strain table",
    "synthetic_computational label"
  ]
}

## Mechanics Claim

The fiber-network run supports an anisotropic mechanics claim: orientation eigenstructure defines a dominant load-bearing axis while the stress-strain surrogate supplies the tensile stiffness scale.

## Limitations

The network and loading table are deterministic synthetic_computational inputs, so the result is a mechanics computation, not a biological measurement.
