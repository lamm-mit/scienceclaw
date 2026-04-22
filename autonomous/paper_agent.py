#!/usr/bin/env python3
"""
PaperAgent — General-purpose arXiv-style report + figure generator.

Takes any completed ScienceClaw investigation (artifacts in ~/.scienceclaw/)
and a working directory, then produces:
  - sci1.png … sciN.png   — matplotlib figures derived from artifact payloads
  - synthesis_report.tex  — arXiv-style LaTeX paper
  - refs.bib              — auto-generated BibTeX from artifact metadata
  - synthesis_post.md     — markdown mirror for Infinite posting

Usage (Python):
    from autonomous.paper_agent import PaperAgent

    agent = PaperAgent("PaperAgent")
    agent.run(
        topic="climate-driven vector-borne disease emergence",
        case_dir="/path/to/output",
        agent_names=["ClimateSignalExtractor", "NicheMapper"],
    )
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

logger = logging.getLogger(__name__)

# ── Shared palette (matches CS6 generate_figures.py style) ───────────────────
CORAL  = "#E8604C"
BLUE   = "#2E86AB"
GREEN  = "#3BB273"
AMBER  = "#F4A261"
PURPLE = "#6A4C93"
GREY   = "#888888"
LGREY  = "#F0F0F0"

PALETTE = [CORAL, BLUE, GREEN, AMBER, PURPLE, GREY]

plt.rcParams.update({
    "font.family":          "sans-serif",
    "font.size":            10,
    "axes.spines.top":      False,
    "axes.spines.right":    False,
    "axes.labelsize":       11,
    "axes.titlesize":       12,
    "axes.titleweight":     "bold",
    "figure.dpi":           150,
})


# ── Skill-to-figure-type heuristic ───────────────────────────────────────────
_TIME_SERIES_SKILLS = {
    "climate-data", "nasa-power", "noaa", "era5", "cmip6",
    "temporal-analysis", "time-series",
}
_DISTRIBUTION_SKILLS = {
    "gbif", "gbif-occurrences", "species-distribution",
    "geo-database", "geospatial",
}
_ALERT_SKILLS = {
    "promed-surveillance", "healthmap", "ecdc", "cdc",
    "surveillance", "epi-alerts", "disease-alerts",
}
_MECHANISM_SKILLS = {
    "mechanistic-model", "ode-model", "vector-model",
    "pharmacodynamics", "kinetics", "briere",
}


# =============================================================================
# FigureFactory
# =============================================================================

class FigureFactory:
    """
    Inspects artifact skill_used + payload keys to choose a figure type,
    then renders a matplotlib PNG. Returns the saved path or None on failure.
    """

    def __init__(self, case_dir: Path):
        self.case_dir = case_dir
        self._index = 0

    def _next_path(self, label: str = "") -> Path:
        self._index += 1
        slug = re.sub(r"[^a-z0-9]", "_", label.lower())[:20].strip("_")
        name = f"sci{self._index}_{slug}.png" if slug else f"sci{self._index}.png"
        return self.case_dir / name

    # ------------------------------------------------------------------ public

    def make_figure(self, artifact: Any) -> Optional[Path]:
        skill = getattr(artifact, "skill_used", "") or ""
        payload = getattr(artifact, "payload", {}) or {}
        atype = getattr(artifact, "artifact_type", "") or ""

        try:
            if skill in _TIME_SERIES_SKILLS or self._has_time_series(payload):
                return self._time_series_fig(artifact, payload)
            if skill in _DISTRIBUTION_SKILLS or self._has_distribution(payload):
                return self._distribution_fig(artifact, payload)
            if skill in _ALERT_SKILLS or self._has_alerts(payload):
                return self._alert_timeline_fig(artifact, payload)
            if skill in _MECHANISM_SKILLS or self._has_mechanism(payload):
                return self._mechanism_fig(artifact, payload)
            # Generic fallback
            return self._summary_bar_fig(artifact, payload)
        except Exception as e:
            logger.warning(f"[FigureFactory] Failed for {skill}/{atype}: {e}")
            return None

    # ---------------------------------------------------------------- detection

    def _has_time_series(self, p: dict) -> bool:
        keys = set(p.keys())
        return bool({"years", "dates", "time_series", "annual_values"} & keys)

    def _has_distribution(self, p: dict) -> bool:
        keys = set(p.keys())
        return bool({"countries", "latitudes", "occurrences", "records", "counts"} & keys)

    def _has_alerts(self, p: dict) -> bool:
        keys = set(p.keys())
        return bool({"alerts", "events", "cases", "timeline"} & keys)

    def _has_mechanism(self, p: dict) -> bool:
        keys = set(p.keys())
        return bool({"parameters", "model", "function", "equation", "simulation"} & keys)

    # -------------------------------------------------------------- renderers

    def _time_series_fig(self, artifact: Any, payload: dict) -> Path:
        years = payload.get("years") or payload.get("dates") or []
        values = (
            payload.get("annual_values")
            or payload.get("time_series")
            or payload.get("values")
            or []
        )
        secondary = payload.get("secondary_values") or []
        label = payload.get("variable_label", "Value")
        title = payload.get("title", f"Time series — {getattr(artifact, 'artifact_type', '')}")
        out = self._next_path(label)

        fig, ax1 = plt.subplots(figsize=(10, 4.5))
        ax1.plot(years, values, color=CORAL, linewidth=2.2, marker="o", markersize=4)

        if values and years:
            z = np.polyfit(range(len(years)), values, 1)
            p = np.poly1d(z)
            trend_per_unit = z[0]
            ax1.plot(years, p(range(len(years))), color=CORAL, linewidth=1.2,
                     linestyle="--", alpha=0.45)
            ax1.text(0.02, 0.97, f"Trend: {trend_per_unit:+.4f}/yr",
                     transform=ax1.transAxes, fontsize=7.5, color=CORAL,
                     va="top")

        if secondary and len(secondary) == len(years):
            ax2 = ax1.twinx()
            ax2.bar(years, secondary, color=BLUE, alpha=0.35, width=0.6, zorder=1)
            ax2.set_ylabel(payload.get("secondary_label", "Secondary"), color=BLUE)
            ax2.tick_params(axis="y", labelcolor=BLUE)

        ax1.yaxis.grid(True, color="#dddddd", linewidth=0.5)
        ax1.set_axisbelow(True)
        ax1.set_ylabel(label, color=CORAL)
        ax1.tick_params(axis="y", labelcolor=CORAL)
        ax1.set_xlabel("Year")
        ax1.set_title(title)
        fig.tight_layout(pad=1.2)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out

    def _distribution_fig(self, artifact: Any, payload: dict) -> Path:
        items  = payload.get("countries") or payload.get("labels") or []
        counts = payload.get("counts") or payload.get("occurrences") or payload.get("values") or []
        title  = payload.get("title", f"Distribution — {getattr(artifact, 'artifact_type', '')}")
        out    = self._next_path("distribution")

        if not items or not counts:
            return self._summary_bar_fig(artifact, payload)

        # Limit to top 12
        paired = sorted(zip(counts, items), reverse=True)[:12]
        counts_s, items_s = zip(*paired) if paired else ([], [])

        colors = [PALETTE[i % len(PALETTE)] for i in range(len(items_s))]
        fig, ax = plt.subplots(figsize=(8, max(3, len(items_s) * 0.45)))
        ax.barh(items_s, counts_s, color=colors, alpha=0.85)
        ax.set_xlabel("Count")
        ax.set_title(title)
        ax.invert_yaxis()
        ax.xaxis.grid(True, color="#dddddd", linewidth=0.5)
        ax.set_axisbelow(True)
        fig.tight_layout(pad=1.2)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out

    def _alert_timeline_fig(self, artifact: Any, payload: dict) -> Path:
        alerts  = payload.get("alerts") or payload.get("events") or []
        title   = payload.get("title", f"Surveillance — {getattr(artifact, 'artifact_type', '')}")
        out     = self._next_path("alerts")

        # Aggregate by date and disease/type
        from collections import defaultdict
        date_counts: dict = defaultdict(int)
        disease_counts: dict = defaultdict(int)
        for a in alerts:
            date = a.get("date", "unknown")
            disease = a.get("disease") or a.get("type") or "Unknown"
            date_counts[date] += 1
            disease_counts[disease] += 1

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

        # Left: disease pie
        if disease_counts:
            diseases = list(disease_counts.keys())
            vals = list(disease_counts.values())
            colors = [PALETTE[i % len(PALETTE)] for i in range(len(diseases))]
            ax1.pie(vals, labels=diseases, colors=colors, autopct="%1.0f%%",
                    startangle=90, textprops={"fontsize": 8})
            ax1.set_title("Alert composition")

        # Right: timeline bar
        if date_counts:
            dates = sorted(date_counts.keys())
            cnts = [date_counts[d] for d in dates]
            ax2.bar(range(len(dates)), cnts, color=CORAL, alpha=0.8)
            ax2.set_xticks(range(len(dates)))
            ax2.set_xticklabels(dates, rotation=45, ha="right", fontsize=7)
            ax2.set_ylabel("Alerts")
            ax2.set_title("Daily alert timeline")
            ax2.yaxis.grid(True, color="#dddddd", linewidth=0.5)
            ax2.set_axisbelow(True)

        fig.suptitle(title, fontsize=11, fontweight="bold")
        fig.tight_layout(pad=1.2)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out

    def _mechanism_fig(self, artifact: Any, payload: dict) -> Path:
        title = payload.get("title", f"Mechanism — {getattr(artifact, 'artifact_type', '')}")
        out   = self._next_path("mechanism")

        x = np.linspace(0, 100, 300)
        # Generic sigmoid as placeholder for mechanistic output
        params = payload.get("parameters", {})
        k = float(params.get("k", 0.1))
        x0 = float(params.get("x0", 50))
        y = 1 / (1 + np.exp(-k * (x - x0)))

        x_range = payload.get("x_range") or payload.get("input_values") or []
        y_range = payload.get("y_range") or payload.get("output_values") or []
        if x_range and y_range and len(x_range) == len(y_range):
            x, y = np.array(x_range), np.array(y_range)

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(x, y, color=CORAL, linewidth=2.5)
        ax.fill_between(x, 0, y, alpha=0.12, color=CORAL)
        ax.set_xlabel(payload.get("x_label", "Input"))
        ax.set_ylabel(payload.get("y_label", "Output"))
        ax.set_title(title)
        ax.yaxis.grid(True, color="#dddddd", linewidth=0.5)
        ax.set_axisbelow(True)
        fig.tight_layout(pad=1.2)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out

    def _summary_bar_fig(self, artifact: Any, payload: dict) -> Optional[Path]:
        # Try to find any numeric key-value pairs to plot
        numeric = {k: v for k, v in payload.items()
                   if isinstance(v, (int, float)) and not k.startswith("_")}
        if len(numeric) < 2:
            return None

        items = list(numeric.keys())[:12]
        vals  = [numeric[k] for k in items]
        title = payload.get("title", getattr(artifact, "artifact_type", "Summary"))
        out   = self._next_path("summary")

        colors = [PALETTE[i % len(PALETTE)] for i in range(len(items))]
        fig, ax = plt.subplots(figsize=(8, max(3, len(items) * 0.45)))
        ax.barh(items, vals, color=colors, alpha=0.85)
        ax.set_xlabel("Value")
        ax.set_title(str(title))
        ax.invert_yaxis()
        ax.xaxis.grid(True, color="#dddddd", linewidth=0.5)
        ax.set_axisbelow(True)
        fig.tight_layout(pad=1.2)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out


# =============================================================================
# ReportData — intermediate struct between artifact collection and writing
# =============================================================================

@dataclass
class ReportData:
    topic: str
    title: str = ""
    abstract: str = ""
    introduction: str = ""
    methods: str = ""
    results: str = ""
    discussion: str = ""
    conclusion: str = ""
    open_questions: List[str] = field(default_factory=list)
    figure_paths: List[Path] = field(default_factory=list)
    figure_captions: List[str] = field(default_factory=list)
    data_sources: List[Dict] = field(default_factory=list)
    references: List[Dict] = field(default_factory=list)
    agent_names: List[str] = field(default_factory=list)
    artifact_count: int = 0
    date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))


# =============================================================================
# SynthesisPostWriter
# =============================================================================

class SynthesisPostWriter:
    """
    Converts a ReportData into:
      - synthesis_report.tex  (arXiv-style LaTeX)
      - refs.bib              (BibTeX)
      - synthesis_post.md     (markdown mirror)
    """

    def __init__(self, case_dir: Path):
        self.case_dir = case_dir

    # ------------------------------------------------------------------ public

    def write(self, report: ReportData) -> Dict[str, Path]:
        tex_path = self.case_dir / "synthesis_report.tex"
        bib_path = self.case_dir / "refs.bib"
        md_path  = self.case_dir / "synthesis_post.md"

        bib_entries = self._build_bib(report)
        tex_content = self._build_latex(report, bib_entries)
        md_content  = self._build_markdown(report)

        tex_path.write_text(tex_content, encoding="utf-8")
        bib_path.write_text("\n\n".join(bib_entries.values()), encoding="utf-8")
        md_path.write_text(md_content, encoding="utf-8")

        # Try to compile PDF
        pdf_path = self._compile_pdf(tex_path)

        return {
            "tex": tex_path,
            "bib": bib_path,
            "md":  md_path,
            "pdf": pdf_path,
        }

    # ----------------------------------------------------------------- LaTeX

    def _build_latex(self, r: ReportData, bib_entries: dict) -> str:
        authors_str = " \\and ".join(r.agent_names) if r.agent_names else "ScienceClaw Multi-Agent"
        figures_tex = self._figures_tex(r)

        preamble = textwrap.dedent(r"""
            \documentclass[12pt]{article}
            \usepackage[margin=1in]{geometry}
            \usepackage{amsmath,amssymb}
            \usepackage{graphicx}
            \usepackage[colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue]{hyperref}
            \usepackage[numbers,sort&compress]{natbib}
            \usepackage{booktabs}
            \usepackage{setspace}
            \usepackage{microtype}
            \usepackage{caption}
            \captionsetup{font=small,labelfont=bf}
            \onehalfspacing
        """).strip()

        bib_keys_str = ", ".join(list(bib_entries.keys())[:3]) if bib_entries else ""
        cite_example = f"\\cite{{{bib_keys_str}}}" if bib_keys_str else ""

        body = textwrap.dedent(f"""
            {preamble}

            \\title{{{self._latex_escape(r.title or r.topic)}}}
            \\author{{{self._latex_escape(authors_str)} \\\\
            \\small ScienceClaw Multi-Agent Investigation}}
            \\date{{{r.date}}}

            \\begin{{document}}
            \\maketitle

            \\begin{{abstract}}
            {self._latex_escape(r.abstract)}
            \\end{{abstract}}

            \\tableofcontents
            \\newpage

            \\section{{Introduction}}
            {self._latex_escape(r.introduction)}

            \\section{{Methods}}
            {self._latex_escape(r.methods)}
            {self._data_sources_table(r)}

            \\section{{Results}}
            {self._latex_escape(r.results)}
            {figures_tex}

            \\section{{Discussion}}
            {self._latex_escape(r.discussion)}

            \\section{{Conclusion}}
            {self._latex_escape(r.conclusion)}

            \\section*{{Open Questions}}
            \\begin{{enumerate}}
            {chr(10).join(f"  \\item {self._latex_escape(q)}" for q in r.open_questions)}
            \\end{{enumerate}}

            \\bibliographystyle{{unsrtnat}}
            \\bibliography{{refs}}

            \\end{{document}}
        """).strip()

        return body

    def _figures_tex(self, r: ReportData) -> str:
        blocks = []
        for i, (path, caption) in enumerate(
            zip(r.figure_paths, r.figure_captions), start=1
        ):
            rel = path.name
            cap = self._latex_escape(caption or f"Figure {i}.")
            blocks.append(textwrap.dedent(f"""
                \\begin{{figure}}[htbp]
                  \\centering
                  \\includegraphics[width=\\linewidth]{{{rel}}}
                  \\caption{{{cap}}}
                  \\label{{fig:{i}}}
                \\end{{figure}}
            """).strip())
        return "\n\n".join(blocks)

    def _data_sources_table(self, r: ReportData) -> str:
        if not r.data_sources:
            return ""
        rows = []
        for ds in r.data_sources:
            name    = self._latex_escape(str(ds.get("name", "")))
            records = self._latex_escape(str(ds.get("records", "")))
            access  = self._latex_escape(str(ds.get("accessed", "")))
            rows.append(f"  {name} & {records} & {access} \\\\")

        return textwrap.dedent(r"""
            \subsection*{Data Sources}
            \begin{table}[htbp]
            \centering
            \begin{tabular}{lll}
            \toprule
            Source & Records & Accessed \\
            \midrule
        """).strip() + "\n" + "\n".join(rows) + textwrap.dedent(r"""
            \bottomrule
            \end{tabular}
            \end{table}
        """)

    @staticmethod
    def _latex_escape(text: str) -> str:
        if not text:
            return ""
        replacements = [
            ("&",  r"\&"),
            ("%",  r"\%"),
            ("$",  r"\$"),
            ("#",  r"\#"),
            ("_",  r"\_"),
            ("{",  r"\{"),
            ("}",  r"\}"),
            ("~",  r"\textasciitilde{}"),
            ("^",  r"\textasciicircum{}"),
            ("\\", r"\textbackslash{}"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    # ------------------------------------------------------------------- BibTeX

    def _build_bib(self, r: ReportData) -> dict:
        entries: dict = {}
        for ref in r.references:
            key   = re.sub(r"\W+", "", str(ref.get("key") or ref.get("id") or "ref"))
            title = ref.get("title", "")
            year  = ref.get("year", "")
            auth  = ref.get("authors") or ref.get("author") or ""
            url   = ref.get("url") or ref.get("doi") or ""
            entry = (
                f"@article{{{key},\n"
                f"  title   = {{{title}}},\n"
                f"  author  = {{{auth}}},\n"
                f"  year    = {{{year}}},\n"
                f"  url     = {{{url}}}\n"
                f"}}"
            )
            entries[key] = entry
        if not entries:
            entries["scienceclaw2026"] = (
                "@misc{scienceclaw2026,\n"
                "  title   = {ScienceClaw Multi-Agent Investigation},\n"
                "  year    = {2026},\n"
                "  url     = {https://infinite-lamm.vercel.app}\n"
                "}"
            )
        return entries

    # ----------------------------------------------------------------- Markdown

    def _build_markdown(self, r: ReportData) -> str:
        fig_lines = []
        for i, (path, caption) in enumerate(
            zip(r.figure_paths, r.figure_captions), start=1
        ):
            fig_lines.append(f"![Fig {i}](./{path.name})\n*{caption}*")

        oq_lines = "\n".join(f"{i+1}. {q}" for i, q in enumerate(r.open_questions))
        ds_lines = "\n".join(
            f"| {ds.get('name','')} | {ds.get('records','')} | {ds.get('accessed','')} |"
            for ds in r.data_sources
        )

        return f"""---
title: {r.title or r.topic}
date: {r.date}
agents: {", ".join(r.agent_names)}
artifacts: {r.artifact_count}
---

## Abstract

{r.abstract}

## 1. Introduction

{r.introduction}

## 2. Methods

{r.methods}

{"| Source | Records | Accessed |" if r.data_sources else ""}
{"| --- | --- | --- |" if r.data_sources else ""}
{ds_lines}

## 3. Results

{r.results}

{chr(10).join(fig_lines)}

## 4. Discussion

{r.discussion}

## 5. Conclusion

{r.conclusion}

## Open Questions

{oq_lines}
"""

    # -------------------------------------------------------------------- PDF

    def _compile_pdf(self, tex_path: Path) -> Optional[Path]:
        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory",
                 str(tex_path.parent), str(tex_path)],
                capture_output=True,
                timeout=60,
                cwd=tex_path.parent,
            )
            # Run twice for TOC/references
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory",
                 str(tex_path.parent), str(tex_path)],
                capture_output=True,
                timeout=60,
                cwd=tex_path.parent,
            )
            pdf = tex_path.with_suffix(".pdf")
            if pdf.exists():
                logger.info(f"[PaperAgent] PDF compiled: {pdf}")
                return pdf
        except FileNotFoundError:
            logger.info("[PaperAgent] pdflatex not found — skipping PDF compilation")
        except Exception as e:
            logger.warning(f"[PaperAgent] PDF compilation failed: {e}")
        return None


# =============================================================================
# LLMSectionBuilder — wraps LLMScientificReasoner for section prose
# =============================================================================

class LLMSectionBuilder:
    def __init__(self, agent_name: str):
        self._agent_name = agent_name
        self._reasoner = None

    def _get_reasoner(self):
        if self._reasoner is None:
            from autonomous.llm_reasoner import LLMScientificReasoner
            self._reasoner = LLMScientificReasoner(self._agent_name)
        return self._reasoner

    def generate(self, section: str, topic: str, context: str, max_tokens: int = 600) -> str:
        prompt = (
            f"You are writing the {section} section of an arXiv-style scientific paper.\n"
            f"Research topic: {topic}\n\n"
            f"Evidence from the investigation:\n{context[:2000]}\n\n"
            f"Write 2–4 paragraphs of concise, precise academic prose for the {section} section. "
            f"Do not use markdown. Use present tense for established facts, past tense for methods."
        )
        try:
            return self._get_reasoner()._call_llm(prompt, max_tokens=max_tokens).strip()
        except Exception as e:
            logger.warning(f"[LLMSectionBuilder] LLM unavailable for {section}: {e}")
            return f"[{section} — LLM unavailable: {e}]"

    def generate_title(self, topic: str, findings_summary: str) -> str:
        prompt = (
            f"Generate a concise, specific arXiv-style paper title for this investigation.\n"
            f"Topic: {topic}\n"
            f"Key findings: {findings_summary[:500]}\n\n"
            f"Respond with only the title, no quotes or punctuation at the end."
        )
        try:
            raw = self._get_reasoner()._call_llm(prompt, max_tokens=60).strip()
            return raw.strip('"\'')
        except Exception:
            return topic.title()


# =============================================================================
# ArtifactSummarizer — extracts text summaries from artifact payloads
# =============================================================================

class ArtifactSummarizer:
    """Flattens artifact payloads into readable text for LLM prompts."""

    @staticmethod
    def summarize(artifacts: List[Any]) -> str:
        lines = []
        for a in artifacts[:30]:
            skill  = getattr(a, "skill_used", "unknown")
            atype  = getattr(a, "artifact_type", "unknown")
            agent  = getattr(a, "producer_agent", "unknown")
            payload = getattr(a, "payload", {}) or {}

            # Pull the most informative scalar fields
            snippets = []
            for key in ("summary", "findings", "result", "description", "title",
                        "abstract", "content", "text", "conclusion"):
                val = payload.get(key)
                if isinstance(val, str) and val.strip():
                    snippets.append(val.strip()[:200])
                    break

            # Numeric highlights
            numerics = {k: v for k, v in payload.items()
                        if isinstance(v, (int, float)) and not k.startswith("_")}
            num_str = "; ".join(f"{k}={v}" for k, v in list(numerics.items())[:4])

            line = f"[{agent}/{skill}/{atype}]"
            if snippets:
                line += f" {snippets[0]}"
            if num_str:
                line += f" ({num_str})"
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def extract_references(artifacts: List[Any]) -> List[Dict]:
        refs = []
        seen = set()
        for a in artifacts:
            payload = getattr(a, "payload", {}) or {}
            papers  = payload.get("papers") or payload.get("references") or []
            for p in papers[:5]:
                if not isinstance(p, dict):
                    continue
                title = p.get("title") or p.get("Title") or ""
                if not title or title in seen:
                    continue
                seen.add(title)
                key = re.sub(r"\W+", "", title)[:20]
                refs.append({
                    "key":     key,
                    "title":   title,
                    "authors": p.get("authors") or p.get("author") or "",
                    "year":    p.get("year") or p.get("published") or "",
                    "url":     p.get("doi") or p.get("url") or p.get("pmid") or "",
                })
        return refs


# =============================================================================
# PaperAgent — top-level orchestrator
# =============================================================================

class PaperAgent:
    """
    General-purpose paper + figure generator.

    Loads artifacts from ~/.scienceclaw/artifacts/ for the given agents,
    generates matplotlib figures from payload data, writes an arXiv-style
    LaTeX report, and optionally posts a markdown mirror to Infinite.
    """

    def __init__(self, agent_name: str = "PaperAgent"):
        self.agent_name = agent_name
        self._llm = LLMSectionBuilder(agent_name)

    def run(
        self,
        topic: str,
        case_dir: str | Path,
        agent_names: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        investigation_id: Optional[str] = None,
        post_to_infinite: bool = False,
    ) -> Dict[str, Any]:
        case_dir = Path(case_dir)
        case_dir.mkdir(parents=True, exist_ok=True)

        print(f"[PaperAgent] Loading artifacts for topic: {topic}")
        artifacts = self._collect_artifacts(
            topic, agent_names, session_id, investigation_id
        )
        print(f"[PaperAgent] {len(artifacts)} artifacts loaded from "
              f"{len(set(getattr(a,'producer_agent','?') for a in artifacts))} agents")

        # Generate figures
        factory = FigureFactory(case_dir)
        figure_paths: List[Path] = []
        figure_captions: List[str] = []
        figurable = self._select_figurable_artifacts(artifacts)
        for artifact in figurable:
            path = factory.make_figure(artifact)
            if path:
                atype   = getattr(artifact, "artifact_type", "")
                skill   = getattr(artifact, "skill_used", "")
                caption = (
                    getattr(artifact, "payload", {}).get("caption")
                    or f"{atype.replace('_',' ').title()} ({skill}). "
                       f"Derived from {getattr(artifact,'producer_agent','')} artifact."
                )
                figure_paths.append(path)
                figure_captions.append(caption)
                print(f"[PaperAgent] Figure saved: {path.name}")

        # Build report data via LLM
        report = self._build_report(topic, artifacts, agent_names or [], figure_paths, figure_captions)

        # Write outputs
        writer = SynthesisPostWriter(case_dir)
        paths  = writer.write(report)
        print(f"[PaperAgent] LaTeX:    {paths['tex']}")
        print(f"[PaperAgent] Markdown: {paths['md']}")
        if paths.get("pdf"):
            print(f"[PaperAgent] PDF:      {paths['pdf']}")

        # Optional Infinite post
        if post_to_infinite:
            self._post_to_infinite(report, paths["md"].read_text())

        return {
            "report":   report,
            "paths":    paths,
            "figures":  figure_paths,
            "artifacts": len(artifacts),
        }

    # ----------------------------------------------------------------- internal

    def _collect_artifacts(
        self,
        topic: str,
        agent_names: Optional[List[str]],
        session_id: Optional[str],
        investigation_id: Optional[str],
    ) -> List[Any]:
        from artifacts.artifact import ArtifactStore

        # Derive investigation_id from topic if not provided
        if not investigation_id:
            investigation_id = re.sub(r"[^a-z0-9]+", "-", topic.lower())[:60]

        artifacts = []
        agents_to_check = agent_names or []

        # If no agents specified, scan all agent stores in ~/.scienceclaw/artifacts/
        if not agents_to_check:
            base = Path.home() / ".scienceclaw" / "artifacts"
            if base.exists():
                agents_to_check = [d.name for d in base.iterdir() if d.is_dir()]

        for name in agents_to_check:
            try:
                store = ArtifactStore(name)
                found = store.list(investigation_id=investigation_id, limit=500)
                artifacts.extend(found)
            except Exception as e:
                logger.debug(f"[PaperAgent] Could not load store for {name}: {e}")

        # Fallback: load all artifacts from listed agents regardless of investigation_id
        if not artifacts and agents_to_check:
            for name in agents_to_check:
                try:
                    store = ArtifactStore(name)
                    found = store.list(limit=50)
                    artifacts.extend(found)
                except Exception:
                    pass

        artifacts.sort(key=lambda a: getattr(a, "timestamp", ""))
        return artifacts

    def _select_figurable_artifacts(self, artifacts: List[Any]) -> List[Any]:
        """
        Pick one artifact per skill type that has meaningful payload data.
        Cap at 8 figures.
        """
        seen_skills: set = set()
        selected = []
        for a in artifacts:
            skill   = getattr(a, "skill_used", "")
            payload = getattr(a, "payload", {}) or {}
            if skill in seen_skills:
                continue
            # Skip artifacts with very thin payloads
            if len(json.dumps(payload)) < 100:
                continue
            seen_skills.add(skill)
            selected.append(a)
            if len(selected) >= 8:
                break
        return selected

    def _build_report(
        self,
        topic: str,
        artifacts: List[Any],
        agent_names: List[str],
        figure_paths: List[Path],
        figure_captions: List[str],
    ) -> ReportData:
        summarizer = ArtifactSummarizer()
        context    = summarizer.summarize(artifacts)
        references = summarizer.extract_references(artifacts)

        report = ReportData(
            topic          = topic,
            agent_names    = agent_names,
            artifact_count = len(artifacts),
            figure_paths   = figure_paths,
            figure_captions= figure_captions,
            references     = references,
        )

        print("[PaperAgent] Generating paper sections via LLM ...")
        report.title        = self._llm.generate_title(topic, context)
        report.abstract     = self._llm.generate("Abstract",      topic, context, max_tokens=250)
        report.introduction = self._llm.generate("Introduction",  topic, context, max_tokens=500)
        report.methods      = self._llm.generate("Methods",       topic, context, max_tokens=500)
        report.results      = self._llm.generate("Results",       topic, context, max_tokens=700)
        report.discussion   = self._llm.generate("Discussion",    topic, context, max_tokens=600)
        report.conclusion   = self._llm.generate("Conclusion",    topic, context, max_tokens=300)

        # Open questions: ask LLM for a JSON list
        oq_prompt = (
            f"Given this investigation on '{topic}', list 5 open scientific questions "
            f"as a JSON array of strings. Only output the JSON array."
        )
        try:
            raw = self._llm._get_reasoner()._call_llm(oq_prompt, max_tokens=200)
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                report.open_questions = json.loads(match.group())[:5]
        except Exception:
            pass

        # Data sources from artifacts
        skill_counts: dict = {}
        for a in artifacts:
            skill = getattr(a, "skill_used", "unknown")
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
        report.data_sources = [
            {"name": skill, "records": count, "accessed": report.date}
            for skill, count in sorted(skill_counts.items(), key=lambda x: -x[1])[:8]
        ]

        return report

    def _post_to_infinite(self, report: ReportData, md_content: str) -> None:
        try:
            sys_path_dir = str(Path(__file__).parent.parent / "skills" / "infinite" / "scripts")
            import sys
            if sys_path_dir not in sys.path:
                sys.path.insert(0, sys_path_dir)
            from infinite_client import InfiniteClient

            client = InfiniteClient()
            client.register_agent(
                name=self.agent_name,
                bio="Synthesis specialist — generates arXiv-style reports from multi-agent investigations.",
                capabilities=["synthesis", "report-generation", "figure-generation"],
            )
            client.create_post(
                community="science",
                title=report.title or report.topic,
                content=md_content[:4000],
                hypothesis=report.abstract[:500],
                method="Artifact-grounded LLM synthesis + matplotlib figure generation",
                tools_used=["paper_agent", "matplotlib", "pdflatex"],
            )
            print(f"[PaperAgent] Posted to Infinite.")
        except Exception as e:
            logger.warning(f"[PaperAgent] Infinite post failed: {e}")


# =============================================================================
# CLI convenience
# =============================================================================

def setup_paper_agent_profile() -> Path:
    """Write PaperAgent profile to ~/.scienceclaw/profiles/PaperAgent/."""
    profile = {
        "name": "PaperAgent",
        "bio": (
            "Synthesis specialist — reads investigation artifacts and generates "
            "arXiv-style reports with matplotlib figures and LaTeX output."
        ),
        "research": {
            "interests": [
                "scientific synthesis", "cross-domain integration",
                "literature review", "mechanistic modelling",
            ],
            "organisms": [],
            "proteins": [],
            "compounds": [],
        },
        "personality": {
            "curiosity_style": "synthesizer",
            "communication_style": "formal",
        },
        "preferences": {
            "tools": [
                "pubmed", "arxiv", "openalex-database", "biorxiv-database",
                "websearch", "datavis", "scientific-visualization",
                "write-review-paper", "scientific-writing", "statistical-analysis",
            ],
            "exploration_mode": "systematic",
        },
        "community": "science",
        "expertise_preset": "synthesis",
    }
    profile_dir = Path.home() / ".scienceclaw" / "profiles" / "PaperAgent"
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_path = profile_dir / "agent_profile.json"
    profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(f"[PaperAgent] Profile written: {profile_path}")
    return profile_path
