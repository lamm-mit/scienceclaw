#!/usr/bin/env python3
"""
scientific-report-pdf skill: Generate a structured scientific PDF report from a JSON description.

Accepts a JSON file describing the report (title, authors, abstract, sections, tables, figures,
and inline data panels). Produces a publication-style PDF using reportlab. All figures are
either loaded from existing PNG paths or generated on-the-fly from inline data specifications.

Usage:
  python3 scientific_report_pdf.py --input-json report.json
  python3 scientific_report_pdf.py --input-json report.json --output-dir /tmp/
  python3 scientific_report_pdf.py --describe-schema
"""

import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    p = argparse.ArgumentParser(description="Generate scientific PDF from JSON description")
    p.add_argument("--input-json", required=False, help="Path to report JSON file")
    p.add_argument("--output-dir", default=".", help="Directory for the output PDF")
    p.add_argument("--output-filename", default="", help="Override output filename (default: auto-timestamped)")
    p.add_argument("--describe-schema", action="store_true", help="Print input JSON schema and exit")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = {
    "type": "object",
    "description": "Input specification for the scientific-report-pdf skill",
    "required": ["title"],
    "properties": {
        "title": {"type": "string", "description": "Paper title"},
        "authors": {"type": "array", "items": {"type": "string"}, "description": "Author names"},
        "subtitle": {"type": "string", "description": "Optional subtitle / affiliation line"},
        "abstract": {"type": "string", "description": "Abstract text (plain text, no markup)"},
        "sections": {
            "type": "array",
            "description": "Ordered list of content blocks",
            "items": {
                "type": "object",
                "required": ["type"],
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["heading", "text", "table", "figure", "panel", "pagebreak", "hr"],
                        "description": (
                            "heading: section/subsection heading; "
                            "text: paragraph body; "
                            "table: data table; "
                            "figure: embed a PNG file; "
                            "panel: generate a plot from inline data; "
                            "pagebreak: force a page break; "
                            "hr: horizontal rule"
                        ),
                    },
                    # heading fields
                    "level": {"type": "integer", "minimum": 1, "maximum": 3,
                              "description": "Heading level (1=H1, 2=H2, 3=H3)"},
                    "text": {"type": "string", "description": "Text content (for heading/text blocks)"},

                    # table fields
                    "label": {"type": "string", "description": "e.g. 'Table 1'"},
                    "caption": {"type": "string"},
                    "headers": {"type": "array", "items": {"type": "string"}},
                    "rows": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                    "highlight_col": {
                        "type": "integer",
                        "description": "0-indexed column to bold-highlight per row (e.g. argmax column)",
                    },

                    # figure fields
                    "path": {"type": "string", "description": "Absolute or relative path to PNG/JPG"},

                    # panel fields (auto-generate a matplotlib figure)
                    "panel_type": {
                        "type": "string",
                        "enum": ["heatmap", "bar", "grouped_bar", "scatter", "line", "matrix"],
                        "description": "Type of auto-generated plot",
                    },
                    "data": {
                        "type": "object",
                        "description": "Data payload for auto-generated panels (structure depends on panel_type)",
                        "properties": {
                            # heatmap / matrix
                            "values": {"type": "array", "description": "2D array of numbers (rows × cols)"},
                            "row_labels": {"type": "array", "items": {"type": "string"}},
                            "col_labels": {"type": "array", "items": {"type": "string"}},
                            "row_colors": {"type": "object", "description": "label → hex color for row tick coloring"},
                            "cmap": {"type": "string", "description": "matplotlib colormap name"},
                            "vmin": {"type": "number"},
                            "vmax": {"type": "number"},
                            "annotate": {"type": "boolean", "description": "Show cell values"},
                            # bar / grouped_bar
                            "categories": {"type": "array", "items": {"type": "string"}},
                            "series": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "values": {"type": "array", "items": {"type": "number"}},
                                        "color": {"type": "string"},
                                    },
                                },
                            },
                            # scatter / line
                            "x": {"type": "array", "items": {"type": "number"}},
                            "y": {"type": "array", "items": {"type": "number"}},
                            "point_labels": {"type": "array", "items": {"type": "string"}},
                            "point_colors": {"type": "array", "items": {"type": "string"}},
                            "point_sizes": {"type": "array", "items": {"type": "number"}},
                            # axis labels
                            "xlabel": {"type": "string"},
                            "ylabel": {"type": "string"},
                            "title": {"type": "string"},
                            "legend": {"type": "object", "description": "label → hex color"},
                            "legend_title": {"type": "string"},
                        },
                    },
                    "figsize": {
                        "type": "array", "items": {"type": "number"},
                        "description": "[width_inches, height_inches] for auto-generated panels",
                    },
                },
            },
        },
        "metadata": {
            "type": "object",
            "description": "Optional footer metadata",
            "properties": {
                "investigation_id": {"type": "string"},
                "platform": {"type": "string"},
                "agents": {"type": "array", "items": {"type": "string"}},
                "date": {"type": "string"},
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Panel (auto-figure) generators
# ---------------------------------------------------------------------------

def _panel_to_png(block: dict, tmp_dir: str) -> str:
    """Render a 'panel' block to a PNG file. Returns the path."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    panel_type = block.get("panel_type", "heatmap")
    data = block.get("data", {})
    figsize = block.get("figsize", None)

    fig, ax = plt.subplots(figsize=figsize or (9, 5))

    if panel_type in ("heatmap", "matrix"):
        values = np.array(data.get("values", [[0]]))
        row_labels = data.get("row_labels", [str(i) for i in range(values.shape[0])])
        col_labels = data.get("col_labels", [str(i) for i in range(values.shape[1])])
        cmap = data.get("cmap", "YlOrRd")
        vmin = data.get("vmin", None)
        vmax = data.get("vmax", None)
        annotate = data.get("annotate", True)
        row_colors = data.get("row_colors", {})

        im = ax.imshow(values, aspect="auto", cmap=cmap,
                       vmin=vmin if vmin is not None else values.min(),
                       vmax=vmax if vmax is not None else values.max())
        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, rotation=35, ha="right", fontsize=8)
        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels, fontsize=8)
        if row_colors:
            for i, rl in enumerate(row_labels):
                col = row_colors.get(rl)
                if col:
                    ax.get_yticklabels()[i].set_color(col)
        if annotate:
            for i in range(values.shape[0]):
                for j in range(values.shape[1]):
                    v = values[i, j]
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                            fontsize=6, color="white" if v > (values.max() * 0.65) else "black")
        plt.colorbar(im, ax=ax)

    elif panel_type == "bar":
        categories = data.get("categories", [])
        series = data.get("series", [])
        x = range(len(categories))
        colors = [s.get("color", None) for s in series]
        if len(series) == 1:
            vals = series[0]["values"]
            ax.bar(x, vals, color=colors[0] or "#4472C4")
        else:
            width = 0.8 / max(len(series), 1)
            for si, s in enumerate(series):
                offsets = [xi + si * width for xi in x]
                ax.bar(offsets, s["values"], width=width,
                       color=s.get("color"), label=s.get("name", ""))
            ax.legend(fontsize=8)
        ax.set_xticks(list(x))
        ax.set_xticklabels(categories, rotation=35, ha="right", fontsize=8)

    elif panel_type == "grouped_bar":
        categories = data.get("categories", [])
        series = data.get("series", [])
        n = len(categories)
        width = 0.8 / max(len(series), 1)
        for si, s in enumerate(series):
            offsets = [i + si * width for i in range(n)]
            ax.bar(offsets, s["values"], width=width,
                   color=s.get("color"), label=s.get("name", ""), alpha=0.85)
        ax.set_xticks([i + (len(series) - 1) * width / 2 for i in range(n)])
        ax.set_xticklabels(categories, rotation=35, ha="right", fontsize=8)
        ax.legend(fontsize=8)

    elif panel_type in ("scatter", "line"):
        xs = data.get("x", [])
        ys = data.get("y", [])
        pt_labels = data.get("point_labels", [])
        pt_colors = data.get("point_colors", None)
        pt_sizes = data.get("point_sizes", None)
        if panel_type == "scatter":
            ax.scatter(xs, ys,
                       c=pt_colors or "#4472C4",
                       s=pt_sizes or 60,
                       alpha=0.85, edgecolors="white", linewidths=0.6)
        else:
            ax.plot(xs, ys, marker="o", linewidth=1.5, color="#4472C4")
        for i, lbl in enumerate(pt_labels):
            ax.annotate(lbl, (xs[i], ys[i]),
                        textcoords="offset points", xytext=(5, 3), fontsize=7)
        ax.grid(True, alpha=0.2)

    # Common formatting
    ax.set_xlabel(data.get("xlabel", ""), fontsize=9)
    ax.set_ylabel(data.get("ylabel", ""), fontsize=9)
    ax.set_title(data.get("title", ""), fontsize=10, fontweight="bold")

    legend_def = data.get("legend")
    if legend_def:
        import matplotlib.patches as mpatches
        patches = [mpatches.Patch(color=c, label=lbl) for lbl, c in legend_def.items()]
        ax.legend(handles=patches, title=data.get("legend_title", ""),
                  fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")

    plt.tight_layout()
    out = Path(tmp_dir) / f"panel_{id(block)}.png"
    fig.savefig(str(out), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------

def _rgb_img(path: str, tmp_dir: str) -> str:
    """Convert any image to RGB PNG (handles RGBA transparency for reportlab)."""
    from PIL import Image as PILImage
    img = PILImage.open(path).convert("RGB")
    out = Path(tmp_dir) / f"rgb_{Path(path).stem}.png"
    img.save(str(out))
    return str(out), img.width, img.height


def build_pdf(report: dict, output_path: str) -> dict:
    """Build the PDF. Returns {"pdf_path": str, "n_pages": int, "n_figures": int}."""
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
        Table, TableStyle, Image, HRFlowable, KeepTogether, PageBreak,
    )

    W, H = A4
    MARGIN = 2.0 * cm
    TEXT_WIDTH = W - 2 * MARGIN

    styles = getSampleStyleSheet()

    BLUE_DARK   = rl_colors.HexColor("#1a237e")
    BLUE_MID    = rl_colors.HexColor("#283593")
    GREY        = rl_colors.HexColor("#555555")
    LIGHT_GREY  = rl_colors.HexColor("#f5f5f5")

    title_s   = ParagraphStyle("PT",  parent=styles["Title"],
                                fontSize=16, leading=20, spaceAfter=4)
    sub_s     = ParagraphStyle("PS",  parent=styles["Normal"],
                                fontSize=9,  leading=12, spaceAfter=2, textColor=GREY)
    h1_s      = ParagraphStyle("H1",  parent=styles["Heading1"],
                                fontSize=13, leading=16, spaceBefore=14, spaceAfter=5,
                                textColor=BLUE_DARK)
    h2_s      = ParagraphStyle("H2",  parent=styles["Heading2"],
                                fontSize=11, leading=13, spaceBefore=10, spaceAfter=3,
                                textColor=BLUE_MID)
    h3_s      = ParagraphStyle("H3",  parent=styles["Heading3"],
                                fontSize=10, leading=12, spaceBefore=8, spaceAfter=2,
                                textColor=BLUE_MID, fontName="Helvetica-BoldOblique")
    body_s    = ParagraphStyle("BD",  parent=styles["Normal"],
                                fontSize=9,  leading=13, spaceAfter=5)
    caption_s = ParagraphStyle("CP",  parent=styles["Normal"],
                                fontSize=8,  leading=10, spaceAfter=8, textColor=GREY)
    th_s      = ParagraphStyle("TH",  parent=styles["Normal"],
                                fontSize=8,  leading=10, fontName="Helvetica-Bold")
    tc_s      = ParagraphStyle("TC",  parent=styles["Normal"],
                                fontSize=8,  leading=10)

    HEADING_STYLES = {1: h1_s, 2: h2_s, 3: h3_s}

    # Table style helper
    def _table_style(header_color="#e3f2fd"):
        return TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), rl_colors.HexColor(header_color)),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
            ("GRID",         (0, 0), (-1, -1), 0.4, rl_colors.HexColor("#bbbbbb")),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, LIGHT_GREY]),
        ])

    doc = BaseDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    frame = Frame(MARGIN, MARGIN, TEXT_WIDTH, H - 2 * MARGIN, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

    story = []
    tmp_dir = tempfile.mkdtemp()
    n_figures = 0

    # ── Title block ──────────────────────────────────────────────────────────
    story.append(Paragraph(report.get("title", "Untitled Report"), title_s))
    authors = report.get("authors", [])
    if authors:
        story.append(Paragraph(", ".join(authors), sub_s))
    if report.get("subtitle"):
        story.append(Paragraph(report["subtitle"], sub_s))
    meta = report.get("metadata", {})
    date_str = meta.get("date") or datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Generated: {date_str}", sub_s))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=rl_colors.HexColor("#cccccc"), spaceAfter=10))

    # ── Abstract ─────────────────────────────────────────────────────────────
    if report.get("abstract"):
        story.append(Paragraph("Abstract", h1_s))
        story.append(Paragraph(report["abstract"], body_s))

    # ── Sections ─────────────────────────────────────────────────────────────
    for block in report.get("sections", []):
        btype = block.get("type", "text")

        if btype == "heading":
            level = block.get("level", 1)
            story.append(Paragraph(block.get("text", ""), HEADING_STYLES.get(level, h1_s)))

        elif btype == "text":
            story.append(Paragraph(block.get("text", ""), body_s))

        elif btype == "hr":
            story.append(HRFlowable(width="100%", thickness=0.5,
                                     color=rl_colors.HexColor("#dddddd"), spaceAfter=6))

        elif btype == "pagebreak":
            story.append(PageBreak())

        elif btype == "table":
            headers = block.get("headers", [])
            rows = block.get("rows", [])
            hl_col = block.get("highlight_col", None)
            n_cols = max(len(headers), max((len(r) for r in rows), default=0))
            col_w = TEXT_WIDTH / max(n_cols, 1)
            col_widths = [col_w] * n_cols

            table_data = [[Paragraph(h, th_s) for h in headers]]
            for row in rows:
                tr = []
                best_val = None
                if hl_col is not None:
                    try:
                        best_val = float(row[hl_col])
                    except (ValueError, IndexError):
                        pass
                for ci, cell in enumerate(row):
                    style = tc_s
                    text = str(cell)
                    if hl_col is not None and ci == hl_col and best_val is not None:
                        text = f"<b>{text}</b>"
                    tr.append(Paragraph(text, style))
                table_data.append(tr)

            t = Table(table_data, colWidths=col_widths)
            t.setStyle(_table_style())
            label = block.get("label", "")
            caption_text = block.get("caption", "")
            story.append(KeepTogether([
                t,
                Paragraph(f"<i>{label}. {caption_text}</i>" if label else f"<i>{caption_text}</i>",
                          caption_s),
            ]))

        elif btype in ("figure", "panel"):
            if btype == "panel":
                try:
                    img_path = _panel_to_png(block, tmp_dir)
                except Exception as e:
                    story.append(Paragraph(f"<i>[Panel generation failed: {e}]</i>", caption_s))
                    continue
            else:
                img_path = block.get("path", "")

            if img_path and Path(img_path).exists():
                try:
                    rgb_path, orig_w, orig_h = _rgb_img(img_path, tmp_dir)
                    aspect = orig_h / orig_w
                    img = Image(rgb_path, width=TEXT_WIDTH, height=TEXT_WIDTH * aspect)
                    label = block.get("label", "")
                    caption_text = block.get("caption", "")
                    story.append(KeepTogether([
                        img,
                        Paragraph(
                            f"<b>{label}.</b> {caption_text}" if label else caption_text,
                            caption_s,
                        ),
                        Spacer(1, 8),
                    ]))
                    n_figures += 1
                except Exception as e:
                    story.append(Paragraph(f"<i>[Figure load failed: {e}]</i>", caption_s))
            else:
                story.append(Paragraph(
                    f"<i>[{block.get('label','Figure')}: path not found — {img_path}]</i>",
                    caption_s,
                ))

    # ── Footer metadata ───────────────────────────────────────────────────────
    if meta:
        story.append(HRFlowable(width="100%", thickness=0.5,
                                 color=rl_colors.HexColor("#dddddd"), spaceAfter=4))
        parts = []
        if meta.get("investigation_id"):
            parts.append(f"Investigation: {meta['investigation_id']}")
        if meta.get("platform"):
            parts.append(f"Platform: {meta['platform']}")
        if meta.get("agents"):
            parts.append(f"Agents: {', '.join(meta['agents'])}")
        if parts:
            story.append(Paragraph(" | ".join(parts), sub_s))

    doc.build(story)

    # Count pages via PyPDF2 if available, else estimate
    n_pages = 0
    try:
        import pypdf
        with open(output_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            n_pages = len(reader.pages)
    except Exception:
        n_pages = -1

    return {
        "pdf_path": str(output_path),
        "n_pages": n_pages,
        "n_figures": n_figures,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(input_json: str, output_dir: str = ".", output_filename: str = "") -> dict:
    p = Path(input_json)
    if not p.exists():
        return {"error": f"Input file not found: {input_json}"}

    with open(p) as f:
        report = json.load(f)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if output_filename:
        pdf_path = out_dir / output_filename
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() or c in "-_" else "_"
                             for c in report.get("title", "report")[:40])
        pdf_path = out_dir / f"{safe_title}_{ts}.pdf"

    result = build_pdf(report, str(pdf_path))
    size_kb = Path(pdf_path).stat().st_size // 1024 if Path(pdf_path).exists() else 0
    result["size_kb"] = size_kb
    return result


def main():
    args = _parse_args()

    if args.describe_schema:
        print(json.dumps(SCHEMA, indent=2))
        return

    if not args.input_json:
        print("Error: --input-json is required unless --describe-schema is used", file=sys.stderr)
        sys.exit(1)

    result = run(
        input_json=args.input_json,
        output_dir=args.output_dir,
        output_filename=args.output_filename,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
