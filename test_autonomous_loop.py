#!/usr/bin/env python3
"""
Phase 3 Test Runner

Quick test runner for Phase 3 autonomous control loop.

Usage:
    python3 test_phase3.py               # Run all tests
    python3 test_phase3.py --quick       # Run quick smoke tests
    python3 test_phase3.py --demo        # Run demo mode
"""

import sys
import argparse
from pathlib import Path

# Add parent dir to path
SCIENCECLAW_DIR = Path(__file__).parent
sys.path.insert(0, str(SCIENCECLAW_DIR))


def demo_mode():
    """Run demo of Phase 3 components."""
    print("="*70)
    print("PHASE 3 DEMO: Autonomous Control Loop")
    print("="*70)
    print()
    
    # Demo 1: Post Parser
    print("1. Testing Post Parser")
    print("-"*70)
    from utils.post_parser import test_parser
    test_parser()
    print()
    
    # Demo 2: Tool Selector
    print("2. Testing Tool Selector")
    print("-"*70)
    from utils.tool_selector import test_tool_selector
    test_tool_selector()
    print()
    
    # Demo 3: Loop Controller (basic)
    print("3. Testing Loop Controller")
    print("-"*70)
    try:
        from autonomous.loop_controller import test_loop_controller
        test_loop_controller()
    except Exception as e:
        print(f"Note: Loop controller requires platform configuration")
        print(f"Error: {e}")
    print()
    
    print("="*70)
    print("DEMO COMPLETE")
    print("="*70)


def quick_tests():
    """Run quick smoke tests."""
    print("Running quick smoke tests...")
    
    # Test imports
    try:
        from autonomous import AutonomousLoopController
        from utils.post_parser import parse_scientific_post
        from utils.tool_selector import recommend_tools_for_hypothesis
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def full_tests():
    """Run comprehensive test suite."""
    from tests.test_phase3 import run_tests
    return run_tests()


def main():
    parser = argparse.ArgumentParser(description="Test Phase 3 components")
    parser.add_argument("--quick", action="store_true", help="Quick smoke tests")
    parser.add_argument("--demo", action="store_true", help="Demo mode")
    
    args = parser.parse_args()
    
    if args.demo:
        demo_mode()
        return 0
    elif args.quick:
        success = quick_tests()
        return 0 if success else 1
    else:
        success = full_tests()
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
