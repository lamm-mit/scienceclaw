# Mechanics Discovery Synthesis

The four runs now move from isolated descriptors to explicit computational mechanics explanations: contact-supported tensile response, anisotropic network stiffness, graph-mediated load routing, and curvature-dependent membrane energy.

## 7T10 structure-contact tensile mechanics

- Report: `7t10_formal_extension/presentable_results/DISCOVERY_REPORT.md`
- Evidence label: `imported_computational_surrogate, imported_real_structure`
- Accepted model: `linear force-extension model`
- Rejected model: `mean-force null model`
- Claim: 7T10 supports a contact-localized tensile mechanics interpretation: a small hotspot set concentrates structural anchoring while the force trace passes a linear tensile-response gate with measurable stiffness, work, and peak force.

## Fiber-network anisotropic mechanics

- Report: `biomechanics_fiber_network/presentable_results/DISCOVERY_REPORT.md`
- Evidence label: `synthetic_computational`
- Accepted model: `orientation-tensor anisotropic stiffness surrogate`
- Rejected model: `isotropic fiber-count descriptor`
- Claim: The fiber-network run supports an anisotropic mechanics claim: orientation eigenstructure defines a dominant load-bearing axis while the stress-strain surrogate supplies the tensile stiffness scale.

## Mechanobiology force-path mechanics

- Report: `mechanobiology_force_paths/presentable_results/DISCOVERY_REPORT.md`
- Evidence label: `synthetic_computational`
- Accepted model: `full force-path regression`
- Rejected model: `adhesion-only traction model`
- Claim: The mechanobiology run supports a graph-mediated load-routing claim: traction is best explained as a force-path property combining adhesion, cytoskeletal coupling, displacement, and path length, not as adhesion alone.

## Membrane curvature-energy mechanics

- Report: `membrane_biophysics/presentable_results/DISCOVERY_REPORT.md`
- Evidence label: `synthetic_computational`
- Accepted model: `Helfrich-style curvature-energy proxy`
- Rejected model: `curvature-only shape descriptor`
- Claim: The membrane run supports a curvature-energy mechanics claim: the synthetic curvature field has localized bending-energy structure whose total magnitude is controlled by the assigned bending modulus.
