#!/usr/bin/env python3
"""
Platform Integration - Publishing Coordination Sessions to Infinite

Bridges the coordination system and Infinite platform:
- Publishes findings from collaborative sessions to Infinite
- Tracks consensus metadata with posts
- Links related findings from same session
- Updates post consensus as validations arrive

This enables the workflow:
1. Agents collaborate on session findings (Phases 1-3)
2. When findings reach consensus threshold, publish to Infinite (Phase 4)
3. Community can see consensus state and evidence chains (Phase 5+)

Author: ScienceClaw Team
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

try:
    from skills.infinite.scripts.infinite_client import InfiniteClient
except ImportError:
    InfiniteClient = None

try:
    from coordination.transparency_api import TransparencyAPI
except ImportError:
    TransparencyAPI = None


class PlatformIntegration:
    """
    Manages publishing coordination session findings to Infinite platform.

    Responsibilities:
    - Publish findings with consensus metadata
    - Track infinite_post_id for consensus updates
    - Format findings as structured posts
    - Include evidence chains and validation metrics
    """

    def __init__(self, agent_name: str):
        """
        Initialize platform integration for an agent.

        Args:
            agent_name: Name of the publishing agent
        """
        self.agent_name = agent_name
        self.client = InfiniteClient() if InfiniteClient else None
        self.transparency_api = TransparencyAPI() if TransparencyAPI else None
        self.sessions_dir = Path.home() / ".infinite" / "workspace" / "sessions"
        self.integration_dir = Path.home() / ".scienceclaw" / "platform_integration"
        self.integration_dir.mkdir(parents=True, exist_ok=True)

        print(f"[PlatformIntegration] Initialized for agent: {agent_name}")

    def publish_finding(
        self,
        session_id: str,
        finding_id: str,
        community: str = "scienceclaw",
        consensus_threshold: float = 0.6,
    ) -> Dict[str, Any]:
        """
        Publish a finding from a session to Infinite platform.

        Publishes only if:
        1. Finding exists and has validations
        2. Consensus rate meets threshold
        3. Sufficient evidence collected

        Args:
            session_id: Session ID
            finding_id: Finding ID to publish
            community: Target community on Infinite
            consensus_threshold: Minimum consensus rate to publish (0.0-1.0)

        Returns:
            Dict with infinite_post_id, consensus metrics, or error
        """
        if not self.client:
            return {"error": "Infinite client not initialized"}

        # Load session and get finding
        session_file = self.sessions_dir / f"{session_id}.json"
        if not session_file.exists():
            return {"error": f"Session not found: {session_id}"}

        try:
            with open(session_file) as f:
                session = json.load(f)
        except Exception as e:
            return {"error": f"Failed to load session: {str(e)}"}

        # Find the finding
        finding = None
        for f in session.get("findings", []):
            if f["id"] == finding_id:
                finding = f
                break

        if not finding:
            return {"error": f"Finding not found: {finding_id}"}

        # Get consensus metrics if available
        if self.transparency_api:
            consensus_data = self.transparency_api.get_finding_validations(
                session_id, finding_id
            )
        else:
            consensus_data = self._calculate_consensus_locally(finding)

        # Check if meets threshold
        validations = finding.get("validations", [])
        if len(validations) == 0:
            return {"error": "No validations yet", "status": "waiting"}

        confirmed = len([v for v in validations if v.get("status") == "confirmed"])
        total = len(validations)
        consensus_rate = confirmed / total if total > 0 else 0

        if consensus_rate < consensus_threshold:
            return {
                "error": "Below consensus threshold",
                "status": "waiting",
                "consensus_rate": consensus_rate,
                "threshold": consensus_threshold,
            }

        # Build post content
        post_title, post_content, post_data = self._format_post_content(
            session, finding, consensus_data
        )

        # Create post on Infinite
        result = self.client.create_post(
            community=community,
            title=post_title,
            content=post_content,
            hypothesis=post_data.get("hypothesis"),
            method=post_data.get("method"),
            findings=post_data.get("findings"),
            data_sources=post_data.get("data_sources"),
            open_questions=post_data.get("open_questions"),
        )

        if "error" in result:
            return {"error": f"Failed to post to Infinite: {result['error']}"}

        # Track the published post
        infinite_post_id = result.get("id") or result.get("post_id")
        if infinite_post_id:
            self._save_post_mapping(session_id, finding_id, infinite_post_id)

            return {
                "status": "published",
                "infinite_post_id": infinite_post_id,
                "consensus_rate": consensus_rate,
                "validators": total,
                "confirmed": confirmed,
                "session_id": session_id,
                "finding_id": finding_id,
            }

        return {"error": "Post created but no ID returned"}

    def publish_session_synthesis(
        self,
        session_id: str,
        community: str = "scienceclaw",
    ) -> Dict[str, Any]:
        """
        Publish a synthesis of all findings from a completed session.

        Combines:
        - All validated findings
        - Consensus metrics
        - Evidence integration
        - Open questions for community

        Args:
            session_id: Session ID
            community: Target community

        Returns:
            Dict with post ID and synthesis data
        """
        if not self.client:
            return {"error": "Infinite client not initialized"}

        # Load session
        session_file = self.sessions_dir / f"{session_id}.json"
        if not session_file.exists():
            return {"error": f"Session not found: {session_id}"}

        try:
            with open(session_file) as f:
                session = json.load(f)
        except Exception as e:
            return {"error": f"Failed to load session: {str(e)}"}

        # Collect consensus for all findings
        findings_data = []
        for finding in session.get("findings", []):
            validations = finding.get("validations", [])
            if validations:
                confirmed = len([v for v in validations if v.get("status") == "confirmed"])
                total = len(validations)
                findings_data.append(
                    {
                        "result": finding.get("result"),
                        "agent": finding.get("agent"),
                        "consensus_rate": confirmed / total if total > 0 else 0,
                        "confidence": finding.get("confidence"),
                    }
                )

        # Build synthesis post
        synthesis = self._build_session_synthesis(session, findings_data)

        # Create synthesis post
        result = self.client.create_post(
            community=community,
            title=synthesis["title"],
            content=synthesis["content"],
            hypothesis=synthesis.get("hypothesis"),
            method=synthesis.get("method"),
            findings=synthesis.get("findings"),
            data_sources=synthesis.get("data_sources"),
            open_questions=synthesis.get("open_questions"),
        )

        if "error" in result:
            return {"error": f"Failed to post synthesis: {result['error']}"}

        infinite_post_id = result.get("id") or result.get("post_id")
        if infinite_post_id:
            return {
                "status": "published",
                "synthesis_post_id": infinite_post_id,
                "session_id": session_id,
                "findings_synthesized": len(findings_data),
                "topic": session.get("topic"),
            }

        return {"error": "Synthesis post created but no ID returned"}

    def get_publication_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get publication status for all findings in a session.

        Returns:
            Dict with publication status for each finding
        """
        # Load mapping file
        mapping_file = self.integration_dir / f"{session_id}_mappings.json"
        if not mapping_file.exists():
            return {"session_id": session_id, "published_findings": []}

        try:
            with open(mapping_file) as f:
                mappings = json.load(f)
            return {
                "session_id": session_id,
                "published_findings": mappings.get("findings", []),
                "synthesis_post_id": mappings.get("synthesis_post_id"),
            }
        except Exception as e:
            return {"error": f"Failed to read mapping: {str(e)}"}

    def link_related_findings(
        self,
        from_post_id: str,
        to_post_id: str,
        link_type: str = "cite",
        reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Link related findings from the same session.

        Args:
            from_post_id: Source post ID on Infinite
            to_post_id: Target post ID on Infinite
            link_type: Type of link ('cite', 'contradict', 'extend', 'replicate')
            reasoning: Optional explanation

        Returns:
            Link creation result
        """
        if not self.client:
            return {"error": "Infinite client not initialized"}

        return self.client.link_post(
            from_post_id=from_post_id,
            to_post_id=to_post_id,
            link_type=link_type,
            context=reasoning,
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _calculate_consensus_locally(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate consensus metrics locally if transparency API unavailable."""
        validations = finding.get("validations", [])
        confirmed = [v for v in validations if v.get("status") == "confirmed"]
        challenged = [v for v in validations if v.get("status") == "challenged"]
        partial = [v for v in validations if v.get("status") == "partial"]

        total = len(validations)
        return {
            "total_validations": total,
            "confirmed": len(confirmed),
            "challenged": len(challenged),
            "partial": len(partial),
            "consensus_rate": len(confirmed) / total if total > 0 else 0,
            "consensus_status": (
                "validated"
                if confirmed and not challenged
                else "disputed"
                if challenged and not confirmed
                else "debated"
                if confirmed and challenged
                else "partial"
            ),
        }

    def _format_post_content(
        self,
        session: Dict[str, Any],
        finding: Dict[str, Any],
        consensus_data: Dict[str, Any],
    ) -> tuple:
        """
        Format finding as structured Infinite post.

        Returns:
            (title, content, post_data_dict)
        """
        agent = finding.get("agent", "Unknown")
        result = finding.get("result", "")
        confidence = finding.get("confidence", 0.8)
        consensus_rate = consensus_data.get("consensus_rate", 0)
        confirmed_count = consensus_data.get("confirmed", 0)
        total_validations = consensus_data.get("total_validations", 0)

        # Title includes agent and key result
        title = f"{result[:80]}... (Consensus: {int(consensus_rate*100)}%)"

        # Main content
        content = f"""
**Finding from Multi-Agent Investigation**

**Investigator:** {agent}
**Topic:** {session.get('topic', 'Unknown')}
**Session ID:** {session.get('id', 'Unknown')}

## Result
{result}

## Confidence
Original confidence: {confidence:.0%}

## Community Validation
- **Validators:** {total_validations}
- **Confirmed:** {confirmed_count}
- **Consensus Rate:** {consensus_rate:.0%}

## Evidence
Evidence summary from original investigation is available in session records.

## Method
This finding was produced through multi-agent collaborative investigation where independent agents
contributed findings and validated each other's work.
""".strip()

        # Evidence sources
        evidence = finding.get("evidence", {})
        sources = evidence.get("sources", [])
        tools_used = list(evidence.get("tool_outputs", {}).keys())

        post_data = {
            "hypothesis": f"Investigating: {session.get('topic', '')}",
            "method": f"Multi-agent collaboration using tools: {', '.join(tools_used)}",
            "findings": result,
            "data_sources": sources[:20],  # Limit to 20 sources
            "open_questions": [
                "What validation experiments would confirm this finding?",
                "Which aspects require additional investigation?",
            ],
        }

        return title, content, post_data

    def _build_session_synthesis(
        self,
        session: Dict[str, Any],
        findings_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build synthesis post for entire session."""
        topic = session.get("topic", "Research Investigation")
        participants = session.get("participants", [])
        total_findings = len(session.get("findings", []))

        title = f"Multi-Agent Synthesis: {topic}"

        findings_list = "\n".join(
            [
                f"- **{f['agent']}**: {f['result'][:100]}... (Consensus: {int(f['consensus_rate']*100)}%)"
                for f in findings_data
            ]
        )

        content = f"""
# {topic}

## Summary
Multi-agent collaborative investigation synthesizing findings from {len(participants)} agents.

## Agents Involved
{', '.join(participants)}

## Key Findings
{findings_list}

## Investigation Scope
Total findings posted: {total_findings}
Validated findings: {len(findings_data)}
Session ID: {session.get('id', 'Unknown')}

## Next Steps
- Community validation and extension
- Further investigation of open questions
- Integration with other research
""".strip()

        return {
            "title": title,
            "content": content,
            "hypothesis": f"Multi-agent investigation of {topic}",
            "method": "Collaborative multi-agent investigation with peer validation",
            "findings": "\n".join([f["result"] for f in findings_data]),
            "data_sources": [],
            "open_questions": [
                "What validation experiments would confirm these findings?",
                "Which aspects require additional investigation?",
                "How do these findings extend existing knowledge?",
            ],
        }

    def _save_post_mapping(
        self, session_id: str, finding_id: str, infinite_post_id: str
    ) -> None:
        """Save mapping between coordination findings and Infinite posts."""
        mapping_file = self.integration_dir / f"{session_id}_mappings.json"

        mappings = {}
        if mapping_file.exists():
            try:
                with open(mapping_file) as f:
                    mappings = json.load(f)
            except Exception:
                pass

        if "findings" not in mappings:
            mappings["findings"] = []

        mappings["findings"].append(
            {
                "finding_id": finding_id,
                "infinite_post_id": infinite_post_id,
                "published_at": datetime.utcnow().isoformat(),
            }
        )

        with open(mapping_file, "w") as f:
            json.dump(mappings, f, indent=2)


# Test function
def test_platform_integration():
    """Test platform integration."""
    print("\n=== Phase 4 Test: Platform Integration ===\n")

    from coordination.session_manager import SessionManager

    # Create test session
    manager1 = SessionManager("BioAgent-7")
    session_id = manager1.create_collaborative_session(
        topic="Test finding publication",
        description="Test publishing to Infinite",
        suggested_investigations=[
            {"id": "inv_1", "description": "Test investigation", "tools": ["pubmed"]}
        ],
    )

    # Post finding
    finding_result = manager1.post_finding(
        session_id,
        result="Test finding for publication",
        evidence={"tool_outputs": {"pubmed": {"papers": 5}}},
        confidence=0.85,
    )
    finding_id = finding_result["finding_id"]

    # Validate finding
    manager2 = SessionManager("CrazyChem")
    manager2.join_session(session_id)
    manager2.validate_finding(
        session_id, finding_id, "confirmed", "Confirmed by independent search", 0.80
    )

    # Try to publish
    integration = PlatformIntegration("BioAgent-7")

    print("[TEST] Publishing finding with consensus\n")
    pub_result = integration.publish_finding(session_id, finding_id, "scienceclaw")
    print(f"Publication result: {pub_result}")

    print("[TEST] Checking publication status\n")
    status = integration.get_publication_status(session_id)
    print(f"Status: {status}")

    print("\n✓ Platform integration test complete")


if __name__ == "__main__":
    test_platform_integration()
