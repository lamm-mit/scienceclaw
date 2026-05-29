# Figure Results

This report links every publication-style figure to the mechanics result, model gate, input files, and scientific interpretation it visualizes.

- Figure agent: `ScienceClaw scientific-visualization/matplotlib figure agent`
- Output directory: `run_exports/formal_mechanics_runs/figures`

## FIG1: 7T10 contact-localized tensile mechanics

- PNG: `fig1_7t10_discovery_mechanics.png`
- SVG: `fig1_7t10_discovery_mechanics.svg`
- PDF: `fig1_7t10_discovery_mechanics.pdf`
- Mechanical conclusion: 7T10 supports a contact-localized tensile mechanics interpretation: a small hotspot set concentrates structural anchoring while the force trace passes a linear tensile-response gate with measurable stiffness, work, and peak force.
- Evidence labeling: Imported structure/surrogate evidence and synthetic computational evidence are labeled by result origin; synthetic inputs are not biological measurements.
- Publication significance: Figure emphasizes accepted model, rejected alternative, gate or stress test, and mechanics claim.

**Mechanics results visualized:**

- 7T10 peptide-receptor contact hotspot mechanics anchor
- 7T10 coarse-grained force-extension descriptor
- linear force-extension model

**Input provenance:**

- `/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/7T10.pdb`
- `/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/force_extension_7T10.csv`
- `/home/fiona/LAMM/scienceclaw_category_interface/examples/actual_runs/structure_contact_7T10/force_extension_7T10.json`
- `run_exports/formal_mechanics_runs/7t10_formal_extension/presentable_results/MECHANICS_INVESTIGATION.json`

## FIG2: Fiber-network anisotropic mechanics

- PNG: `fig2_fiber_network_discovery_mechanics.png`
- SVG: `fig2_fiber_network_discovery_mechanics.svg`
- PDF: `fig2_fiber_network_discovery_mechanics.pdf`
- Mechanical conclusion: The fiber-network run supports an anisotropic mechanics claim: orientation eigenstructure defines a dominant load-bearing axis while the stress-strain surrogate supplies the tensile stiffness scale.
- Evidence labeling: Imported structure/surrogate evidence and synthetic computational evidence are labeled by result origin; synthetic inputs are not biological measurements.
- Publication significance: Figure emphasizes accepted model, rejected alternative, gate or stress test, and mechanics claim.

**Mechanics results visualized:**

- Synthetic fiber-network anisotropy and stiffness computation
- orientation-tensor anisotropic stiffness surrogate

**Input provenance:**

- `run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/computational_inputs/fiber_network_synthetic.csv`
- `run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/computational_inputs/fiber_stress_strain_synthetic.csv`
- `run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/MECHANICS_INVESTIGATION.json`

## FIG3: Mechanobiology graph-mediated load routing

- PNG: `fig3_mechanobiology_discovery_mechanics.png`
- SVG: `fig3_mechanobiology_discovery_mechanics.svg`
- PDF: `fig3_mechanobiology_discovery_mechanics.pdf`
- Mechanical conclusion: The mechanobiology run supports a graph-mediated load-routing claim: traction is best explained as a force-path property combining adhesion, cytoskeletal coupling, displacement, and path length, not as adhesion alone.
- Evidence labeling: Imported structure/surrogate evidence and synthetic computational evidence are labeled by result origin; synthetic inputs are not biological measurements.
- Publication significance: Figure emphasizes accepted model, rejected alternative, gate or stress test, and mechanics claim.

**Mechanics results visualized:**

- Synthetic mechanobiology force-path load score computation
- full force-path regression

**Input provenance:**

- `run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/computational_inputs/force_paths_synthetic.csv`
- `run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/computational_inputs/adhesion_cytoskeleton_graph_synthetic.json`
- `run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/MECHANICS_INVESTIGATION.json`

## FIG4: Membrane curvature-energy regime transition

- PNG: `fig4_membrane_discovery_mechanics.png`
- SVG: `fig4_membrane_discovery_mechanics.svg`
- PDF: `fig4_membrane_discovery_mechanics.pdf`
- Mechanical conclusion: The membrane run supports a curvature-energy mechanics claim: the synthetic curvature field has localized bending-energy structure whose total magnitude is controlled by the assigned bending modulus.
- Evidence labeling: Imported structure/surrogate evidence and synthetic computational evidence are labeled by result origin; synthetic inputs are not biological measurements.
- Publication significance: Figure emphasizes accepted model, rejected alternative, gate or stress test, and mechanics claim.

**Mechanics results visualized:**

- Synthetic membrane curvature-energy computation
- Helfrich-style curvature-energy proxy

**Input provenance:**

- `run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/computational_inputs/membrane_curvature_field_synthetic.csv`
- `run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/computational_inputs/membrane_material_model.json`
- `run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/MECHANICS_INVESTIGATION.json`

## FIG5: Integrated four-run discovery significance summary

- PNG: `fig5_integrated_discovery_summary.png`
- SVG: `fig5_integrated_discovery_summary.svg`
- PDF: `fig5_integrated_discovery_summary.pdf`
- Mechanical conclusion: The four runs communicate mechanics significance through model gates, rejected alternatives, stress tests, and regime-transition claims rather than raw metrics alone.
- Evidence labeling: Imported structure/surrogate evidence and synthetic computational evidence are labeled by result origin; synthetic inputs are not biological measurements.
- Publication significance: Figure emphasizes accepted model, rejected alternative, gate or stress test, and mechanics claim.

**Mechanics results visualized:**

- linear force-extension model
- orientation-tensor anisotropic stiffness surrogate
- full force-path regression
- Helfrich-style curvature-energy proxy

**Input provenance:**

- `run_exports/formal_mechanics_runs/7t10_formal_extension/presentable_results/MECHANICS_INVESTIGATION.json`
- `run_exports/formal_mechanics_runs/biomechanics_fiber_network/presentable_results/MECHANICS_INVESTIGATION.json`
- `run_exports/formal_mechanics_runs/mechanobiology_force_paths/presentable_results/MECHANICS_INVESTIGATION.json`
- `run_exports/formal_mechanics_runs/membrane_biophysics/presentable_results/MECHANICS_INVESTIGATION.json`
