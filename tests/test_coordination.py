#!/usr/bin/env python3
"""
Phase 5 Tests: Multi-Agent Coordination

Tests for collaborative investigation sessions.

Author: ScienceClaw Team
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
import sys

# Add scienceclaw to path
SCIENCECLAW_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCIENCECLAW_DIR))

from coordination import SessionManager


class TestSessionManager(unittest.TestCase):
    """Tests for session manager."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.workspace_dir = Path(self.test_dir) / ".openclaw" / "workspace"
        self.sessions_dir = self.workspace_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock home directory
        from unittest.mock import patch
        self.mock_home_patcher = patch("pathlib.Path.home", return_value=Path(self.test_dir))
        self.mock_home_patcher.start()
        
        self.manager1 = SessionManager("Agent1")
        self.manager2 = SessionManager("Agent2")
    
    def tearDown(self):
        """Clean up test environment."""
        self.mock_home_patcher.stop()
        shutil.rmtree(self.test_dir)
    
    def test_create_session(self):
        """Test session creation."""
        tasks = [
            {"id": "task_1", "description": "Test A", "tool": "tdc"},
            {"id": "task_2", "description": "Test B", "tool": "tdc"}
        ]
        
        session_id = self.manager1.create_collaborative_session(
            topic="BBB test",
            description="Test BBB model",
            tasks=tasks,
            max_participants=2
        )
        
        self.assertIsNotNone(session_id)
        self.assertTrue(session_id.startswith("scienceclaw-collab-"))
        
        # Verify session file exists
        session_file = self.sessions_dir / f"{session_id}.json"
        self.assertTrue(session_file.exists())
        
        # Verify session content
        with open(session_file) as f:
            session = json.load(f)
        
        self.assertEqual(session["topic"], "BBB test")
        self.assertEqual(len(session["tasks"]), 2)
        self.assertIn("Agent1", session["participants"])
    
    def test_join_session(self):
        """Test joining an existing session."""
        tasks = [{"id": "task_1", "description": "Test", "tool": "tdc"}]
        
        session_id = self.manager1.create_collaborative_session(
            topic="Test",
            description="Test session",
            tasks=tasks
        )
        
        # Agent 2 joins
        result = self.manager2.join_session(session_id)
        
        self.assertEqual(result["status"], "joined")
        self.assertIn("Agent2", result["session"]["participants"])
    
    def test_claim_task(self):
        """Test task claiming."""
        tasks = [
            {"id": "task_1", "description": "Test A", "tool": "tdc"},
            {"id": "task_2", "description": "Test B", "tool": "tdc"}
        ]
        
        session_id = self.manager1.create_collaborative_session(
            topic="Test",
            description="Test session",
            tasks=tasks
        )
        
        # Claim task
        result = self.manager1.claim_task(session_id, "task_1")
        
        self.assertEqual(result["status"], "claimed")
        self.assertEqual(result["task"]["id"], "task_1")
        
        # Try to claim already claimed task (should fail)
        self.manager2.join_session(session_id)
        result2 = self.manager2.claim_task(session_id, "task_1")
        self.assertIn("error", result2)
    
    def test_share_finding(self):
        """Test sharing findings to session."""
        tasks = [{"id": "task_1", "description": "Test", "tool": "tdc"}]
        
        session_id = self.manager1.create_collaborative_session(
            topic="Test",
            description="Test session",
            tasks=tasks
        )
        
        self.manager1.claim_task(session_id, "task_1")
        
        # Share finding
        finding = {
            "task_id": "task_1",
            "result": {"bbb_prediction": 0.75},
            "interpretation": "High BBB penetration"
        }
        
        result = self.manager1.share_to_session(session_id, finding)
        
        self.assertEqual(result["status"], "shared")
        self.assertEqual(result["finding_count"], 1)
        
        # Verify finding was saved
        state = self.manager1.get_session_state(session_id)
        self.assertEqual(len(state["session"]["findings"]), 1)
        self.assertIn("task_1", state["session"]["completed_tasks"])
    
    def test_session_progress_tracking(self):
        """Test session progress calculation."""
        tasks = [
            {"id": "task_1", "description": "Test A", "tool": "tdc"},
            {"id": "task_2", "description": "Test B", "tool": "tdc"},
            {"id": "task_3", "description": "Test C", "tool": "tdc"}
        ]
        
        session_id = self.manager1.create_collaborative_session(
            topic="Test",
            description="Test session",
            tasks=tasks
        )
        
        # Complete first task
        self.manager1.claim_task(session_id, "task_1")
        self.manager1.share_to_session(session_id, {
            "task_id": "task_1",
            "result": {"data": "test"}
        })
        
        # Check progress
        state = self.manager1.get_session_state(session_id)
        progress = state["progress"]
        
        self.assertEqual(progress["total_tasks"], 3)
        self.assertEqual(progress["completed_tasks"], 1)
        self.assertAlmostEqual(progress["progress_percent"], 33.33, places=1)
    
    def test_list_active_sessions(self):
        """Test listing active sessions."""
        # Create multiple sessions
        tasks = [{"id": "task_1", "description": "Test", "tool": "tdc"}]
        
        session1 = self.manager1.create_collaborative_session(
            topic="Session 1",
            description="Test 1",
            tasks=tasks
        )
        
        session2 = self.manager1.create_collaborative_session(
            topic="Session 2",
            description="Test 2",
            tasks=tasks
        )
        
        # List sessions
        active = self.manager1.list_active_sessions()
        
        self.assertEqual(len(active), 2)
        session_ids = [s["id"] for s in active]
        self.assertIn(session1, session_ids)
        self.assertIn(session2, session_ids)
    
    def test_complete_session(self):
        """Test marking session as complete."""
        tasks = [{"id": "task_1", "description": "Test", "tool": "tdc"}]
        
        session_id = self.manager1.create_collaborative_session(
            topic="Test",
            description="Test session",
            tasks=tasks
        )
        
        # Complete session
        result = self.manager1.complete_session(
            session_id,
            summary="All tasks completed successfully",
            post_id="post_123"
        )
        
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["session"]["status"], "complete")
        self.assertIn("completed_at", result["session"])
        
        # Verify it's no longer in active sessions
        active = self.manager1.list_active_sessions()
        session_ids = [s["id"] for s in active]
        self.assertNotIn(session_id, session_ids)
    
    def test_find_available_tasks(self):
        """Test finding unclaimed tasks."""
        tasks = [
            {"id": "task_1", "description": "Test A", "tool": "tdc"},
            {"id": "task_2", "description": "Test B", "tool": "tdc"},
            {"id": "task_3", "description": "Test C", "tool": "tdc"}
        ]
        
        session_id = self.manager1.create_collaborative_session(
            topic="Test",
            description="Test session",
            tasks=tasks
        )
        
        # Claim one task
        self.manager1.claim_task(session_id, "task_1")
        
        # Find available
        available = self.manager1.find_available_tasks(session_id)
        
        self.assertEqual(len(available), 2)
        available_ids = [t["id"] for t in available]
        self.assertNotIn("task_1", available_ids)
        self.assertIn("task_2", available_ids)
        self.assertIn("task_3", available_ids)


def run_tests():
    """Run all Phase 5 tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSessionManager)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("PHASE 5 TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
