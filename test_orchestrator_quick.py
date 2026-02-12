#!/usr/bin/env python3
"""
Quick test for autonomous orchestration - checks system can initialize.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coordination.autonomous_orchestrator import AutonomousOrchestrator

print("Testing Autonomous Orchestrator initialization...")

try:
    orchestrator = AutonomousOrchestrator()
    print("✓ Orchestrator initialized successfully")

    # Test topic analysis (rule-based fallback)
    print("\nTesting topic analysis...")
    strategy = orchestrator._rule_based_strategy("Alzheimer's disease drug targets")
    print(f"✓ Strategy determined: {strategy['investigation_type']}")
    print(f"  Agents needed: {len(strategy['agents'])}")
    print(f"  Pattern: {strategy['collaboration_pattern']}")

    # Test agent spawning
    print("\nTesting agent spawning...")
    agents = orchestrator._spawn_agents(strategy['agents'], "Test topic")
    print(f"✓ Spawned {len(agents)} agents:")
    for agent in agents:
        print(f"  - {agent['name']} ({agent['domain']})")
        print(f"    Skills: {', '.join(agent['skills'])}")

    print("\n✓ All basic tests passed!")
    print("\nSystem is ready for autonomous orchestration.")
    print("Run full demo with: python3 test_autonomous_orchestration.py")

except Exception as e:
    print(f"\n✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
