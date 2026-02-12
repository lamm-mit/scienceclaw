#!/usr/bin/env python3
"""
Agent Discovery Service - Skill-Based Agent Discovery

Enables agents to discover collaborative sessions matching their skills and interests.
Uses a shared index file for decentralized discovery (no central server).

Index location: ~/.infinite/workspace/discovery/agent_index.json

Features:
- Agent registration with skills and interests
- Session broadcasting for discovery
- Skill-based agent matching
- Interest-based matching
- Agent availability tracking
- Atomic writes to prevent conflicts

Author: ScienceClaw Team
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Any


class AgentDiscoveryService:
    """
    Enables skill-based agent discovery for multi-agent coordination.

    Agents register their skills during heartbeat. Sessions broadcast needed skills.
    Agents discover sessions by checking index during heartbeat.

    Design: Shared index file with atomic writes (no central server, fully distributed).
    """

    def __init__(self):
        """Initialize discovery service."""
        # Discovery index location
        self.discovery_dir = Path.home() / ".infinite" / "workspace" / "discovery"
        self.discovery_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.discovery_dir / "agent_index.json"

        # Create empty index if doesn't exist
        if not self.index_path.exists():
            self._save_index({
                "agents": {},
                "skill_index": {},
                "active_sessions": {},
                "last_updated": datetime.utcnow().isoformat()
            })

        print(f"[AgentDiscoveryService] Initialized")
        print(f"[AgentDiscoveryService] Index file: {self.index_path}")

    # =========================================================================
    # Agent Registration
    # =========================================================================

    def register_agent(
        self,
        agent_name: str,
        profile: Dict[str, Any],
        status: str = "available"
    ) -> Dict[str, Any]:
        """
        Register or update agent in discovery index.

        Called during heartbeat to advertise skills and availability.

        Args:
            agent_name: Agent name
            profile: Agent profile with:
                - domain: "biology", "chemistry", "mixed"
                - preferred_tools: List of tools (skills)
                - interests: List of research interests
                - curiosity_style: "explorer", "deep-diver", "connector", "skeptic"
            status: "available", "busy", "investigating"

        Returns:
            Registration status
        """
        index = self._load_index()

        # Extract skills and interests
        skills = set(profile.get("preferred_tools", []))
        interests = set(profile.get("interests", []))
        domain = profile.get("profile", "mixed")  # Old key name compatibility
        if not domain or domain == "mixed":
            domain = profile.get("domain", "mixed")

        # Register agent
        index["agents"][agent_name] = {
            "name": agent_name,
            "domain": domain,
            "skills": sorted(list(skills)),
            "interests": sorted(list(interests)),
            "status": status,
            "curiosity_style": profile.get("curiosity_style", "explorer"),
            "last_heartbeat": datetime.utcnow().isoformat()
        }

        # Update skill index for fast lookup
        self._update_skill_index(index, agent_name, skills)

        # Save
        index["last_updated"] = datetime.utcnow().isoformat()
        self._save_index(index)

        print(f"[AgentDiscoveryService] Registered agent: {agent_name}")
        print(f"[AgentDiscoveryService]   Domain: {domain}, Skills: {len(skills)}, Interests: {len(interests)}")

        return {"status": "registered", "agent": agent_name}

    def unregister_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Remove agent from discovery index.

        Args:
            agent_name: Agent to remove

        Returns:
            Removal status
        """
        index = self._load_index()

        if agent_name not in index["agents"]:
            return {"status": "not_found", "agent": agent_name}

        # Remove agent
        agent = index["agents"].pop(agent_name)

        # Remove from skill index
        for skill in agent.get("skills", []):
            if skill in index["skill_index"]:
                index["skill_index"][skill] = [
                    a for a in index["skill_index"][skill] if a != agent_name
                ]
                # Clean up empty skill entries
                if not index["skill_index"][skill]:
                    del index["skill_index"][skill]

        # Save
        index["last_updated"] = datetime.utcnow().isoformat()
        self._save_index(index)

        print(f"[AgentDiscoveryService] Unregistered agent: {agent_name}")

        return {"status": "unregistered", "agent": agent_name}

    # =========================================================================
    # Session Broadcasting & Discovery
    # =========================================================================

    def broadcast_session(
        self,
        session_id: str,
        topic: str,
        investigation_type: str = "multi-agent",
        suggested_investigations: Optional[List[Dict[str, Any]]] = None,
        needed_skills: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Broadcast a new session to the discovery index.

        Agents discover this session during heartbeat and can join.

        Args:
            session_id: Session ID
            topic: Research topic
            investigation_type: "multi-agent", "validation", "screening"
            suggested_investigations: Optional investigation suggestions
            needed_skills: Required skills for this session (if None, inferred from investigations)

        Returns:
            Broadcast status
        """
        index = self._load_index()

        # Infer needed skills from suggested investigations if not provided
        if needed_skills is None:
            needed_skills = []
            if suggested_investigations:
                skills_set = set()
                for inv in suggested_investigations:
                    tools = inv.get("tools", [])
                    skills_set.update(tools)
                needed_skills = sorted(list(skills_set))

        # Broadcast session
        index["active_sessions"][session_id] = {
            "session_id": session_id,
            "topic": topic,
            "investigation_type": investigation_type,
            "needed_skills": needed_skills,
            "created_at": datetime.utcnow().isoformat(),
            "suggestion_count": len(suggested_investigations or [])
        }

        # Save
        index["last_updated"] = datetime.utcnow().isoformat()
        self._save_index(index)

        print(f"[AgentDiscoveryService] Broadcasted session: {session_id}")
        print(f"[AgentDiscoveryService]   Topic: {topic}, Needed skills: {needed_skills}")

        return {"status": "broadcasted", "session_id": session_id}

    def remove_session(self, session_id: str) -> Dict[str, Any]:
        """
        Remove session from discovery index (when completed/abandoned).

        Args:
            session_id: Session to remove

        Returns:
            Removal status
        """
        index = self._load_index()

        if session_id not in index["active_sessions"]:
            return {"status": "not_found", "session_id": session_id}

        index["active_sessions"].pop(session_id)

        # Save
        index["last_updated"] = datetime.utcnow().isoformat()
        self._save_index(index)

        print(f"[AgentDiscoveryService] Removed session: {session_id}")

        return {"status": "removed", "session_id": session_id}

    # =========================================================================
    # Agent Discovery Queries
    # =========================================================================

    def find_agents_by_skill(
        self,
        skills: List[str],
        exclude: Optional[List[str]] = None,
        availability: str = "available"
    ) -> List[Dict[str, Any]]:
        """
        Find agents with specific skills.

        Args:
            skills: Required skills (agents must have ALL of them)
            exclude: Agents to exclude from results
            availability: Filter by status ("available", "busy", "investigating", or None for all)

        Returns:
            List of matching agents sorted by skill match
        """
        index = self._load_index()
        exclude = exclude or []

        # Find agents with ALL required skills
        candidates = set()
        for skill in skills:
            agents_with_skill = set(index["skill_index"].get(skill, []))
            if not candidates:
                candidates = agents_with_skill
            else:
                candidates &= agents_with_skill  # Intersection: only agents with ALL skills

        # Filter by availability and exclude list
        results = []
        for agent_name in candidates:
            if agent_name in exclude:
                continue
            agent = index["agents"].get(agent_name)
            if not agent:
                continue
            if availability and agent.get("status") != availability:
                continue
            results.append(agent)

        # Sort by skill match count (more matching skills = higher priority)
        results.sort(
            key=lambda a: len(set(a.get("skills", [])) & set(skills)),
            reverse=True
        )

        return results

    def find_agents_by_interest(
        self,
        topic: str,
        max_agents: int = 5,
        exclude: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find agents interested in a topic (keyword matching).

        Args:
            topic: Research topic (will match against agent interests)
            max_agents: Maximum agents to return
            exclude: Agents to exclude

        Returns:
            List of matching agents sorted by relevance
        """
        index = self._load_index()
        exclude = exclude or []
        topic_lower = topic.lower()

        # Score agents by interest match
        scored_agents = []
        for agent_name, agent in index["agents"].items():
            if agent_name in exclude:
                continue

            score = 0
            # Simple keyword matching against interests
            for interest in agent.get("interests", []):
                interest_lower = interest.lower()
                if interest_lower in topic_lower or topic_lower in interest_lower:
                    score += 2  # Direct match
                elif any(word in topic_lower for word in interest_lower.split()):
                    score += 1  # Partial match

            if score > 0:
                scored_agents.append((score, agent))

        # Sort by score and return top N
        scored_agents.sort(reverse=True, key=lambda x: x[0])
        return [agent for score, agent in scored_agents[:max_agents]]

    def find_sessions_by_skill(
        self,
        skills: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find sessions needing specific skills.

        Args:
            skills: Skills agent has
            limit: Maximum sessions to return

        Returns:
            List of matching sessions
        """
        index = self._load_index()
        agent_skills = set(skills)

        # Score sessions by skill match
        scored_sessions = []
        for session_id, session in index["active_sessions"].items():
            needed = set(session.get("needed_skills", []))
            # Count how many needed skills agent has
            matches = len(agent_skills & needed)

            if matches > 0:
                scored_sessions.append((matches, session))

        # Sort by match count (highest first)
        scored_sessions.sort(reverse=True, key=lambda x: x[0])
        return [session for matches, session in scored_sessions[:limit]]

    def find_sessions_by_interest(
        self,
        topic: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find sessions by topic interest (keyword matching).

        Args:
            topic: Research interest
            limit: Maximum sessions to return

        Returns:
            List of matching sessions
        """
        index = self._load_index()
        topic_lower = topic.lower()

        # Score sessions by topic match
        scored_sessions = []
        for session_id, session in index["active_sessions"].items():
            session_topic = session.get("topic", "").lower()

            # Calculate match score
            score = 0
            if topic_lower in session_topic or session_topic in topic_lower:
                score = 3  # Direct match
            elif any(word in session_topic for word in topic_lower.split()):
                score = 1  # Partial match

            if score > 0:
                scored_sessions.append((score, session))

        # Sort by score and return top N
        scored_sessions.sort(reverse=True, key=lambda x: x[0])
        return [session for score, session in scored_sessions[:limit]]

    # =========================================================================
    # Status & Reporting
    # =========================================================================

    def get_discovery_status(self) -> Dict[str, Any]:
        """Get current discovery index status."""
        index = self._load_index()

        return {
            "total_agents": len(index["agents"]),
            "active_agents": sum(
                1 for a in index["agents"].values() if a.get("status") == "available"
            ),
            "total_skills": len(index["skill_index"]),
            "total_sessions": len(index["active_sessions"]),
            "last_updated": index.get("last_updated")
        }

    def list_all_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        index = self._load_index()
        return list(index["agents"].values())

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        index = self._load_index()
        return list(index["active_sessions"].values())

    # =========================================================================
    # Internal: Index Management
    # =========================================================================

    def _load_index(self) -> Dict[str, Any]:
        """Load index with atomic read."""
        try:
            with open(self.index_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[AgentDiscoveryService] Error loading index: {e}")
            return {
                "agents": {},
                "skill_index": {},
                "active_sessions": {},
                "last_updated": datetime.utcnow().isoformat()
            }

    def _save_index(self, index: Dict[str, Any]):
        """Save index with atomic write (temp file + rename)."""
        try:
            temp_path = self.index_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(index, f, indent=2)
            temp_path.replace(self.index_path)
        except Exception as e:
            print(f"[AgentDiscoveryService] Error saving index: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _update_skill_index(
        self,
        index: Dict[str, Any],
        agent_name: str,
        skills: Set[str]
    ):
        """Update skill index when agent's skills change."""
        # Clear old entries for this agent
        for skill in list(index["skill_index"].keys()):
            if agent_name in index["skill_index"][skill]:
                index["skill_index"][skill] = [
                    a for a in index["skill_index"][skill] if a != agent_name
                ]
                # Clean up empty skill entries
                if not index["skill_index"][skill]:
                    del index["skill_index"][skill]

        # Add new entries
        for skill in skills:
            if skill not in index["skill_index"]:
                index["skill_index"][skill] = []
            if agent_name not in index["skill_index"][skill]:
                index["skill_index"][skill].append(agent_name)


# Test function
def test_agent_discovery():
    """Test the agent discovery service."""

    discovery = AgentDiscoveryService()

    print("\n=== Phase 2 Test: Agent Discovery ===\n")

    # Register agents with different skills
    print("[TEST] Registering agents...")
    discovery.register_agent("BioAgent-7", {
        "domain": "biology",
        "preferred_tools": ["pubmed", "uniprot", "pdb", "alphafold"],
        "interests": ["protein structure", "disease mechanisms", "drug targets"],
        "curiosity_style": "deep-diver"
    })

    discovery.register_agent("CrazyChem", {
        "domain": "chemistry",
        "preferred_tools": ["pubchem", "tdc", "rdkit"],
        "interests": ["drug discovery", "ADMET", "binding kinetics"],
        "curiosity_style": "explorer"
    })

    discovery.register_agent("SkepticalBot", {
        "domain": "biology",
        "preferred_tools": ["pubmed", "uniprot", "arxiv"],
        "interests": ["mechanism validation", "literature review"],
        "curiosity_style": "skeptic"
    })

    # Broadcast a session
    print("\n[TEST] Broadcasting session...")
    discovery.broadcast_session(
        session_id="scienceclaw-collab-abc123",
        topic="BACE1 as drug target for Alzheimer's disease",
        investigation_type="multi-agent",
        suggested_investigations=[
            {"id": "inv_1", "description": "Literature review", "tools": ["pubmed"]},
            {"id": "inv_2", "description": "Protein structure", "tools": ["uniprot", "pdb"]},
            {"id": "inv_3", "description": "Drug screening", "tools": ["pubchem", "tdc"]}
        ]
    )

    # Test skill-based discovery
    print("\n[TEST] Finding agents with pubmed + uniprot skills...")
    matching_agents = discovery.find_agents_by_skill(["pubmed", "uniprot"])
    print(f"Found {len(matching_agents)} agents:")
    for agent in matching_agents:
        print(f"  - {agent['name']}: {agent['skills']}")

    # Test interest-based discovery
    print("\n[TEST] Finding agents interested in 'drug discovery'...")
    interested_agents = discovery.find_agents_by_interest("drug discovery", max_agents=3)
    print(f"Found {len(interested_agents)} agents:")
    for agent in interested_agents:
        print(f"  - {agent['name']}: {agent['interests']}")

    # Test session discovery by skill
    print("\n[TEST] Finding sessions for agent with pubchem + tdc skills...")
    matching_sessions = discovery.find_sessions_by_skill(["pubchem", "tdc"])
    print(f"Found {len(matching_sessions)} sessions:")
    for session in matching_sessions:
        print(f"  - {session['topic']}")

    # Test session discovery by interest
    print("\n[TEST] Finding sessions for agent interested in 'Alzheimer's'...")
    interested_sessions = discovery.find_sessions_by_interest("Alzheimer's disease")
    print(f"Found {len(interested_sessions)} sessions:")
    for session in interested_sessions:
        print(f"  - {session['topic']}")

    # Status report
    print("\n[TEST] Discovery status...")
    status = discovery.get_discovery_status()
    print(f"Agents: {status['total_agents']}, Active: {status['active_agents']}")
    print(f"Skills indexed: {status['total_skills']}")
    print(f"Sessions: {status['total_sessions']}")

    print("\n✓ Agent discovery test complete")


if __name__ == "__main__":
    test_agent_discovery()
