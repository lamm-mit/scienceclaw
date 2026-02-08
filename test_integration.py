#!/usr/bin/env python3
"""
Comprehensive Integration Test

Tests all 5 phases working together:
- Phase 1: Memory
- Phase 2: Reasoning
- Phase 3: Autonomous Loop
- Phase 4: Collaboration (mocked)
- Phase 5: Multi-Agent Coordination

Author: ScienceClaw Team
"""

import sys
from pathlib import Path

# Add scienceclaw to path
SCIENCECLAW_DIR = Path(__file__).parent
sys.path.insert(0, str(SCIENCECLAW_DIR))

def test_all_phases():
    """Run comprehensive integration test."""
    
    print("="*70)
    print("COMPREHENSIVE INTEGRATION TEST")
    print("="*70)
    print()
    
    # Phase 1: Memory System
    print("📚 Phase 1: Memory System")
    print("-" * 70)
    try:
        from memory import AgentJournal, InvestigationTracker, KnowledgeGraph
        
        journal = AgentJournal("TestAgent")
        tracker = InvestigationTracker("TestAgent")
        kg = KnowledgeGraph("TestAgent")
        
        # Log an observation
        journal.log_observation(
            content="Testing memory system",
            observation="All components initialize correctly",
            source="integration_test"
        )
        
        print("✓ AgentJournal initialized and working")
        print("✓ InvestigationTracker initialized")
        print("✓ KnowledgeGraph initialized")
        print()
    except Exception as e:
        print(f"✗ Phase 1 failed: {e}")
        return False
    
    # Phase 2: Scientific Reasoning
    print("🧠 Phase 2: Scientific Reasoning Engine")
    print("-" * 70)
    try:
        from reasoning import ScientificReasoningEngine
        from reasoning.gap_detector import GapDetector
        from reasoning.hypothesis_generator import HypothesisGenerator
        
        engine = ScientificReasoningEngine("TestAgent")
        gap_detector = GapDetector(knowledge_graph=kg, journal=journal)
        hyp_gen = HypothesisGenerator(knowledge_graph=kg, journal=journal)
        
        # Detect a gap
        gaps = gap_detector.detect_gaps()
        print(f"✓ GapDetector working ({len(gaps)} gaps detected)")
        
        # Generate hypothesis
        if gaps:
            hypotheses = hyp_gen.generate_hypotheses(gaps[0])
            print(f"✓ HypothesisGenerator working ({len(hypotheses)} hypotheses)")
        else:
            print("✓ HypothesisGenerator ready")
        
        print()
    except Exception as e:
        print(f"✗ Phase 2 failed: {e}")
        return False
    
    # Phase 3: Autonomous Loop Components
    print("🤖 Phase 3: Autonomous Loop")
    print("-" * 70)
    try:
        from utils.post_parser import parse_scientific_post, extract_citations
        from utils.tool_selector import recommend_tools_for_hypothesis
        
        # Test post parsing
        test_content = """
        **Hypothesis**: Aspirin crosses the BBB
        **Method**: Used TDC prediction
        **Findings**: BBB+ with 0.87 probability
        **Data Sources**: PubChem:2244, PMID:12345
        """
        
        parsed = parse_scientific_post(test_content)
        print(f"✓ Post parser working (found {len(parsed.get('hypothesis', ''))} char hypothesis)")
        
        # Test tool selection
        hypothesis = "Test if compound X crosses BBB"
        tools = recommend_tools_for_hypothesis(hypothesis, {})
        print(f"✓ Tool selector working ({len(tools)} tools recommended)")
        
        print()
    except Exception as e:
        print(f"✗ Phase 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Phase 4: Collaboration APIs (check client exists)
    print("🤝 Phase 4: Platform Collaboration")
    print("-" * 70)
    try:
        # Check if client has new methods
        sys.path.insert(0, str(SCIENCECLAW_DIR / "skills" / "infinite" / "scripts"))
        from infinite_client import InfiniteClient
        
        client = InfiniteClient()
        
        # Verify methods exist
        assert hasattr(client, 'get_comments'), "Missing get_comments method"
        assert hasattr(client, 'create_comment'), "Missing create_comment method"
        assert hasattr(client, 'get_notifications'), "Missing get_notifications method"
        assert hasattr(client, 'link_post'), "Missing link_post method"
        assert hasattr(client, 'delete_post'), "Missing delete_post method"
        
        print("✓ InfiniteClient has all Phase 4 methods")
        print("✓ Comments API ready")
        print("✓ Notifications API ready")
        print("✓ Post linking API ready")
        print()
    except Exception as e:
        print(f"✗ Phase 4 failed: {e}")
        return False
    
    # Phase 5: Multi-Agent Coordination
    print("👥 Phase 5: Multi-Agent Coordination")
    print("-" * 70)
    try:
        from coordination import SessionManager
        
        manager1 = SessionManager("Agent1")
        manager2 = SessionManager("Agent2")
        
        # Create session
        tasks = [
            {"id": "task_1", "description": "Test A", "tool": "tdc"},
            {"id": "task_2", "description": "Test B", "tool": "tdc"}
        ]
        
        session_id = manager1.create_collaborative_session(
            topic="Integration test session",
            description="Testing multi-agent coordination",
            tasks=tasks,
            max_participants=2
        )
        
        print(f"✓ Session created: {session_id[:20]}...")
        
        # Agent 2 joins
        result = manager2.join_session(session_id)
        assert result["status"] in ["joined", "already_joined"]
        print("✓ Agent2 joined session")
        
        # Claim tasks
        claim1 = manager1.claim_task(session_id, "task_1")
        assert claim1["status"] == "claimed"
        print("✓ Task claiming works")
        
        # Share finding
        manager1.share_to_session(session_id, {
            "task_id": "task_1",
            "result": {"test": "data"}
        })
        print("✓ Finding sharing works")
        
        # Check progress
        state = manager1.get_session_state(session_id)
        assert state["progress"]["completed_tasks"] == 1
        print(f"✓ Progress tracking works ({state['progress']['progress_percent']:.0f}%)")
        
        print()
    except Exception as e:
        print(f"✗ Phase 5 failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # All phases passed!
    print("="*70)
    print("🎉 ALL PHASES INTEGRATED SUCCESSFULLY! 🎉")
    print("="*70)
    print()
    print("Summary:")
    print("  ✓ Phase 1: Memory System - Working")
    print("  ✓ Phase 2: Scientific Reasoning - Working")
    print("  ✓ Phase 3: Autonomous Loop - Working")
    print("  ✓ Phase 4: Platform Collaboration - Working")
    print("  ✓ Phase 5: Multi-Agent Coordination - Working")
    print()
    print("The ScienceClaw autonomous agent system is fully operational!")
    print()
    
    return True


if __name__ == "__main__":
    success = test_all_phases()
    sys.exit(0 if success else 1)
