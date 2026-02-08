#!/usr/bin/env python3
"""
Test Scientific Reasoning Engine (Phase 2)

Tests autonomous scientific method loop:
- Gap detection
- Hypothesis generation
- Experiment design
- Experiment execution
- Result analysis
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from reasoning import ScientificReasoningEngine


def test_reasoning_engine():
    """Test the complete reasoning engine."""
    print("\n" + "="*80)
    print("TESTING SCIENTIFIC REASONING ENGINE")
    print("="*80)
    
    # Initialize engine
    engine = ScientificReasoningEngine("TestAgent")
    print("✓ Reasoning engine initialized")
    
    # Create some test context (simulated posts from Infinite)
    context = {
        "posts": [
            {
                "id": "post_001",
                "title": "LNP delivery efficiency in muscle tissue",
                "content": "Studied different LNP formulations",
                "openQuestions": [
                    "What is the optimal DLin-MC3-DMA concentration?",
                    "How does temperature affect LNP stability?"
                ]
            }
        ]
    }
    
    print("\n" + "-"*80)
    print("Running scientific cycle...")
    print("-"*80)
    
    # Run one complete scientific cycle
    result = engine.run_scientific_cycle(context)
    
    print(f"\nMode: {result.get('mode')}")
    print(f"Status: {result.get('status')}")
    
    if "gap" in result:
        print(f"\nGap detected: {result['gap'].get('description', '')[:100]}...")
    
    if "hypothesis" in result:
        print(f"\nHypothesis: {result['hypothesis'].get('statement', '')[:100]}...")
    
    if "investigation_id" in result:
        print(f"\nInvestigation ID: {result['investigation_id'][:8]}...")
    
    if "experiment_plan" in result:
        plan = result['experiment_plan']
        print(f"\nExperiment: {plan.get('tool')} - {plan.get('description', '')[:80]}...")
    
    if "experiment_result" in result:
        exp_result = result['experiment_result']
        print(f"\nResult Status: {exp_result.get('status')}")
        if exp_result.get('status') == 'success':
            print(f"Summary: {exp_result.get('summary', '')}")
    
    if "analysis" in result:
        analysis = result['analysis']
        print(f"\nAnalysis:")
        print(f"  Support: {analysis.get('support')}")
        print(f"  Confidence: {analysis.get('confidence')}")
        print(f"  Reasoning: {analysis.get('reasoning', '')[:100]}...")
    
    if "conclusion" in result:
        conclusion = result['conclusion']
        print(f"\nConclusion: {conclusion.get('statement', '')[:100]}...")
    
    print("\n✅ Reasoning engine test complete!")
    print("\nActions taken:")
    for i, action in enumerate(result.get('actions', []), 1):
        if isinstance(action, str):
            print(f"  {i}. {action}")
        else:
            print(f"  {i}. {action.get('action', 'unknown')}")
    
    return result


def test_components():
    """Test individual reasoning components."""
    print("\n" + "="*80)
    print("TESTING INDIVIDUAL COMPONENTS")
    print("="*80)
    
    engine = ScientificReasoningEngine("TestAgent")
    
    # Test gap detection
    print("\n1. Gap Detection:")
    gaps = engine.observe_knowledge_gaps([{
        "id": "post_001",
        "openQuestions": ["How does X affect Y?"]
    }])
    print(f"   Found {len(gaps)} gaps")
    if gaps:
        print(f"   First gap: {gaps[0].get('description', '')[:80]}...")
    
    # Test hypothesis generation
    if gaps:
        print("\n2. Hypothesis Generation:")
        hypotheses = engine.generate_hypotheses(gaps[0])
        print(f"   Generated {len(hypotheses)} hypotheses")
        if hypotheses:
            print(f"   First: {hypotheses[0].get('statement', '')[:80]}...")
    
            # Test experiment design
            print("\n3. Experiment Design:")
            plan = engine.design_experiment(hypotheses[0])
            print(f"   Tool: {plan.get('tool')}")
            print(f"   Description: {plan.get('description', '')[:80]}...")
    
    print("\n✅ Component tests complete!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Phase 2 Reasoning Engine")
    parser.add_argument("--unit", action="store_true", help="Run comprehensive unit tests")
    parser.add_argument("--quick", action="store_true", help="Run quick demo only (no unit tests)")
    args = parser.parse_args()
    
    if args.unit:
        # Run comprehensive unittest suite
        import unittest
        from tests import test_reasoning_phase2
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_reasoning_phase2)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        exit(0 if result.wasSuccessful() else 1)
    
    print("\n" + "="*80)
    print("SCIENCECLAW PHASE 2 - SCIENTIFIC REASONING ENGINE TEST")
    print("="*80)
    
    # Test components
    test_components()
    
    # Test full engine
    test_reasoning_engine()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETE ✅")
    print("="*80)
    print("\nPhase 2 reasoning engine is operational!")
    print("\nRun comprehensive unit tests: python3 test_reasoning.py --unit")
    print("Next: Integrate with heartbeat_daemon.py")
    print("="*80 + "\n")
