#!/usr/bin/env python3
"""
Case Study: KRAS G12C Inhibitor Resistance Mechanisms

Demonstrates the skills-aware hypothesis validation workflow using a
multi-agent panel approach with multiple validator personalities.

Agents:
  MaterialsProposer  — connector, proposes initial hypothesis
  SkepticalSam       — skeptic validator, demands quantitative specificity
  DeepDiverDan       — deep-diver validator, checks tool chain completeness
  ChemReactionAgent  — explorer reacting agent (chemistry perspective)
  StructureAgent     — deep-diver reacting agent (crystal structure)

Topic: "Defect engineering in perovskite solar cell absorbers for enhanced carrier lifetime"
"""

import sys
from pathlib import Path

# Ensure scienceclaw root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from coordination.hypothesis_validation_workflow import HypothesisValidationWorkflow

TOPIC = "Defect engineering in perovskite solar cell absorbers for enhanced carrier lifetime"

workflow = HypothesisValidationWorkflow()

result = workflow.run(
    topic=TOPIC,
    proposer_agent="MaterialsProposer",
    validator_agents=[
        {"name": "SkepticalSam",  "personality": "skeptic"},
        {"name": "DeepDiverDan", "personality": "deep-diver"},
    ],
    reacting_agents=[
        {
            "name": "ChemReactionAgent",
            "domain": "chemistry",
            "tools": ["pubchem", "rdkit"],
        },
        {
            "name": "StructureAgent",
            "domain": "materials",
            "tools": ["materials", "pubmed", "arxiv"],
        },
    ],
    community="materials",
    max_iterations=6,
    validation_threshold=0.75,
    post_live=True,
)

# ------------------------------------------------------------------ #
# Print before/after comparison                                        #
# ------------------------------------------------------------------ #
print("\n" + "=" * 60)
print("HYPOTHESIS VALIDATION SUMMARY")
print("=" * 60)

for iter_record in result["history"]:
    i = iter_record.iteration
    h = iter_record.hypothesis
    print(f"\n{'='*60}")
    print(f"ITERATION {i}")
    print(f"  Hypothesis: {h.get('statement', '')[:120]}")
    print(f"  Tools: {', '.join(h.get('planned_tools', []))}")
    for vr in iter_record.validator_results:
        print(f"  [{vr.validator_agent} / {vr.personality}] score={vr.score:.2f}: {vr.critique[:80]}")
    status = "ACCEPTED" if iter_record.accepted else "REFINED"
    print(f"  Consensus: {iter_record.consensus_score:.2f} — {status}")
    if iter_record.post_id:
        print(f"  Thread post: {iter_record.post_id}")
    if iter_record.reactions:
        print(f"  Reactions: {[r['agent'] for r in iter_record.reactions]}")

print(f"\n{'='*60}")
print("FINAL RESULT")
print(f"  Accepted: {result['accepted']}")
print(f"  Final consensus: {result['consensus_score']:.2f}")
if result.get("thread_post_id"):
    print(f"  Infinite thread: {result['thread_post_id']}")
fh = result["final_hypothesis"]
print(f"  Final hypothesis: {fh.get('statement', '')[:200]}")
print(f"  Validated tools: {', '.join(fh.get('planned_tools', []))}")
