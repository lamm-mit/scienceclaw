# Actual Mechanics Investigation Findings

> Act like a mechanics investigator, not a generic data analyzer.

This file is the presentation-level answer from the four mechanics investigations. It separates quantitative computational mechanics supported by available inputs from formal-only results and additional computational input needs.

## Example A: 7T10 formal descriptor extension

**Question.** Which contact-supported peptide positions and coarse-grained force-extension features support a mechanics interpretation of PDB 7T10?

**Quantitative computational mechanics findings:**

- 7T10 peptide-receptor contact hotspot mechanics anchor
  - Evidence class: `structural_computational`
  - Input origin: `imported_real_structure`
  - Method: ScienceClaw structure-contact-analysis on local 7T10 PDB file
  - Input: `/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/7T10.pdb`
  - Hotspot positions: `[8, 9, 6, 7, 1, 11]`
  - Scientific meaning: The contact graph identifies a localized mechanical anchoring motif on the peptide: positions 8, 9, 6, 7, 1, and 11 carry the largest contact counts under the cutoff and are therefore the residues most plausibly coupled to load transfer in this structural model.
  - Limitation: Contact counts identify structural anchoring positions under a 4.5 angstrom cutoff; they do not assign residue-resolved force without a validated mechanics model.

- 7T10 coarse-grained force-extension descriptor
  - Evidence class: `computational_surrogate`
  - Input origin: `imported_computational_surrogate`
  - Method: ScienceClaw csv-read on force_extension_7T10.csv plus deterministic force-extension extraction from ScienceClaw-generated JSON
  - Input: `/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/force_extension_7T10.json`
  - Peak force: `766.98959` pN at `2.4` nm
  - Linear force-extension slope: `253.068938` pN/nm
  - Linear fit R^2: `0.942723`
  - Scientific meaning: The monotonic force-extension trace and positive linear slope provide a coarse-grained tensile mechanics descriptor for the 7T10 model: the imported surrogate behaves as a load-bearing extension response with a high peak force, but not as a replicated measured or atomistic stiffness estimate.
  - Limitation: Single coarse-grained OpenMM surrogate trace; no replicate simulation ensemble, confidence interval, or atomistic validation is present.

**Formal/symbolic result classes:**

formal_artifact_record, formal_claim_synthesis, formal_validation_record, symbolic_mechanics_expression, symbolic_parity_descriptor, typed_provenance_graph

**Additional computational input needs:**

- None.

## Example B: fiber-network biomechanics

**Question.** Can image-derived fiber geometry and boundary conditions support quantitative anisotropy or network-mechanics estimates?

**Quantitative computational mechanics findings:**

- Synthetic fiber-network anisotropy and stiffness computation
  - Evidence class: `synthetic_computational`
  - Input origin: `synthetic_computational`
  - Method: ScienceClaw csv-read on generated computational CSVs plus deterministic fiber-orientation tensor and statsmodels linear stress-strain fit
  - Input: `run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/computational_inputs/fiber_network_synthetic.csv`
  - Fiber orientation order: `0.673115`; principal orientation `47.877581` deg; linear stiffness `119.4` kPa
  - Linear fit R^2: `0.999989`
  - Scientific meaning: The synthetic network is strongly directionally organized rather than isotropic, and the stress-strain table gives a high-confidence linear stiffness for that computational loading protocol. Mechanically, this supports an anisotropic fiber-network interpretation with a dominant orientation near 48 degrees and a tensile stiffness scale of about 119 kPa.
  - Limitation: Deterministic synthetic computational network and stress-strain table; useful for pipeline mechanics computation, not a biological measurement.

**Formal/symbolic result classes:**

formal_claim_synthesis, formal_validation_record, symbolic_mechanics_expression, symbolic_parity_descriptor, typed_provenance_graph

**Additional computational input needs:**

- None.

## Example C: membrane curvature biophysics

**Question.** Can membrane geometry, curvature measurements, and material parameters support quantitative energy or shape-transition estimates?

**Quantitative computational mechanics findings:**

- Synthetic membrane curvature-energy computation
  - Evidence class: `synthetic_computational`
  - Input origin: `synthetic_computational`
  - Method: ScienceClaw csv-read on generated computational curvature CSV plus deterministic Helfrich-style quadratic curvature-energy summary
  - Input: `run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/computational_inputs/membrane_curvature_field_synthetic.csv`
  - RMS curvature: `0.15471241` 1/um; mean energy proxy `0.23935931` kBT/um^2; total grid energy proxy `11.72860601` kBT
  - Scientific meaning: The curvature field yields a compact bending-energy summary for the membrane model: the RMS curvature and total quadratic energy proxy quantify how far the synthetic patch departs from flat geometry under the assigned bending modulus. Mechanically, the result supports a curvature-energy interpretation rather than a topology-only membrane descriptor.
  - Limitation: Deterministic synthetic computational curvature field and material model; useful for energy-pipeline computation, not a measured membrane shape.

**Formal/symbolic result classes:**

formal_artifact_record, formal_claim_synthesis, formal_validation_record, symbolic_mechanics_expression, symbolic_parity_descriptor, typed_provenance_graph

**Additional computational input needs:**

- None.

## Example D: mechanobiology force paths

**Question.** Can cell geometry, adhesion maps, and traction/cytoskeleton measurements support quantitative force-path inference?

**Quantitative computational mechanics findings:**

- Synthetic mechanobiology force-path load score computation
  - Evidence class: `synthetic_computational`
  - Input origin: `synthetic_computational`
  - Method: ScienceClaw csv-read on generated computational CSV plus deterministic force-path scoring and statsmodels traction-vs-adhesion fit
  - Input: `run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/computational_inputs/force_paths_synthetic.csv`
  - Mean load-path score: `4.421814` Pa/um; max traction `72.886` Pa on path `12`
  - Linear fit R^2: `0.398862`
  - Scientific meaning: The synthetic force-path computation converts adhesion, cytoskeletal score, displacement, and path length into a traction-proxy load-path ranking. The strongest path is path 12, while the moderate adhesion-traction fit shows that adhesion alone does not explain the load distribution in this computational graph.
  - Limitation: Deterministic synthetic computational force-path field; useful for testing quantitative mechanobiology logic, not a measured cell traction map.

**Formal/symbolic result classes:**

formal_claim_synthesis, formal_validation_record, symbolic_mechanics_expression, symbolic_parity_descriptor, typed_provenance_graph

**Additional computational input needs:**

- None.

## Figures

Presentation-ready mechanics figures are available under `figures/`.

- **7T10 contact-localized tensile mechanics**: `figures/fig1_7t10_discovery_mechanics.png`
  - Conclusion: 7T10 supports a contact-localized tensile mechanics interpretation: a small hotspot set concentrates structural anchoring while the force trace passes a linear tensile-response gate with measurable stiffness, work, and peak force.
- **Fiber-network anisotropic mechanics**: `figures/fig2_fiber_network_discovery_mechanics.png`
  - Conclusion: The fiber-network run supports an anisotropic mechanics claim: orientation eigenstructure defines a dominant load-bearing axis while the stress-strain surrogate supplies the tensile stiffness scale.
- **Mechanobiology graph-mediated load routing**: `figures/fig3_mechanobiology_discovery_mechanics.png`
  - Conclusion: The mechanobiology run supports a graph-mediated load-routing claim: traction is best explained as a force-path property combining adhesion, cytoskeletal coupling, displacement, and path length, not as adhesion alone.
- **Membrane curvature-energy regime transition**: `figures/fig4_membrane_discovery_mechanics.png`
  - Conclusion: The membrane run supports a curvature-energy mechanics claim: the synthetic curvature field has localized bending-energy structure whose total magnitude is controlled by the assigned bending modulus.
- **Integrated four-run discovery significance summary**: `figures/fig5_integrated_discovery_summary.png`
  - Conclusion: The four runs communicate mechanics significance through model gates, rejected alternatives, stress tests, and regime-transition claims rather than raw metrics alone.

- Figure legends: `figures/FIGURE_LEGENDS.md`
- Figure provenance report: `figures/FIGURE_RESULTS.md`
