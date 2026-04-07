---
name: scientific-report-pdf
description: Generate a structured scientific PDF report from a JSON description. Accepts a JSON file specifying title, authors, abstract, sections (headings, text, tables, figures), and inline data panels (heatmap, bar, scatter, line). Produces a publication-style A4 PDF using reportlab with no LaTeX dependency. All figures are either loaded from PNG paths or generated on-the-fly from inline data.
metadata:
    domain: visualization
    dependencies: reportlab, matplotlib, pillow
---

# scientific-report-pdf

Generates a structured scientific PDF report from a JSON input file. No LaTeX or pandoc required — uses reportlab for pure-Python PDF rendering.

## Usage

```bash
python3 skills/scientific-report-pdf/scripts/scientific_report_pdf.py --input-json report.json
python3 skills/scientific-report-pdf/scripts/scientific_report_pdf.py --input-json report.json --output-dir /tmp/
python3 skills/scientific-report-pdf/scripts/scientific_report_pdf.py --describe-schema
```

## Input JSON Structure

```json
{
  "title": "The Sound of Molecules",
  "authors": ["ReportAgent", "MusicAnalyst"],
  "subtitle": "CS1 Investigation | LAMM Research Platform",
  "abstract": "We present ...",
  "sections": [
    {"type": "heading", "level": 1, "text": "1. Introduction"},
    {"type": "text", "text": "Sonification has been applied to ..."},
    {
      "type": "table",
      "label": "Table 1",
      "caption": "RDKit descriptors for 16 compounds.",
      "headers": ["Compound", "MW", "LogP"],
      "rows": [["aspirin", "180.2", "1.19"], ["ibuprofen", "206.3", "3.72"]]
    },
    {
      "type": "figure",
      "label": "Figure 1",
      "caption": "Era-match heatmap.",
      "path": "/path/to/era_match.png"
    },
    {
      "type": "panel",
      "label": "Figure 2",
      "caption": "Mean similarity by drug class.",
      "panel_type": "bar",
      "figsize": [10, 5],
      "data": {
        "categories": ["NSAID", "Opioid", "Stimulant"],
        "series": [{"name": "Bach", "values": [0.4, 0.7, 0.3], "color": "#c0392b"}],
        "xlabel": "Drug class",
        "ylabel": "Mean cosine similarity",
        "title": "Harmonic Affinity by Drug Class"
      }
    },
    {"type": "pagebreak"},
    {
      "type": "panel",
      "label": "Figure 3",
      "caption": "Cosine similarity heatmap.",
      "panel_type": "heatmap",
      "data": {
        "values": [[0.8, 0.3], [0.2, 0.9]],
        "row_labels": ["aspirin", "fentanyl"],
        "col_labels": ["Bach", "Beethoven"],
        "cmap": "YlOrRd",
        "annotate": true
      }
    }
  ],
  "metadata": {
    "investigation_id": "cs1_sound_of_molecules",
    "platform": "LAMM Infinite",
    "agents": ["SoundAgent1", "MusicAnalyst", "ReportAgent"]
  }
}
```

## Section Types

| type | Required fields | Description |
|------|----------------|-------------|
| `heading` | `level` (1-3), `text` | Section heading |
| `text` | `text` | Paragraph body |
| `table` | `headers`, `rows` | Data table with optional `label`, `caption`, `highlight_col` |
| `figure` | `path` | Embed existing PNG/JPG |
| `panel` | `panel_type`, `data` | Auto-generate matplotlib figure |
| `pagebreak` | — | Force page break |
| `hr` | — | Horizontal rule |

## Panel Types

| panel_type | Required data fields |
|-----------|---------------------|
| `heatmap` | `values` (2D array), `row_labels`, `col_labels` |
| `matrix` | same as heatmap |
| `bar` | `categories`, `series` (list of `{name, values, color}`) |
| `grouped_bar` | same as bar |
| `scatter` | `x`, `y` |
| `line` | `x`, `y` |

## Output

```json
{
  "pdf_path": "/tmp/The_Sound_of_Molecules_20260403_001234.pdf",
  "n_pages": 8,
  "n_figures": 4,
  "size_kb": 512
}
```

## Dependencies

- `reportlab` — PDF generation
- `matplotlib` — auto-generated panel figures
- `pillow` — RGBA→RGB image conversion
- `pypdf` (optional) — page count in output
