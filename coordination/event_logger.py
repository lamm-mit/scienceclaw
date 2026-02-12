#!/usr/bin/env python3
"""
Coordination Event Logger - Transparency Layer for Multi-Agent Coordination

Logs structured coordination events to JSONL, making all agent actions visible
with full traceability. Follows the proven AgentJournal pattern.

Event log location: ~/.scienceclaw/coordination/{session_id}/events.jsonl

Event types:
- SessionCreated: Session initialized with topic and strategy
- AgentJoinedSession: Agent discovered and joined session
- AgentClaimedTask: Agent claimed a task with role assignment
- AgentStartedTask: Agent began task execution
- AgentCompletedTask: Agent completed task with evidence chain
- AgentPostedFinding: Agent shared finding to session
- AgentValidatedFinding: Agent validated another's finding with evidence
- AgentChallengedFinding: Agent challenged finding with alternative hypothesis
- RoleAssigned: Role assigned to agent with reasoning
- ConsensusReached: Consensus emerged on findings
- DisagreementRecorded: Agents disagreed on finding

Author: ScienceClaw Team
"""

import json
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, Optional, List


class CoordinationEventLogger:
    """
    Logs structured coordination events to JSONL.

    Each session has its own event log at:
    ~/.scienceclaw/coordination/{session_id}/events.jsonl

    Events are append-only and include full reasoning/evidence chains.
    """

    def __init__(self, session_id: str):
        """
        Initialize event logger for a session.

        Args:
            session_id: Session ID (creates dedicated directory)
        """
        self.session_id = session_id

        # Create coordination directory structure
        self.base_dir = Path.home() / ".scienceclaw" / "coordination"
        self.session_dir = self.base_dir / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Events log file (JSONL format)
        self.events_path = self.session_dir / "events.jsonl"
        if not self.events_path.exists():
            self.events_path.touch()

        print(f"[CoordinationEventLogger] Initialized for session: {session_id}")
        print(f"[CoordinationEventLogger] Events file: {self.events_path}")

    # =========================================================================
    # Public API: Log different event types
    # =========================================================================

    def log_session_created(
        self,
        topic: str,
        created_by: str,
        strategy: Optional[Dict[str, Any]] = None,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Log SessionCreated event.

        Args:
            topic: Research topic
            created_by: Agent that created the session
            strategy: Investigation strategy (from AutonomousOrchestrator._analyze_topic())
            description: Session description

        Returns:
            The logged event
        """
        return self._log_event("SessionCreated", {
            "session_id": self.session_id,
            "topic": topic,
            "description": description,
            "created_by": created_by,
            "strategy": strategy or {}
        })

    def log_agent_joined(
        self,
        agent_name: str,
        reasoning: str,
        skill_match: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log AgentJoinedSession event.

        Args:
            agent_name: Agent that joined
            reasoning: Why agent joined (e.g., "Skill match: pubmed, uniprot")
            skill_match: Skills that matched required skills

        Returns:
            The logged event
        """
        return self._log_event("AgentJoinedSession", {
            "agent_name": agent_name,
            "reasoning": reasoning,
            "skill_match": skill_match or {}
        })

    def log_task_claimed(
        self,
        task_id: str,
        agent_name: str,
        role: str,
        reasoning: str
    ) -> Dict[str, Any]:
        """
        Log AgentClaimedTask event.

        Args:
            task_id: Task ID claimed
            agent_name: Agent claiming the task
            role: Role assigned (investigator, validator, critic, etc.)
            reasoning: Why agent claimed this task

        Returns:
            The logged event
        """
        return self._log_event("AgentClaimedTask", {
            "task_id": task_id,
            "agent_name": agent_name,
            "role": role,
            "reasoning": reasoning
        })

    def log_task_started(
        self,
        task_id: str,
        agent_name: str,
        plan: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log AgentStartedTask event.

        Args:
            task_id: Task ID being started
            agent_name: Agent starting the task
            plan: Optional execution plan (tools, parameters)

        Returns:
            The logged event
        """
        return self._log_event("AgentStartedTask", {
            "task_id": task_id,
            "agent_name": agent_name,
            "plan": plan or {}
        })

    def log_task_completed(
        self,
        task_id: str,
        agent_name: str,
        result: Any,
        evidence: Optional[Dict[str, Any]] = None,
        reasoning_trace: str = ""
    ) -> Dict[str, Any]:
        """
        Log AgentCompletedTask event with full evidence chain.

        Args:
            task_id: Task ID completed
            agent_name: Agent that completed the task
            result: Task result/conclusion
            evidence: Evidence chain with:
                - tool_outputs: {tool_name: result}
                - tool_params: Parameters used
                - reasoning_trace: Step-by-step reasoning
                - confidence: Confidence level (0.0-1.0)
                - sources: Data sources (PMIDs, UniProt IDs, etc.)
            reasoning_trace: Full reasoning trace (can be multiline)

        Returns:
            The logged event
        """
        if evidence is None:
            evidence = {}

        return self._log_event("AgentCompletedTask", {
            "task_id": task_id,
            "agent_name": agent_name,
            "result": result,
            "evidence": {
                "tool_outputs": evidence.get("tool_outputs", {}),
                "tool_params": evidence.get("tool_params", {}),
                "reasoning_trace": evidence.get("reasoning_trace", reasoning_trace),
                "confidence": evidence.get("confidence", 0.8),
                "sources": evidence.get("sources", [])
            },
            "relationships": {
                "validates": None,  # task_id if validating another finding
                "challenged_by": None,
                "consensus_with": []
            }
        })

    def log_finding_posted(
        self,
        agent_name: str,
        task_id: str,
        finding_summary: str,
        confidence: float = 0.8
    ) -> Dict[str, Any]:
        """
        Log AgentPostedFinding event.

        Args:
            agent_name: Agent posting the finding
            task_id: Associated task
            finding_summary: Summary of the finding
            confidence: Confidence in the finding (0.0-1.0)

        Returns:
            The logged event
        """
        return self._log_event("AgentPostedFinding", {
            "agent_name": agent_name,
            "task_id": task_id,
            "finding_summary": finding_summary,
            "confidence": confidence
        })

    def log_finding_validated(
        self,
        validator_agent: str,
        validated_task_id: str,
        validation_result: Dict[str, Any],
        consensus_with: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Log AgentValidatedFinding event.

        Args:
            validator_agent: Agent performing validation
            validated_task_id: Task/finding being validated
            validation_result: Validation result with:
                - status: "confirmed", "partial", "inconclusive"
                - confidence: Confidence level (0.0-1.0)
                - method: Validation method used (e.g., "independent PubMed search")
                - reasoning: Explanation of validation
            consensus_with: Other agents who reached same conclusion

        Returns:
            The logged event
        """
        return self._log_event("AgentValidatedFinding", {
            "validator_agent": validator_agent,
            "validated_task_id": validated_task_id,
            "validation_result": validation_result,
            "consensus_with": consensus_with or []
        })

    def log_finding_challenged(
        self,
        challenger_agent: str,
        challenged_task_id: str,
        challenge_reasoning: str,
        alternative_hypothesis: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log AgentChallengedFinding event.

        Args:
            challenger_agent: Agent challenging the finding
            challenged_task_id: Task/finding being challenged
            challenge_reasoning: Why the finding is being challenged
            alternative_hypothesis: Alternative explanation for the data

        Returns:
            The logged event
        """
        return self._log_event("AgentChallengedFinding", {
            "challenger_agent": challenger_agent,
            "challenged_task_id": challenged_task_id,
            "challenge_reasoning": challenge_reasoning,
            "alternative_hypothesis": alternative_hypothesis
        })

    def log_role_assigned(
        self,
        agent_name: str,
        role: str,
        reasoning: str,
        responsibilities: str = ""
    ) -> Dict[str, Any]:
        """
        Log RoleAssigned event.

        Args:
            agent_name: Agent being assigned a role
            role: Role name (investigator, validator, critic, etc.)
            reasoning: Why this role was assigned
            responsibilities: Description of role responsibilities

        Returns:
            The logged event
        """
        return self._log_event("RoleAssigned", {
            "agent_name": agent_name,
            "role": role,
            "reasoning": reasoning,
            "responsibilities": responsibilities
        })

    def log_consensus_reached(
        self,
        task_id: str,
        consensus_statement: str,
        validators: List[str],
        confidence: float = 0.8
    ) -> Dict[str, Any]:
        """
        Log ConsensusReached event.

        Args:
            task_id: Task/finding reaching consensus
            consensus_statement: What the consensus is about
            validators: List of agents who validated
            confidence: Overall confidence in consensus

        Returns:
            The logged event
        """
        return self._log_event("ConsensusReached", {
            "task_id": task_id,
            "consensus_statement": consensus_statement,
            "validators": validators,
            "confidence": confidence
        })

    def log_disagreement_recorded(
        self,
        task_id: str,
        agent_names: List[str],
        disagreement_type: str,
        description: str
    ) -> Dict[str, Any]:
        """
        Log DisagreementRecorded event.

        Args:
            task_id: Task/finding with disagreement
            agent_names: Agents who disagree
            disagreement_type: Type of disagreement (e.g., "methodology", "interpretation")
            description: Description of the disagreement

        Returns:
            The logged event
        """
        return self._log_event("DisagreementRecorded", {
            "task_id": task_id,
            "agent_names": agent_names,
            "disagreement_type": disagreement_type,
            "description": description
        })

    # =========================================================================
    # Query API: Search and filter events
    # =========================================================================

    def query_events(
        self,
        event_types: Optional[List[str]] = None,
        agent_filter: Optional[str] = None,
        task_filter: Optional[str] = None,
        time_range: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Query events from the log.

        Args:
            event_types: Filter by event types (e.g., ["AgentCompletedTask"])
            agent_filter: Filter by agent name
            task_filter: Filter by task ID
            time_range: Filter by time (start_time, end_time) as ISO strings

        Returns:
            List of matching events
        """
        events = []

        # Read JSONL file
        try:
            with open(self.events_path, 'r') as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
        except Exception as e:
            print(f"[CoordinationEventLogger] Error reading events: {e}")
            return []

        # Filter by event type
        if event_types:
            events = [e for e in events if e.get("event_type") in event_types]

        # Filter by agent
        if agent_filter:
            events = [
                e for e in events
                if (e.get("agent_name") == agent_filter or
                    e.get("validator_agent") == agent_filter or
                    e.get("challenger_agent") == agent_filter)
            ]

        # Filter by task
        if task_filter:
            events = [
                e for e in events
                if (e.get("task_id") == task_filter or
                    e.get("validated_task_id") == task_filter or
                    e.get("challenged_task_id") == task_filter)
            ]

        # Filter by time range
        if time_range:
            start_time, end_time = time_range
            events = [
                e for e in events
                if (start_time <= e.get("timestamp", "") <= end_time)
            ]

        return events

    def get_evidence_chain(self, task_id: str) -> Dict[str, Any]:
        """
        Reconstruct evidence chain for a task/finding.

        Returns:
            {
                "task_id": str,
                "conclusion": str,
                "evidence_trail": [
                    {"type": "tool_output", "tool": str, "result": any},
                    {"type": "reasoning", "step": str, "confidence": float},
                    {"type": "validation", "agent": str, "result": str}
                ],
                "validations": [{"agent": str, "status": str, "confidence": float}],
                "challenges": [{"agent": str, "reasoning": str, "alternative": str}]
            }
        """
        # Find the completion event for this task
        completion_events = self.query_events(
            event_types=["AgentCompletedTask"],
            task_filter=task_id
        )

        if not completion_events:
            return {"error": "Task not found"}

        # Use the first (and typically only) completion event
        completion = completion_events[0]

        evidence_trail = []

        # Add tool outputs
        evidence = completion.get("evidence", {})
        for tool, result in evidence.get("tool_outputs", {}).items():
            evidence_trail.append({
                "type": "tool_output",
                "tool": tool,
                "result": result
            })

        # Add reasoning trace (split by newlines)
        reasoning = evidence.get("reasoning_trace", "")
        if reasoning:
            for step in reasoning.split('\n'):
                if step.strip():
                    evidence_trail.append({
                        "type": "reasoning",
                        "step": step.strip(),
                        "confidence": evidence.get("confidence", 0.8)
                    })

        # Find validations
        validation_events = self.query_events(
            event_types=["AgentValidatedFinding"],
            task_filter=task_id
        )
        validations = [
            {
                "agent": e.get("validator_agent"),
                "status": e.get("validation_result", {}).get("status"),
                "confidence": e.get("validation_result", {}).get("confidence"),
                "method": e.get("validation_result", {}).get("method")
            }
            for e in validation_events
        ]

        # Find challenges
        challenge_events = self.query_events(
            event_types=["AgentChallengedFinding"],
            task_filter=task_id
        )
        challenges = [
            {
                "agent": e.get("challenger_agent"),
                "reasoning": e.get("challenge_reasoning"),
                "alternative": e.get("alternative_hypothesis")
            }
            for e in challenge_events
        ]

        return {
            "task_id": task_id,
            "conclusion": completion.get("result"),
            "agent": completion.get("agent_name"),
            "timestamp": completion.get("timestamp"),
            "evidence_trail": evidence_trail,
            "validations": validations,
            "challenges": challenges
        }

    def get_consensus_state(self) -> Dict[str, Any]:
        """
        Get consensus metrics for entire session.

        Returns:
            {
                "total_findings": int,
                "validated": int,
                "challenged": int,
                "under_review": int,
                "disputed": int,
                "consensus_rate": float
            }
        """
        completion_events = self.query_events(event_types=["AgentCompletedTask"])
        validation_events = self.query_events(event_types=["AgentValidatedFinding"])
        challenge_events = self.query_events(event_types=["AgentChallengedFinding"])

        total_findings = len(completion_events)

        # Count validated findings (2+ validations with high confidence)
        task_validations = {}
        for v in validation_events:
            task_id = v.get("validated_task_id")
            if task_id not in task_validations:
                task_validations[task_id] = []
            task_validations[task_id].append(v)

        validated = sum(
            1 for task_id, validations in task_validations.items()
            if len(validations) >= 2 or any(
                v.get("validation_result", {}).get("confidence", 0) >= 0.8
                for v in validations
            )
        )

        # Count challenged findings
        challenged_task_ids = set(
            e.get("challenged_task_id") for e in challenge_events
        )
        challenged = len(challenged_task_ids)

        disputed = sum(
            1 for task_id in challenged_task_ids
            if task_id in task_validations
        )

        under_review = total_findings - validated - (challenged - disputed)

        return {
            "total_findings": total_findings,
            "validated": validated,
            "challenged": challenged,
            "under_review": max(0, under_review),
            "disputed": disputed,
            "consensus_rate": validated / total_findings if total_findings > 0 else 0
        }

    # =========================================================================
    # Internal: Write events to JSONL
    # =========================================================================

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal: Write event to JSONL file.

        Args:
            event_type: Type of event
            data: Event data

        Returns:
            The logged event (with timestamp and ID)
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_id": f"evt_{uuid4().hex[:8]}",
            "event_type": event_type,
            **data
        }

        try:
            with open(self.events_path, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            print(f"[CoordinationEventLogger] Error logging event: {e}")

        return event


# Test function
def test_event_logger():
    """Test the event logger with sample events."""

    logger = CoordinationEventLogger("scienceclaw-collab-test")

    # Log session creation
    print("\n[TEST] Logging session creation...")
    logger.log_session_created(
        topic="Alzheimer's disease drug targets",
        created_by="BioAgent-7",
        strategy={"investigation_type": "multi-tool", "phases": 3}
    )

    # Log agent joining
    print("[TEST] Logging agent join...")
    logger.log_agent_joined(
        agent_name="CrazyChem",
        reasoning="Skills match: uniprot, pubchem, tdc",
        skill_match={"uniprot": True, "pubchem": True, "tdc": True}
    )

    # Log task claim
    print("[TEST] Logging task claim...")
    logger.log_task_claimed(
        task_id="task_1",
        agent_name="BioAgent-7",
        role="investigator",
        reasoning="Domain expert in neurodegenerative disease"
    )

    # Log task completion with evidence
    print("[TEST] Logging task completion...")
    logger.log_task_completed(
        task_id="task_1",
        agent_name="BioAgent-7",
        result="BACE1 is central to amyloid-beta processing",
        evidence={
            "tool_outputs": {
                "pubmed": {"papers": 12, "relevance": 0.92},
                "uniprot": {"bace1_id": "P56817"}
            },
            "reasoning_trace": "Step 1: Found 12 papers on BACE1\nStep 2: Confirmed BACE1 domain structure\nStep 3: Identified regulatory mechanisms",
            "confidence": 0.85,
            "sources": ["pmid:12345", "pmid:23456", "uniprot:P56817"]
        }
    )

    # Log validation
    print("[TEST] Logging validation...")
    logger.log_finding_validated(
        validator_agent="CrazyChem",
        validated_task_id="task_1",
        validation_result={
            "status": "confirmed",
            "confidence": 0.80,
            "method": "independent PubChem search for BACE1 inhibitors",
            "reasoning": "Found 45 BACE1 inhibitors in development; mechanism matches hypothesis"
        }
    )

    # Log challenge
    print("[TEST] Logging challenge...")
    logger.log_finding_challenged(
        challenger_agent="SkepticalBot",
        challenged_task_id="task_1",
        challenge_reasoning="BACE1 knockouts don't eliminate amyloid pathology in mice",
        alternative_hypothesis="Multiple proteases contribute; BACE1 alone insufficient"
    )

    # Query events
    print("\n[TEST] Querying all events...")
    all_events = logger.query_events()
    print(f"Total events logged: {len(all_events)}")

    # Get evidence chain
    print("\n[TEST] Getting evidence chain for task_1...")
    chain = logger.get_evidence_chain("task_1")
    print(f"Evidence chain: {json.dumps(chain, indent=2)}")

    # Get consensus state
    print("\n[TEST] Getting consensus state...")
    consensus = logger.get_consensus_state()
    print(f"Consensus: {json.dumps(consensus, indent=2)}")

    print("\n✓ Event logger test complete")


if __name__ == "__main__":
    test_event_logger()
