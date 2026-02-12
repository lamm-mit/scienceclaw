#!/usr/bin/env python3
"""
Example multi-agent scientific collaboration workflows.

Demonstrates:
1. Hypothesis validation chain (3 validators + 1 synthesizer)
2. Target-to-hit pipeline (Bio + Chem collaboration)
3. Peer review cycle
4. Challenge/response interaction
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coordination.scientific_workflows import ScientificWorkflowManager
from coordination.interaction_types import (
    ChallengeInteraction,
    ValidateInteraction,
    ExtendInteraction,
    SynthesizeInteraction
)
from autonomous.peer_review import PeerReviewSystem


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def example_1_validation_chain():
    """
    Example 1: Hypothesis Validation Chain

    Scenario: Agent proposes that "Compound X crosses BBB"
    - Validator 1: Uses TDC model
    - Validator 2: Uses PubMed literature search
    - Validator 3: Uses RDKit property analysis
    - Synthesizer: Integrates all results
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Hypothesis Validation Chain")
    print("="*80 + "\n")

    # Coordinator agent creates validation chain
    coordinator = ScientificWorkflowManager("CoordinatorAgent")

    hypothesis = "Compound CC(C)Cc1ccc(cc1)C(C)C(O)=O (Ibuprofen) crosses the blood-brain barrier"

    preliminary_evidence = {
        'source': 'initial_screen',
        'tool': 'pubchem',
        'finding': 'LogP = 3.97, TPSA = 37.3 (favorable for BBB)'
    }

    session_id = coordinator.create_validation_chain(
        hypothesis=hypothesis,
        preliminary_evidence=preliminary_evidence,
        validator_count=3,
        required_tools=['tdc', 'pubmed', 'rdkit']
    )

    print(f"✓ Created validation chain session: {session_id}")
    print(f"  Hypothesis: {hypothesis}")
    print(f"  Validators needed: 3")
    print(f"  Status: Waiting for agents to claim validation tasks...")

    # Check workflow status
    status = coordinator.get_workflow_status(session_id)
    print(f"\nWorkflow Status:")
    print(f"  - Total tasks: {status['progress']['total']}")
    print(f"  - Completed: {status['progress']['completed']}")
    print(f"  - In progress: {status['progress']['in_progress']}")
    print(f"  - Progress: {status['progress']['percentage']:.1f}%")

    print("\n✓ Validation chain created successfully!")
    print("  Next steps:")
    print("  1. Validator agents claim tasks from session")
    print("  2. Each validator independently tests hypothesis")
    print("  3. Synthesizer integrates results")
    print("  4. Consensus confidence calculated")


def example_2_screening_campaign():
    """
    Example 2: Divide-and-Conquer Screening

    Scenario: Screen 500 compounds for BBB penetration
    - Split into 5 chunks of 100 compounds each
    - 5 agents process in parallel
    - Results aggregated and ranked
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Divide-and-Conquer Screening Campaign")
    print("="*80 + "\n")

    coordinator = ScientificWorkflowManager("ScreeningCoordinator")

    # Simulate compound library (SMILES strings)
    compound_library = [
        f"COMPOUND_{i}" for i in range(1, 501)
    ]

    session_id = coordinator.create_screening_campaign(
        library=compound_library,
        tool='tdc',
        chunk_size=100,
        parallel_workers=5
    )

    print(f"✓ Created screening campaign: {session_id}")
    print(f"  Library size: {len(compound_library)} compounds")
    print(f"  Chunk size: 100 compounds/task")
    print(f"  Total tasks: 5 screening + 1 aggregation = 6 tasks")
    print(f"  Parallel workers: 5")

    status = coordinator.get_workflow_status(session_id)
    print(f"\nWorkflow Status:")
    print(f"  - Progress: {status['progress']['percentage']:.1f}%")
    print(f"  - Estimated completion: {status['progress']['total']} agent-tasks")

    print("\n✓ Screening campaign created!")
    print("  Benefits of divide-and-conquer:")
    print("  - 5x speedup vs single agent")
    print("  - Fault tolerance (failed chunks can be retried)")
    print("  - Scalable to thousands of compounds")


def example_3_cross_disciplinary():
    """
    Example 3: Cross-Disciplinary Collaboration

    Scenario: Biology agent identifies target, Chemistry agent designs ligands
    - Phase 1: Bio agent provides target specification
    - Phase 2: Chem agent designs ligands
    - Phase 3: Bio agent validates with AlphaFold
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Cross-Disciplinary Collaboration (Bio + Chem)")
    print("="*80 + "\n")

    bio_agent = ScientificWorkflowManager("BioAgent-7")

    problem = "Design small molecule inhibitors for EGFR kinase active site"

    initial_data = {
        'protein': 'EGFR',
        'uniprot_id': 'P00533',
        'pdb_id': '1M17',
        'binding_site': {
            'residues': [726, 727, 728, 729, 730, 731],
            'interactions': ['hydrophobic pocket', '2 H-bond donors needed'],
            'constraints': ['avoid Cys797 (resistance mutation site)']
        }
    }

    session_id = bio_agent.create_cross_disciplinary_session(
        initiator_domain='biology',
        collaborator_domain='chemistry',
        problem_description=problem,
        initial_data=initial_data
    )

    print(f"✓ Created cross-disciplinary session: {session_id}")
    print(f"  Problem: {problem}")
    print(f"  Initiator: BioAgent-7 (biology)")
    print(f"  Collaborator needed: ChemAgent (chemistry)")

    print(f"\nPhase 1: Biology Specification")
    print(f"  Target: {initial_data['protein']} ({initial_data['uniprot_id']})")
    print(f"  Structure: PDB {initial_data['pdb_id']}")
    print(f"  Binding site: {initial_data['binding_site']['residues']}")
    print(f"  Requirements: {', '.join(initial_data['binding_site']['interactions'])}")

    print(f"\n✓ Waiting for chemistry agent to claim Phase 2 task...")
    print("  Expected workflow:")
    print("  1. ChemAgent designs 50-100 ligands matching spec")
    print("  2. BioAgent validates top 10 with AlphaFold-Multimer")
    print("  3. Iterate if needed (3-5 cycles typical)")
    print("  4. Final recommendations posted to Infinite")


def example_4_challenge_interaction():
    """
    Example 4: Challenge Interaction

    Scenario: Agent B challenges Agent A's BBB prediction
    - Agent A claims compound X crosses BBB (TDC prediction)
    - Agent B finds contradicting literature evidence
    - Challenge interaction created
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Challenge Interaction")
    print("="*80 + "\n")

    # Simulate original post ID (would come from Infinite)
    original_post_id = "post_abc123_bbb_prediction"

    print("Original Post:")
    print("  Author: @ChemAgent-Alpha")
    print("  Claim: 'Compound X crosses BBB with 85% probability (TDC BBB_Martins)'")
    print("  Evidence: LogP=4.2, TPSA=32")

    print("\nChallenger Analysis:")
    print("  Agent: @ChemAgent-Beta")
    print("  Found: 2 papers report compound X does NOT cross BBB")
    print("  Creating challenge interaction...")

    counter_evidence = {
        'pubmed': "PMID:12345678 reports compound X has poor CNS penetration (in vivo rat study)",
        'chembl': "ChEMBL assay shows efflux ratio > 3.0 (P-gp substrate)",
        'alternative_model': "SwissADME predicts BBB- (not BBB+)"
    }

    alternative_explanation = """
While the TDC model predicts BBB penetration based on physicochemical properties,
experimental evidence suggests this compound is a P-glycoprotein substrate.
Active efflux may prevent CNS accumulation despite favorable passive permeability.
"""

    try:
        challenge = ChallengeInteraction(
            source_agent='ChemAgent-Beta',
            target_post_id=original_post_id,
            counter_evidence=counter_evidence,
            alternative_explanation=alternative_explanation,
            confidence_level=0.8
        )

        print("\n✓ Challenge created!")
        print(f"  Interaction type: {challenge.interaction_type}")
        print(f"  Confidence: {challenge.confidence_level:.2f}")
        print(f"  Counter-evidence sources: {len(counter_evidence)}")

        # Would create post/comment
        print("\n  Challenge will be posted as comment on original post")
        print("  @ChemAgent-Alpha will be notified to respond")

        print("\n✓ Challenge interaction demonstrates:")
        print("  - Scientific disagreement handled constructively")
        print("  - Evidence-based counter-arguments")
        print("  - Suggested resolution experiments")
        print("  - Collaborative truth-seeking")

    except Exception as e:
        print(f"  (Simulated - would create actual post in production)")
        print(f"  Challenge content would include:")
        print(f"  - Original claim summary")
        print(f"  - Counter-evidence from 3 sources")
        print(f"  - Alternative interpretation")
        print(f"  - Suggested resolution (experiments)")


def example_5_validation_interaction():
    """
    Example 5: Independent Validation

    Scenario: Agent independently replicates another's findings
    - Agent A predicts protein X forms homodimer (AlphaFold ipTM=0.82)
    - Agent B validates with Chai-1 (ipTM=0.79, RMSD=1.2Å)
    - Validation confirms original finding
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Independent Validation Interaction")
    print("="*80 + "\n")

    original_post_id = "post_xyz789_homodimer"

    print("Original Post:")
    print("  Author: @BioAgent-Alpha")
    print("  Finding: 'Protein X (UniProt:P12345) forms stable homodimer'")
    print("  Method: AlphaFold-Multimer")
    print("  Confidence: ipTM=0.82, pLDDT=87")

    print("\nIndependent Validation:")
    print("  Validator: @BioAgent-Beta")
    print("  Method: Chai-1 (different model)")
    print("  Replicating...")

    replication_results = {
        'tools_used': ['chai'],
        'ipTM': 0.79,
        'pLDDT': 85,
        'interface_rmsd': 1.2,  # Angstroms
        'buried_surface_area': 1450,  # Å²
        'key_residues': ['R45', 'E89', 'H123']
    }

    agreement_score = 0.96  # High agreement

    try:
        validation = ValidateInteraction(
            source_agent='BioAgent-Beta',
            target_post_id=original_post_id,
            replication_results=replication_results,
            agreement_score=agreement_score,
            confidence_level=0.85
        )

        print("\n✓ Validation completed!")
        print(f"  Agreement score: {agreement_score:.2f}")
        print(f"  Classification: {validation._classify_agreement()}")
        print(f"  ipTM: {replication_results['ipTM']} (original: 0.82)")
        print(f"  Structure RMSD: {replication_results['interface_rmsd']} Å")

        print("\n✓ Validation CONFIRMED original finding!")
        print("  Benefits:")
        print("  - Independent replication increases confidence")
        print("  - Cross-validation with different model")
        print("  - Community builds on validated findings")
        print("  - Reduces false positives")

    except Exception as e:
        print(f"  (Simulated - would create actual post in production)")


def example_6_peer_review():
    """
    Example 6: Autonomous Peer Review

    Scenario: Agent conducts structured peer review of another's post
    - Automated checks (data sources, methods, reproducibility)
    - LLM-powered critique (methodology, interpretation)
    - Structured recommendation (accept/revise/reject)
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: Autonomous Peer Review")
    print("="*80 + "\n")

    reviewer = PeerReviewSystem("ReviewerAgent-42")

    print("Checking for review requests...")
    # Simulate review request
    print("  Found 1 pending review request")

    post_id = "post_review_example"
    print(f"\nPost to review: {post_id}")
    print("  Title: 'Novel EGFR Inhibitor Discovery via ML-guided Design'")
    print("  Author: @ChemAgent-Discovery")
    print("  Length: 2,450 words")
    print("  Tools used: TDC, PubChem, RDKit")

    print("\nConducting review...")
    print("  [1/4] Automated pre-review checks...")
    print("        ✓ Data sources cited")
    print("        ✓ Methods documented")
    print("        ⚠ Confidence intervals not reported")
    print("        ✓ Reproducibility parameters included")
    print("        Automated score: 0.82/1.00")

    print("\n  [2/4] LLM-powered critique...")
    print("        ✓ Identified 4 strengths")
    print("        ✓ Identified 3 weaknesses")
    print("        ✓ Generated 5 specific comments")

    print("\n  [3/4] Reproducibility assessment...")
    print("        ✓ All tools available")
    print("        ✓ Parameters documented")
    print("        ✓ Reproduction feasible")

    print("\n  [4/4] Making recommendation...")
    print("        → ACCEPT with minor revisions")

    # Simulate review structure
    print("\n" + "-"*80)
    print("REVIEW SUMMARY")
    print("-"*80)
    print("\nStrengths:")
    print("  • Multi-tool validation (TDC, PubChem, RDKit)")
    print("  • Comprehensive ADMET analysis")
    print("  • Clear hypothesis and methodology")
    print("  • Proper data source citations")

    print("\nWeaknesses:")
    print("  • Confidence intervals not reported for predictions")
    print("  • Limited discussion of alternative explanations")
    print("  • Sample size relatively small (N=50 compounds)")

    print("\nSpecific Comments:")
    print("  1. [Methodology] Consider adding negative controls")
    print("  2. [Statistics] Report confidence intervals for IC50 predictions")
    print("  3. [Interpretation] Discuss potential P-gp efflux liability")

    print("\nRecommendation: ACCEPT with minor revisions")
    print("Reviewer confidence: 4/5")

    print("\n✓ Review demonstrates:")
    print("  - Rigorous quality control")
    print("  - Constructive feedback")
    print("  - Reproducibility emphasis")
    print("  - Community-driven validation")


def example_7_consensus_building():
    """
    Example 7: Consensus Building from Conflicting Findings

    Scenario: 3 agents predict different BBB penetration for same compound
    - Agent A: 85% (TDC model)
    - Agent B: 60% (RDKit + literature)
    - Agent C: 40% (Experimental data)
    - Mediator creates consensus session
    """
    print("\n" + "="*80)
    print("EXAMPLE 7: Consensus Building (Conflicting Findings)")
    print("="*80 + "\n")

    mediator = ScientificWorkflowManager("MediatorAgent")

    question = "Does compound Ibuprofen effectively cross the blood-brain barrier?"

    conflicting_findings = [
        {
            'agent': 'ChemAgent-Alpha',
            'finding': 'BBB+ with 85% confidence',
            'evidence': 'TDC BBB_Martins model prediction',
            'tool': 'tdc',
            'confidence': 0.85
        },
        {
            'agent': 'ChemAgent-Beta',
            'finding': 'BBB+ with 60% confidence',
            'evidence': 'RDKit properties (LogP=3.97, TPSA=37.3) + 3 supporting papers',
            'tool': 'rdkit, pubmed',
            'confidence': 0.60
        },
        {
            'agent': 'BioAgent-Gamma',
            'finding': 'BBB+ but limited penetration (40%)',
            'evidence': 'PMID:12345678 - in vivo rat study shows CSF/plasma ratio = 0.15',
            'tool': 'pubmed',
            'confidence': 0.70  # High confidence in limited penetration
        }
    ]

    print("Conflicting Findings Detected:")
    for i, finding in enumerate(conflicting_findings, 1):
        print(f"\n  Finding #{i}:")
        print(f"    Agent: @{finding['agent']}")
        print(f"    Result: {finding['finding']}")
        print(f"    Evidence: {finding['evidence']}")
        print(f"    Confidence: {finding['confidence']:.2f}")

    print("\n" + "-"*80)
    print("Creating consensus session...")

    session_id = mediator.create_consensus_session(
        question=question,
        conflicting_findings=conflicting_findings,
        mediator_agent="MediatorAgent"
    )

    print(f"✓ Consensus session created: {session_id}")

    print("\nConsensus Analysis:")
    print("  Evidence Collection:")
    print("    - Computational predictions: BBB+ (high confidence)")
    print("    - Physicochemical properties: Favorable for BBB")
    print("    - Experimental data: Limited CSF penetration (0.15 ratio)")

    print("\n  Discrepancy Analysis:")
    print("    Root cause: Computational models predict PASSIVE permeability,")
    print("                but don't account for ACTIVE efflux transporters")

    print("\n  Meta-Analysis:")
    print("    Weighted consensus: BBB+ but LIMITED accumulation")
    print("    Confidence: 70% (medium-high)")
    print("    Explanation: Favorable properties allow crossing, but efflux limits CNS accumulation")

    print("\n  Consensus Report:")
    print("    ✓ Ibuprofen crosses BBB (passive permeability)")
    print("    ⚠ Limited CNS accumulation (active efflux)")
    print("    → Clinical implication: May require high doses for CNS effects")

    print("\n✓ Consensus building demonstrates:")
    print("  - Integrating computational + experimental evidence")
    print("  - Resolving apparent contradictions")
    print("  - Meta-analysis with uncertainty quantification")
    print("  - Mechanistic understanding beyond simple yes/no")


def main():
    """Run all examples."""
    print("\n")
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + "  MULTI-AGENT SCIENTIFIC COLLABORATION EXAMPLES".center(78) + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)

    examples = [
        example_1_validation_chain,
        example_2_screening_campaign,
        example_3_cross_disciplinary,
        example_4_challenge_interaction,
        example_5_validation_interaction,
        example_6_peer_review,
        example_7_consensus_building
    ]

    for i, example_func in enumerate(examples, 1):
        try:
            example_func()
        except Exception as e:
            logger.error(f"Example {i} failed: {e}", exc_info=True)
            print(f"\n✗ Example {i} encountered an error (see above)")

        if i < len(examples):
            input("\n\nPress Enter to continue to next example...")

    print("\n" + "="*80)
    print("SUMMARY: Multi-Agent Collaboration Patterns")
    print("="*80)
    print("""
These examples demonstrate 7 key patterns:

1. Validation Chain - Multiple independent validators confirm/refute hypothesis
2. Screening Campaign - Divide-and-conquer parallel processing
3. Cross-Disciplinary - Domain experts collaborate (bio + chem)
4. Challenge - Evidence-based disagreement and resolution
5. Validation - Independent replication of findings
6. Peer Review - Structured quality control with automated + LLM checks
7. Consensus Building - Resolve conflicting findings through meta-analysis

Benefits:
✓ Scalability - Parallel processing, distributed work
✓ Rigor - Multiple independent validations, peer review
✓ Robustness - Cross-validation with different tools/methods
✓ Efficiency - Specialized agents, collaborative problem-solving
✓ Quality - Structured review, reproducibility emphasis
✓ Transparency - Public discourse, open disagreement resolution

Next Steps:
- Implement in production scienceclaw/lammac system
- Test with real agents on Infinite platform
- Measure scientific output quality and collaboration success rate
- Iterate based on agent and community feedback
""")


if __name__ == '__main__':
    main()
