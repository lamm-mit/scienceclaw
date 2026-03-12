#!/usr/bin/env python3
import argparse
import datetime as _dt
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    out: List[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return out


def _load_artifacts(investigation_id: str) -> List[dict]:
    base = Path.home() / ".scienceclaw" / "artifacts"
    arts: List[dict] = []
    for store in sorted(base.glob("*/store.jsonl")):
        agent = store.parent.name
        for rec in _read_jsonl(store):
            if investigation_id and rec.get("investigation_id") != investigation_id:
                continue
            rec["_agent_dir"] = agent
            arts.append(rec)
    return arts


def _pick_best(payloads: List[dict], key_fn) -> Optional[dict]:
    best = None
    best_k = None
    for p in payloads:
        try:
            k = key_fn(p)
        except Exception:
            continue
        if best is None or (best_k is None) or (k > best_k):
            best = p
            best_k = k
    return best


def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _ensure_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless
        import matplotlib.pyplot as plt  # noqa
        return True
    except Exception:
        return False


def _fig1_artifact_heatmap(arts: List[dict], out_path: Path, investigation_id: str) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    by_agent: Dict[str, Counter] = defaultdict(Counter)
    for a in arts:
        agent = str(a.get("producer_agent") or a.get("_agent_dir") or "Unknown")
        atype = str(a.get("artifact_type") or "unknown")
        if atype.startswith("_"):
            continue
        by_agent[agent][atype] += 1

    agents = sorted(by_agent.keys())
    all_types = Counter()
    for c in by_agent.values():
        all_types.update(c)
    types = [t for (t, _) in all_types.most_common(12)]
    if not agents or not types:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.set_title("Investigation Output Overview", fontweight="bold")
        ax.text(0.5, 0.5, "Insufficient artifacts to plot.", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        plt.tight_layout()
        plt.savefig(out_path, dpi=160, bbox_inches="tight")
        plt.close()
        return

    M = np.zeros((len(agents), len(types)), dtype=float)
    for i, ag in enumerate(agents):
        for j, tp in enumerate(types):
            M[i, j] = float(by_agent[ag].get(tp, 0))

    fig, ax = plt.subplots(figsize=(10, max(4.0, 0.42 * len(agents))))
    im = ax.imshow(M, aspect="auto", cmap="Blues")
    ax.set_title(f"Fig 1 · Investigation Yield by Agent × Artifact Type\n{investigation_id}", fontweight="bold")
    ax.set_xticks(range(len(types)))
    ax.set_xticklabels(types, rotation=35, ha="right", fontsize=8)
    ax.set_yticks(range(len(agents)))
    ax.set_yticklabels(agents, fontsize=9)
    for i in range(len(agents)):
        for j in range(len(types)):
            if M[i, j] > 0:
                ax.text(j, i, str(int(M[i, j])), ha="center", va="center", fontsize=7, color="#0b1220")
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("count", fontsize=9)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close()


def _fig2_hotspots_vs_conservation(
    conservation: Optional[dict],
    hotspots: Optional[dict],
    out_path: Path,
    investigation_id: str,
) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.set_title(f"Fig 2 · Binding Hotspots vs Conservation (Peptide Positions)\n{investigation_id}", fontweight="bold")

    if not conservation or not isinstance(conservation.get("positions"), list):
        ax.text(0.5, 0.5, "No conservation_map positions available.", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        plt.tight_layout()
        plt.savefig(out_path, dpi=160, bbox_inches="tight")
        plt.close()
        return

    pos_rows = conservation["positions"]
    xs = [int(p.get("col") or 0) for p in pos_rows]
    ys = [float(p.get("conservation") or 0.0) for p in pos_rows]
    ax.plot(xs, ys, color="#2563eb", lw=2, label="conservation")
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlabel("Alignment column (1-based)")
    ax.set_ylabel("Conservation (max freq)")

    hs_positions = []
    contacts = {}
    if hotspots and isinstance(hotspots.get("per_position_contacts"), list):
        for r in hotspots["per_position_contacts"]:
            try:
                contacts[int(r.get("position"))] = int(r.get("contacts") or 0)
            except Exception:
                continue
    if hotspots:
        hs_positions = [int(x) for x in (hotspots.get("hotspot_positions") or []) if isinstance(x, int) or str(x).isdigit()]
        hs_positions = [int(x) for x in hs_positions if x > 0]

    if contacts:
        ax2 = ax.twinx()
        x2 = sorted(contacts.keys())
        y2 = [contacts[k] for k in x2]
        ax2.bar(x2, y2, color="#94a3b8", alpha=0.35, width=0.85, label="contacts")
        ax2.set_ylabel("Contacts (count, proxy)")

    for p in hs_positions[:10]:
        ax.axvline(p, color="#dc2626", alpha=0.6, lw=1)
    if hs_positions:
        ax.text(
            0.01,
            0.02,
            f"hotspot_positions={hs_positions[:10]}",
            transform=ax.transAxes,
            fontsize=9,
            color="#475569",
            va="bottom",
        )

    ax.legend(loc="upper right", fontsize=9)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close()


def _fig3_candidate_landscape(
    ranked: Optional[dict],
    mutation_spaces: List[dict],
    out_path: Path,
    investigation_id: str,
) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.set_title(f"Fig 3 · Candidate Landscape (Stability vs Distance)\n{investigation_id}", fontweight="bold")

    if not ranked or not isinstance(ranked.get("ranked_candidates"), list):
        ax.text(0.5, 0.5, "No ranked_candidates available.", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        plt.tight_layout()
        plt.savefig(out_path, dpi=160, bbox_inches="tight")
        plt.close()
        return

    seq_to_strategy: Dict[str, str] = {}
    for ms in mutation_spaces or []:
        strat = str(ms.get("strategy") or "variants")
        for v in (ms.get("variants") or []):
            if isinstance(v, dict) and v.get("sequence"):
                seq_to_strategy[str(v["sequence"]).strip().upper()] = strat

    rows = ranked.get("ranked_candidates") or []
    pts = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        seq = str(r.get("sequence") or "").strip().upper()
        stab = _safe_float(r.get("stability_score"))
        dist = _safe_float(r.get("edit_distance"))
        score = _safe_float(r.get("combined_score"))
        if not seq or stab is None or dist is None:
            continue
        pts.append((seq, dist, stab, score if score is not None else stab, seq_to_strategy.get(seq, "ranked")))

    if not pts:
        ax.text(0.5, 0.5, "Ranked candidates contained no numeric fields.", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        plt.tight_layout()
        plt.savefig(out_path, dpi=160, bbox_inches="tight")
        plt.close()
        return

    colors = {"conservative": "#16a34a", "aggressive": "#dc2626", "ranked": "#0ea5e9", "variants": "#0ea5e9"}
    for strat in sorted({p[4] for p in pts}):
        sub = [p for p in pts if p[4] == strat]
        ax.scatter(
            [p[1] for p in sub],
            [p[2] for p in sub],
            s=70,
            alpha=0.85,
            label=strat,
            color=colors.get(strat, "#64748b"),
            edgecolors="white",
            linewidths=0.6,
        )

    # annotate top 5 by combined score
    pts_sorted = sorted(pts, key=lambda t: (-(t[3] or 0.0), t[1], -t[2]))
    for seq, dist, stab, score, strat in pts_sorted[:5]:
        ax.annotate(seq[:12], (dist, stab), textcoords="offset points", xytext=(6, 4), fontsize=8, color="#334155")

    ax.set_xlabel("Edit distance vs reference")
    ax.set_ylabel("Stability score (heuristic)")
    ax.set_ylim(-0.02, 1.05)
    ax.legend(fontsize=9, loc="lower right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close()


def _fig4_benchmark_coverage(pubmed_payloads: List[dict], out_path: Path, investigation_id: str) -> None:
    import matplotlib.pyplot as plt

    # Aggregate paper-like items
    texts: List[str] = []
    for p in pubmed_payloads:
        for paper in (p.get("papers") or p.get("articles") or p.get("items") or []):
            if not isinstance(paper, dict):
                continue
            t = (paper.get("title") or "") + " " + (paper.get("abstract") or "")
            t = t.strip()
            if t:
                texts.append(t)

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.set_title(f"Fig 4 · Benchmark Evidence Coverage (Abstract-Level)\n{investigation_id}", fontweight="bold")

    if not texts:
        ax.text(0.5, 0.5, "No paper abstracts available to summarize.", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        plt.tight_layout()
        plt.savefig(out_path, dpi=160, bbox_inches="tight")
        plt.close()
        return

    ligands = {
        "octreotide": re.compile(r"\\boctreotide\\b", re.I),
        "lanreotide": re.compile(r"\\blanreotide\\b", re.I),
        # Use \^ to ensure caret is treated literally (not start-of-string anchor).
        "DOTATATE": re.compile(r"dotatate|\^?68ga[- ]?dotatate|gallium[- ]?68", re.I),
    }
    endpoints = {
        "Ki/IC50/Kd": re.compile(r"\\bki\\b|ic50|kd\\b", re.I),
        "EC50/cAMP": re.compile(r"ec50|\\bcamp\\b|cAMP", re.I),
        "Uptake/PET": re.compile(r"uptake|pet\\b|suv\\b|%\\s*id\\s*/\\s*g", re.I),
    }

    counts = {lig: Counter() for lig in ligands.keys()}
    totals = Counter()
    for txt in texts:
        present_l = [l for l, pat in ligands.items() if pat.search(txt)]
        present_e = [e for e, pat in endpoints.items() if pat.search(txt)]
        for l in present_l:
            totals[l] += 1
            for e in present_e:
                counts[l][e] += 1

    x = list(ligands.keys())
    y_tot = [totals.get(l, 0) for l in x]
    if sum(y_tot) == 0:
        ax.text(
            0.5,
            0.5,
            "Could not detect ligand keywords in abstracts.\n(Still saved papers, but nothing to plot.)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_xticks([]); ax.set_yticks([])
        plt.tight_layout()
        plt.savefig(out_path, dpi=160, bbox_inches="tight")
        plt.close()
        return

    # stacked bars for endpoint coverage
    bottoms = [0] * len(x)
    colors = {"Ki/IC50/Kd": "#0ea5e9", "EC50/cAMP": "#16a34a", "Uptake/PET": "#dc2626"}
    for e in endpoints.keys():
        vals = [counts[l].get(e, 0) for l in x]
        ax.bar(x, vals, bottom=bottoms, label=e, color=colors.get(e, "#64748b"), alpha=0.85)
        bottoms = [bottoms[i] + vals[i] for i in range(len(x))]

    for i, l in enumerate(x):
        ax.text(i, y_tot[i] + 0.3, f"n={y_tot[i]}", ha="center", fontsize=9, color="#475569")
    ax.set_ylabel("Abstract count (keyword co-mentions)")
    ax.legend(fontsize=9, loc="upper right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close()


def plot_investigation(investigation_id: str, ts: str = "") -> Dict[str, object]:
    if not investigation_id:
        return {"error": "Missing investigation_id"}
    if not _ensure_matplotlib():
        return {"error": "matplotlib is required for investigation-plotter"}

    arts = _load_artifacts(investigation_id)

    payloads_by_type: Dict[str, List[dict]] = defaultdict(list)
    for a in arts:
        payload = a.get("payload") if isinstance(a.get("payload"), dict) else {}
        payloads_by_type[str(a.get("artifact_type") or "")].append(payload)

    cons = _pick_best(payloads_by_type.get("conservation_map", []), lambda p: len(p.get("positions") or []))
    hs = _pick_best(payloads_by_type.get("binding_hotspots", []), lambda p: len(p.get("per_position_contacts") or []))
    ranked = _pick_best(payloads_by_type.get("ranked_candidates", []), lambda p: len(p.get("ranked_candidates") or []))
    mutation_spaces = payloads_by_type.get("mutation_space", [])
    pubmed_payloads = payloads_by_type.get("pubmed_results", [])

    out_dir = Path.home() / ".scienceclaw" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = ts.strip() or str(int(_dt.datetime.now(_dt.timezone.utc).timestamp()))

    p1 = out_dir / f"pd_fig1_success_vs_params_{ts}.png"
    p2 = out_dir / f"pd_fig2_structural_confidence_{ts}.png"
    p3 = out_dir / f"pd_fig3_method_landscape_{ts}.png"
    p4 = out_dir / f"pd_fig4_publication_trend_{ts}.png"

    _fig1_artifact_heatmap(arts, p1, investigation_id=investigation_id)
    _fig2_hotspots_vs_conservation(cons, hs, p2, investigation_id=investigation_id)
    _fig3_candidate_landscape(ranked, mutation_spaces, p3, investigation_id=investigation_id)
    _fig4_benchmark_coverage(pubmed_payloads, p4, investigation_id=investigation_id)

    figures = [
        {"path": str(p1), "label": "Fig 1 · Investigation yield (agents × artifact types)"},
        {"path": str(p2), "label": "Fig 2 · Binding hotspots vs conservation"},
        {"path": str(p3), "label": "Fig 3 · Candidate landscape (stability vs distance)"},
        {"path": str(p4), "label": "Fig 4 · Benchmark coverage (abstract-level keywords)"},
    ]

    return {
        "investigation_id": investigation_id,
        "timestamp": ts,
        "figure_count": len(figures),
        "figures": figures,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Generate investigation-specific figures from local ScienceClaw artifacts")
    p.add_argument("--investigation-id", default="", help="Investigation ID to plot (required)")
    p.add_argument("--query", "-q", default="", help="Alias for --investigation-id")
    p.add_argument("--ts", default="", help="Timestamp tag for output filenames (optional)")
    p.add_argument("--format", "-f", choices=["json", "summary"], default="json")
    p.add_argument("--describe-schema", action="store_true")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps({"input_json_fields": []}))
        return

    inv = (args.investigation_id or args.query or "").strip()
    out = plot_investigation(inv, ts=str(args.ts or ""))
    if args.format == "summary":
        if out.get("error"):
            print(out["error"])
            return
        print(f"Generated {out.get('figure_count', 0)} figure(s) for {out.get('investigation_id')}")
        for f in out.get("figures", [])[:8]:
            print(f"  - {f.get('label')}: {f.get('path')}")
        return
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
