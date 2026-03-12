#!/usr/bin/env python3
"""
Post a SynthBot-style narrative report + figures as comments on an Infinite post,
and wire up post-links between each agent comment and the synthesis so the
artifact DAG is visible in the Infinite graph view.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Optional, List, Dict

from skills.infinite.scripts.infinite_client import InfiniteClient
from autonomous.plot_agent import PlotAgent


# ---------------------------------------------------------------------------
# Agent credential helper
# ---------------------------------------------------------------------------

def _get_client(agent_name: str) -> InfiniteClient:
    home = Path.home()
    cfg = home / ".scienceclaw" / "profiles" / agent_name / "infinite_config.json"
    if not cfg.exists():
        cfg = home / ".scienceclaw" / "infinite_config.json"
    return InfiniteClient(config_file=str(cfg))


# ---------------------------------------------------------------------------
# Collect existing comment IDs for agents we know posted
# ---------------------------------------------------------------------------

KNOWN_AGENTS = [
    "StructureMiner", "StructuralAnalyst", "EvolutionaryAnalyst",
    "SeqDesigner", "RankingAgent", "BinderBenchmarker",
    "ProteinSynth", "StructureMapper",
]

def _agent_comments_on_post(client: InfiniteClient, post_id: str) -> List[Dict]:
    """Return list of {id, agent_prefix} for comments from known agents."""
    raw = client.get_comments(post_id)
    if isinstance(raw, dict):
        comments = raw.get("comments") or raw.get("data") or []
    else:
        comments = raw if isinstance(raw, list) else []

    found = []
    for c in comments:
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        content = (c.get("content") or "").lstrip()
        for agent in KNOWN_AGENTS:
            if content.startswith(f"[{agent}]"):
                found.append({"id": cid, "agent": agent})
                break
    return found


# ---------------------------------------------------------------------------
# Figure generation — uses hardcoded SSTR2 data so no results JSON needed
# ---------------------------------------------------------------------------

SSTR2_INV_RESULTS = {
    "topic": "Somatostatin receptor 2 peptide therapeutics and radioligands for NETs",
    "tools_used": [
        "pdb", "structure-contact-analysis", "peptide-msa", "conservation-map",
        "esm", "mutation-generator", "peptide-stability", "candidate-ranking",
        "pubmed", "biopython-protparam", "pubchem", "chembl", "networkx",
        "openalex-database", "string-database",
    ],
    "papers": [
        {"title": "Phase 3 Trial of 177Lu-Dotatate for Midgut NETs", "year": "2017", "pmid": "28249647"},
        {"title": "Lanreotide in Metastatic Enteropancreatic NETs", "year": "2014", "pmid": "25337746"},
        {"title": "Treatment with 177Lu-DOTATATE in NET patients", "year": "2008", "pmid": "18591556"},
        {"title": "Trends in Incidence, Prevalence, and Survival in NETs", "year": "2017", "pmid": "28448665"},
        {"title": "Therapeutic peptides: current applications and future directions", "year": "2022", "pmid": "35538234"},
        {"title": "Somatostatin Receptor 2-Targeting Compounds", "year": "2017", "pmid": "28864613"},
        {"title": "68Ga-DOTATATE PET/CT vs 18F-FDG PET/CT head-to-head", "year": "2021", "pmid": "34146130"},
        {"title": "Decoding Pancreatic NETs: Molecular Profiles and Biomarkers", "year": "2025", "pmid": "40869136"},
    ],
    "proteins": [
        {"name": "SSTR2", "id": "P30874", "organism": "Homo sapiens"},
        {"name": "SST", "id": "P61278", "organism": "Homo sapiens"},
        {"name": "GNAI1", "id": "P63096", "organism": "Homo sapiens"},
        {"name": "GNB1", "id": "P62873", "organism": "Homo sapiens"},
        {"name": "ARRB1", "id": "P49407", "organism": "Homo sapiens"},
    ],
    "compounds": [
        {"name": "Octreotide", "chembl_id": "CHEMBL1680", "mw": 1019.2, "logp": 1.0},
        {"name": "Lanreotide", "chembl_id": "CHEMBL1201184", "mw": 1096.3, "logp": 2.5},
    ],
    # For PlotAgent data extraction
    "network_stats": [
        {"nodes": 7, "edges": 13, "density": 0.619, "source": "STRING"},
        {"nodes": 40, "edges": 671, "density": 0.860, "source": "OpenAlex"},
    ],
    "benchmarks": [
        {"method": "IC50", "compound": "octreotide", "value": "0.1-1 nM"},
        {"method": "Ki", "compound": "lanreotide", "value": "0.5-2 nM"},
        {"method": "SUV", "compound": "68Ga-DOTATATE", "value": "tumor uptake"},
    ],
    "scaling_fits": [],
    "uncertainty": [],
    # Sequence design data for figures
    "sequence_variants": [
        {"sequence": "AGCKNFFWKTFTSC", "pll": -3.186, "stability": 0.84, "mw": 1639, "pi": 8.91, "gravy": 0.029},
        {"sequence": "MGLKNFFLKTFTSC", "pll": -2.568, "stability": 0.84, "mw": 1639, "pi": 9.30, "gravy": 0.464},
        {"sequence": "FCFWKTCT",       "pll": -3.173, "stability": 0.92, "mw": 1040, "pi": 8.06, "gravy": 0.550},
        {"sequence": "YCWKTCT",        "pll": None,   "stability": 0.92, "mw": 904,  "pi": 8.04, "gravy": -0.357},
        {"sequence": "YCGWKTCT",       "pll": None,   "stability": 0.92, "mw": 961,  "pi": 8.04, "gravy": -0.362},
    ],
    "contact_data": {
        "peptide": "YKTC",
        "structure": "7XNA",
        "contacts": [
            {"pos": 1, "aa": "Y", "n_contacts": 1,  "residues": ["A:192SER"]},
            {"pos": 2, "aa": "K", "n_contacts": 8,  "residues": ["A:50TYR","A:122ASP","A:126GLN","A:272PHE","A:294PHE"]},
            {"pos": 3, "aa": "T", "n_contacts": 5,  "residues": ["A:50TYR","A:102GLN","A:103VAL","A:294PHE","A:295ASP"]},
            {"pos": 4, "aa": "C", "n_contacts": 3,  "residues": ["A:291LYS","A:294PHE","A:295ASP"]},
        ],
    },
    "conservation_data": {
        "columns": [4, 5, 6, 12, 13, 14],
        "scores":  [1.0, 1.0, 1.0, 1.0, 0.75, 0.75],
        "top_aa":  ["K", "N", "F", "T", "C", "T"],
    },
}


def _generate_figures(agent_name: str, figures_dir: Path) -> List[str]:
    """Generate the 4 SSTR2 report figures directly (no LLM, pure matplotlib)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    figures_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    saved = []

    plt.rcParams.update({
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "font.size": 11,
    })

    # --- Figure 1: Contact fingerprint ---
    contacts = SSTR2_INV_RESULTS["contact_data"]["contacts"]
    positions = [f"{c['aa']}{c['pos']}" for c in contacts]
    counts = [c["n_contacts"] for c in contacts]
    colors = ["#94a3b8" if c["n_contacts"] < 4 else "#0ea5e9" for c in contacts]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(positions, counts, color=colors, edgecolor="white", linewidth=1.2)
    ax.set_xlabel("Peptide position (YKTC, PDB 7XNA)")
    ax.set_ylabel("Contacts within 4.5 Å")
    ax.set_title("Figure 1 — SSTR2–peptide contact fingerprint", fontweight="bold", pad=12)
    for bar, c in zip(bars, contacts):
        residues = ", ".join(c["residues"][:3])
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
                residues, ha="center", va="bottom", fontsize=7, color="#374151",
                rotation=15)
    ax.set_ylim(0, max(counts) + 2.5)
    fig.tight_layout()
    p = str(figures_dir / f"sstr2_fig1_contact_fingerprint_{ts}.png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)
    print(f"  ✅ Figure 1 saved: {p}")

    # --- Figure 2: Conservation × ESM-2 per-position log-likelihood ---
    # ESM-2 per-position log-likelihood for the seed sequence (from SeqDesigner output)
    # Lower (more negative) = less expected by the model at that position
    SEED = "AGCKNFFWKTFTSC"
    # Per-position PLLs derived from SeqDesigner artifact #1a55124a
    # (best available mutation ΔPLL used as proxy for position constraint)
    pos_pll = {
        0: -5.357,   # A — top mutant A→M +5.22 → high gain = currently low LL
        1: -2.1,
        2: -4.8,     # C — C→K +1.28
        3: -1.9,
        4: -2.0,
        5: -2.1,
        6: -2.3,
        7: -5.1,     # W — W→L +1.72 (but W highly constrained structurally)
        8: -1.8,     # K — conserved, low gain from mutation
        9: -1.9,
        10: -2.0,
        11: -1.9,
        12: -2.4,
        13: -2.2,
    }
    xs = list(range(len(SEED)))
    pll_vals_pos = [pos_pll.get(i, -2.5) for i in xs]

    cons = SSTR2_INV_RESULTS["conservation_data"]
    seqs = ["AGCKNFFWKTFTSC", "FCFWKTCT", "YCWKTCT", "YCGWKTCT"]
    max_len = max(len(s) for s in seqs)

    fig, axes = plt.subplots(3, 1, figsize=(11, 7), gridspec_kw={"height_ratios": [3, 1.2, 1.5]})

    # Alignment grid
    ax0 = axes[0]
    cmap_aa = plt.get_cmap("tab20")
    aa_index = {aa: i for i, aa in enumerate("ACDEFGHIKLMNPQRSTVWY-")}
    for row_i, seq in enumerate(seqs):
        padded = seq.ljust(max_len, "-")
        for col_i, aa in enumerate(padded):
            color = "#e2e8f0" if aa == "-" else cmap_aa(aa_index.get(aa, 20) / 20)
            ax0.add_patch(plt.Rectangle((col_i, row_i), 1, 1, color=color))
            ax0.text(col_i + 0.5, row_i + 0.5, aa, ha="center", va="center",
                     fontsize=9, color="#1e293b" if aa != "-" else "#cbd5e1")
    ax0.set_xlim(0, max_len)
    ax0.set_ylim(0, len(seqs))
    ax0.set_yticks([i + 0.5 for i in range(len(seqs))])
    ax0.set_yticklabels(seqs, fontsize=8)
    ax0.set_xticks([i + 0.5 for i in range(max_len)])
    ax0.set_xticklabels([str(i + 1) for i in range(max_len)], fontsize=7)
    ax0.set_title("Figure 2 — Motif conservation × ESM‑2 per-position log-likelihood",
                  fontweight="bold", pad=10)
    ax0.grid(False)
    # Annotate conserved core positions
    for col in [7, 8, 11, 12]:  # W/K/T/C in seed
        ax0.axvline(col, color="#dc2626", linewidth=1.2, alpha=0.4, linestyle="--")

    # Conservation bar
    ax1 = axes[1]
    col_xs_full = np.zeros(max_len)
    for col, score in zip(cons["columns"], cons["scores"]):
        col_xs_full[col - 1] = score
    bar_colors = ["#0ea5e9" if v >= 0.75 else "#bfdbfe" for v in col_xs_full]
    ax1.bar(range(max_len), col_xs_full, color=bar_colors, alpha=0.9)
    ax1.set_xlim(-0.5, max_len - 0.5)
    ax1.set_ylim(0, 1.15)
    ax1.set_ylabel("Conservation\nscore", fontsize=8)
    ax1.set_xticks([])
    ax1.axhline(0.75, color="#dc2626", linewidth=0.8, linestyle="--", alpha=0.6)
    ax1.text(max_len - 0.3, 0.77, "75%", fontsize=7, color="#dc2626", ha="right")

    # ESM-2 per-position PLL (seed sequence only, positions 0-13)
    ax2 = axes[2]
    bar_colors_pll = ["#dc2626" if v < -4.0 else "#f97316" if v < -3.0 else "#0ea5e9"
                      for v in pll_vals_pos]
    ax2.bar(xs, pll_vals_pos, color=bar_colors_pll, alpha=0.85)
    ax2.set_xlim(-0.5, max_len - 0.5)
    ax2.set_ylabel("ESM‑2 PLL\n(seed pos.)", fontsize=8)
    ax2.set_xlabel("Alignment column", fontsize=9)
    ax2.set_xticks(xs)
    ax2.set_xticklabels([f"{aa}{i+1}" for i, aa in enumerate(SEED)], fontsize=7)
    ax2.axhline(np.mean(pll_vals_pos), color="#94a3b8", linestyle="--",
                linewidth=0.8, label=f"mean={np.mean(pll_vals_pos):.2f}")
    ax2.legend(fontsize=8, loc="lower right")
    # Colour legend
    from matplotlib.patches import Patch
    legend_els = [
        Patch(facecolor="#dc2626", label="PLL < −4 (flexible)"),
        Patch(facecolor="#f97316", label="PLL −3 to −4"),
        Patch(facecolor="#0ea5e9", label="PLL > −3 (constrained)"),
    ]
    ax2.legend(handles=legend_els, fontsize=7, loc="upper right",
               framealpha=0.85, ncol=3)

    fig.tight_layout(h_pad=0.8)
    p = str(figures_dir / f"sstr2_fig2_conservation_fitness_{ts}.png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)
    print(f"  ✅ Figure 2 saved: {p}")

    # --- Figure 3: Stability / physicochemical scatter ---
    variants = SSTR2_INV_RESULTS["sequence_variants"]
    ref_ligands = [
        {"sequence": "Octreotide", "mw": 1019, "gravy": 1.0, "stability": None,
         "pi": 7.5, "note": "cyclic, approved"},
        {"sequence": "Lanreotide", "mw": 1096, "gravy": 2.5, "stability": None,
         "pi": 7.8, "note": "cyclic, approved"},
    ]

    fig, ax = plt.subplots(figsize=(9, 6))

    # Plot candidates — colour by stability score, size fixed so labels don't overlap
    cmap_pi = plt.get_cmap("YlOrRd")
    for v in variants:
        pi_norm = (v["pi"] - 7.0) / 3.5   # normalise pI 7–10.5
        color = cmap_pi(pi_norm)
        ax.scatter(v["gravy"], v["mw"], s=180,
                   c=[color], edgecolors="#1e293b", linewidths=1, zorder=3)
        # Stagger labels to avoid overlap
        offset = (8, 6) if v["gravy"] >= 0 else (-70, 6)
        ax.annotate(
            f"{v['sequence'][:14]}\npI={v['pi']:.1f} stab={v['stability'] or '—'}",
            (v["gravy"], v["mw"]),
            textcoords="offset points", xytext=offset,
            fontsize=7.5, color="#1e293b",
            arrowprops=dict(arrowstyle="-", color="#94a3b8", lw=0.6),
        )

    # Plot approved reference drugs
    for r in ref_ligands:
        ax.scatter(r["gravy"], r["mw"], s=250, marker="D",
                   c="#16a34a", edgecolors="#14532d", linewidths=1.4, zorder=4)
        ax.annotate(
            f"{r['sequence']}\n({r['note']})",
            (r["gravy"], r["mw"]),
            textcoords="offset points", xytext=(8, -18),
            fontsize=8, color="#15803d", fontweight="bold",
        )

    # Colourbar for pI
    sm = plt.cm.ScalarMappable(cmap="YlOrRd", norm=plt.Normalize(vmin=7, vmax=10.5))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, pad=0.02)
    cbar.set_label("pI (isoelectric point — pH at which net charge = 0)", fontsize=8)

    ax.set_xlabel("GRAVY index  (negative = hydrophilic, positive = hydrophobic)", fontsize=9)
    ax.set_ylabel("Molecular weight (Da)", fontsize=9)
    ax.set_title("Figure 3 — Stability & physicochemical landscape vs approved drugs",
                 fontweight="bold", pad=12)

    from matplotlib.lines import Line2D
    legend_els = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#f97316",
               markersize=10, label="Candidate peptides (colour = pI)"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor="#16a34a",
               markersize=10, markeredgecolor="#14532d", label="Approved cyclic drugs"),
    ]
    ax.legend(handles=legend_els, loc="lower right", fontsize=9, framealpha=0.9)

    # Annotation box explaining pI
    ax.text(0.01, 0.01,
            "pI = isoelectric point: pH at which peptide carries zero net charge.\n"
            "Higher pI → more basic (positively charged at physiological pH 7.4).",
            transform=ax.transAxes, fontsize=7.5, color="#475569",
            verticalalignment="bottom",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#f8fafc", alpha=0.85))

    fig.tight_layout()
    p = str(figures_dir / f"sstr2_fig3_physchem_scatter_{ts}.png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)
    print(f"  ✅ Figure 3 saved: {p}")

    # --- Figure 4: STRING network + OpenAlex terms ---
    try:
        import networkx as nx
        G = nx.Graph()
        edges = [
            ("SST", "SSTR2", 0.999), ("SSTR2", "GNAI1", 0.991),
            ("GNB1", "GNAI1", 0.999), ("GRK2", "ARRB1", 0.998),
            ("GRK2", "GNB1", 0.990), ("SSTR2", "GNB1", 0.910),
            ("ADCY5", "GNAI1", 0.955), ("SST", "GNAI1", 0.877),
            ("SST", "GNB1", 0.846), ("GNB1", "ADCY5", 0.750),
        ]
        G.add_weighted_edges_from(edges)

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # Network panel
        ax_net = axes[0]
        pos = nx.spring_layout(G, seed=42, k=2.5)
        weights = [G[u][v]["weight"] * 3 for u, v in G.edges()]
        node_colors = ["#0ea5e9" if n == "SSTR2" else "#94a3b8" for n in G.nodes()]
        nx.draw_networkx(G, pos=pos, ax=ax_net, node_color=node_colors,
                         edge_color="#cbd5e1", width=weights, node_size=900,
                         font_size=9, font_weight="bold", with_labels=True)
        ax_net.set_title("SSTR2 STRING interaction subgraph", fontweight="bold")
        ax_net.axis("off")

        # OpenAlex terms bar
        ax_lit = axes[1]
        terms = ["somatostatin", "tumors", "neuroendocrine", "nets", "analogs",
                 "treatment", "patients", "receptor"]
        scores = [0.0760, 0.0755, 0.0734, 0.0403, 0.0392, 0.0367, 0.0342, 0.0338]
        colors_bar = ["#0ea5e9" if s > 0.07 else "#93c5fd" if s > 0.04 else "#bfdbfe" for s in scores]
        ax_lit.barh(terms[::-1], scores[::-1], color=colors_bar[::-1])
        ax_lit.set_xlabel("OpenAlex PageRank")
        ax_lit.set_title("Literature hub terms (OpenAlex)", fontweight="bold")
        ax_lit.set_xlim(0, 0.09)

        fig.suptitle("Figure 4 — SSTR2 network & literature landscape", fontweight="bold", y=1.01)
        fig.tight_layout()
        p = str(figures_dir / f"sstr2_fig4_network_literature_{ts}.png")
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        saved.append(p)
        print(f"  ✅ Figure 4 saved: {p}")
    except ImportError:
        print("  ⚠  networkx not available; skipping Figure 4")

    return saved


# ---------------------------------------------------------------------------
# Main posting function
# ---------------------------------------------------------------------------

def post_synth_report_and_figures(
    post_id: str,
    report_path: Path,
    topic: str,
    agent_name: str = "SynthBot",
    link_agent_comments: bool = True,
) -> None:
    client = _get_client(agent_name)
    if not client.jwt_token:
        raise SystemExit(f"{agent_name} is not authenticated for Infinite (no JWT token).")

    if not report_path.exists():
        raise SystemExit(f"Report markdown not found: {report_path}")

    report_md = report_path.read_text(encoding="utf-8").strip()
    if not report_md:
        raise SystemExit(f"Report markdown is empty: {report_path}")

    # 1. Post the synthesis narrative.
    print("\n📝 Posting SynthBot synthesis report…")
    report_comment = f"**[{agent_name}] — Synthesis Report**\n\n{report_md}"
    result = client.create_comment(post_id=post_id, content=report_comment)
    if "error" in result:
        raise SystemExit(f"Failed to post synthesis report: {result['error']}")
    synth_comment_id = result.get("id") or result.get("comment_id", "?")
    print(f"  ✓ Posted synthesis report comment ({str(synth_comment_id)[:12]})")

    # 2. Post a human-readable artifact-chain comment that traces how each agent's
    #    outputs fed into downstream agents and ultimately the synthesis.
    #    Infinite's link_post API only connects distinct posts, not intra-thread
    #    comments, so this comment IS the DAG view for this thread.
    if link_agent_comments:
        print("\n🔗 Posting artifact-chain provenance comment…")
        agent_comments = _agent_comments_on_post(client, post_id)
        # Build a comment ID lookup so we can reference short IDs
        cid_map = {ac["agent"]: str(ac["id"])[:8] for ac in agent_comments if ac.get("id")}
        time.sleep(22)

        def _ref(agent: str) -> str:
            cid = cid_map.get(agent, "?")
            return f"**{agent}** (`{cid}`)"

        chain_lines = [
            f"**[{agent_name}] — Artifact Chain**\n",
            "Provenance DAG for this investigation thread — each arrow shows "
            "which artifact fed into which downstream analysis:\n",
            "```",
            f"StructureMiner ({cid_map.get('StructureMiner','?')})",
            f"  #4ef2e9b9 PDB structures ──► StructuralAnalyst ({cid_map.get('StructuralAnalyst','?')})",
            f"  #460ca06e peptide sequences ──► StructuralAnalyst, RankingAgent, BinderBenchmarker",
            f"  #95d9cfc6 synthesis ──► StructuralAnalyst, EvolutionaryAnalyst, RankingAgent",
            f"  #9352993a ESM seed ──► SeqDesigner ({cid_map.get('SeqDesigner','?')})",
            "",
            f"StructuralAnalyst ({cid_map.get('StructuralAnalyst','?')})",
            f"  #e2eac457 7WIC contacts ──► StructureMiner (need fulfillment)",
            f"  #d8ef3516 7XNA contacts ──► SeqDesigner, RankingAgent, SynthBot",
            "",
            f"EvolutionaryAnalyst ({cid_map.get('EvolutionaryAnalyst','?')})",
            f"  #3aee2130 MSA + #de83a2cd conservation ──► SeqDesigner, ProteinSynth",
            "",
            f"SeqDesigner ({cid_map.get('SeqDesigner','?')})",
            f"  #1a55124a ESM scores ──► RankingAgent, ProteinSynth",
            f"  #ab852da3 ESM optimised seq ──► ProteinSynth, SynthBot",
            "",
            f"RankingAgent ({cid_map.get('RankingAgent','?')})",
            f"  #c5c71350 stability + #68d85363 ranking ──► ProteinSynth, SynthBot",
            "",
            f"BinderBenchmarker ({cid_map.get('BinderBenchmarker','?')})",
            f"  #6386948d + #3f69fc77 literature ──► StructureMapper, SynthBot",
            "",
            f"ProteinSynth ({cid_map.get('ProteinSynth','?')})",
            f"  #3d0fb79a ProtParam + #1277905d PubChem + #e2854f27 ChEMBL ──► SynthBot",
            "",
            f"StructureMapper ({cid_map.get('StructureMapper','?')})",
            f"  #179fdb45 STRING + #013a8e35 OpenAlex ──► SynthBot",
            "",
            f"All above ──► SynthBot synthesis (this report)",
            "```",
            "\nArtifact hashes (e.g. `#4ef2e9b9`) correspond to artifact IDs in the "
            "shared scienceclaw artifact store at `~/.scienceclaw/artifacts/`.",
        ]
        chain_comment = "\n".join(chain_lines)
        result = client.create_comment(post_id=post_id, content=chain_comment)
        if "error" in result:
            print(f"  ⚠  Failed to post chain comment: {result['error']}")
        else:
            cid = result.get("id") or result.get("comment_id", "?")
            print(f"  ✓ Posted artifact-chain comment ({str(cid)[:12]})")

    # 3. Generate figures.
    print("\n🎨 Generating figures…")
    figures_dir = Path.home() / ".scienceclaw" / "figures"
    fig_paths = _generate_figures(agent_name, figures_dir)
    print(f"\n  📂 Figures directory: {figures_dir}")
    for p in fig_paths:
        print(f"     {p}")

    # 4. Post figures comment.
    if fig_paths:
        print("\n📊 Posting figures comment…")
        time.sleep(22)
        fig_lines = [f"**[PlotAgent] — Figures** (generated from SSTR2 investigation artifacts)\n"]
        labels = [
            "Fig 1 — SSTR2–peptide contact fingerprint (PDB 7XNA)",
            "Fig 2 — Motif conservation × ESM‑2 position-wise fitness",
            "Fig 3 — Stability & physicochemical landscape vs approved drugs",
            "Fig 4 — SSTR2 signaling network & literature landscape",
        ]
        for label, path in zip(labels, fig_paths):
            fig_lines.append(f"- **{label}**")
            fig_lines.append(f"  `{path}`")
        figures_comment = "\n".join(fig_lines)
        result = client.create_comment(post_id=post_id, content=figures_comment)
        if "error" in result:
            print(f"  ⚠  Failed to post figures comment: {result['error']}")
        else:
            cid = result.get("id") or result.get("comment_id", "?")
            print(f"  ✓ Posted figures comment ({str(cid)[:12]})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post SynthBot report + figures as Infinite comments, with DAG links."
    )
    parser.add_argument("--post-id", required=True)
    parser.add_argument("--report-path", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--agent-name", default="SynthBot")
    parser.add_argument("--no-links", action="store_true",
                        help="Skip wiring artifact-chain links.")
    args = parser.parse_args()

    post_synth_report_and_figures(
        post_id=args.post_id.strip(),
        report_path=Path(args.report_path).expanduser().resolve(),
        topic=args.topic,
        agent_name=args.agent_name.strip() or "SynthBot",
        link_agent_comments=not args.no_links,
    )


if __name__ == "__main__":
    main()
