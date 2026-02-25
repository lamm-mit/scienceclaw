#!/usr/bin/env python3
"""
InvestigationConclusion — paper generator from artifacts.

Takes a completed multi-agent investigation (identified by investigation_id or
session_id) and produces a publication-structured output (Methods, Results,
Discussion, Conclusion) grounded strictly in artifact payloads from the
global JSONL store.

Usage:
    from autonomous.investigation_conclusion import InvestigationConclusion

    paper = InvestigationConclusion(agent_name="Orchestrator").conclude(
        session_id="scienceclaw-collab-abc123"
    )
    print(paper.convergence)
    print(paper.conclusion)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PaperOutput dataclass
# ---------------------------------------------------------------------------

@dataclass
class PaperOutput:
    title: str
    abstract: str
    methods: str            # Markdown table
    results: str            # Markdown with subsections + figure refs
    discussion: str         # LLM prose, seeded by payload-derived facts only
    conclusion: str         # Convergence status + quantitative summary
    figures: List[str]      # Absolute paths to generated PNGs
    tables: List[Dict]      # [{name, headers, rows, artifact_ids_used}]
    convergence: Dict       # {converged, reason, coverage_score, confidence}
    artifact_count: int
    agent_count: int
    investigation_id: str


# ---------------------------------------------------------------------------
# ArtifactCollector
# ---------------------------------------------------------------------------

class ArtifactCollector:
    """Loads artifacts from store.jsonl files and the global index."""

    def __init__(self):
        self._base = Path(os.path.expanduser("~/.scienceclaw"))
        self._global_index = self._base / "artifacts" / "global_index.jsonl"

    def collect_index_entries(self, investigation_id: str) -> List[Dict]:
        """Scan global_index.jsonl, return metadata-only entries for investigation."""
        entries = []
        if not self._global_index.exists():
            return entries
        for line in self._global_index.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("investigation_id") == investigation_id:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue
        return entries

    def collect_full_artifacts(self, investigation_id: str) -> List[Any]:
        """Load full artifact objects (with payloads) for the investigation."""
        from artifacts.artifact import ArtifactStore

        index_entries = self.collect_index_entries(investigation_id)
        if not index_entries:
            return []

        # Group artifact IDs by producer agent
        agent_to_ids: Dict[str, List[str]] = {}
        for entry in index_entries:
            agent = entry.get("producer_agent", "unknown")
            aid = entry.get("artifact_id")
            if aid:
                agent_to_ids.setdefault(agent, []).append(aid)

        artifacts = []
        for agent_name, ids in agent_to_ids.items():
            store = ArtifactStore(agent_name)
            id_set = set(ids)
            for artifact in store.list(investigation_id=investigation_id, limit=1000):
                if artifact.artifact_id in id_set:
                    artifacts.append(artifact)

        # Sort by timestamp
        artifacts.sort(key=lambda a: a.timestamp)
        return artifacts

    def collect_session_findings(self, session_id: str, agent_name: str) -> List[Dict]:
        """Return findings list from a collaborative session."""
        try:
            from coordination.session_manager import SessionManager
            mgr = SessionManager(agent_name)
            state = mgr.get_session_state(session_id)
            if state:
                return state.get("findings", [])
        except Exception as e:
            logger.warning(f"Could not load session findings: {e}")
        return []


# ---------------------------------------------------------------------------
# ConvergenceDetector
# ---------------------------------------------------------------------------

COVERAGE_TYPES = [
    "pubmed_results",
    "protein_data",
    "compound_data",
    "admet_prediction",
    "sequence_alignment",
    "synthesis",
    "peer_validation",
]


class ConvergenceDetector:
    """Determines whether the investigation has converged on a solution."""

    def detect(self, artifacts: List[Any], findings: List[Dict]) -> Dict:
        artifact_types = {a.artifact_type for a in artifacts}

        has_synthesis = "synthesis" in artifact_types

        # Validation counts from findings
        confirmed = 0
        challenged = 0
        for finding in findings:
            for v in finding.get("validations", []):
                status = v.get("status", "")
                if status == "confirmed":
                    confirmed += 1
                elif status in ("challenged", "disputed"):
                    challenged += 1
        total_validated = confirmed + challenged
        confirmed_ratio = confirmed / total_validated if total_validated > 0 else 0.0

        # Coverage score
        covered = len(artifact_types & set(COVERAGE_TYPES))
        coverage_score = covered / len(COVERAGE_TYPES)

        # Decision table
        if has_synthesis and confirmed_ratio >= 0.6:
            return {
                "converged": True,
                "confidence": "high",
                "reason": (
                    f"Synthesis artifact present; {confirmed}/{total_validated} "
                    f"findings confirmed ({confirmed_ratio:.0%})"
                ),
                "coverage_score": coverage_score,
            }
        if has_synthesis:
            return {
                "converged": True,
                "confidence": "medium",
                "reason": (
                    f"Synthesis artifact present; limited cross-validation "
                    f"({confirmed}/{total_validated} confirmed)"
                ),
                "coverage_score": coverage_score,
            }
        if coverage_score >= 0.5 and confirmed_ratio >= 0.5:
            return {
                "converged": True,
                "confidence": "medium",
                "reason": (
                    f"Multi-domain coverage {coverage_score:.0%}; "
                    f"majority of findings confirmed ({confirmed_ratio:.0%})"
                ),
                "coverage_score": coverage_score,
            }
        if coverage_score >= 0.3:
            return {
                "converged": False,
                "confidence": "low",
                "reason": (
                    f"Partial coverage {coverage_score:.0%}; "
                    f"investigation incomplete (partial paper generated)"
                ),
                "coverage_score": coverage_score,
            }
        return {
            "converged": False,
            "confidence": "low",
            "reason": (
                f"Insufficient coverage {coverage_score:.0%}; "
                f"too few artifact types ({covered}/{len(COVERAGE_TYPES)})"
            ),
            "coverage_score": coverage_score,
        }


# ---------------------------------------------------------------------------
# CompletionJudge
# ---------------------------------------------------------------------------

@dataclass
class CompletionVerdict:
    complete: bool
    confidence: str          # "high" | "medium" | "low"
    reasoning: str           # 1-2 sentences
    missing_evidence: List[str]  # gaps; empty if complete
    collaboration_score: float = 0.0  # cross-agent edges / total edges (0.0–1.0)


class CompletionJudge:
    """
    LLM-based judge that decides whether an investigation has produced a
    defensible answer to the original research question.

    Reads session findings + artifact coverage and returns a CompletionVerdict.
    Falls back gracefully if LLM is unavailable.
    """

    def __init__(self, agent_name: str = "Orchestrator"):
        self.agent_name = agent_name

    def judge(
        self,
        topic: str,
        findings: List[Dict],
        index_entries: List[Dict],
    ) -> CompletionVerdict:
        n_total = len(findings)
        confirmed_findings = [
            f for f in findings
            if any(v.get("status") == "confirmed" for v in f.get("validations", []))
        ]
        n_confirmed = len(confirmed_findings)

        artifact_types = list({e.get("artifact_type", "unknown") for e in index_entries})
        agents_present = list({e.get("producer_agent", "unknown") for e in index_entries})

        # Build coverage score (reuse COVERAGE_TYPES)
        covered = len(set(artifact_types) & set(COVERAGE_TYPES))
        coverage_score = covered / len(COVERAGE_TYPES) if COVERAGE_TYPES else 0.0

        # Collaboration score: cross-agent edges / total edges
        collab_score = self._collaboration_score(index_entries)

        # Try LLM judge first
        try:
            verdict = self._llm_judge(
                topic, findings, artifact_types, agents_present, n_total, n_confirmed,
                collab_score,
            )
            if verdict is not None:
                return verdict
        except Exception as e:
            logger.warning(f"[CompletionJudge] LLM unavailable: {e}")

        # Fallback: rule-based
        if n_confirmed >= 1 and coverage_score >= 0.3:
            return CompletionVerdict(
                complete=True,
                confidence="low",
                reasoning=(
                    f"Fallback: {n_confirmed} confirmed finding(s), "
                    f"coverage {coverage_score:.0%}."
                ),
                missing_evidence=[],
                collaboration_score=collab_score,
            )
        missing = []
        if n_confirmed == 0:
            missing.append("No independently confirmed findings")
        if coverage_score < 0.3:
            missing.append(
                f"Low artifact coverage ({coverage_score:.0%}); "
                f"present types: {', '.join(artifact_types) or 'none'}"
            )
        return CompletionVerdict(
            complete=False,
            confidence="low",
            reasoning=f"Fallback: insufficient evidence (coverage {coverage_score:.0%}).",
            missing_evidence=missing,
            collaboration_score=collab_score,
        )

    @staticmethod
    def _collaboration_score(index_entries: List[Dict]) -> float:
        """
        Compute (# cross-agent edges) / (# total edges).

        An "edge" exists when an artifact's parent_artifact_ids contains
        another artifact's ID.  A cross-agent edge is one where the parent
        and child belong to different producer_agents.

        Returns 0.0 when there are no edges at all.
        """
        # Build id → agent map
        id_to_agent: Dict[str, str] = {
            e["artifact_id"]: e.get("producer_agent", "unknown")
            for e in index_entries
            if e.get("artifact_id")
        }

        total = 0
        cross = 0
        for entry in index_entries:
            child_id = entry.get("artifact_id")
            child_agent = id_to_agent.get(child_id, "unknown")
            for parent_id in entry.get("parent_artifact_ids", []):
                if parent_id in id_to_agent:
                    total += 1
                    if id_to_agent[parent_id] != child_agent:
                        cross += 1

        return cross / total if total > 0 else 0.0

    def _llm_judge(
        self,
        topic: str,
        findings: List[Dict],
        artifact_types: List[str],
        agents_present: List[str],
        n_total: int,
        n_confirmed: int,
        collab_score: float = 0.0,
    ) -> Optional["CompletionVerdict"]:
        from autonomous.llm_reasoner import LLMScientificReasoner

        finding_lines = []
        for f in findings[:20]:
            result_text = f.get("result", f.get("description", ""))[:120]
            conf = f.get("confidence", 0.0)
            val_status = "unvalidated"
            for v in f.get("validations", []):
                if v.get("status") == "confirmed":
                    val_status = "confirmed"
                    break
                elif v.get("status") in ("challenged", "disputed"):
                    val_status = "challenged"
            finding_lines.append(
                f"  - {result_text} (confidence={conf:.0%}, {val_status})"
            )

        prompt_lines = [
            f"Original question: {topic}",
            "",
            f"Findings posted ({n_total} total, {n_confirmed} confirmed by peer agents):",
        ]
        prompt_lines.extend(finding_lines or ["  (none)"])
        prompt_lines += [
            "",
            f"Artifact coverage: {', '.join(artifact_types) or 'none'}",
            f"Agents participating: {', '.join(agents_present) or 'none'}",
            "",
            "Has this investigation produced a defensible answer to the original question?",
            "Consider: Are multiple independent lines of evidence present? Are key findings",
            "cross-validated? Are the major claims specific and mechanistically grounded?",
            "",
            'Respond in JSON only:',
            '{',
            '  "complete": true/false,',
            '  "confidence": "high"/"medium"/"low",',
            '  "reasoning": "one or two sentences",',
            '  "missing_evidence": ["gap1", "gap2"]',
            '}',
        ]
        prompt = "\n".join(prompt_lines)

        reasoner = LLMScientificReasoner(self.agent_name)
        raw = reasoner._call_llm(prompt, max_tokens=300)
        if not raw:
            return None

        import re
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not json_match:
            return None

        data = json.loads(json_match.group())
        return CompletionVerdict(
            complete=bool(data.get("complete", False)),
            confidence=str(data.get("confidence", "low")),
            reasoning=str(data.get("reasoning", "")),
            missing_evidence=list(data.get("missing_evidence", [])),
            collaboration_score=collab_score,
        )


# ---------------------------------------------------------------------------
# MethodsBuilder
# ---------------------------------------------------------------------------

class MethodsBuilder:
    """Builds a Methods markdown table from index metadata (no payloads)."""

    def build(self, index_entries: List[Dict]) -> Tuple[str, Dict]:
        headers = ["Agent", "Skill", "Artifact Type", "Timestamp (UTC)", "Artifact ID"]
        rows = []
        artifact_ids_used = []

        # Sort by agent then timestamp
        sorted_entries = sorted(
            index_entries,
            key=lambda e: (e.get("producer_agent", ""), e.get("timestamp", ""))
        )

        for entry in sorted_entries:
            aid = entry.get("artifact_id", "")
            artifact_ids_used.append(aid)
            rows.append([
                entry.get("producer_agent", "unknown"),
                entry.get("skill_used", "unknown"),
                entry.get("artifact_type", "unknown"),
                entry.get("timestamp", "")[:19].replace("T", " "),
                aid[:8],
            ])

        if not rows:
            md = "_No artifact index entries found._"
        else:
            header_line = "| " + " | ".join(headers) + " |"
            sep_line = "|" + "|".join(["---"] * len(headers)) + "|"
            row_lines = [
                "| " + " | ".join(str(c) for c in row) + " |"
                for row in rows
            ]
            md = "\n".join([header_line, sep_line] + row_lines)

        table_dict = {
            "name": "Methods",
            "headers": headers,
            "rows": rows,
            "artifact_ids_used": artifact_ids_used,
        }
        return md, table_dict


# ---------------------------------------------------------------------------
# ResultsBuilder
# ---------------------------------------------------------------------------

class ResultsBuilder:
    """Builds Results markdown from full artifact payloads."""

    def build(self, artifacts: List[Any]) -> Tuple[str, List[Dict]]:
        # Group by type
        by_type: Dict[str, List[Any]] = {}
        for a in artifacts:
            by_type.setdefault(a.artifact_type, []).append(a)

        sections = []
        tables = []

        # pubmed_results
        if "pubmed_results" in by_type:
            headers = ["PMID", "Title", "Year", "Journal", "Artifact"]
            rows = []
            ids_used = []
            for a in by_type["pubmed_results"]:
                ids_used.append(a.artifact_id)
                papers = self._extract_list(a.payload, ["papers", "results", "articles"])
                for paper in papers:
                    rows.append([
                        str(paper.get("pmid", paper.get("id", ""))),
                        paper.get("title", "")[:80],
                        str(paper.get("year", paper.get("pub_date", ""))),
                        paper.get("journal", paper.get("source", "")),
                        a.artifact_id[:8],
                    ])
            if rows:
                sections.append(self._md_table("### Literature (PubMed)", headers, rows))
                tables.append({"name": "pubmed_results", "headers": headers,
                                "rows": rows, "artifact_ids_used": ids_used})

        # protein_data
        if "protein_data" in by_type:
            headers = ["Accession", "Name", "Length (aa)", "Mass (Da)", "Key Domains", "Artifact"]
            rows = []
            ids_used = []
            for a in by_type["protein_data"]:
                ids_used.append(a.artifact_id)
                proteins = self._extract_list(a.payload, ["proteins", "results", "entries"])
                # also handle single-protein payload
                if not proteins and "accession" in a.payload:
                    proteins = [a.payload]
                for p in proteins:
                    domains = ", ".join(
                        d.get("name", d) if isinstance(d, dict) else str(d)
                        for d in p.get("domains", p.get("features", []))[:3]
                    )
                    rows.append([
                        p.get("accession", p.get("id", "")),
                        p.get("name", p.get("protein_name", ""))[:60],
                        str(p.get("length", p.get("sequence_length", ""))),
                        str(p.get("mass", p.get("molecular_weight", ""))),
                        domains or "—",
                        a.artifact_id[:8],
                    ])
            if rows:
                sections.append(self._md_table("### Protein Data (UniProt)", headers, rows))
                tables.append({"name": "protein_data", "headers": headers,
                                "rows": rows, "artifact_ids_used": ids_used})

        # compound_data
        if "compound_data" in by_type:
            headers = ["Name", "CID", "Formula", "MW (g/mol)", "XLogP", "SMILES", "Artifact"]
            rows = []
            ids_used = []
            for a in by_type["compound_data"]:
                ids_used.append(a.artifact_id)
                compounds = self._extract_list(a.payload, ["compounds", "results", "hits"])
                if not compounds and "cid" in a.payload:
                    compounds = [a.payload]
                for c in compounds:
                    rows.append([
                        c.get("name", c.get("iupac_name", ""))[:50],
                        str(c.get("cid", c.get("id", ""))),
                        c.get("molecular_formula", c.get("formula", "")),
                        str(c.get("molecular_weight", c.get("mw", ""))),
                        str(c.get("xlogp", c.get("logp", ""))),
                        c.get("canonical_smiles", c.get("smiles", ""))[:30],
                        a.artifact_id[:8],
                    ])
            if rows:
                sections.append(self._md_table("### Compound Data (PubChem/ChEMBL)", headers, rows))
                tables.append({"name": "compound_data", "headers": headers,
                                "rows": rows, "artifact_ids_used": ids_used})

        # admet_prediction
        if "admet_prediction" in by_type:
            headers = ["Compound", "Model", "Task", "Prediction", "Label", "Artifact"]
            rows = []
            ids_used = []
            for a in by_type["admet_prediction"]:
                ids_used.append(a.artifact_id)
                preds = self._extract_list(a.payload, ["predictions", "results"])
                if not preds and "model" in a.payload:
                    preds = [a.payload]
                for pred in preds:
                    rows.append([
                        pred.get("compound", pred.get("smiles", ""))[:30],
                        pred.get("model", ""),
                        pred.get("task", pred.get("task_type", "")),
                        str(pred.get("prediction", pred.get("value", ""))),
                        pred.get("label", str(pred.get("class", ""))),
                        a.artifact_id[:8],
                    ])
            if rows:
                sections.append(self._md_table("### ADMET Predictions (TDC)", headers, rows))
                tables.append({"name": "admet_prediction", "headers": headers,
                                "rows": rows, "artifact_ids_used": ids_used})

        # sequence_alignment
        if "sequence_alignment" in by_type:
            headers = ["Query", "Subject", "E-value", "Bitscore", "Identity (%)", "Artifact"]
            rows = []
            ids_used = []
            for a in by_type["sequence_alignment"]:
                ids_used.append(a.artifact_id)
                hits = self._extract_list(a.payload, ["hits", "alignments", "results"])
                for hit in hits:
                    rows.append([
                        hit.get("query", hit.get("query_id", ""))[:30],
                        hit.get("subject", hit.get("title", hit.get("hit_id", "")))[:40],
                        str(hit.get("evalue", hit.get("e_value", ""))),
                        str(hit.get("bitscore", hit.get("bit_score", ""))),
                        str(hit.get("identity", hit.get("pct_identity", ""))),
                        a.artifact_id[:8],
                    ])
            if rows:
                sections.append(self._md_table("### Sequence Alignments (BLAST)", headers, rows))
                tables.append({"name": "sequence_alignment", "headers": headers,
                                "rows": rows, "artifact_ids_used": ids_used})

        if not sections:
            return "_No structured result data extracted from artifacts._", []

        return "\n\n".join(sections), tables

    @staticmethod
    def _extract_list(payload: Dict, keys: List[str]) -> List[Dict]:
        for key in keys:
            val = payload.get(key)
            if isinstance(val, list):
                return val
        return []

    @staticmethod
    def _md_table(heading: str, headers: List[str], rows: List[List]) -> str:
        header_line = "| " + " | ".join(headers) + " |"
        sep_line = "|" + "|".join(["---"] * len(headers)) + "|"
        row_lines = [
            "| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |"
            for row in rows
        ]
        return "\n".join([heading, header_line, sep_line] + row_lines)


# ---------------------------------------------------------------------------
# FigureGenerator
# ---------------------------------------------------------------------------

class FigureGenerator:
    """Generates summary figures from compound_data and admet_prediction artifacts."""

    def __init__(self, report_dir: Path):
        self.report_dir = report_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, artifacts: List[Any], index_entries: List[Dict] = None) -> List[str]:
        figures = []

        panel_fig = self._rdkit_panel_chart(artifacts)
        if panel_fig:
            figures.append(panel_fig)

        compound_fig = self._compound_scatter(artifacts)
        if compound_fig:
            figures.append(compound_fig)

        admet_fig = self._admet_bar(artifacts)
        if admet_fig:
            figures.append(admet_fig)

        if index_entries:
            dag_fig = self._cross_agent_dependency_graph(index_entries)
            if dag_fig:
                figures.append(dag_fig)

        return figures

    def _rdkit_panel_chart(self, artifacts: List[Any]) -> Optional[str]:
        """Bar chart of MW, logP, QED, TPSA for each compound in the panel."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        rows = []
        for a in artifacts:
            if a.artifact_type not in ("rdkit_properties", "compound_data"):
                continue
            panel = a.payload.get("compounds", [])
            if panel:
                rows.extend(panel)
            elif "compound_name" in a.payload or "smiles" in a.payload:
                rows.append(a.payload)

        if len(rows) < 2:
            return None

        names = [r.get("compound_name", r.get("smiles", "")[:12]) for r in rows]

        def _f(r, *keys):
            for k in keys:
                v = r.get(k)
                try:
                    return float(v) if v is not None else None
                except (TypeError, ValueError):
                    continue
            return None

        props = {
            "MW": [_f(r, "Molecular Weight", "molecular_weight", "MW", "full_mwt") for r in rows],
            "LogP": [_f(r, "LogP", "logP", "MolLogP", "alogp") for r in rows],
            "TPSA": [_f(r, "TPSA", "tpsa", "PSA") for r in rows],
            "QED": [_f(r, "QED Score", "qed", "qed_weighted") for r in rows],
        }
        # Drop props where all values are None
        props = {k: v for k, v in props.items() if any(x is not None for x in v)}
        if not props:
            return None

        n_props = len(props)
        fig, axes = plt.subplots(1, n_props, figsize=(3.5 * n_props, 4))
        if n_props == 1:
            axes = [axes]

        x = np.arange(len(names))
        colors = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63", "#9C27B0"]

        for ax, (prop_name, vals) in zip(axes, props.items()):
            clean = [v if v is not None else 0 for v in vals]
            bars = ax.bar(x, clean, color=colors[:len(names)], alpha=0.85, edgecolor="white")
            ax.set_xticks(x)
            ax.set_xticklabels(names, rotation=35, ha="right", fontsize=8)
            ax.set_ylabel(prop_name)
            ax.set_title(prop_name)
            for bar, val in zip(bars, vals):
                if val is not None:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                            f"{val:.2f}", ha="center", va="bottom", fontsize=7)

        fig.suptitle("BTK Inhibitor Panel — Molecular Properties", fontsize=11, fontweight="bold")
        fig.tight_layout()
        out_path = self.report_dir / "fig_rdkit_panel.png"
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return str(out_path)

    def _compound_scatter(self, artifacts: List[Any]) -> Optional[str]:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        mw_vals = []
        logp_vals = []
        names = []

        for a in artifacts:
            if a.artifact_type != "compound_data":
                continue
            compounds = ResultsBuilder._extract_list(
                a.payload, ["compounds", "results", "hits"]
            )
            if not compounds and "cid" in a.payload:
                compounds = [a.payload]
            for c in compounds:
                try:
                    mw = float(c.get("molecular_weight", c.get("mw", 0)) or 0)
                    xlogp = float(c.get("xlogp", c.get("logp", 0)) or 0)
                    if mw > 0:
                        mw_vals.append(mw)
                        logp_vals.append(xlogp)
                        names.append(c.get("name", c.get("iupac_name", ""))[:15])
                except (TypeError, ValueError):
                    continue

        if len(mw_vals) < 2:
            return None

        out_path = self.report_dir / "fig_compound_scatter.png"
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(mw_vals, logp_vals, color="#2196F3", alpha=0.8, s=60)
        for name, x, y in zip(names, mw_vals, logp_vals):
            ax.annotate(name, (x, y), textcoords="offset points",
                        xytext=(4, 4), fontsize=7)
        ax.set_xlabel("Molecular Weight (g/mol)")
        ax.set_ylabel("XLogP")
        ax.set_title("Compound Space: MW vs XLogP")
        ax.axhline(5, color="#FF5722", linestyle="--", linewidth=0.8,
                   label="Lipinski MW=500 boundary")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return str(out_path)

    def _admet_bar(self, artifacts: List[Any]) -> Optional[str]:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        model_sums: Dict[str, List[float]] = {}

        for a in artifacts:
            if a.artifact_type != "admet_prediction":
                continue
            preds = ResultsBuilder._extract_list(
                a.payload, ["predictions", "results"]
            )
            if not preds and "model" in a.payload:
                preds = [a.payload]
            for pred in preds:
                model = pred.get("model", "unknown")
                try:
                    val = float(pred.get("prediction", pred.get("value", 0)) or 0)
                    model_sums.setdefault(model, []).append(val)
                except (TypeError, ValueError):
                    continue

        if len(model_sums) < 2:
            return None

        models = list(model_sums.keys())
        averages = [sum(v) / len(v) for v in model_sums.values()]

        out_path = self.report_dir / "fig_admet_bar.png"
        fig, ax = plt.subplots(figsize=(max(6, len(models) * 1.2), 4))
        bars = ax.bar(models, averages, color="#4CAF50", alpha=0.85)
        ax.bar_label(bars, fmt="%.3f", padding=2, fontsize=8)
        ax.set_ylabel("Mean Prediction Value")
        ax.set_title("ADMET Predictions by Model")
        ax.tick_params(axis="x", rotation=30)
        fig.tight_layout()
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return str(out_path)


    def _cross_agent_dependency_graph(self, index_entries: List[Dict]) -> Optional[str]:
        """
        Generate a DAG showing how artifact chains cross agent boundaries.

        Only produced when >= 2 distinct agents are present in index_entries.
        Cross-agent edges (src.agent != dst.agent) are colored orange; same-agent
        edges are grey.  One color per agent via tab10.
        """
        unique_agents = {e.get("producer_agent", "unknown") for e in index_entries}
        if len(unique_agents) < 2:
            return None

        try:
            import networkx as nx
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            import matplotlib.cm as cm
        except ImportError as exc:
            logger.warning(f"[FigureGenerator] cross-agent DAG skipped: {exc}")
            return None

        # Build node metadata
        node_meta: Dict[str, Dict] = {}
        for entry in index_entries:
            aid = entry.get("artifact_id")
            if not aid:
                continue
            node_meta[aid] = {
                "producer_agent": entry.get("producer_agent", "unknown"),
                "artifact_type": entry.get("artifact_type", "unknown"),
            }

        G = nx.DiGraph()
        for aid, meta in node_meta.items():
            G.add_node(aid, **meta)

        # Add edges from parent_artifact_ids
        for entry in index_entries:
            aid = entry.get("artifact_id")
            for parent_id in entry.get("parent_artifact_ids", []):
                if parent_id in node_meta and aid in node_meta:
                    G.add_edge(parent_id, aid)

        if G.number_of_nodes() == 0:
            return None

        # Assign one color per unique agent
        agent_list = sorted(unique_agents)
        palette = cm.tab10.colors
        agent_colors = {agent: palette[i % len(palette)] for i, agent in enumerate(agent_list)}

        node_colors = [
            agent_colors.get(node_meta[n]["producer_agent"], "#BDBDBD")
            for n in G.nodes()
        ]

        # Edge colors: cross-agent = orange, same-agent = grey
        edge_colors = []
        edge_widths = []
        for src, dst in G.edges():
            src_agent = node_meta.get(src, {}).get("producer_agent", "")
            dst_agent = node_meta.get(dst, {}).get("producer_agent", "")
            if src_agent != dst_agent:
                edge_colors.append("#E64A19")
                edge_widths.append(2.0)
            else:
                edge_colors.append("#BDBDBD")
                edge_widths.append(0.8)

        # Layout
        try:
            pos = nx.nx_pydot.graphviz_layout(G, prog="dot")
        except Exception:
            pos = nx.spring_layout(G, k=2.5, seed=42)

        # Node labels
        labels = {
            n: f"{node_meta[n]['artifact_type'][:14]}\n{n[:6]}"
            for n in G.nodes()
        }

        fig, ax = plt.subplots(figsize=(max(8, G.number_of_nodes() * 1.2), 6))
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=700,
                               alpha=0.9, ax=ax)
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=6, ax=ax)
        if G.number_of_edges() > 0:
            nx.draw_networkx_edges(
                G, pos,
                edge_color=edge_colors,
                width=edge_widths,
                arrows=True,
                arrowsize=15,
                ax=ax,
            )

        # Legend: one patch per agent
        patches = [
            mpatches.Patch(color=agent_colors[a], label=a) for a in agent_list
        ]
        ax.legend(handles=patches, loc="upper right", fontsize=8, title="Agent")
        ax.set_title("Cross-Agent Artifact Dependency Graph")
        ax.axis("off")
        fig.tight_layout()

        out_path = self.report_dir / "fig_cross_agent_dag.png"
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        logger.info(f"Cross-agent DAG saved: {out_path}")
        return str(out_path)


# ---------------------------------------------------------------------------
# DiscussionWriter
# ---------------------------------------------------------------------------

class DiscussionWriter:
    """Generates discussion prose seeded exclusively from payload-derived facts."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def build(self, artifacts: List[Any], findings: List[Dict]) -> str:
        # Extract payload-derived facts (no LLM speculation at this stage)
        facts = self._extract_facts(artifacts, findings)

        try:
            from autonomous.llm_reasoner import LLMScientificReasoner
            reasoner = LLMScientificReasoner(self.agent_name)
            prompt = self._build_prompt(facts)
            discussion = reasoner._call_llm(prompt, max_tokens=800)
            if discussion and len(discussion) > 50:
                return discussion
        except Exception as e:
            logger.warning(f"LLM discussion unavailable: {e}")

        # Fallback: structured bullet synthesis
        return self._fallback(facts)

    @staticmethod
    def _extract_facts(artifacts: List[Any], findings: List[Dict]) -> Dict:
        paper_titles = []
        protein_info = []
        compound_info = []
        admet_info = []
        confirmed_count = 0
        challenged_count = 0

        for a in artifacts:
            if a.artifact_type == "pubmed_results":
                papers = ResultsBuilder._extract_list(
                    a.payload, ["papers", "results", "articles"]
                )
                for p in papers[:5]:
                    title = p.get("title", "")
                    if title:
                        paper_titles.append(title)
            elif a.artifact_type == "protein_data":
                proteins = ResultsBuilder._extract_list(
                    a.payload, ["proteins", "results", "entries"]
                )
                if not proteins and "accession" in a.payload:
                    proteins = [a.payload]
                for p in proteins[:3]:
                    acc = p.get("accession", p.get("id", ""))
                    name = p.get("name", p.get("protein_name", ""))
                    mw = p.get("mass", p.get("molecular_weight", ""))
                    if name:
                        protein_info.append(f"{name} ({acc}), {mw} Da")
            elif a.artifact_type == "compound_data":
                compounds = ResultsBuilder._extract_list(
                    a.payload, ["compounds", "results", "hits"]
                )
                if not compounds and "cid" in a.payload:
                    compounds = [a.payload]
                for c in compounds[:3]:
                    name = c.get("name", c.get("iupac_name", ""))
                    mw = c.get("molecular_weight", c.get("mw", ""))
                    xlogp = c.get("xlogp", c.get("logp", ""))
                    if name:
                        compound_info.append(f"{name} (MW={mw}, XLogP={xlogp})")
            elif a.artifact_type == "admet_prediction":
                preds = ResultsBuilder._extract_list(
                    a.payload, ["predictions", "results"]
                )
                if not preds and "model" in a.payload:
                    preds = [a.payload]
                for pred in preds[:4]:
                    model = pred.get("model", "")
                    val = pred.get("prediction", pred.get("value", ""))
                    label = pred.get("label", pred.get("class", ""))
                    if model:
                        admet_info.append(f"{model}: {val} ({label})")

        for finding in findings:
            for v in finding.get("validations", []):
                if v.get("status") == "confirmed":
                    confirmed_count += 1
                elif v.get("status") in ("challenged", "disputed"):
                    challenged_count += 1

        return {
            "paper_titles": paper_titles,
            "protein_info": protein_info,
            "compound_info": compound_info,
            "admet_info": admet_info,
            "confirmed_count": confirmed_count,
            "challenged_count": challenged_count,
        }

    @staticmethod
    def _build_prompt(facts: Dict) -> str:
        lines = ["You are a scientific writer. Write a discussion section (4-6 paragraphs)."]
        lines.append("Use ONLY the following data. Do not describe the investigation process.\n")

        if facts["paper_titles"]:
            lines.append("Literature surveyed:")
            for t in facts["paper_titles"]:
                lines.append(f"  - {t}")

        if facts["protein_info"]:
            lines.append("\nProteins characterized:")
            for p in facts["protein_info"]:
                lines.append(f"  - {p}")

        if facts["compound_info"]:
            lines.append("\nCompounds analyzed:")
            for c in facts["compound_info"]:
                lines.append(f"  - {c}")

        if facts["admet_info"]:
            lines.append("\nADMET predictions:")
            for a in facts["admet_info"]:
                lines.append(f"  - {a}")

        lines.append(
            f"\nFinding validation: {facts['confirmed_count']} confirmed, "
            f"{facts['challenged_count']} challenged."
        )
        lines.append(
            "\nInstructions: synthesize the above findings, identify mechanistic "
            "convergence, cite specific values, note remaining gaps, suggest "
            "computational follow-up experiments. Be concise and quantitative."
        )
        return "\n".join(lines)

    @staticmethod
    def _fallback(facts: Dict) -> str:
        parts = []
        if facts["paper_titles"]:
            parts.append(
                "**Literature context:** " + "; ".join(facts["paper_titles"][:3]) + "."
            )
        if facts["protein_info"]:
            parts.append(
                "**Proteins identified:** " + "; ".join(facts["protein_info"]) + "."
            )
        if facts["compound_info"]:
            parts.append(
                "**Compounds characterized:** " + "; ".join(facts["compound_info"]) + "."
            )
        if facts["admet_info"]:
            parts.append(
                "**ADMET profile:** " + "; ".join(facts["admet_info"]) + "."
            )
        parts.append(
            f"**Validation consensus:** {facts['confirmed_count']} confirmed, "
            f"{facts['challenged_count']} challenged findings."
        )
        return "\n\n".join(parts) if parts else "_No discussion data available._"


# ---------------------------------------------------------------------------
# ConclusionWriter
# ---------------------------------------------------------------------------

class ConclusionWriter:
    """Generates conclusion from convergence data and session findings — no LLM."""

    def build(
        self,
        convergence: Dict,
        artifacts: List[Any],
        findings: List[Dict],
    ) -> str:
        paras = []

        # Para 1: convergence status
        status = "converged" if convergence.get("converged") else "did not converge"
        confidence = convergence.get("confidence", "unknown")
        reason = convergence.get("reason", "")
        paras.append(
            f"This investigation {status} with **{confidence}** confidence. {reason}"
        )

        # Para 2: quantitative artifact summary
        type_counts: Dict[str, int] = {}
        for a in artifacts:
            type_counts[a.artifact_type] = type_counts.get(a.artifact_type, 0) + 1
        unique_agents = len({a.producer_agent for a in artifacts})

        validated_findings = sum(
            1 for f in findings
            if any(v.get("status") == "confirmed" for v in f.get("validations", []))
        )

        type_summary = ", ".join(
            f"{count} {atype}" for atype, count in sorted(type_counts.items())
        )
        paras.append(
            f"The investigation produced **{len(artifacts)} artifacts** across "
            f"{unique_agents} agent(s): {type_summary}. "
            f"**{validated_findings}** of {len(findings)} findings were independently validated."
        )

        # Para 3: most specific confirmed finding
        best_finding = self._best_finding(findings)
        if best_finding:
            result_text = best_finding.get("result", "")
            confidence_val = best_finding.get("confidence", 0)
            paras.append(
                f"The highest-confidence result ({confidence_val:.0%} confidence): "
                f"{result_text}"
            )

        return "\n\n".join(paras)

    @staticmethod
    def _best_finding(findings: List[Dict]) -> Optional[Dict]:
        confirmed = [
            f for f in findings
            if any(v.get("status") == "confirmed" for v in f.get("validations", []))
        ]
        if not confirmed:
            confirmed = findings
        if not confirmed:
            return None
        return max(confirmed, key=lambda f: f.get("confidence", 0))


# ---------------------------------------------------------------------------
# InvestigationConclusion — main orchestrator
# ---------------------------------------------------------------------------

class InvestigationConclusion:
    """
    Orchestrates paper generation from completed investigation artifacts.

    Args:
        agent_name: Used for SessionManager access and LLM calls.
    """

    def __init__(self, agent_name: str = "Orchestrator"):
        self.agent_name = agent_name
        self._base = Path(os.path.expanduser("~/.scienceclaw"))

    def conclude(
        self,
        investigation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> PaperOutput:
        """
        Generate a PaperOutput from all artifacts for the investigation.

        Provide either investigation_id or session_id (or topic to derive the slug).
        """
        # Resolve investigation_id
        if investigation_id is None:
            if session_id:
                # Try to derive from session state
                investigation_id = self._resolve_investigation_id(session_id, topic)
            elif topic:
                investigation_id = self._slugify(topic)
            else:
                raise ValueError("Provide investigation_id, session_id, or topic")

        logger.info(f"Generating paper for investigation: {investigation_id}")

        # 1. Collect data
        collector = ArtifactCollector()
        index_entries = collector.collect_index_entries(investigation_id)
        artifacts = collector.collect_full_artifacts(investigation_id)
        findings = (
            collector.collect_session_findings(session_id, self.agent_name)
            if session_id else []
        )

        logger.info(
            f"Collected {len(artifacts)} artifacts from "
            f"{len({a.producer_agent for a in artifacts})} agents, "
            f"{len(findings)} findings"
        )

        # 2. Convergence
        detector = ConvergenceDetector()
        convergence = detector.detect(artifacts, findings)
        logger.info(f"Convergence: {convergence['confidence']} — {convergence['reason']}")

        # 3. Methods, Results, Figures (all parallelisable but run sequentially)
        report_dir = self._base / "reports" / investigation_id
        report_dir.mkdir(parents=True, exist_ok=True)

        methods_builder = MethodsBuilder()
        methods_md, methods_table = methods_builder.build(index_entries)

        results_builder = ResultsBuilder()
        results_md, result_tables = results_builder.build(artifacts)

        fig_gen = FigureGenerator(report_dir)
        figures = fig_gen.generate(artifacts, index_entries)

        # 4. Discussion (LLM-powered)
        disc_writer = DiscussionWriter(self.agent_name)
        discussion = disc_writer.build(artifacts, findings)

        # 5. Conclusion (pure logic)
        conc_writer = ConclusionWriter()
        conclusion = conc_writer.build(convergence, artifacts, findings)

        # 6. Abstract (short LLM call)
        abstract = self._generate_abstract(
            investigation_id, artifacts, findings, convergence
        )

        # 7. Title
        title = self._format_title(investigation_id, convergence)

        # 8. Figures section in results
        if figures:
            fig_lines = ["\n\n### Figures"]
            for fig_path in figures:
                fig_name = Path(fig_path).name
                fig_lines.append(f"- `{fig_name}`: {fig_path}")
            results_md += "\n".join(fig_lines)

        # 9. All tables
        all_tables = [methods_table] + result_tables

        # 10. Assemble PaperOutput
        paper = PaperOutput(
            title=title,
            abstract=abstract,
            methods=methods_md,
            results=results_md,
            discussion=discussion,
            conclusion=conclusion,
            figures=figures,
            tables=all_tables,
            convergence=convergence,
            artifact_count=len(artifacts),
            agent_count=len({a.producer_agent for a in artifacts}),
            investigation_id=investigation_id,
        )

        # 11. Save outputs
        self._save(paper, report_dir)

        return paper

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_investigation_id(
        self, session_id: str, topic: Optional[str]
    ) -> str:
        """Try to extract investigation_id from session state, fallback to topic slug."""
        try:
            from coordination.session_manager import SessionManager
            mgr = SessionManager(self.agent_name)
            state = mgr.get_session_state(session_id)
            if state:
                slug = self._slugify(state.get("topic", topic or session_id))
                return slug
        except Exception:
            pass
        return self._slugify(topic or session_id)

    @staticmethod
    def _slugify(text: str) -> str:
        import re
        return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:64]

    def _generate_abstract(
        self,
        investigation_id: str,
        artifacts: List[Any],
        findings: List[Dict],
        convergence: Dict,
    ) -> str:
        type_counts: Dict[str, int] = {}
        for a in artifacts:
            type_counts[a.artifact_type] = type_counts.get(a.artifact_type, 0) + 1

        # Gather first 3 paper titles for context
        paper_titles = []
        for a in artifacts:
            if a.artifact_type == "pubmed_results":
                papers = ResultsBuilder._extract_list(
                    a.payload, ["papers", "results", "articles"]
                )
                for p in papers[:3]:
                    t = p.get("title", "")
                    if t:
                        paper_titles.append(t)
                if len(paper_titles) >= 3:
                    break

        type_summary = ", ".join(
            f"{count} {t}" for t, count in sorted(type_counts.items())
        )
        agent_count = len({a.producer_agent for a in artifacts})
        validated = sum(
            1 for f in findings
            if any(v.get("status") == "confirmed" for v in f.get("validations", []))
        )

        prompt = (
            f"Write a 3-sentence abstract for a multi-agent scientific investigation.\n"
            f"Topic: {investigation_id.replace('_', ' ')}\n"
            f"Artifacts: {type_summary}\n"
            f"Agents: {agent_count}\n"
            f"Validated findings: {validated}/{len(findings)}\n"
            f"Convergence: {convergence.get('reason', 'unknown')}\n"
            f"Key papers: {'; '.join(paper_titles[:3])}\n"
            f"Be concise, quantitative, and factual."
        )

        try:
            from autonomous.llm_reasoner import LLMScientificReasoner
            reasoner = LLMScientificReasoner(self.agent_name)
            abstract = reasoner._call_llm(prompt, max_tokens=200)
            if abstract and len(abstract) > 30:
                return abstract
        except Exception as e:
            logger.warning(f"Abstract LLM unavailable: {e}")

        # Fallback abstract
        return (
            f"A multi-agent computational investigation of "
            f"'{investigation_id.replace('_', ' ')}' produced {len(artifacts)} artifacts "
            f"({type_summary}) across {agent_count} agent(s). "
            f"{validated} of {len(findings)} findings were independently validated. "
            f"Convergence status: {convergence.get('confidence', 'unknown')} — "
            f"{convergence.get('reason', '')}."
        )

    @staticmethod
    def _format_title(investigation_id: str, convergence: Dict) -> str:
        topic = investigation_id.replace("_", " ").title()
        confidence = convergence.get("confidence", "")
        if confidence == "high":
            return f"{topic}: Convergent Multi-Agent Analysis"
        elif confidence == "medium":
            return f"{topic}: Multi-Agent Computational Investigation"
        return f"{topic}: Preliminary Multi-Agent Analysis"

    def _save(self, paper: PaperOutput, report_dir: Path) -> None:
        """Save paper.md and paper.json to the report directory."""
        import dataclasses

        # Markdown
        md_lines = [
            f"# {paper.title}\n",
            f"**Investigation ID:** `{paper.investigation_id}`  ",
            f"**Generated:** {datetime.utcnow().isoformat()}Z  ",
            f"**Artifacts:** {paper.artifact_count}  ",
            f"**Agents:** {paper.agent_count}  ",
            f"**Convergence:** {paper.convergence.get('confidence', 'unknown')} — "
            f"{paper.convergence.get('reason', '')}\n",
            "---\n",
            "## Abstract\n",
            paper.abstract,
            "\n\n## Methods\n",
            paper.methods,
            "\n\n## Results\n",
            paper.results,
            "\n\n## Discussion\n",
            paper.discussion,
            "\n\n## Conclusion\n",
            paper.conclusion,
        ]
        md_path = report_dir / "paper.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")
        logger.info(f"Paper saved to {md_path}")

        # JSON (dataclass → dict, replace non-serialisable with str)
        try:
            paper_dict = dataclasses.asdict(paper)
            json_path = report_dir / "paper.json"
            json_path.write_text(
                json.dumps(paper_dict, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Could not save paper.json: {e}")
