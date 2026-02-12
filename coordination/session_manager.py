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

try:
    from core.skill_registry import get_registry
    from core.topic_analyzer import LLMTopicAnalyzer
except Exception:
    get_registry = None
    LLMTopicAnalyzer = None

try:
    from coordination.event_logger import CoordinationEventLogger
except ImportError:
    CoordinationEventLogger = None


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

        # Event logger (initialized per-session)
        self.event_logger = None

        print(f"[SessionManager] Initialized for agent: {agent_name}")
        print(f"[SessionManager] Sessions directory: {self.sessions_dir}")
    
    def create_collaborative_session(
        self,
        topic: str,
        description: str,
        suggested_investigations: Optional[List[Dict[str, Any]]] = None,
        max_participants: int = 5,
        investigation_type: str = "multi-agent",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new collaborative investigation session (hybrid model).

        Hybrid approach: agents can work on suggested investigations OR contribute independently.
        Not mandatory—agents have agency to self-organize.

        Args:
            topic: Research topic/goal
            description: Detailed description of the investigation
            suggested_investigations: Optional list of suggested investigation areas:
                [{"id": "inv_1", "description": "Investigate X", "tools": ["pubmed", "uniprot"]}]
                These are suggestions, not requirements.
            max_participants: Maximum number of agents allowed
            investigation_type: Type of investigation (e.g., "multi-agent", "validation", "screening")
            metadata: Optional metadata

        Returns:
            Session ID

        Example:
            session_id = manager.create_collaborative_session(
                topic="BACE1 as drug target for Alzheimer's disease",
                description="Multi-agent investigation of BACE1 mechanisms",
                suggested_investigations=[
                    {"id": "inv_1", "description": "Literature review on BACE1 proteolysis", "tools": ["pubmed"]},
                    {"id": "inv_2", "description": "BACE1 protein structure analysis", "tools": ["uniprot", "pdb"]},
                    {"id": "inv_3", "description": "Screen BACE1 inhibitors", "tools": ["pubchem", "tdc"]}
                ],
                max_participants=4
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
            "investigation_type": investigation_type,
            "max_participants": max_participants,
            "participants": [self.agent_name],
            # Hybrid model: suggested investigations + independent findings
            "suggested_investigations": suggested_investigations or [],  # Optional suggestions
            "claimed_investigations": {},  # inv_id -> agent_name (agents can claim if interested)
            "findings": [],  # List of posted findings (both from claimed invs and independent)
            # Optional task graph for fine-grained tracking
            "graph": [],
            "graph_links": {},
            "metadata": metadata or {}
        }

        # Save session
        session_file = self.sessions_dir / f"{session_id}.json"
        with open(session_file, "w") as f:
            json.dump(session, f, indent=2)

        # Initialize and log event
        if CoordinationEventLogger:
            self.event_logger = CoordinationEventLogger(session_id)
            self.event_logger.log_session_created(
                topic=topic,
                created_by=self.agent_name,
                strategy={"investigation_type": investigation_type},
                description=description
            )

        print(f"[SessionManager] Created finding-centric session: {session_id}")
        print(f"[SessionManager] Topic: {topic}")
        print(f"[SessionManager] Investigation type: {investigation_type}")

        return session_id

    def annotate_tasks_with_skill_plan(
        self,
        session_id: str,
        agent_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
        max_skills: int = 5,
    ) -> Dict[str, Any]:
        """
        Annotate each task with a recommended skill plan using the same LLM-powered
        topic->skill selection used elsewhere (TopicAnalyzer).

        This does NOT execute any tools; it only suggests what to run.

        Args:
            session_id: session to update
            agent_profiles: optional dict keyed by agent name (BioLook, etc.) with profile info
            max_skills: max skills to recommend per task
        """
        session = self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        if not get_registry or not LLMTopicAnalyzer:
            return {"error": "Skill planning unavailable (core modules missing)"}

        registry = get_registry()
        all_skills = list(registry.skills.values())

        analyzer = LLMTopicAnalyzer(agent_name=self.agent_name)

        for task in session.get("tasks", []):
            topic = task.get("description") or task.get("id") or ""
            claimed_by = session.get("claimed_tasks", {}).get(task.get("id", ""), "")
            profile = None
            if agent_profiles and claimed_by in agent_profiles:
                profile = agent_profiles[claimed_by]

            available = all_skills
            if profile:
                preferred = set(profile.get("preferences", {}).get("tools", []))
                if preferred:
                    available = [s for s in all_skills if s.get("name") in preferred]

            analysis, selected = analyzer.analyze_and_select_skills(
                topic=topic,
                available_skills=available,
                max_skills=max_skills,
                agent_profile=profile,
            )

            task["skill_plan"] = {
                "investigation_type": getattr(analysis, "investigation_type", ""),
                "reasoning": getattr(analysis, "reasoning", ""),
                "key_concepts": getattr(analysis, "key_concepts", []) or [],
                "selected_skills": [
                    {
                        "name": s.get("name"),
                        "reason": s.get("reason", ""),
                        "suggested_params": s.get("suggested_params", {}) or {},
                    }
                    for s in (selected or [])
                ],
            }

        session["metadata"][f"skill_plan_updated_at"] = datetime.utcnow().isoformat()
        self._save_session(session_id, session)
        return {"status": "ok", "tasks": len(session.get("tasks", []))}

    # -------------------------------------------------------------------------
    # Task graph API (science-native coordination layer)
    # -------------------------------------------------------------------------

    def add_graph_to_session(
        self,
        session_id: str,
        graph_spec: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Attach or replace a science-native task graph for a session.

        The graph is stored in-session only (no DB changes) and is designed
        to mirror the scientific workflow at a finer granularity than the
        flat `tasks` list.

        Node schema (soft-enforced, not strictly validated):
            {
                "id": str,                        # graph node id (unique)
                "label": str,                     # short label
                "description": str,               # longer description
                "task_id": Optional[str],         # link to high-level task
                "status": "pending" | "in_progress" | "completed" | "blocked",
                "assigned_agent": Optional[str],  # agent currently responsible
                "upstream_ids": List[str],        # dependencies
                "downstream_ids": List[str],      # dependents
            }

        Args:
            session_id: Session to update.
            graph_spec: List of node dicts (see above).
        """
        session = self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        # Minimal sanity: ensure ids are unique and present
        seen_ids = set()
        cleaned: List[Dict[str, Any]] = []
        for node in graph_spec:
            node_id = node.get("id")
            if not node_id:
                continue
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)
            cleaned.append(
                {
                    "id": node_id,
                    "label": node.get("label") or node.get("description") or node_id,
                    "description": node.get("description", ""),
                    "task_id": node.get("task_id"),
                    "status": node.get("status", "pending"),
                    "assigned_agent": node.get("assigned_agent"),
                    "upstream_ids": list(node.get("upstream_ids", []) or []),
                    "downstream_ids": list(node.get("downstream_ids", []) or []),
                }
            )

        session["graph"] = cleaned
        # Ensure links mapping exists
        if "graph_links" not in session or not isinstance(session["graph_links"], dict):
            session["graph_links"] = {}

        session["metadata"][f"graph_updated_at"] = datetime.utcnow().isoformat()
        self._save_session(session_id, session)
        return {"status": "ok", "nodes": len(cleaned)}

    def update_task_node(
        self,
        session_id: str,
        node_id: str,
        **fields: Any,
    ) -> Dict[str, Any]:
        """
        Update a graph node in-place (status, assignment, etc.).

        This is intentionally flexible: any provided fields are shallow-merged
        onto the node dict, so callers can update status, assigned_agent,
        label/description, etc., without a rigid schema dependency.
        """
        session = self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        graph = session.get("graph") or []
        node = None
        for n in graph:
            if n.get("id") == node_id:
                node = n
                break

        if not node:
            return {"error": "Node not found"}

        for key, value in fields.items():
            # Avoid clobbering node id
            if key == "id":
                continue
            node[key] = value

        session["metadata"][f"graph_node_{node_id}_updated_at"] = datetime.utcnow().isoformat()
        self._save_session(session_id, session)
        return {"status": "ok", "node": node}

    def link_task_to_comment(
        self,
        session_id: str,
        node_id: str,
        post_id: str,
        comment_id: str,
    ) -> Dict[str, Any]:
        """
        Record that a particular graph node has evidence in an Infinite
        post comment.

        This keeps the linkage in the session JSON only (no API calls),
        so later tooling / UI can render investigation graphs without
        modifying the Infinite schema.
        """
        session = self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        if "graph_links" not in session or not isinstance(session["graph_links"], dict):
            session["graph_links"] = {}

        links = session["graph_links"].get(node_id) or {"post_id": post_id, "comment_ids": []}
        # If we already have a post_id and it's different, we still keep
        # the original as canonical, but avoid hard failing.
        if "post_id" not in links or not links["post_id"]:
            links["post_id"] = post_id

        if comment_id and comment_id not in links.get("comment_ids", []):
            links.setdefault("comment_ids", []).append(comment_id)

        session["graph_links"][node_id] = links
        session["metadata"][f"graph_node_{node_id}_linked_at"] = datetime.utcnow().isoformat()
        self._save_session(session_id, session)
        return {"status": "ok", "links": links}
    
    def join_session(self, session_id: str, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Join an existing collaborative session.

        Args:
            session_id: ID of the session to join
            agent_name: Optional override for the joining agent. If not provided,
                defaults to this SessionManager's agent_name. This is used by
                autonomous orchestrators that join on behalf of spawned agents.

        Returns:
            Session state or error
        """
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return {"error": "Session not found"}

        # Load session with lock to prevent race conditions
        session = self._load_session(session_id)

        joiner = agent_name or self.agent_name

        # Check if already a participant
        if joiner in session["participants"]:
            return {"status": "already_joined", "session": session}

        # Check participant limit
        if len(session["participants"]) >= session["max_participants"]:
            return {"error": "Session full"}

        # Add participant
        session["participants"].append(joiner)
        session["metadata"][f"{joiner}_joined_at"] = datetime.utcnow().isoformat()

        # Save
        self._save_session(session_id, session)

        # Log event (initialize logger if needed)
        if CoordinationEventLogger:
            if not self.event_logger:
                self.event_logger = CoordinationEventLogger(session_id)
            self.event_logger.log_agent_joined(
                agent_name=joiner,
                reasoning="Joined manually",
                skill_match={}
            )

        print(f"[SessionManager] Joined session: {session_id}")
        print(f"[SessionManager] Participants: {len(session['participants'])}")

        return {"status": "joined", "session": session}
    
    def claim_investigation(
        self,
        session_id: str,
        investigation_id: str
    ) -> Dict[str, Any]:
        """
        Optionally claim a suggested investigation (not mandatory).

        Agents can claim investigations if interested, or work independently.

        Args:
            session_id: Session ID
            investigation_id: Suggested investigation ID to claim

        Returns:
            Claim status
        """
        session = self._load_session(session_id)

        if not session:
            return {"error": "Session not found"}

        if self.agent_name not in session["participants"]:
            return {"error": "Not a participant. Join session first."}

        # Find the suggested investigation
        investigation = None
        for inv in session.get("suggested_investigations", []):
            if inv["id"] == investigation_id:
                investigation = inv
                break

        if not investigation:
            return {"error": "Investigation not found"}

        # Check if already claimed
        if investigation_id in session.get("claimed_investigations", {}):
            current_claimer = session["claimed_investigations"][investigation_id]
            if current_claimer == self.agent_name:
                return {"status": "already_claimed_by_you", "investigation": investigation}
            else:
                return {"status": "already_claimed", "claimed_by": current_claimer}

        # Claim investigation (optional)
        session["claimed_investigations"][investigation_id] = self.agent_name
        session["metadata"][f"investigation_{investigation_id}_claimed_at"] = datetime.utcnow().isoformat()

        # Save
        self._save_session(session_id, session)

        # Log event
        if CoordinationEventLogger:
            if not self.event_logger:
                self.event_logger = CoordinationEventLogger(session_id)
            self.event_logger.log_task_claimed(
                task_id=investigation_id,
                agent_name=self.agent_name,
                role="investigator",
                reasoning=f"Claimed suggested investigation: {investigation.get('description', '')}"
            )

        print(f"[SessionManager] Claimed investigation: {investigation_id}")

        return {"status": "claimed", "investigation": investigation}

    def post_finding(
        self,
        session_id: str,
        result: str,
        evidence: Optional[Dict[str, Any]] = None,
        confidence: float = 0.8,
        reasoning_trace: str = ""
    ) -> Dict[str, Any]:
        """
        Post a finding to the session.

        Findings are the unit of collaboration. Other agents can validate/challenge.

        Args:
            session_id: Session ID
            result: Main conclusion/result
            evidence: Evidence supporting the result:
                - tool_outputs: {tool_name: result}
                - sources: [PMID, UniProt ID, etc.]
            confidence: Confidence in finding (0.0-1.0)
            reasoning_trace: Step-by-step reasoning

        Returns:
            Finding ID and status
        """
        session = self._load_session(session_id)

        if not session:
            return {"error": "Session not found"}

        if self.agent_name not in session["participants"]:
            return {"error": "Not a participant. Join session first."}

        # Create finding
        finding_id = f"finding_{uuid4().hex[:8]}"
        finding = {
            "id": finding_id,
            "agent": self.agent_name,
            "result": result,
            "evidence": evidence or {},
            "confidence": confidence,
            "reasoning_trace": reasoning_trace,
            "timestamp": datetime.utcnow().isoformat(),
            "validations": []  # Will be filled by validators
        }

        # Add to findings
        session["findings"].append(finding)
        session["metadata"][f"finding_{finding_id}_posted_at"] = datetime.utcnow().isoformat()

        # Save
        self._save_session(session_id, session)

        # Log event
        if CoordinationEventLogger:
            if not self.event_logger:
                self.event_logger = CoordinationEventLogger(session_id)
            self.event_logger.log_finding_posted(
                agent_name=self.agent_name,
                task_id=finding_id,  # Use finding_id as task_id for event logging
                finding_summary=result,
                confidence=confidence
            )

        print(f"[SessionManager] Posted finding to session: {session_id}")
        print(f"[SessionManager] Finding ID: {finding_id}")

        return {"status": "posted", "finding_id": finding_id, "finding": finding}
    
    def validate_finding(
        self,
        session_id: str,
        finding_id: str,
        validation_status: str,
        reasoning: str,
        confidence: float = 0.8
    ) -> Dict[str, Any]:
        """
        Validate (or challenge) another agent's finding.

        Args:
            session_id: Session ID
            finding_id: Finding ID to validate
            validation_status: "confirmed", "partial", "challenged", "inconclusive"
            reasoning: Explanation for validation
            confidence: Confidence in validation (0.0-1.0)

        Returns:
            Validation record
        """
        session = self._load_session(session_id)

        if not session:
            return {"error": "Session not found"}

        if self.agent_name not in session["participants"]:
            return {"error": "Not a participant. Join session first."}

        # Find the finding
        finding = None
        for f in session.get("findings", []):
            if f["id"] == finding_id:
                finding = f
                break

        if not finding:
            return {"error": "Finding not found"}

        # Don't self-validate
        if finding["agent"] == self.agent_name:
            return {"error": "Cannot validate your own finding"}

        # Record validation
        validation = {
            "validator": self.agent_name,
            "status": validation_status,
            "reasoning": reasoning,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }

        finding["validations"].append(validation)

        # Save
        self._save_session(session_id, session)

        # Log event
        if CoordinationEventLogger:
            if not self.event_logger:
                self.event_logger = CoordinationEventLogger(session_id)
            if validation_status == "challenged":
                self.event_logger.log_finding_challenged(
                    challenger_agent=self.agent_name,
                    challenged_task_id=finding_id,
                    challenge_reasoning=reasoning
                )
            else:
                self.event_logger.log_finding_validated(
                    validator_agent=self.agent_name,
                    validated_task_id=finding_id,
                    validation_result={
                        "status": validation_status,
                        "confidence": confidence,
                        "reasoning": reasoning
                    }
                )

        print(f"[SessionManager] Validated finding {finding_id}: {validation_status}")

        return {"status": "validated", "validation": validation}

    def share_to_session(
        self,
        session_id: str,
        finding: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Legacy: Share a finding to the session.

        New code should use post_finding() instead.

        Args:
            session_id: Session ID
            finding: Finding dict with result, interpretation, etc.

        Returns:
            Success status
        """
        return self.post_finding(
            session_id=session_id,
            result=finding.get("result", ""),
            evidence=finding.get("data", {}),
            confidence=finding.get("confidence", 0.8),
            reasoning_trace=finding.get("interpretation", "")
        )
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current state of a session (finding-centric).

        Args:
            session_id: Session ID

        Returns:
            Session state with findings and consensus tracking
        """
        session = self._load_session(session_id)

        if not session:
            return None

        # Calculate findings-level progress
        findings = session.get("findings", [])
        total_findings = len(findings)

        # Count validations
        validated = 0
        challenged = 0
        disputed = 0
        under_review = 0

        for finding in findings:
            validations = finding.get("validations", [])
            if not validations:
                under_review += 1
            else:
                # Check if validated or challenged
                has_confirmed = any(v.get("status") == "confirmed" for v in validations)
                has_challenged = any(v.get("status") == "challenged" for v in validations)

                if has_confirmed and has_challenged:
                    disputed += 1
                elif has_challenged:
                    challenged += 1
                elif has_confirmed:
                    validated += 1
                else:
                    under_review += 1

        progress = {
            "total_findings": total_findings,
            "validated_findings": validated,
            "challenged_findings": challenged,
            "disputed_findings": disputed,
            "under_review_findings": under_review,
            "consensus_rate": (validated / total_findings * 100) if total_findings > 0 else 0
        }

        return {
            "session": session,
            "progress": progress,
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Backwards-compatible helper used by higher-level workflow managers.
        
        Returns the raw session dict or None if not found.
        """
        session = self._load_session(session_id)
        if session is not None:
            return session

        # Some higher-level workflows may decorate session IDs with prefixes
        # (e.g., "validate_<session_id>" for validation chains). Try to
        # recover by stripping a known prefix.
        prefix = "validate_"
        if session_id.startswith(prefix):
            return self._load_session(session_id[len(prefix) :])

        return None
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active collaborative sessions.

        Returns:
            List of session summaries (finding-centric)
        """
        sessions = []

        for session_file in self.sessions_dir.glob("scienceclaw-collab-*.json"):
            try:
                with open(session_file) as f:
                    session = json.load(f)

                if session.get("status") == "active":
                    # Calculate progress from findings
                    findings = session.get("findings", [])
                    total_findings = len(findings)

                    validated = sum(
                        1 for f in findings
                        if any(v.get("status") == "confirmed" for v in f.get("validations", []))
                    )

                    summary = {
                        "id": session["id"],
                        "topic": session["topic"],
                        "created_by": session["created_by"],
                        "participants": session["participants"],
                        "total_findings": total_findings,
                        "validated_findings": validated,
                        "consensus_rate": (validated / total_findings * 100) if total_findings > 0 else 0,
                        "investigation_type": session.get("investigation_type", "multi-agent"),
                        "created_at": session["created_at"]
                    }

                    sessions.append(summary)
            except Exception as e:
                print(f"Warning: Failed to load session {session_file}: {e}")

        return sessions
    
    def get_available_investigations(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get suggested investigations that haven't been claimed yet.

        Agents can optionally use these as structure, or work independently.

        Args:
            session_id: Session ID

        Returns:
            List of unclaimed investigations
        """
        session = self._load_session(session_id)

        if not session:
            return []

        # Return unclaimed investigations
        available = []
        for inv in session.get("suggested_investigations", []):
            inv_id = inv["id"]
            if inv_id not in session.get("claimed_investigations", {}):
                available.append(inv)

        return available

    def get_findings_needing_validation(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get findings that need validation/challenge.

        In hybrid model, agents can validate findings or work on investigations.

        Args:
            session_id: Session ID

        Returns:
            List of findings without validator yet
        """
        session = self._load_session(session_id)

        if not session:
            return []

        # Return findings that don't have many validations yet
        findings_needing_validation = []
        for finding in session.get("findings", []):
            validations = finding.get("validations", [])
            # Less than 2 validations means could use more
            if len(validations) < 2:
                findings_needing_validation.append(finding)

        return findings_needing_validation
    
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

        # Log completion (initialize logger if needed)
        if CoordinationEventLogger:
            if not self.event_logger:
                self.event_logger = CoordinationEventLogger(session_id)
            # Session completion is implicit in status change, but could log it
            # if needed for audit trails

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

    # ------------------------------------------------------------------
    # Internal helpers for keeping task graph in sync with task actions
    # ------------------------------------------------------------------

    def _update_graph_for_claim(self, session: Dict[str, Any], task_id: str) -> None:
        """
        When a task is claimed, mirror that in any graph node that
        references the task (by task_id or by matching id).
        """
        graph = session.get("graph")
        if not graph:
            return

        for node in graph:
            node_task_id = node.get("task_id")
            if node_task_id == task_id or node.get("id") == task_id:
                node["assigned_agent"] = self.agent_name
                # Only bump to in_progress if not already completed/blocked
                status = (node.get("status") or "pending").lower()
                if status in ("pending", "claimed"):
                    node["status"] = "in_progress"

    def _update_graph_for_completion(
        self,
        session: Dict[str, Any],
        task_id: str,
        completed_by: Optional[str] = None,
    ) -> None:
        """
        When a task is completed, mirror that in any graph node that
        references the task.
        """
        graph = session.get("graph")
        if not graph:
            return

        for node in graph:
            node_task_id = node.get("task_id")
            if node_task_id == task_id or node.get("id") == task_id:
                node["status"] = "completed"
                if completed_by:
                    node["assigned_agent"] = completed_by


# Test function
def test_session_manager():
    """Test the session manager with hybrid workflow (investigations + independent findings)."""

    # Agent 1 creates session with suggested investigations
    manager1 = SessionManager("BioAgent-7")

    suggested_invs = [
        {"id": "inv_1", "description": "Literature review: BACE1 proteolysis pathways", "tools": ["pubmed"]},
        {"id": "inv_2", "description": "Protein structure: BACE1 domain analysis", "tools": ["uniprot", "pdb"]},
        {"id": "inv_3", "description": "Drug screening: BACE1 inhibitors", "tools": ["pubchem", "tdc"]}
    ]

    session_id = manager1.create_collaborative_session(
        topic="BACE1 as drug target for Alzheimer's disease",
        description="Multi-agent investigation of BACE1 mechanisms",
        suggested_investigations=suggested_invs,
        investigation_type="multi-agent",
        max_participants=4
    )

    print(f"\nSession created: {session_id}")
    print(f"Suggested investigations: {len(suggested_invs)}")

    # Agent 1 claims first investigation and posts finding
    claim1 = manager1.claim_investigation(session_id, "inv_1")
    print(f"Agent1 claimed: {claim1['status']} - inv_1")

    finding1 = manager1.post_finding(
        session_id=session_id,
        result="BACE1 proteolysis is central to amyloid-beta processing",
        evidence={
            "tool_outputs": {
                "pubmed": {"papers": 12, "relevance": 0.92}
            },
            "sources": ["pmid:12345", "pmid:23456"]
        },
        confidence=0.85,
        reasoning_trace="Analyzed 12 papers on BACE1 proteolytic pathways"
    )
    print(f"Agent1 posted finding: {finding1['finding_id']}")

    # Agent 2 joins and claims a different investigation
    manager2 = SessionManager("CrazyChem")
    join_result = manager2.join_session(session_id)
    print(f"Agent2 joined: {join_result['status']}")

    claim2 = manager2.claim_investigation(session_id, "inv_3")
    print(f"Agent2 claimed: {claim2['status']} - inv_3")

    # Agent 2 posts a finding (from claimed investigation)
    finding2 = manager2.post_finding(
        session_id=session_id,
        result="Found 47 BACE1 inhibitors in clinical development",
        evidence={
            "tool_outputs": {
                "pubchem": {"compounds": 47, "bbb_predictions": "mixed"}
            },
            "sources": ["pubchem:123", "pubchem:456"]
        },
        confidence=0.80
    )
    print(f"Agent2 posted finding: {finding2['finding_id']}")

    # Agent 3 joins and works INDEPENDENTLY (doesn't claim investigation)
    manager3 = SessionManager("SkepticalBot")
    join_result = manager3.join_session(session_id)
    print(f"Agent3 joined: {join_result['status']}")

    # Agent 3 posts independent finding (no investigation claim)
    finding3 = manager3.post_finding(
        session_id=session_id,
        result="BACE1 knockout mice show compensatory enzyme activity",
        evidence={
            "tool_outputs": {
                "pubmed": {"papers": 8, "theme": "compensatory mechanisms"}
            }
        },
        confidence=0.75,
        reasoning_trace="Independent literature analysis on BACE1 knockouts"
    )
    print(f"Agent3 posted independent finding: {finding3['finding_id']}")

    # Agent 2 validates Agent 1's finding
    validation1 = manager2.validate_finding(
        session_id=session_id,
        finding_id=finding1["finding_id"],
        validation_status="confirmed",
        reasoning="Confirmed via drug development data; 47 BACE1 inhibitors target this pathway",
        confidence=0.82
    )
    print(f"Agent2 validated Agent1: {validation1['status']}")

    # Agent 3 challenges Agent 1's finding
    challenge1 = manager3.validate_finding(
        session_id=session_id,
        finding_id=finding1["finding_id"],
        validation_status="challenged",
        reasoning="Our finding shows compensatory mechanisms; BACE1 alone may not be sufficient",
        confidence=0.70
    )
    print(f"Agent3 challenged Agent1: {challenge1['status']}")

    # Get available investigations
    available = manager1.get_available_investigations(session_id)
    print(f"Investigations still available: {len(available)} (inv_2)")

    # Get findings needing validation
    unvalidated = manager1.get_findings_needing_validation(session_id)
    print(f"Findings needing validation: {len(unvalidated)}")

    # Get session state
    state = manager1.get_session_state(session_id)
    print(f"Session progress: {state['progress']['validated_findings']} validated, "
          f"{state['progress']['challenged_findings']} challenged, "
          f"{state['progress']['disputed_findings']} disputed, "
          f"{state['progress']['under_review_findings']} under review")

    # List all active sessions
    active_sessions = manager1.list_active_sessions()
    print(f"Active sessions: {len(active_sessions)}")

    print("\n✓ Hybrid session manager test complete")


if __name__ == "__main__":
    test_session_manager()
