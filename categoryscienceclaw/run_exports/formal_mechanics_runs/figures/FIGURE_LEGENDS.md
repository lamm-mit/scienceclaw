# Mechanics Figure Legends

These publication-oriented figures are generated from `MECHANICS_INVESTIGATION.json`, `discovery_report` sidecars, and recorded computational input files. Synthetic computational inputs are labeled as synthetic computational evidence and are not biological measurements.

## FIG1. 7T10 contact-localized tensile mechanics

**Files:** `fig1_7t10_discovery_mechanics.png`, `fig1_7t10_discovery_mechanics.svg`, `fig1_7t10_discovery_mechanics.pdf`

**Publication significance:** Figure emphasizes accepted model, rejected alternative, gate or stress test, and mechanics claim.

**Panels:**

- Contact hotspot concentration with entropy, Gini, and load-anchor index.
- Force-extension trace comparing accepted linear tensile model against rejected mean-force descriptor.
- AIC gate showing why extension-dependent tensile response is retained.
- Mechanics claim, stress-test meaning, and regime-transition residual content.

**Mechanical conclusion:** 7T10 supports a contact-localized tensile mechanics interpretation: a small hotspot set concentrates structural anchoring while the force trace passes a linear tensile-response gate with measurable stiffness, work, and peak force.

**Input files:**

- `/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/7T10.pdb`
- `/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/force_extension_7T10.csv`
- `/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/force_extension_7T10.json`
- `run_exports/formal_mechanics_runs/7t10_formal_extension/presentable_results/MECHANICS_INVESTIGATION.json`

## FIG2. Fiber-network anisotropic mechanics

**Files:** `fig2_fiber_network_discovery_mechanics.png`, `fig2_fiber_network_discovery_mechanics.svg`, `fig2_fiber_network_discovery_mechanics.pdf`

**Publication significance:** Figure emphasizes accepted model, rejected alternative, gate or stress test, and mechanics claim.

**Panels:**

- Orientation tensor and eigenstructure.
- Stress-strain accepted model compared with isotropic descriptor.
- AIC model gate.
- Perturbation stress test and mechanics claim.

**Mechanical conclusion:** The fiber-network run supports an anisotropic mechanics claim: orientation eigenstructure defines a dominant load-bearing axis while the stress-strain surrogate supplies the tensile stiffness scale.

**Input files:**

- `run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/computational_inputs/fiber_network_synthetic.csv`
- `run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/computational_inputs/fiber_stress_strain_synthetic.csv`
- `run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/MECHANICS_INVESTIGATION.json`

## FIG3. Mechanobiology graph-mediated load routing

**Files:** `fig3_mechanobiology_discovery_mechanics.png`, `fig3_mechanobiology_discovery_mechanics.svg`, `fig3_mechanobiology_discovery_mechanics.pdf`

**Publication significance:** Figure emphasizes accepted model, rejected alternative, gate or stress test, and mechanics claim.

**Panels:**

- Load-path ranking and load concentration.
- Full force-path model motivation versus adhesion-only ablation.
- Graph visualization of traction-proxy routing.
- Strongest-path removal stress test.

**Mechanical conclusion:** The mechanobiology run supports a graph-mediated load-routing claim: traction is best explained as a force-path property combining adhesion, cytoskeletal coupling, displacement, and path length, not as adhesion alone.

**Input files:**

- `run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/computational_inputs/force_paths_synthetic.csv`
- `run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/computational_inputs/adhesion_cytoskeleton_graph_synthetic.json`
- `run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/MECHANICS_INVESTIGATION.json`

## FIG4. Membrane curvature-energy regime transition

**Files:** `fig4_membrane_discovery_mechanics.png`, `fig4_membrane_discovery_mechanics.svg`, `fig4_membrane_discovery_mechanics.pdf`

**Publication significance:** Figure emphasizes accepted model, rejected alternative, gate or stress test, and mechanics claim.

**Panels:**

- Curvature field geometry.
- Helfrich-style energy map and localization.
- Bending-modulus sensitivity stress test.
- Mechanics claim and regime-transition interpretation.

**Mechanical conclusion:** The membrane run supports a curvature-energy mechanics claim: the synthetic curvature field has localized bending-energy structure whose total magnitude is controlled by the assigned bending modulus.

**Input files:**

- `run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/computational_inputs/membrane_curvature_field_synthetic.csv`
- `run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/computational_inputs/membrane_material_model.json`
- `run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/MECHANICS_INVESTIGATION.json`

## FIG5. Integrated four-run discovery significance summary

**Files:** `fig5_integrated_discovery_summary.png`, `fig5_integrated_discovery_summary.svg`, `fig5_integrated_discovery_summary.pdf`

**Publication significance:** Figure emphasizes accepted model, rejected alternative, gate or stress test, and mechanics claim.

**Panels:**

- 7T10 accepted/rejected tensile mechanics claim.
- Fiber anisotropic model significance.
- Mechanobiology graph-load-routing significance.
- Membrane curvature-energy regime significance.

**Mechanical conclusion:** The four runs communicate mechanics significance through model gates, rejected alternatives, stress tests, and regime-transition claims rather than raw metrics alone.

**Input files:**

- `run_exports/formal_mechanics_runs/7t10_formal_extension/presentable_results/MECHANICS_INVESTIGATION.json`
- `run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/MECHANICS_INVESTIGATION.json`
- `run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/MECHANICS_INVESTIGATION.json`
- `run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/MECHANICS_INVESTIGATION.json`
