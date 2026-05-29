"""ScienceClaw-style figure agent for mechanics investigation outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


RUNS = {
    "7t10_formal_extension": "7T10 structure-contact and force-extension mechanics",
    "biomechanics_fiber_network": "Fiber-network biomechanics",
    "mechanobiology_force_paths": "Mechanobiology force paths",
    "membrane_biophysics": "Membrane curvature biophysics",
}


PALETTE = {
    "imported_real_structure": "#2563eb",
    "imported_computational_surrogate": "#0891b2",
    "synthetic_computational": "#7c3aed",
    "fit": "#111827",
    "highlight": "#dc2626",
    "muted": "#64748b",
}


def generate_mechanics_figures(root_dir: str | Path) -> dict[str, Any]:
    root = Path(root_dir)
    figures_dir = root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    investigations = {
        run: _load_investigation(root, run)
        for run in RUNS
    }
    manifest: dict[str, Any] = {
        "figure_agent": "ScienceClaw scientific-visualization/matplotlib figure agent",
        "root_dir": str(root),
        "figures": [],
    }

    manifest["figures"].append(_plot_7t10(root, figures_dir, investigations["7t10_formal_extension"]))
    manifest["figures"].append(_plot_fiber(root, figures_dir, investigations["biomechanics_fiber_network"]))
    manifest["figures"].append(_plot_mechanobio(root, figures_dir, investigations["mechanobiology_force_paths"]))
    manifest["figures"].append(_plot_membrane(root, figures_dir, investigations["membrane_biophysics"]))
    manifest["figures"].append(_plot_integrated_summary(root, figures_dir, investigations))

    _write_legend_file(figures_dir, manifest)
    _write_results_report(figures_dir, manifest)
    _update_actual_findings(root, manifest)
    (figures_dir / "figure_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def _load_investigation(root: Path, run: str) -> dict[str, Any]:
    path = root / run / "presentable_results" / "MECHANICS_INVESTIGATION.json"
    investigation = json.loads(path.read_text(encoding="utf-8"))
    investigation["_sidecar_file"] = str(path)
    return investigation


def _result_by_name(investigation: dict[str, Any], name_part: str) -> dict[str, Any]:
    for result in investigation.get("quantitative_computational_mechanics_results", []):
        if name_part.lower() in result.get("name", "").lower():
            return result
    raise KeyError(f"missing result containing {name_part!r}")


def _save_figure(fig: plt.Figure, figures_dir: Path, stem: str) -> dict[str, str]:
    paths = {}
    for fmt in ("png", "svg", "pdf"):
        output = figures_dir / f"{stem}.{fmt}"
        fig.savefig(output, format=fmt, dpi=300, bbox_inches="tight", facecolor="white")
        paths[fmt] = str(output)
    plt.close(fig)
    return paths


def _common_style(ax: plt.Axes, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=11, fontweight="bold", loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, color="#e5e7eb", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _annotation(ax: plt.Axes, text: str, loc: tuple[float, float] = (0.02, 0.98)) -> None:
    ax.text(
        loc[0],
        loc[1],
        text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.5,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.94},
    )


def _plot_7t10(root: Path, figures_dir: Path, investigation: dict[str, Any]) -> dict[str, Any]:
    contact = _result_by_name(investigation, "contact hotspot")
    force = _result_by_name(investigation, "force-extension")
    hotspots = contact["computed_values"]["binding_hotspots"]
    force_csv = _execution_input(investigation, "csv-read:force_extension_7T10.csv")
    force_df = pd.read_csv(force_csv)
    values = force["computed_values"]
    diagnostic = force["diagnostic"]

    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.4), constrained_layout=True)
    positions = [item["position"] for item in hotspots]
    contacts = [item["contacts"] for item in hotspots]
    axes[0].bar(positions, contacts, color=PALETTE["imported_real_structure"], alpha=0.9)
    axes[0].set_xticks(positions)
    _common_style(axes[0], "A. Contact hotspots define structural load anchors", "Peptide position", "Residue contacts")
    _annotation(
        axes[0],
        "Input: 7T10.pdb\nScienceClaw: structure-contact-analysis\nConclusion: top-contact residues mark plausible load-transfer anchors.",
    )

    x = force_df["extension_nm"].to_numpy()
    y = force_df["force_pN"].to_numpy()
    slope = values["linear_force_extension_slope_pN_per_nm"]
    intercept = values["linear_force_extension_intercept_pN"]
    axes[1].plot(x, y, color=PALETTE["imported_computational_surrogate"], marker="o", label="force-extension trace")
    axes[1].plot(x, intercept + slope * x, color=PALETTE["fit"], linestyle="--", label="linear fit")
    axes[1].scatter([values["peak_extension_nm"]], [values["peak_force_pN"]], color=PALETTE["highlight"], zorder=5, label="peak force")
    _common_style(axes[1], "B. Coarse tensile response", "Extension (nm)", "Force (pN)")
    axes[1].legend(frameon=False, fontsize=8)
    _annotation(
        axes[1],
        f"Slope: {slope:.3f} pN/nm\nPeak: {values['peak_force_pN']:.2f} pN\nR2: {diagnostic['linear_fit_r_squared']:.3f}",
    )

    fig.suptitle("7T10 mechanics: contact topology plus tensile force-extension response", fontsize=13, fontweight="bold")
    files = _save_figure(fig, figures_dir, "fig1_7t10_contact_force_extension")
    return _figure_entry(
        figure_id="fig1",
        title="7T10 contact and force-extension mechanics",
        files=files,
        panels=[
            "Contact hotspot bar plot for peptide residues with highest local contacts.",
            "Force-extension curve with fitted slope, peak force, and fit diagnostic.",
        ],
        input_files=[contact["input_file"], force_csv, force["input_file"], investigation["_sidecar_file"]],
        result_names=[contact["name"], force["name"]],
        conclusion="7T10 has a contact-defined mechanical anchoring motif and a coarse computational tensile response with positive fitted stiffness.",
    )


def _plot_fiber(root: Path, figures_dir: Path, investigation: dict[str, Any]) -> dict[str, Any]:
    result = _result_by_name(investigation, "fiber-network")
    input_dir = root / "biomechanics_fiber_network" / "presentable_results" / "computational_inputs"
    network_csv = input_dir / "fiber_network_synthetic.csv"
    stress_csv = input_dir / "fiber_stress_strain_synthetic.csv"
    fibers = pd.read_csv(network_csv)
    stress = pd.read_csv(stress_csv)
    values = result["computed_values"]
    diagnostic = result["diagnostic"]

    fig = plt.figure(figsize=(11.6, 4.4), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.25])
    ax0 = fig.add_subplot(gs[0, 0], projection="polar")
    theta = np.deg2rad(fibers["orientation_deg"].to_numpy())
    lengths = fibers["length_um"].to_numpy()
    ax0.scatter(theta, lengths, s=55, color=PALETTE["synthetic_computational"], alpha=0.85)
    principal = np.deg2rad(values["principal_orientation_deg"])
    ax0.plot([principal, principal], [0, max(lengths) * 1.08], color=PALETTE["highlight"], linewidth=2.5)
    ax0.set_title("A. Fiber orientation field", fontsize=11, fontweight="bold", loc="left")
    ax0.set_theta_zero_location("E")
    ax0.set_theta_direction(-1)
    ax0.text(
        0.02,
        0.06,
        f"Order S={values['orientation_order_parameter']:.3f}\nDominant axis={values['principal_orientation_deg']:.1f} deg",
        transform=ax0.transAxes,
        fontsize=8.5,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cbd5e1"},
    )

    ax1 = fig.add_subplot(gs[0, 1])
    x = stress["strain"].to_numpy()
    y = stress["stress_kpa"].to_numpy()
    slope = values["linear_stiffness_kpa"]
    intercept = values["stress_intercept_kpa"]
    ax1.scatter(x, y, color=PALETTE["synthetic_computational"], label="synthetic stress-strain")
    ax1.plot(x, intercept + slope * x, color=PALETTE["fit"], linestyle="--", label="linear fit")
    _common_style(ax1, "B. Network tensile stiffness", "Strain (dimensionless)", "Stress (kPa)")
    ax1.legend(frameon=False, fontsize=8)
    _annotation(
        ax1,
        f"Stiffness: {slope:.1f} kPa\nR2: {diagnostic['linear_fit_r_squared']:.5f}\nConclusion: anisotropic network with linear tensile response.",
    )
    fig.suptitle("Fiber-network biomechanics: anisotropy constrains tensile stiffness", fontsize=13, fontweight="bold")
    files = _save_figure(fig, figures_dir, "fig2_fiber_network_anisotropy_stiffness")
    return _figure_entry(
        figure_id="fig2",
        title="Fiber-network anisotropy and stiffness",
        files=files,
        panels=[
            "Polar fiber-orientation plot with dominant orientation axis.",
            "Stress-strain fit reporting linear stiffness and fit diagnostic.",
        ],
        input_files=[str(network_csv), str(stress_csv), investigation["_sidecar_file"]],
        result_names=[result["name"]],
        conclusion="The computational fiber network is directionally organized and supports an anisotropic mechanics interpretation with a fitted tensile stiffness near 119 kPa.",
    )


def _plot_mechanobio(root: Path, figures_dir: Path, investigation: dict[str, Any]) -> dict[str, Any]:
    result = _result_by_name(investigation, "force-path")
    input_dir = root / "mechanobiology_force_paths" / "presentable_results" / "computational_inputs"
    table_csv = input_dir / "force_paths_synthetic.csv"
    graph_json = input_dir / "adhesion_cytoskeleton_graph_synthetic.json"
    table = pd.read_csv(table_csv)
    graph_data = json.loads(graph_json.read_text(encoding="utf-8"))
    values = result["computed_values"]
    diagnostic = result["diagnostic"]
    table["load_path_score"] = table["traction_pa"] / table["path_length_um"]

    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.4), constrained_layout=True)
    colors = [PALETTE["highlight"] if int(pid) == values["max_traction_path_id"] else PALETTE["synthetic_computational"] for pid in table["path_id"]]
    axes[0].bar(table["path_id"], table["load_path_score"], color=colors, alpha=0.9)
    _common_style(axes[0], "A. Load-path score ranking", "Path id", "Traction / path length (Pa/um)")
    _annotation(axes[0], f"Strongest path: {values['max_traction_path_id']}\nMean score: {values['mean_load_path_score_pa_per_um']:.3f} Pa/um")

    x = table["adhesion_score"].to_numpy()
    y = table["traction_pa"].to_numpy()
    slope = values["adhesion_traction_slope_pa_per_score"]
    intercept = values["adhesion_traction_intercept_pa"]
    axes[1].scatter(x, y, color=PALETTE["synthetic_computational"], label="force-path records")
    axes[1].plot(x, intercept + slope * x, color=PALETTE["fit"], linestyle="--", label="linear fit")
    _common_style(axes[1], "B. Adhesion-to-traction association", "Adhesion score", "Traction proxy (Pa)")
    axes[1].legend(frameon=False, fontsize=8)
    _annotation(axes[1], f"Slope: {slope:.2f} Pa/score\nR2: {diagnostic['linear_fit_r_squared']:.3f}")

    graph = nx.Graph()
    for node in graph_data["nodes"]:
        graph.add_node(node["id"])
    for edge in graph_data["edges"]:
        graph.add_edge(edge["source"], edge["target"])
    pos = {f"path_{int(row.path_id)}": (row.path_id, 0.15 * np.sin(row.path_id)) for row in table.itertuples()}
    node_values = {f"path_{int(row.path_id)}": row.traction_pa for row in table.itertuples()}
    nx.draw_networkx_edges(graph, pos, ax=axes[2], edge_color="#94a3b8", width=1.4)
    nodes = nx.draw_networkx_nodes(
        graph,
        pos,
        ax=axes[2],
        node_color=[node_values[node] for node in graph.nodes],
        cmap="viridis",
        node_size=[90 + node_values[node] * 3 for node in graph.nodes],
        edgecolors="#111827",
        linewidths=0.6,
    )
    nx.draw_networkx_labels(graph, pos, ax=axes[2], labels={node: node.split("_")[1] for node in graph.nodes}, font_size=7)
    axes[2].set_title("C. Cytoskeleton/adhesion path graph", fontsize=11, fontweight="bold", loc="left")
    axes[2].axis("off")
    cbar = fig.colorbar(nodes, ax=axes[2], shrink=0.75)
    cbar.set_label("Traction proxy (Pa)")
    _annotation(axes[2], "Node color and size encode traction proxy.\nConclusion: load concentrates on path 12.", (0.0, 0.96))

    fig.suptitle("Mechanobiology force paths: load ranking and adhesion-cytoskeleton routing", fontsize=13, fontweight="bold")
    files = _save_figure(fig, figures_dir, "fig3_mechanobiology_force_paths")
    return _figure_entry(
        figure_id="fig3",
        title="Mechanobiology force-path ranking",
        files=files,
        panels=[
            "Load-path score ranking highlights the strongest path.",
            "Adhesion-vs-traction fit reports association strength and R2.",
            "Graph-style visualization shows path topology and traction-proxy concentration.",
        ],
        input_files=[str(table_csv), str(graph_json), investigation["_sidecar_file"]],
        result_names=[result["name"]],
        conclusion="The computational force-path field concentrates load on path 12, and adhesion alone is an incomplete predictor of traction-proxy load.",
    )


def _plot_membrane(root: Path, figures_dir: Path, investigation: dict[str, Any]) -> dict[str, Any]:
    result = _result_by_name(investigation, "membrane")
    input_dir = root / "membrane_biophysics" / "presentable_results" / "computational_inputs"
    curvature_csv = input_dir / "membrane_curvature_field_synthetic.csv"
    material_json = input_dir / "membrane_material_model.json"
    table = pd.read_csv(curvature_csv)
    material = json.loads(material_json.read_text(encoding="utf-8"))
    kappa = float(material["bending_modulus_kbt"])
    table["energy_proxy"] = 0.5 * kappa * table["mean_curvature_1_um"] ** 2
    values = result["computed_values"]

    curv = table.pivot(index="y_um", columns="x_um", values="mean_curvature_1_um").sort_index(ascending=False)
    energy = table.pivot(index="y_um", columns="x_um", values="energy_proxy").sort_index(ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.6), constrained_layout=True)
    im0 = axes[0].imshow(curv, cmap="coolwarm", extent=[curv.columns.min(), curv.columns.max(), curv.index.min(), curv.index.max()], aspect="equal")
    axes[0].set_title("A. Membrane curvature field", fontsize=11, fontweight="bold", loc="left")
    axes[0].set_xlabel("x (um)")
    axes[0].set_ylabel("y (um)")
    c0 = fig.colorbar(im0, ax=axes[0], shrink=0.82)
    c0.set_label("Mean curvature (1/um)")
    _annotation(axes[0], f"RMS curvature: {values['rms_curvature_1_um']:.4f} 1/um")

    im1 = axes[1].imshow(energy, cmap="magma", extent=[energy.columns.min(), energy.columns.max(), energy.index.min(), energy.index.max()], aspect="equal")
    axes[1].set_title("B. Quadratic bending-energy proxy", fontsize=11, fontweight="bold", loc="left")
    axes[1].set_xlabel("x (um)")
    axes[1].set_ylabel("y (um)")
    c1 = fig.colorbar(im1, ax=axes[1], shrink=0.82)
    c1.set_label("Energy proxy (kBT/um^2)")
    _annotation(axes[1], f"kappa: {kappa:.1f} kBT\nTotal proxy: {values['total_grid_energy_proxy_kbt']:.2f} kBT")

    fig.suptitle("Membrane biophysics: curvature field translated into bending-energy summary", fontsize=13, fontweight="bold")
    files = _save_figure(fig, figures_dir, "fig4_membrane_curvature_energy")
    return _figure_entry(
        figure_id="fig4",
        title="Membrane curvature-energy mechanics",
        files=files,
        panels=[
            "Curvature heatmap shows the geometry field used for mechanics computation.",
            "Energy proxy heatmap maps curvature into a quadratic bending-energy summary.",
        ],
        input_files=[str(curvature_csv), str(material_json), investigation["_sidecar_file"]],
        result_names=[result["name"]],
        conclusion="The membrane run supports a curvature-energy mechanics interpretation with a quantified RMS curvature and total energy proxy.",
    )


def _plot_integrated_summary(root: Path, figures_dir: Path, investigations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.2), constrained_layout=True)

    force = _result_by_name(investigations["7t10_formal_extension"], "force-extension")
    force_csv = _execution_input(investigations["7t10_formal_extension"], "csv-read:force_extension_7T10.csv")
    force_df = pd.read_csv(force_csv)
    axes[0, 0].plot(force_df["extension_nm"], force_df["force_pN"], color=PALETTE["imported_computational_surrogate"], marker="o", markersize=3)
    _common_style(axes[0, 0], "A. 7T10 tensile response", "Extension (nm)", "Force (pN)")
    _annotation(axes[0, 0], f"Peak {force['computed_values']['peak_force_pN']:.1f} pN\nSlope {force['computed_values']['linear_force_extension_slope_pN_per_nm']:.1f} pN/nm")

    fiber = _result_by_name(investigations["biomechanics_fiber_network"], "fiber-network")
    stress_csv = root / "biomechanics_fiber_network" / "presentable_results" / "computational_inputs" / "fiber_stress_strain_synthetic.csv"
    stress = pd.read_csv(stress_csv)
    axes[0, 1].plot(stress["strain"], stress["stress_kpa"], color=PALETTE["synthetic_computational"], marker="o")
    _common_style(axes[0, 1], "B. Fiber-network stiffness", "Strain", "Stress (kPa)")
    _annotation(axes[0, 1], f"S={fiber['computed_values']['orientation_order_parameter']:.3f}\nStiffness {fiber['computed_values']['linear_stiffness_kpa']:.1f} kPa")

    mechanobio = _result_by_name(investigations["mechanobiology_force_paths"], "force-path")
    path_csv = root / "mechanobiology_force_paths" / "presentable_results" / "computational_inputs" / "force_paths_synthetic.csv"
    paths = pd.read_csv(path_csv)
    scores = paths["traction_pa"] / paths["path_length_um"]
    axes[1, 0].bar(paths["path_id"], scores, color=PALETTE["synthetic_computational"])
    _common_style(axes[1, 0], "C. Force-path load ranking", "Path id", "Load-path score (Pa/um)")
    _annotation(axes[1, 0], f"Max path {mechanobio['computed_values']['max_traction_path_id']}\nMean {mechanobio['computed_values']['mean_load_path_score_pa_per_um']:.2f} Pa/um")

    membrane = _result_by_name(investigations["membrane_biophysics"], "membrane")
    curvature_csv = root / "membrane_biophysics" / "presentable_results" / "computational_inputs" / "membrane_curvature_field_synthetic.csv"
    curv_table = pd.read_csv(curvature_csv)
    curv = curv_table.pivot(index="y_um", columns="x_um", values="mean_curvature_1_um").sort_index(ascending=False)
    im = axes[1, 1].imshow(curv, cmap="coolwarm", extent=[curv.columns.min(), curv.columns.max(), curv.index.min(), curv.index.max()])
    axes[1, 1].set_title("D. Membrane curvature mechanics", fontsize=11, fontweight="bold", loc="left")
    axes[1, 1].set_xlabel("x (um)")
    axes[1, 1].set_ylabel("y (um)")
    fig.colorbar(im, ax=axes[1, 1], shrink=0.75, label="Mean curvature (1/um)")
    _annotation(axes[1, 1], f"RMS {membrane['computed_values']['rms_curvature_1_um']:.3f} 1/um\nEnergy proxy {membrane['computed_values']['total_grid_energy_proxy_kbt']:.2f} kBT")

    fig.suptitle("Four-run computational mechanics summary", fontsize=14, fontweight="bold")
    files = _save_figure(fig, figures_dir, "fig5_integrated_four_run_summary")
    return _figure_entry(
        figure_id="fig5",
        title="Integrated four-run mechanics summary",
        files=files,
        panels=[
            "7T10 force-extension mechanics.",
            "Fiber stress-strain mechanics.",
            "Mechanobiology force-path score mechanics.",
            "Membrane curvature mechanics.",
        ],
        input_files=[
            force_csv,
            str(stress_csv),
            str(path_csv),
            str(curvature_csv),
            investigations["7t10_formal_extension"]["_sidecar_file"],
            investigations["biomechanics_fiber_network"]["_sidecar_file"],
            investigations["mechanobiology_force_paths"]["_sidecar_file"],
            investigations["membrane_biophysics"]["_sidecar_file"],
        ],
        result_names=[
            force["name"],
            fiber["name"],
            mechanobio["name"],
            membrane["name"],
        ],
        conclusion="The four investigations now present a coherent computational mechanics panel: contact-mediated tensile response, anisotropic network stiffness, force-path load routing, and membrane curvature-energy mechanics.",
    )


def _execution_input(investigation: dict[str, Any], execution_id: str) -> str:
    for execution in investigation.get("scienceclaw_skill_executions", []):
        if execution.get("execution_id") == execution_id:
            return execution["input_file"]
    raise KeyError(f"missing execution {execution_id}")


def _figure_entry(
    *,
    figure_id: str,
    title: str,
    files: dict[str, str],
    panels: list[str],
    input_files: list[str],
    result_names: list[str],
    conclusion: str,
) -> dict[str, Any]:
    return {
        "figure_id": figure_id,
        "title": title,
        "files": files,
        "panels": panels,
        "input_files": input_files,
        "result_names": result_names,
        "mechanical_conclusion": conclusion,
        "evidence_labeling": "imported, computational surrogate, and synthetic computational evidence are labeled by result origin; synthetic inputs are not biological measurements.",
    }


def _write_legend_file(figures_dir: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# Mechanics Figure Legends",
        "",
        "All panels are generated from `MECHANICS_INVESTIGATION.json` sidecars and the recorded computational input files. Synthetic computational inputs are labeled as synthetic computational evidence and are not biological measurements.",
        "",
    ]
    for fig in manifest["figures"]:
        lines += [
            f"## {fig['figure_id'].upper()}. {fig['title']}",
            "",
            f"**Files:** `{Path(fig['files']['png']).name}`, `{Path(fig['files']['svg']).name}`, `{Path(fig['files']['pdf']).name}`",
            "",
            "**Panels:**",
            "",
        ]
        lines += [f"- {panel}" for panel in fig["panels"]]
        lines += [
            "",
            f"**Mechanical conclusion:** {fig['mechanical_conclusion']}",
            "",
            "**Input files:**",
            "",
        ]
        lines += [f"- `{path}`" for path in fig["input_files"]]
        lines.append("")
    (figures_dir / "FIGURE_LEGENDS.md").write_text("\n".join(lines), encoding="utf-8")


def _write_results_report(figures_dir: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# Figure Results",
        "",
        "This report links every presentation figure to its mechanics result, input files, method context, and scientific interpretation.",
        "",
        f"- Figure agent: `{manifest['figure_agent']}`",
        f"- Output directory: `{figures_dir}`",
        "",
    ]
    for fig in manifest["figures"]:
        lines += [
            f"## {fig['figure_id'].upper()}: {fig['title']}",
            "",
            f"- PNG: `{Path(fig['files']['png']).name}`",
            f"- SVG: `{Path(fig['files']['svg']).name}`",
            f"- PDF: `{Path(fig['files']['pdf']).name}`",
            f"- Mechanical conclusion: {fig['mechanical_conclusion']}",
            f"- Evidence labeling: {fig['evidence_labeling']}",
            "",
            "**Mechanics results visualized:**",
            "",
        ]
        lines += [f"- {name}" for name in fig["result_names"]]
        lines += ["", "**Input provenance:**", ""]
        lines += [f"- `{path}`" for path in fig["input_files"]]
        lines.append("")
    (figures_dir / "FIGURE_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


def _update_actual_findings(root: Path, manifest: dict[str, Any]) -> None:
    path = root / "ACTUAL_MECHANICS_FINDINGS.md"
    text = path.read_text(encoding="utf-8")
    if "\n## Figures\n" in text:
        text = text.split("\n## Figures\n", 1)[0].rstrip() + "\n"
    lines = [text.rstrip(), "", "## Figures", ""]
    lines.append("Presentation-ready mechanics figures are available under `figures/`.")
    lines.append("")
    for fig in manifest["figures"]:
        lines.append(f"- **{fig['title']}**: `figures/{Path(fig['files']['png']).name}`")
        lines.append(f"  - Conclusion: {fig['mechanical_conclusion']}")
    lines += [
        "",
        "- Figure legends: `figures/FIGURE_LEGENDS.md`",
        "- Figure provenance report: `figures/FIGURE_RESULTS.md`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# Publication-grade discovery figures. These later definitions override the compact
# plotting helpers above so the generated figures visualize the discovery layer.
def _discovery(investigation: dict[str, Any]) -> dict[str, Any]:
    return investigation.get("discovery_report", {})


def _gate_scores(discovery: dict[str, Any]) -> tuple[str, str, float, float, str]:
    gate = discovery.get("model_selection_gate", {})
    accepted = gate.get("accepted_model", "accepted model")
    rejected = gate.get("rejected_model", "rejected model")
    scores = gate.get("scores", {})
    score_name = "BIC" if "bic" in gate.get("gate_type", "").lower() else "AIC"
    if "explicit" in gate.get("gate_type", "").lower():
        score_name = "criterion"
    accepted_score = float(scores.get(accepted, 0.0)) if scores else 0.0
    rejected_score = float(scores.get(rejected, accepted_score)) if scores else accepted_score
    return accepted, rejected, accepted_score, rejected_score, score_name


def _wrap_claim(text: str, width: int = 58) -> str:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        if sum(len(w) + 1 for w in current) + len(word) > width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines[:8])


def _model_gate_panel(ax: plt.Axes, discovery: dict[str, Any], title: str) -> None:
    accepted, rejected, accepted_score, rejected_score, score_name = _gate_scores(discovery)
    ax.set_title(title, fontsize=11, fontweight="bold", loc="left")
    if score_name == "criterion":
        ax.axis("off")
        ax.text(0.02, 0.96, "Accepted mechanics regime\n" + accepted + "\n\nRejected descriptor\n" + rejected,
                transform=ax.transAxes, va="top", fontsize=9,
                bbox={"boxstyle": "round,pad=0.45", "facecolor": "white", "edgecolor": "#cbd5e1"})
        return
    ax.bar(["accepted", "rejected"], [accepted_score, rejected_score], color=["#059669", "#b91c1c"], alpha=0.86)
    ax.set_ylabel(score_name)
    ax.grid(True, axis="y", color="#e5e7eb")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    _annotation(ax, f"Lower is better\nDelta={rejected_score - accepted_score:.2f}\nAccepted: {accepted[:32]}")


def _claim_panel(ax: plt.Axes, discovery: dict[str, Any], letter: str) -> None:
    ax.axis("off")
    residual = discovery.get("regime_transition_audit", {}).get("residual_content_added_by_new_regime", [])
    stress = discovery.get("stress_test_or_ablation", {})
    text = (f"Mechanics claim\n{_wrap_claim(discovery.get('scientific_claim', ''))}\n\n"
            f"Stress test: {stress.get('name', 'recorded')}\n"
            f"New regime adds: {', '.join(residual[:3])}")
    ax.text(0.02, 0.96, text, transform=ax.transAxes, va="top", fontsize=9, linespacing=1.28,
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "#f8fafc", "edgecolor": "#cbd5e1"})
    ax.set_title(f"{letter}. Scientific interpretation", fontsize=11, fontweight="bold", loc="left")


def _plot_7t10(root: Path, figures_dir: Path, investigation: dict[str, Any]) -> dict[str, Any]:
    discovery = _discovery(investigation)
    contact = _result_by_name(investigation, "contact hotspot")
    force = _result_by_name(investigation, "force-extension")
    hotspots = contact["computed_values"]["binding_hotspots"]
    force_csv = _execution_input(investigation, "csv-read:force_extension_7T10.csv")
    force_df = pd.read_csv(force_csv)
    values = force["computed_values"]
    diagnostic = force["diagnostic"]
    deeper = discovery.get("deeper_analysis", {})
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 8.4), constrained_layout=True)
    positions = [item["position"] for item in hotspots]
    contacts = [item["contacts"] for item in hotspots]
    axes[0, 0].bar(positions, contacts, color="#1d4ed8", alpha=0.9)
    axes[0, 0].set_xticks(positions)
    _common_style(axes[0, 0], "A. Contact concentration defines load-anchor residues", "Peptide position", "Residue contacts")
    _annotation(axes[0, 0], f"Entropy={deeper.get('contact_entropy_nats', 0):.3f} nats\nGini={deeper.get('contact_gini', 0):.3f}\nAnchor index={deeper.get('hotspot_load_anchor_index', 0):.2f}")
    x = force_df["extension_nm"].to_numpy()
    y = force_df["force_pN"].to_numpy()
    slope = values["linear_force_extension_slope_pN_per_nm"]
    intercept = values["linear_force_extension_intercept_pN"]
    axes[0, 1].plot(x, y, color="#0891b2", marker="o", label="trace", linewidth=2)
    axes[0, 1].plot(x, intercept + slope * x, color="#111827", linestyle="--", label="accepted linear model")
    axes[0, 1].axhline(y.mean(), color="#b91c1c", linestyle=":", label="rejected mean-force model")
    axes[0, 1].scatter([values["peak_extension_nm"]], [values["peak_force_pN"]], color="#dc2626", zorder=5, s=70)
    _common_style(axes[0, 1], "B. Tensile response with accepted/rejected models", "Extension (nm)", "Force (pN)")
    axes[0, 1].legend(frameon=False, fontsize=8)
    _annotation(axes[0, 1], f"k={slope:.1f} pN/nm\nPeak={values['peak_force_pN']:.1f} pN\nWork={values['pulling_work_pN_nm']:.1f} pN nm\nR2={diagnostic['linear_fit_r_squared']:.3f}")
    _model_gate_panel(axes[1, 0], discovery, "C. AIC gate rejects extension-free descriptor")
    _claim_panel(axes[1, 1], discovery, "D")
    fig.suptitle("7T10 discovery figure: contact-localized tensile mechanics", fontsize=14, fontweight="bold")
    files = _save_figure(fig, figures_dir, "fig1_7t10_discovery_mechanics")
    return _figure_entry("fig1", "7T10 contact-localized tensile mechanics", files,
        ["Contact hotspot concentration with entropy, Gini, and load-anchor index.", "Force-extension trace comparing accepted linear tensile model against rejected mean-force descriptor.", "AIC gate showing why extension-dependent tensile response is retained.", "Mechanics claim, stress-test meaning, and regime-transition residual content."],
        [contact["input_file"], force_csv, force["input_file"], investigation["_sidecar_file"]],
        [contact["name"], force["name"], discovery.get("model_selection_gate", {}).get("accepted_model", "discovery gate")],
        discovery.get("scientific_claim", "7T10 supports contact-localized tensile mechanics."))


def _plot_fiber(root: Path, figures_dir: Path, investigation: dict[str, Any]) -> dict[str, Any]:
    discovery = _discovery(investigation)
    result = _result_by_name(investigation, "fiber-network")
    input_dir = root / "biomechanics_fiber_network" / "presentable_results" / "computational_inputs"
    network_csv = input_dir / "fiber_network_synthetic.csv"
    stress_csv = input_dir / "fiber_stress_strain_synthetic.csv"
    fibers = pd.read_csv(network_csv)
    stress = pd.read_csv(stress_csv)
    deeper = discovery.get("deeper_analysis", {})
    stress_test = discovery.get("stress_test_or_ablation", {})
    fig = plt.figure(figsize=(13.0, 8.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    ax0 = fig.add_subplot(gs[0, 0], projection="polar")
    theta = np.deg2rad(fibers["orientation_deg"].to_numpy())
    lengths = fibers["length_um"].to_numpy()
    ax0.scatter(theta, lengths, s=60, color="#7c3aed", alpha=0.85)
    tensor = np.array(deeper.get("orientation_tensor", [[0.5, 0.0], [0.0, 0.5]]))
    eigvals, eigvecs = np.linalg.eigh(tensor)
    principal = eigvecs[:, np.argmax(eigvals)]
    principal_angle = np.arctan2(principal[1], principal[0])
    ax0.plot([principal_angle, principal_angle], [0, max(lengths) * 1.08], color="#dc2626", linewidth=2.8)
    ax0.set_title("A. Orientation tensor identifies load-bearing axis", fontsize=11, fontweight="bold", loc="left")
    ax0.set_theta_zero_location("E")
    ax0.set_theta_direction(-1)
    ax0.text(0.02, 0.06, f"S={deeper.get('orientation_order_parameter', 0):.3f}\nAnisotropy={deeper.get('anisotropy_ratio', 0):.2f}x", transform=ax0.transAxes, fontsize=8.5, bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cbd5e1"})
    ax1 = fig.add_subplot(gs[0, 1])
    x = stress["strain"].to_numpy(); y = stress["stress_kpa"].to_numpy()
    slope = result["computed_values"]["linear_stiffness_kpa"]; intercept = result["computed_values"]["stress_intercept_kpa"]
    ax1.scatter(x, y, color="#7c3aed", label="synthetic computational loading")
    ax1.plot(x, intercept + slope * x, color="#111827", linestyle="--", label="anisotropic stiffness surrogate")
    ax1.axhline(y.mean(), color="#b91c1c", linestyle=":", label="isotropic scalar descriptor")
    _common_style(ax1, "B. Stress-strain model retains stiffness scale", "Strain", "Stress (kPa)")
    ax1.legend(frameon=False, fontsize=8)
    _annotation(ax1, f"E={slope:.1f} kPa\nR2={result['diagnostic']['linear_fit_r_squared']:.5f}")
    _model_gate_panel(fig.add_subplot(gs[1, 0]), discovery, "C. Gate favors anisotropic mechanics over isotropic summary")
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.bar(["baseline", "perturbed"], [stress_test.get("baseline_order", 0), stress_test.get("perturbed_order", 0)], color=["#7c3aed", "#0f766e"])
    _common_style(ax3, "D. Orientation perturbation stress test", "Condition", "Order parameter S")
    _annotation(ax3, _wrap_claim(discovery.get("scientific_claim", ""), 44), (0.36, 0.96))
    fig.suptitle("Fiber-network discovery figure: anisotropic stiffness emerges from orientation structure", fontsize=14, fontweight="bold")
    files = _save_figure(fig, figures_dir, "fig2_fiber_network_discovery_mechanics")
    return _figure_entry("fig2", "Fiber-network anisotropic mechanics", files,
        ["Orientation tensor and eigenstructure.", "Stress-strain accepted model compared with isotropic descriptor.", "AIC model gate.", "Perturbation stress test and mechanics claim."],
        [str(network_csv), str(stress_csv), investigation["_sidecar_file"]], [result["name"], discovery.get("model_selection_gate", {}).get("accepted_model", "discovery gate")], discovery.get("scientific_claim", "Fiber network supports anisotropic mechanics."))


def _plot_mechanobio(root: Path, figures_dir: Path, investigation: dict[str, Any]) -> dict[str, Any]:
    discovery = _discovery(investigation)
    result = _result_by_name(investigation, "force-path")
    input_dir = root / "mechanobiology_force_paths" / "presentable_results" / "computational_inputs"
    table_csv = input_dir / "force_paths_synthetic.csv"; graph_json = input_dir / "adhesion_cytoskeleton_graph_synthetic.json"
    table = pd.read_csv(table_csv)
    graph_data = json.loads(graph_json.read_text(encoding="utf-8"))
    table["load_path_score"] = table["traction_pa"] / table["path_length_um"]
    deeper = discovery.get("deeper_analysis", {}); stress_test = discovery.get("stress_test_or_ablation", {})
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 8.4), constrained_layout=True)
    strongest = int(deeper.get("strongest_path_id", result["computed_values"]["max_traction_path_id"]))
    colors = ["#dc2626" if int(pid) == strongest else "#7c3aed" for pid in table["path_id"]]
    axes[0, 0].bar(table["path_id"], table["load_path_score"], color=colors, alpha=0.9)
    _common_style(axes[0, 0], "A. Load-path ranking exposes dominant route", "Path id", "Traction / path length (Pa/um)")
    _annotation(axes[0, 0], f"Strongest path={strongest}\nLoad concentration={deeper.get('load_concentration', 0):.3f}")
    x = table["adhesion_score"].to_numpy(); y = table["traction_pa"].to_numpy()
    slope = result["computed_values"]["adhesion_traction_slope_pa_per_score"]; intercept = result["computed_values"]["adhesion_traction_intercept_pa"]
    axes[0, 1].scatter(x, y, color="#7c3aed", label="path records")
    axes[0, 1].plot(x, intercept + slope * x, color="#b91c1c", linestyle=":", label="adhesion-only ablation")
    full = discovery.get("candidate_models", [{}, {}])[1].get("diagnostics", {})
    _common_style(axes[0, 1], "B. Adhesion-only ablation is not enough", "Adhesion score", "Traction proxy (Pa)")
    axes[0, 1].legend(frameon=False, fontsize=8)
    _annotation(axes[0, 1], f"Adhesion R2={result['diagnostic']['linear_fit_r_squared']:.3f}\nFull model R2={full.get('r_squared', 0):.3f}")
    graph = nx.Graph()
    for node in graph_data["nodes"]: graph.add_node(node["id"])
    for edge in graph_data["edges"]: graph.add_edge(edge["source"], edge["target"])
    pos = {f"path_{int(row.path_id)}": (row.path_id, 0.25 * np.sin(row.path_id)) for row in table.itertuples()}
    node_values = {f"path_{int(row.path_id)}": row.traction_pa for row in table.itertuples()}
    nx.draw_networkx_edges(graph, pos, ax=axes[1, 0], edge_color="#94a3b8", width=1.4)
    nodes = nx.draw_networkx_nodes(graph, pos, ax=axes[1, 0], node_color=[node_values[node] for node in graph.nodes], cmap="viridis", node_size=[95 + node_values[node] * 3 for node in graph.nodes], edgecolors="#111827", linewidths=0.6)
    nx.draw_networkx_labels(graph, pos, ax=axes[1, 0], labels={node: node.split("_")[1] for node in graph.nodes}, font_size=7)
    axes[1, 0].axis("off"); axes[1, 0].set_title("C. Graph routing localizes force-path significance", fontsize=11, fontweight="bold", loc="left")
    fig.colorbar(nodes, ax=axes[1, 0], shrink=0.75, label="Traction proxy (Pa)")
    axes[1, 1].bar(["all paths", "remove strongest"], [stress_test.get("baseline_mean_load_score_pa_per_um", 0), stress_test.get("after_removing_strongest_mean_load_score_pa_per_um", 0)], color=["#7c3aed", "#0f766e"])
    _common_style(axes[1, 1], "D. Strongest-path robustness", "Condition", "Mean load-path score (Pa/um)")
    _annotation(axes[1, 1], _wrap_claim(discovery.get("scientific_claim", ""), 45), (0.24, 0.96))
    fig.suptitle("Mechanobiology discovery figure: graph-conditioned force-path load routing", fontsize=14, fontweight="bold")
    files = _save_figure(fig, figures_dir, "fig3_mechanobiology_discovery_mechanics")
    return _figure_entry("fig3", "Mechanobiology graph-mediated load routing", files,
        ["Load-path ranking and load concentration.", "Full force-path model motivation versus adhesion-only ablation.", "Graph visualization of traction-proxy routing.", "Strongest-path removal stress test."],
        [str(table_csv), str(graph_json), investigation["_sidecar_file"]], [result["name"], discovery.get("model_selection_gate", {}).get("accepted_model", "discovery gate")], discovery.get("scientific_claim", "Mechanobiology run supports force-path load routing."))


def _plot_membrane(root: Path, figures_dir: Path, investigation: dict[str, Any]) -> dict[str, Any]:
    discovery = _discovery(investigation)
    result = _result_by_name(investigation, "membrane")
    input_dir = root / "membrane_biophysics" / "presentable_results" / "computational_inputs"
    curvature_csv = input_dir / "membrane_curvature_field_synthetic.csv"; material_json = input_dir / "membrane_material_model.json"
    table = pd.read_csv(curvature_csv)
    material = json.loads(material_json.read_text(encoding="utf-8")); kappa = float(material["bending_modulus_kbt"])
    table["energy_proxy"] = 0.5 * kappa * table["mean_curvature_1_um"] ** 2
    curv = table.pivot(index="y_um", columns="x_um", values="mean_curvature_1_um").sort_index(ascending=False)
    energy = table.pivot(index="y_um", columns="x_um", values="energy_proxy").sort_index(ascending=False)
    deeper = discovery.get("deeper_analysis", {})
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 8.6), constrained_layout=True)
    im0 = axes[0, 0].imshow(curv, cmap="coolwarm", extent=[curv.columns.min(), curv.columns.max(), curv.index.min(), curv.index.max()], aspect="equal")
    axes[0, 0].set_title("A. Curvature field supplies geometry", fontsize=11, fontweight="bold", loc="left"); axes[0, 0].set_xlabel("x (um)"); axes[0, 0].set_ylabel("y (um)")
    fig.colorbar(im0, ax=axes[0, 0], shrink=0.78, label="Mean curvature (1/um)")
    _annotation(axes[0, 0], f"RMS={deeper.get('rms_curvature_1_um', 0):.4f} 1/um")
    im1 = axes[0, 1].imshow(energy, cmap="magma", extent=[energy.columns.min(), energy.columns.max(), energy.index.min(), energy.index.max()], aspect="equal")
    axes[0, 1].set_title("B. Helfrich-style energy map adds mechanics", fontsize=11, fontweight="bold", loc="left"); axes[0, 1].set_xlabel("x (um)"); axes[0, 1].set_ylabel("y (um)")
    fig.colorbar(im1, ax=axes[0, 1], shrink=0.78, label="Energy proxy (kBT/um^2)")
    _annotation(axes[0, 1], f"Top 10% localization={deeper.get('curvature_energy_localization_top10_fraction', 0):.3f}\nTotal={deeper.get('total_grid_energy_proxy_kbt', 0):.2f} kBT")
    sensitivity = deeper.get("bending_modulus_sensitivity", {})
    axes[1, 0].plot([0.5, 1.0, 2.0], [sensitivity.get("kappa_0.5x_total_kbt", 0), sensitivity.get("kappa_1x_total_kbt", 0), sensitivity.get("kappa_2x_total_kbt", 0)], color="#7c3aed", marker="o", linewidth=2)
    _common_style(axes[1, 0], "C. Bending-modulus sensitivity", "kappa multiplier", "Total energy proxy (kBT)")
    _annotation(axes[1, 0], "Energy scales with material modulus\nso the accepted claim is not geometry-only.")
    _claim_panel(axes[1, 1], discovery, "D")
    fig.suptitle("Membrane discovery figure: curvature becomes significant through bending energy", fontsize=14, fontweight="bold")
    files = _save_figure(fig, figures_dir, "fig4_membrane_discovery_mechanics")
    return _figure_entry("fig4", "Membrane curvature-energy regime transition", files,
        ["Curvature field geometry.", "Helfrich-style energy map and localization.", "Bending-modulus sensitivity stress test.", "Mechanics claim and regime-transition interpretation."],
        [str(curvature_csv), str(material_json), investigation["_sidecar_file"]], [result["name"], discovery.get("model_selection_gate", {}).get("accepted_model", "discovery gate")], discovery.get("scientific_claim", "Membrane run supports curvature-energy mechanics."))


def _plot_integrated_summary(root: Path, figures_dir: Path, investigations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.0), constrained_layout=True)
    for ax, run_name, letter in zip(axes.flat, RUNS, ["A", "B", "C", "D"]):
        discovery = _discovery(investigations[run_name])
        accepted, rejected, accepted_score, rejected_score, score_name = _gate_scores(discovery)
        ax.axis("off")
        deeper = discovery.get("deeper_analysis", {})
        highlights = []
        for key, value in deeper.items():
            if isinstance(value, (int, float)):
                highlights.append(f"{key}: {value:.3g}")
        txt = (f"{letter}. {discovery.get('title', RUNS[run_name])}\n\nAccepted: {accepted}\nRejected: {rejected}\nGate: {score_name}; improvement={rejected_score - accepted_score:.2f}\n\n" + "\n".join(highlights[:3]) + "\n\nClaim: " + _wrap_claim(discovery.get("scientific_claim", ""), 48))
        ax.text(0.02, 0.98, txt, transform=ax.transAxes, va="top", fontsize=9, linespacing=1.25, bbox={"boxstyle": "round,pad=0.55", "facecolor": "white", "edgecolor": "#cbd5e1"})
        ax.set_title(discovery.get("title", run_name), fontsize=11, fontweight="bold", loc="left")
    fig.suptitle("Integrated mechanics discovery summary: four regime-enlarged computational claims", fontsize=14, fontweight="bold")
    files = _save_figure(fig, figures_dir, "fig5_integrated_discovery_summary")
    return _figure_entry("fig5", "Integrated four-run discovery significance summary", files,
        ["7T10 accepted/rejected tensile mechanics claim.", "Fiber anisotropic model significance.", "Mechanobiology graph-load-routing significance.", "Membrane curvature-energy regime significance."],
        [investigations[run]["_sidecar_file"] for run in RUNS],
        [_discovery(investigations[run]).get("model_selection_gate", {}).get("accepted_model", "accepted model") for run in RUNS],
        "The four runs communicate mechanics significance through model gates, rejected alternatives, stress tests, and regime-transition claims rather than raw metrics alone.")


def _figure_entry(figure_id: str, title: str, files: dict[str, str], panels: list[str], input_files: list[str], result_names: list[str], conclusion: str) -> dict[str, Any]:
    return {"figure_id": figure_id, "title": title, "files": files, "panels": panels, "input_files": input_files, "result_names": result_names, "mechanical_conclusion": conclusion, "evidence_labeling": "Imported structure/surrogate evidence and synthetic computational evidence are labeled by result origin; synthetic inputs are not biological measurements.", "publication_significance": "Figure emphasizes accepted model, rejected alternative, gate or stress test, and mechanics claim."}


def _write_legend_file(figures_dir: Path, manifest: dict[str, Any]) -> None:
    lines = ["# Mechanics Figure Legends", "", "These publication-oriented figures are generated from `MECHANICS_INVESTIGATION.json`, `discovery_report` sidecars, and recorded computational input files. Synthetic computational inputs are labeled as synthetic computational evidence and are not biological measurements.", ""]
    for fig in manifest["figures"]:
        lines += [f"## {fig['figure_id'].upper()}. {fig['title']}", "", f"**Files:** `{Path(fig['files']['png']).name}`, `{Path(fig['files']['svg']).name}`, `{Path(fig['files']['pdf']).name}`", "", f"**Publication significance:** {fig.get('publication_significance', '')}", "", "**Panels:**", ""]
        lines += [f"- {panel}" for panel in fig["panels"]]
        lines += ["", f"**Mechanical conclusion:** {fig['mechanical_conclusion']}", "", "**Input files:**", ""]
        lines += [f"- `{path}`" for path in fig["input_files"]]
        lines.append("")
    (figures_dir / "FIGURE_LEGENDS.md").write_text("\n".join(lines), encoding="utf-8")


def _write_results_report(figures_dir: Path, manifest: dict[str, Any]) -> None:
    lines = ["# Figure Results", "", "This report links every publication-style figure to the mechanics result, model gate, input files, and scientific interpretation it visualizes.", "", f"- Figure agent: `{manifest['figure_agent']}`", f"- Output directory: `{figures_dir}`", ""]
    for fig in manifest["figures"]:
        lines += [f"## {fig['figure_id'].upper()}: {fig['title']}", "", f"- PNG: `{Path(fig['files']['png']).name}`", f"- SVG: `{Path(fig['files']['svg']).name}`", f"- PDF: `{Path(fig['files']['pdf']).name}`", f"- Mechanical conclusion: {fig['mechanical_conclusion']}", f"- Evidence labeling: {fig['evidence_labeling']}", f"- Publication significance: {fig.get('publication_significance', '')}", "", "**Mechanics results visualized:**", ""]
        lines += [f"- {name}" for name in fig["result_names"]]
        lines += ["", "**Input provenance:**", ""]
        lines += [f"- `{path}`" for path in fig["input_files"]]
        lines.append("")
    (figures_dir / "FIGURE_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
