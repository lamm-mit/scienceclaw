#!/usr/bin/env python3
"""
Transparency API - Query Evidence Chains & Session State

Enables high-level queries of coordination events for debugging and understanding
agent decisions. Makes the coordination system transparent and inspectable.

Features:
- Evidence chain reconstruction
- Session timeline views
- Agent activity tracking
- Consensus state queries
- Finding source tracking

Author: ScienceClaw Team
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

try:
    from event_logger import CoordinationEventLogger
except ImportError:
    CoordinationEventLogger = None


class TransparencyAPI:
    """
    High-level API for transparency into agent coordination.

    Provides queryable interfaces to understand:
    - Why findings were posted (evidence chain)
    - How validation decisions were made
    - What consensus emerged on findings
    - Timeline of session events
    - Agent decision traces
    """

    def __init__(self):
        """Initialize transparency API."""
        self.sessions_dir = Path.home() / ".infinite" / "workspace" / "sessions"
        print(f"[TransparencyAPI] Initialized")

    # =========================================================================
    # Evidence Chain Queries
    # =========================================================================

    def get_evidence_chain(self, session_id: str, finding_id: str) -> Dict[str, Any]:
        """
        Reconstruct complete evidence chain for a finding.

        Shows every step from problem → tools → reasoning → evidence → conclusion.

        Args:
            session_id: Session ID
            finding_id: Finding ID to trace

        Returns:
            Complete evidence chain
        """
        if not CoordinationEventLogger:
            return self._get_evidence_from_session_file(session_id, finding_id)

        try:
            logger = CoordinationEventLogger(session_id)
            chain = logger.get_evidence_chain(finding_id)
            return chain
        except Exception as e:
            return {"error": str(e)}

    def get_finding_validations(
        self,
        session_id: str,
        finding_id: str
    ) -> Dict[str, Any]:
        """
        Get all validations and challenges for a finding.

        Args:
            session_id: Session ID
            finding_id: Finding ID

        Returns:
            All validation records
        """
        session = self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        # Find the finding
        finding = None
        for f in session.get("findings", []):
            if f["id"] == finding_id:
                finding = f
                break

        if not finding:
            return {"error": "Finding not found"}

        validations = finding.get("validations", [])

        # Categorize validations
        confirmed = [v for v in validations if v.get("status") == "confirmed"]
        challenged = [v for v in validations if v.get("status") == "challenged"]
        partial = [v for v in validations if v.get("status") == "partial"]

        return {
            "finding_id": finding_id,
            "finding_agent": finding.get("agent"),
            "finding_result": finding.get("result"),
            "total_validations": len(validations),
            "confirmed": confirmed,
            "challenged": challenged,
            "partial": partial,
            "consensus_status": self._calculate_consensus_status(
                confirmed, challenged, partial
            )
        }

    def get_agent_activity(
        self,
        session_id: str,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Get all activities of an agent in a session.

        Args:
            session_id: Session ID
            agent_name: Agent name

        Returns:
            Agent's activities and contributions
        """
        session = self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        # Find agent's findings
        findings = [
            f for f in session.get("findings", [])
            if f.get("agent") == agent_name
        ]

        # Count validations
        validations = []
        for f in session.get("findings", []):
            agent_validations = [
                v for v in f.get("validations", [])
                if v.get("validator") == agent_name
            ]
            validations.extend(agent_validations)

        # Find claimed investigations
        claimed_investigations = [
            inv_id for inv_id, claimer in session.get("claimed_investigations", {}).items()
            if claimer == agent_name
        ]

        return {
            "agent": agent_name,
            "findings_posted": len(findings),
            "findings": findings,
            "validations_given": len(validations),
            "validation_breakdown": self._count_validations(validations),
            "investigations_claimed": claimed_investigations,
            "joined_at": session.get("metadata", {}).get(f"{agent_name}_joined_at")
        }

    # =========================================================================
    # Session State Queries
    # =========================================================================

    def get_session_consensus(self, session_id: str) -> Dict[str, Any]:
        """
        Get consensus metrics and breakdown for a session.

        Args:
            session_id: Session ID

        Returns:
            Consensus state with categories
        """
        session = self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        findings = session.get("findings", [])
        total = len(findings)

        # Categorize findings
        validated = []
        challenged = []
        disputed = []
        under_review = []

        for finding in findings:
            validations = finding.get("validations", [])
            confirmed = any(v.get("status") == "confirmed" for v in validations)
            challenge = any(v.get("status") == "challenged" for v in validations)

            if not validations:
                under_review.append(finding)
            elif confirmed and challenge:
                disputed.append(finding)
            elif challenge:
                challenged.append(finding)
            elif confirmed:
                validated.append(finding)
            else:
                under_review.append(finding)

        return {
            "session_id": session_id,
            "total_findings": total,
            "validated": {
                "count": len(validated),
                "findings": [f["id"] for f in validated]
            },
            "challenged": {
                "count": len(challenged),
                "findings": [f["id"] for f in challenged]
            },
            "disputed": {
                "count": len(disputed),
                "findings": [f["id"] for f in disputed],
                "note": "Both confirmations and challenges - healthy scientific debate"
            },
            "under_review": {
                "count": len(under_review),
                "findings": [f["id"] for f in under_review]
            },
            "consensus_rate": len(validated) / total if total > 0 else 0,
            "debate_rate": len(disputed) / total if total > 0 else 0
        }

    def get_session_timeline(self, session_id: str) -> Dict[str, Any]:
        """
        Get chronological timeline of session events.

        Args:
            session_id: Session ID

        Returns:
            Timeline with key events
        """
        session = self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        events = []

        # Session creation
        events.append({
            "timestamp": session.get("created_at"),
            "type": "session_created",
            "actor": session.get("created_by"),
            "description": f"Created session: {session.get('topic')}"
        })

        # Agent joins
        for agent_name in session.get("participants", []):
            if agent_name != session.get("created_by"):
                joined_at = session.get("metadata", {}).get(f"{agent_name}_joined_at")
                if joined_at:
                    events.append({
                        "timestamp": joined_at,
                        "type": "agent_joined",
                        "actor": agent_name,
                        "description": f"{agent_name} joined session"
                    })

        # Investigation claims
        for inv_id, claimer in session.get("claimed_investigations", {}).items():
            claimed_at = session.get("metadata", {}).get(f"investigation_{inv_id}_claimed_at")
            if claimed_at:
                events.append({
                    "timestamp": claimed_at,
                    "type": "investigation_claimed",
                    "actor": claimer,
                    "description": f"Claimed investigation: {inv_id}"
                })

        # Findings posted
        for finding in session.get("findings", []):
            events.append({
                "timestamp": finding.get("timestamp"),
                "type": "finding_posted",
                "actor": finding.get("agent"),
                "description": f"Posted finding: {finding.get('id')}",
                "finding_id": finding.get("id"),
                "result_preview": finding.get("result")[:80] + "..."
            })

        # Validations
        for finding in session.get("findings", []):
            for validation in finding.get("validations", []):
                events.append({
                    "timestamp": validation.get("timestamp"),
                    "type": "validation",
                    "actor": validation.get("validator"),
                    "description": f"{validation.get('status')} finding {finding.get('id')}",
                    "finding_id": finding.get("id"),
                    "status": validation.get("status")
                })

        # Sort by timestamp
        events.sort(key=lambda e: e.get("timestamp", ""))

        return {
            "session_id": session_id,
            "event_count": len(events),
            "events": events
        }

    # =========================================================================
    # Investigation Tracking
    # =========================================================================

    def get_investigation_status(
        self,
        session_id: str,
        investigation_id: str
    ) -> Dict[str, Any]:
        """
        Get status of a specific investigation.

        Args:
            session_id: Session ID
            investigation_id: Investigation ID

        Returns:
            Investigation details and status
        """
        session = self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        # Find investigation in suggested list
        investigation = None
        for inv in session.get("suggested_investigations", []):
            if inv["id"] == investigation_id:
                investigation = inv
                break

        if not investigation:
            return {"error": "Investigation not found"}

        # Find who claimed it
        claimer = session.get("claimed_investigations", {}).get(investigation_id)

        # Find findings from this investigation
        related_findings = []
        for finding in session.get("findings", []):
            # Heuristic: if agent claimed the investigation, findings posted by them are related
            if claimer and finding.get("agent") == claimer:
                related_findings.append(finding)

        return {
            "investigation_id": investigation_id,
            "description": investigation.get("description"),
            "suggested_tools": investigation.get("tools", []),
            "claimed_by": claimer,
            "claimed_at": session.get("metadata", {}).get(
                f"investigation_{investigation_id}_claimed_at"
            ),
            "related_findings": len(related_findings),
            "findings": [f["id"] for f in related_findings],
            "status": "completed" if related_findings else "unclaimed" if not claimer else "in_progress"
        }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session from file."""
        session_file = self.sessions_dir / f"{session_id}.json"
        if not session_file.exists():
            return None
        try:
            with open(session_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session: {e}")
            return None

    def _get_evidence_from_session_file(
        self,
        session_id: str,
        finding_id: str
    ) -> Dict[str, Any]:
        """Get evidence chain directly from session file."""
        session = self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        # Find finding
        finding = None
        for f in session.get("findings", []):
            if f["id"] == finding_id:
                finding = f
                break

        if not finding:
            return {"error": "Finding not found"}

        # Build evidence trail
        evidence_trail = []

        # Tool outputs
        evidence = finding.get("evidence", {})
        for tool, result in evidence.get("tool_outputs", {}).items():
            evidence_trail.append({
                "type": "tool_output",
                "tool": tool,
                "result": result
            })

        # Reasoning trace
        reasoning = evidence.get("reasoning_trace", "")
        if reasoning:
            for step in reasoning.split('\n'):
                if step.strip():
                    evidence_trail.append({
                        "type": "reasoning",
                        "step": step.strip()
                    })

        return {
            "finding_id": finding_id,
            "agent": finding.get("agent"),
            "conclusion": finding.get("result"),
            "confidence": finding.get("confidence"),
            "timestamp": finding.get("timestamp"),
            "evidence_trail": evidence_trail,
            "sources": evidence.get("sources", []),
            "validations": finding.get("validations", [])
        }

    def _calculate_consensus_status(
        self,
        confirmed: List[Dict],
        challenged: List[Dict],
        partial: List[Dict]
    ) -> str:
        """Determine consensus status from validations."""
        if not confirmed and not challenged and not partial:
            return "unvalidated"
        if confirmed and not challenged:
            return "validated"
        if challenged and not confirmed:
            return "disputed"
        if confirmed and challenged:
            return "debated"
        return "partial_validation"

    def _count_validations(self, validations: List[Dict]) -> Dict[str, int]:
        """Count validations by status."""
        return {
            "confirmed": len([v for v in validations if v.get("status") == "confirmed"]),
            "challenged": len([v for v in validations if v.get("status") == "challenged"]),
            "partial": len([v for v in validations if v.get("status") == "partial"])
        }


# Test function
def test_transparency_api():
    """Test the transparency API."""

    api = TransparencyAPI()

    print("\n=== Phase 3 Test: Transparency API ===\n")

    # Create test data via SessionManager
    from session_manager import SessionManager

    manager = SessionManager("TestAgent")

    # Create session
    session_id = manager.create_collaborative_session(
        topic="Test investigation",
        suggested_investigations=[
            {"id": "inv_1", "description": "Test investigation", "tools": ["pubmed"]}
        ]
    )

    # Post findings
    f1 = manager.post_finding(
        session_id,
        result="Test finding 1",
        evidence={"tool_outputs": {"pubmed": {"papers": 5}}},
        confidence=0.8
    )

    manager2 = SessionManager("Agent2")
    manager2.join_session(session_id)

    f2 = manager2.post_finding(
        session_id,
        result="Test finding 2 (independent)",
        confidence=0.7
    )

    # Validate
    manager2.validate_finding(f1["finding_id"], f1["finding_id"], "confirmed", "Confirmed", 0.8)
    manager2.validate_finding(f2["finding_id"], f2["finding_id"], "challenged", "Challenged", 0.7)

    # Test transparency queries
    print("[TEST] Session Consensus\n")
    consensus = api.get_session_consensus(session_id)
    print(f"Total findings: {consensus['total_findings']}")
    print(f"Validated: {consensus['validated']['count']}")
    print(f"Disputed: {consensus['disputed']['count']}")
    print(f"Consensus rate: {consensus['consensus_rate']:.1%}")

    print("\n[TEST] Agent Activity\n")
    activity = api.get_agent_activity(session_id, "TestAgent")
    print(f"Agent: {activity['agent']}")
    print(f"Findings posted: {activity['findings_posted']}")
    print(f"Validations given: {activity['validations_given']}")

    print("\n[TEST] Session Timeline\n")
    timeline = api.get_session_timeline(session_id)
    print(f"Total events: {timeline['event_count']}")
    for event in timeline['events'][:5]:
        print(f"  {event['timestamp']}: {event['type']} by {event['actor']}")

    print("\n✓ Transparency API test complete")


if __name__ == "__main__":
    test_transparency_api()
