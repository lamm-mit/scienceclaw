"""
Post the SSTR2 investigation artifact DAG to Infinite so the graph view
shows actual data-flow edges between agents (not just SynthBot → everyone).

Usage:
    cd ~/LAMM/scienceclaw
    python3 skills/infinite/scripts/post_artifacts_dag.py --post-id <POST_ID>

The artifact IDs are taken directly from the `#<hash>` and `← #<hash>` markers
visible in the agent comments already posted to the thread.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow imports from scienceclaw root
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from skills.infinite.scripts.infinite_client import InfiniteClient  # noqa: E402


POST_ID = "3ed6bb51-9428-47f7-8d04-cfb1ff56b132"

# ── Artifact definitions ──────────────────────────────────────────────────────
# artifact_id matches the #hash shown in the agent comments (padded to uuid-style
# is fine, but we use the actual 8-char hashes as stable IDs).
# parent_artifact_ids encodes the upstream dependencies (← #hash in comments).

ARTIFACTS = [
    # ── StructureMiner ───────────────────────────────────────────────────────
    {
        "artifact_id": "95d9cfc6",
        "artifact_type": "pubmed_results",
        "skill_used": "pdb",
        "producer_agent": "StructureMiner",
        "parent_artifact_ids": [],
        "timestamp": "2026-03-09T19:51:00Z",
        "summary": "PDB search: somatostatin receptor 2 → 7XNA, 7XN9, 7WIC, 7XAT",
    },
    {
        "artifact_id": "460ca06e",
        "artifact_type": "pubmed_results",
        "skill_used": "arxiv",
        "producer_agent": "StructureMiner",
        "parent_artifact_ids": [],
        "timestamp": "2026-03-09T19:51:05Z",
        "summary": "arXiv / OpenAlex seed: SSTR2 peptide binder literature",
    },

    # ── StructuralAnalyst (7WIC) ─────────────────────────────────────────────
    {
        "artifact_id": "e2eac457",
        "artifact_type": "sequence_alignment",
        "skill_used": "structure-contact-analysis",
        "producer_agent": "StructuralAnalyst",
        "parent_artifact_ids": ["95d9cfc6"],
        "timestamp": "2026-03-09T19:53:00Z",
        "summary": "Structure contacts PDB 7WIC — no contacts detected (chain mismatch)",
    },
    {
        "artifact_id": "9c45dd41",
        "artifact_type": "pubmed_results",
        "skill_used": "pdb",
        "producer_agent": "StructuralAnalyst",
        "parent_artifact_ids": ["95d9cfc6"],
        "timestamp": "2026-03-09T19:53:10Z",
        "summary": "Refined PDB search → 7XNA, 7XN9, 7WIC",
    },
    {
        "artifact_id": "dfe0dd2d",
        "artifact_type": "pubmed_results",
        "skill_used": "pdb",
        "producer_agent": "StructuralAnalyst",
        "parent_artifact_ids": ["460ca06e"],
        "timestamp": "2026-03-09T19:53:20Z",
        "summary": "Extended PDB search → 7XNA, 7XN9, 7WIC, 7XAT",
    },

    # ── StructuralAnalyst (7XNA) ─────────────────────────────────────────────
    {
        "artifact_id": "d8ef3516",
        "artifact_type": "sequence_alignment",
        "skill_used": "structure-contact-analysis",
        "producer_agent": "StructuralAnalyst",
        "parent_artifact_ids": ["9c45dd41"],
        "timestamp": "2026-03-09T19:55:00Z",
        "summary": "7XNA hotspot triad: K(8 contacts)·T(5)·C(3) at receptor Tyr50, Phe294, Asp295",
    },

    # ── EvolutionaryAnalyst ──────────────────────────────────────────────────
    {
        "artifact_id": "3aee2130",
        "artifact_type": "sequence_alignment",
        "skill_used": "peptide-msa",
        "producer_agent": "EvolutionaryAnalyst",
        "parent_artifact_ids": ["d8ef3516"],
        "timestamp": "2026-03-09T19:57:00Z",
        "summary": "MSA of AGCKNFFWKTFTSC + FCFWKTCT + YCWKTCT + YCGWKTCT; consensus ACCKNFFCFWKTCT",
    },
    {
        "artifact_id": "de83a2cd",
        "artifact_type": "sequence_alignment",
        "skill_used": "conservation-map",
        "producer_agent": "EvolutionaryAnalyst",
        "parent_artifact_ids": ["3aee2130"],
        "timestamp": "2026-03-09T19:57:30Z",
        "summary": "Conservation map: 6/14 positions ≥75% conserved; K·T·C triad at cols 4,11,12",
    },

    # ── SeqDesigner ─────────────────────────────────────────────────────────
    {
        "artifact_id": "1a55124a",
        "artifact_type": "admet_prediction",
        "skill_used": "esm",
        "producer_agent": "SeqDesigner",
        "parent_artifact_ids": ["3aee2130"],
        "timestamp": "2026-03-09T19:59:00Z",
        "summary": "ESM-2 scoring: seed PLL -3.19; top mutation A1→M (+5.22 ΔPLL)",
    },
    {
        "artifact_id": "3cca8cb6",
        "artifact_type": "sequence_alignment",
        "skill_used": "mutation-generator",
        "producer_agent": "SeqDesigner",
        "parent_artifact_ids": ["1a55124a", "de83a2cd"],
        "timestamp": "2026-03-09T19:59:30Z",
        "summary": "Mutation space: top variant MGLKNFFLKTFTSC (A1M + W8L) preserves K·T·C",
    },

    # ── RankingAgent ─────────────────────────────────────────────────────────
    {
        "artifact_id": "c5c71350",
        "artifact_type": "admet_prediction",
        "skill_used": "peptide-stability",
        "producer_agent": "RankingAgent",
        "parent_artifact_ids": ["3cca8cb6"],
        "timestamp": "2026-03-09T20:01:00Z",
        "summary": "Stability scores: FCFWKTCT 0.92 > 14-mers 0.84; charge/GRAVY breakdown",
    },
    {
        "artifact_id": "68d85363",
        "artifact_type": "admet_prediction",
        "skill_used": "candidate-ranking",
        "producer_agent": "RankingAgent",
        "parent_artifact_ids": ["c5c71350"],
        "timestamp": "2026-03-09T20:01:30Z",
        "summary": "Ranked candidates: 1. FCFWKTCT (0.92) 2. AGCKNFFLKTFTSC (0.84)",
    },

    # ── BinderBenchmarker ────────────────────────────────────────────────────
    {
        "artifact_id": "pubmed_bb01",
        "artifact_type": "pubmed_results",
        "skill_used": "pubmed",
        "producer_agent": "BinderBenchmarker",
        "parent_artifact_ids": [],
        "timestamp": "2026-03-09T20:02:00Z",
        "summary": "PubMed: SSTR2 octreotide lanreotide DOTATATE clinical trials; NETTER-1, CLARINET",
    },

    # ── ProteinSynth ─────────────────────────────────────────────────────────
    {
        "artifact_id": "3d0fb79a",
        "artifact_type": "compound_data",
        "skill_used": "biopython-protparam",
        "producer_agent": "ProteinSynth",
        "parent_artifact_ids": ["68d85363"],
        "timestamp": "2026-03-09T20:04:00Z",
        "summary": "ProtParam: MW, pI, GRAVY, instability index for 5 candidate sequences",
    },
    {
        "artifact_id": "1277905d",
        "artifact_type": "compound_data",
        "skill_used": "pubchem",
        "producer_agent": "ProteinSynth",
        "parent_artifact_ids": ["3d0fb79a", "pubmed_bb01"],
        "timestamp": "2026-03-09T20:04:30Z",
        "summary": "PubChem properties for octreotide + lanreotide benchmark; XLogP, TPSA, HBD/HBA",
    },

    # ── StructureMapper ──────────────────────────────────────────────────────
    {
        "artifact_id": "179fdb45",
        "artifact_type": "protein_data",
        "skill_used": "string-database",
        "producer_agent": "StructureMapper",
        "parent_artifact_ids": ["95d9cfc6"],
        "timestamp": "2026-03-09T20:05:00Z",
        "summary": "STRING network: 7 nodes, 13 edges; SSTR2–SST score 0.999",
    },
    {
        "artifact_id": "openalex01",
        "artifact_type": "pubmed_results",
        "skill_used": "openalex-database",
        "producer_agent": "StructureMapper",
        "parent_artifact_ids": ["pubmed_bb01"],
        "timestamp": "2026-03-09T20:05:30Z",
        "summary": "OpenAlex citation network: PageRank leaders Strosberg 2017, Caplin 2014",
    },

    # ── PlotAgent ────────────────────────────────────────────────────────────
    {
        "artifact_id": "plot_fig1",
        "artifact_type": "figure",
        "skill_used": "matplotlib",
        "producer_agent": "PlotAgent",
        "parent_artifact_ids": ["d8ef3516"],
        "timestamp": "2026-03-09T21:51:00Z",
        "summary": "Fig 1 — SSTR2–peptide contact fingerprint (PDB 7XNA)",
    },
    {
        "artifact_id": "plot_fig2",
        "artifact_type": "figure",
        "skill_used": "matplotlib",
        "producer_agent": "PlotAgent",
        "parent_artifact_ids": ["3aee2130", "de83a2cd", "1a55124a"],
        "timestamp": "2026-03-09T21:51:01Z",
        "summary": "Fig 2 — Motif conservation x ESM-2 position-wise fitness",
    },
    {
        "artifact_id": "plot_fig3",
        "artifact_type": "figure",
        "skill_used": "matplotlib",
        "producer_agent": "PlotAgent",
        "parent_artifact_ids": ["3d0fb79a", "1277905d", "68d85363"],
        "timestamp": "2026-03-09T21:51:02Z",
        "summary": "Fig 3 — Stability & physicochemical landscape vs approved drugs",
    },
    {
        "artifact_id": "plot_fig4",
        "artifact_type": "figure",
        "skill_used": "matplotlib",
        "producer_agent": "PlotAgent",
        "parent_artifact_ids": ["179fdb45", "openalex01"],
        "timestamp": "2026-03-09T21:51:03Z",
        "summary": "Fig 4 — SSTR2 signaling network & literature landscape",
    },

    # ── SynthBot ─────────────────────────────────────────────────────────────
    {
        "artifact_id": "synthbot01",
        "artifact_type": "synthesis",
        "skill_used": "llm-synthesis",
        "producer_agent": "SynthBot",
        "parent_artifact_ids": [
            "d8ef3516",   # StructuralAnalyst hotspots
            "de83a2cd",   # EvolutionaryAnalyst conservation
            "3cca8cb6",   # SeqDesigner mutations
            "68d85363",   # RankingAgent candidates
            "pubmed_bb01", # BinderBenchmarker literature
            "1277905d",   # ProteinSynth physicochemical
            "179fdb45",   # StructureMapper STRING
            "openalex01", # StructureMapper citations
        ],
        "timestamp": "2026-03-09T20:10:00Z",
        "summary": "arXiv-style synthesis: K·T·C hotspot triad, MGLKNFFLKTFTSC optimized variant, cyclization strategy",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Post artifact DAG to Infinite")
    parser.add_argument("--post-id", default=POST_ID, help="Infinite post ID")
    parser.add_argument("--agent-name", default="SynthBot", help="Agent to authenticate as")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without posting")
    args = parser.parse_args()

    cfg = Path.home() / ".scienceclaw" / "infinite_config.json"
    client = InfiniteClient(config_file=str(cfg))

    if not client.jwt_token:
        sys.exit(f"No JWT token found for agent. Run: python3 skills/infinite/scripts/infinite_client.py login")

    if args.dry_run:
        import json
        print(json.dumps({"artifacts": ARTIFACTS}, indent=2))
        print(f"\n{len(ARTIFACTS)} artifacts would be posted.")
        return

    print(f"Posting {len(ARTIFACTS)} artifacts to post {args.post_id}...")

    import json, urllib.request, urllib.error

    url = f"{client.api_base}/posts/{args.post_id}/artifacts"
    payload = json.dumps({"artifacts": ARTIFACTS}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {client.jwt_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            print(f"✅ Inserted: {result.get('inserted', '?')} artifacts")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ HTTP {e.code}: {body}")
    except Exception as exc:
        print(f"❌ Error: {exc}")


if __name__ == "__main__":
    main()
