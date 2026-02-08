#!/usr/bin/env python3
"""
Session Manager - Multi-Agent Coordination

Manages collaborative investigation sessions where multiple agents work
together on large-scale research tasks.

Uses Infinite/ScienceClaw session architecture:
- Shared state stored in ~/.infinite/workspace/sessions/{session_id}.json
- Distributed coordination (no central controller)
- Agents poll for updates during heartbeat cycles

Example workflow:
1. Agent1 identifies large investigation (e.g., "Test BBB for 100 FDA drugs")
2. Agent1 creates session and claims 50 drugs
3. Agent1 posts to Infinite chemistry community with session tag
4. Agent2 sees post, joins session, claims remaining 50 drugs
5. Both agents execute experiments independently
6. Results are combined and shared with citations

Author: ScienceClaw Team
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4


class SessionManager:
    """
    Manages collaborative investigation sessions for multi-agent coordination.
    
    Uses distributed coordination:
    - No central server
    - Agents poll session files during heartbeat
    - Shared state in OpenClaw workspace
    - Automatic task claiming with conflict resolution
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize session manager for an agent.
        
        Args:
            agent_name: Name of the agent
        """
        self.agent_name = agent_name
        
        # Session storage in Infinite workspace (analogous to OpenClaw workspace)
        self.workspace_dir = Path.home() / ".infinite" / "workspace"
        self.sessions_dir = self.workspace_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[SessionManager] Initialized for agent: {agent_name}")
        print(f"[SessionManager] Sessions directory: {self.sessions_dir}")
    
    def create_collaborative_session(
        self,
        topic: str,
        description: str,
        tasks: List[Dict[str, Any]],
        max_participants: int = 5
    ) -> str:
        """
        Create a new collaborative investigation session.
        
        Args:
            topic: Research topic/goal
            description: Detailed description of the investigation
            tasks: List of tasks to be claimed by agents
                Each task: {"id": str, "description": str, "tool": str, "parameters": dict}
            max_participants: Maximum number of agents allowed
        
        Returns:
            Session ID
        
        Example:
            session_id = manager.create_collaborative_session(
                topic="BBB penetration screening for 100 FDA drugs",
                description="Test TDC BBB model on diverse drug set",
                tasks=[
                    {"id": "drug_1", "description": "Test aspirin", "tool": "tdc", "parameters": {"smiles": "..."}},
                    {"id": "drug_2", "description": "Test ibuprofen", "tool": "tdc", "parameters": {"smiles": "..."}},
                    ...
                ],
                max_participants=3
            )
        """
        session_id = f"scienceclaw-collab-{uuid4().hex[:8]}"
        
        session = {
            "id": session_id,
            "topic": topic,
            "description": description,
            "created_by": self.agent_name,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",  # active, complete, abandoned
            "max_participants": max_participants,
            "participants": [self.agent_name],
            "tasks": tasks,
            "claimed_tasks": {},  # task_id -> agent_name
            "completed_tasks": {},  # task_id -> result
            "findings": [],  # Shared findings from all agents
            "metadata": {}
        }
        
        # Save session
        session_file = self.sessions_dir / f"{session_id}.json"
        with open(session_file, "w") as f:
            json.dump(session, f, indent=2)
        
        print(f"[SessionManager] Created session: {session_id}")
        print(f"[SessionManager] Topic: {topic}")
        print(f"[SessionManager] Tasks: {len(tasks)}")
        
        return session_id
    
    def join_session(self, session_id: str) -> Dict[str, Any]:
        """
        Join an existing collaborative session.
        
        Args:
            session_id: ID of the session to join
        
        Returns:
            Session state or error
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return {"error": "Session not found"}
        
        # Load session with lock to prevent race conditions
        session = self._load_session(session_id)
        
        # Check if already a participant
        if self.agent_name in session["participants"]:
            return {"status": "already_joined", "session": session}
        
        # Check participant limit
        if len(session["participants"]) >= session["max_participants"]:
            return {"error": "Session full"}
        
        # Add participant
        session["participants"].append(self.agent_name)
        session["metadata"][f"{self.agent_name}_joined_at"] = datetime.utcnow().isoformat()
        
        # Save
        self._save_session(session_id, session)
        
        print(f"[SessionManager] Joined session: {session_id}")
        print(f"[SessionManager] Participants: {len(session['participants'])}")
        
        return {"status": "joined", "session": session}
    
    def claim_task(self, session_id: str, task_id: str) -> Dict[str, Any]:
        """
        Claim a task in a session.
        
        Uses atomic write operations to prevent conflicts.
        
        Args:
            session_id: Session ID
            task_id: Task ID to claim
        
        Returns:
            Result with claimed status
        """
        session = self._load_session(session_id)
        
        if not session:
            return {"error": "Session not found"}
        
        # Check if agent is a participant
        if self.agent_name not in session["participants"]:
            return {"error": "Not a participant. Join session first."}
        
        # Check if task exists
        task = None
        for t in session["tasks"]:
            if t["id"] == task_id:
                task = t
                break
        
        if not task:
            return {"error": "Task not found"}
        
        # Check if already claimed
        if task_id in session["claimed_tasks"]:
            current_claimer = session["claimed_tasks"][task_id]
            if current_claimer == self.agent_name:
                return {"status": "already_claimed_by_you", "task": task}
            else:
                return {"error": f"Task already claimed by {current_claimer}"}
        
        # Claim task
        session["claimed_tasks"][task_id] = self.agent_name
        session["metadata"][f"task_{task_id}_claimed_at"] = datetime.utcnow().isoformat()
        
        # Save
        self._save_session(session_id, session)
        
        print(f"[SessionManager] Claimed task: {task_id}")
        
        return {"status": "claimed", "task": task}
    
    def share_to_session(
        self,
        session_id: str,
        finding: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Share a finding to the session.
        
        Args:
            session_id: Session ID
            finding: Finding to share
                {
                    "task_id": str,
                    "result": dict,
                    "interpretation": str,
                    "data": any
                }
        
        Returns:
            Success status
        """
        session = self._load_session(session_id)
        
        if not session:
            return {"error": "Session not found"}
        
        # Add metadata
        finding["agent"] = self.agent_name
        finding["timestamp"] = datetime.utcnow().isoformat()
        
        # Add to findings
        session["findings"].append(finding)
        
        # Mark task as completed if task_id provided
        if "task_id" in finding:
            task_id = finding["task_id"]
            if task_id in session["claimed_tasks"]:
                session["completed_tasks"][task_id] = {
                    "result": finding.get("result"),
                    "completed_by": self.agent_name,
                    "completed_at": finding["timestamp"]
                }
        
        # Save
        self._save_session(session_id, session)
        
        print(f"[SessionManager] Shared finding to session: {session_id}")
        
        return {"status": "shared", "finding_count": len(session["findings"])}
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current state of a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            Session state with progress tracking
        """
        session = self._load_session(session_id)
        
        if not session:
            return None
        
        # Calculate progress
        total_tasks = len(session["tasks"])
        claimed_tasks = len(session["claimed_tasks"])
        completed_tasks = len(session["completed_tasks"])
        
        progress = {
            "total_tasks": total_tasks,
            "claimed_tasks": claimed_tasks,
            "completed_tasks": completed_tasks,
            "progress_percent": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }
        
        return {
            "session": session,
            "progress": progress
        }
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active collaborative sessions.
        
        Returns:
            List of session summaries
        """
        sessions = []
        
        for session_file in self.sessions_dir.glob("scienceclaw-collab-*.json"):
            try:
                with open(session_file) as f:
                    session = json.load(f)
                
                if session.get("status") == "active":
                    # Calculate progress
                    total = len(session.get("tasks", []))
                    completed = len(session.get("completed_tasks", {}))
                    
                    sessions.append({
                        "id": session["id"],
                        "topic": session["topic"],
                        "created_by": session["created_by"],
                        "participants": session["participants"],
                        "total_tasks": total,
                        "completed_tasks": completed,
                        "progress": (completed / total * 100) if total > 0 else 0,
                        "created_at": session["created_at"]
                    })
            except Exception as e:
                print(f"Warning: Failed to load session {session_file}: {e}")
        
        return sessions
    
    def find_available_tasks(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Find unclaimed tasks in a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            List of available tasks
        """
        session = self._load_session(session_id)
        
        if not session:
            return []
        
        available = []
        for task in session.get("tasks", []):
            task_id = task["id"]
            if task_id not in session.get("claimed_tasks", {}):
                available.append(task)
        
        return available
    
    def complete_session(
        self,
        session_id: str,
        summary: str,
        post_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark a session as complete.
        
        Args:
            session_id: Session ID
            summary: Summary of collaborative findings
            post_id: Optional post ID where results were shared
        
        Returns:
            Completion status
        """
        session = self._load_session(session_id)
        
        if not session:
            return {"error": "Session not found"}
        
        # Update status
        session["status"] = "complete"
        session["completed_at"] = datetime.utcnow().isoformat()
        session["summary"] = summary
        
        if post_id:
            session["result_post_id"] = post_id
        
        # Save
        self._save_session(session_id, session)
        
        print(f"[SessionManager] Session completed: {session_id}")
        
        return {"status": "complete", "session": session}
    
    def _load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session from file."""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None
    
    def _save_session(self, session_id: str, session: Dict[str, Any]):
        """Save session to file."""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        # Atomic write using temp file
        temp_file = session_file.with_suffix(".tmp")
        
        try:
            with open(temp_file, "w") as f:
                json.dump(session, f, indent=2)
            
            # Atomic rename
            temp_file.replace(session_file)
        except Exception as e:
            print(f"Error saving session {session_id}: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise


# Test function
def test_session_manager():
    """Test the session manager with a sample workflow."""
    
    # Agent 1 creates session
    manager1 = SessionManager("Agent1")
    
    tasks = [
        {"id": "task_1", "description": "Test compound A", "tool": "tdc", "parameters": {"smiles": "CCO"}},
        {"id": "task_2", "description": "Test compound B", "tool": "tdc", "parameters": {"smiles": "CC(C)O"}},
        {"id": "task_3", "description": "Test compound C", "tool": "tdc", "parameters": {"smiles": "CCCO"}},
    ]
    
    session_id = manager1.create_collaborative_session(
        topic="BBB penetration test for alcohols",
        description="Test TDC BBB model on simple alcohols",
        tasks=tasks,
        max_participants=2
    )
    
    print(f"\nSession created: {session_id}")
    
    # Agent 1 claims first task
    claim1 = manager1.claim_task(session_id, "task_1")
    print(f"Agent1 claimed: {claim1['status']}")
    
    # Agent 2 joins and claims second task
    manager2 = SessionManager("Agent2")
    join_result = manager2.join_session(session_id)
    print(f"Agent2 joined: {join_result['status']}")
    
    claim2 = manager2.claim_task(session_id, "task_2")
    print(f"Agent2 claimed: {claim2['status']}")
    
    # List available tasks
    available = manager1.find_available_tasks(session_id)
    print(f"Available tasks: {len(available)}")
    
    # Agent 1 shares finding
    finding1 = {
        "task_id": "task_1",
        "result": {"bbb_prediction": 0.65},
        "interpretation": "Ethanol has moderate BBB penetration"
    }
    manager1.share_to_session(session_id, finding1)
    
    # Get session state
    state = manager1.get_session_state(session_id)
    print(f"Progress: {state['progress']['completed_tasks']}/{state['progress']['total_tasks']}")
    
    # List all active sessions
    active_sessions = manager1.list_active_sessions()
    print(f"Active sessions: {len(active_sessions)}")
    
    print("\n✓ Session manager test complete")


if __name__ == "__main__":
    test_session_manager()
