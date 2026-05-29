import json
from pathlib import Path

from categoryscienceclaw.example_runs import run_examples_a_to_d
from categoryscienceclaw.figure_agent import generate_mechanics_figures


def test_mechanics_figure_agent_generates_presentable_figures(tmp_path):
    out_root = tmp_path / "runs"
    run_examples_a_to_d(out_root, cycles=30, complexity="high", use_scienceclaw=True)

    manifest = generate_mechanics_figures(out_root)
    figures_dir = out_root / "figures"

    assert len(manifest["figures"]) == 5
    assert (figures_dir / "FIGURE_LEGENDS.md").exists()
    assert (figures_dir / "FIGURE_RESULTS.md").exists()
    assert (figures_dir / "figure_manifest.json").exists()

    legends = (figures_dir / "FIGURE_LEGENDS.md").read_text(encoding="utf-8")
    results = (figures_dir / "FIGURE_RESULTS.md").read_text(encoding="utf-8")
    findings = (out_root / "ACTUAL_MECHANICS_FINDINGS.md").read_text(encoding="utf-8")
    assert "## Figures" in findings
    assert "figures/FIGURE_LEGENDS.md" in findings
    assert "figures/FIGURE_RESULTS.md" in findings

    lower_figure_text = (legends + "\n" + results).lower()
    assert "experimental" not in lower_figure_text
    assert "synthetic computational evidence" in lower_figure_text
    assert "mechanical conclusion" in lower_figure_text

    for figure in manifest["figures"]:
        assert figure["mechanical_conclusion"]
        assert figure["panels"]
        assert figure["input_files"]
        assert figure["result_names"]
        assert figure["evidence_labeling"]
        assert figure["publication_significance"]
        assert "accepted model" in figure["publication_significance"].lower()
        assert "rejected alternative" in figure["publication_significance"].lower()
        assert "mechanics claim" in figure["publication_significance"].lower()
        assert figure["title"] in legends
        assert figure["title"] in results
        for path in figure["input_files"]:
            input_path = Path(path)
            if not input_path.is_absolute():
                input_path = Path.cwd() / path
            assert input_path.exists()
        for fmt, path in figure["files"].items():
            assert fmt in {"png", "svg", "pdf"}
            output = Path(path)
            if not output.is_absolute():
                output = Path.cwd() / path
            assert output.exists()
            assert output.stat().st_size > 1000

    saved_manifest = json.loads((figures_dir / "figure_manifest.json").read_text(encoding="utf-8"))
    assert saved_manifest["figure_agent"] == "ScienceClaw scientific-visualization/matplotlib figure agent"
    titles = {figure["title"] for figure in saved_manifest["figures"]}
    assert "7T10 contact-localized tensile mechanics" in titles
    assert "Fiber-network anisotropic mechanics" in titles
    assert "Mechanobiology graph-mediated load routing" in titles
    assert "Membrane curvature-energy regime transition" in titles
    assert "Integrated four-run discovery significance summary" in titles
    assert "Publication significance" in legends
    assert "accepted model" in results.lower()
    assert "rejected alternative" in results.lower()
