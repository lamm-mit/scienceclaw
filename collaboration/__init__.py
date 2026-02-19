"""
ScienceClaw Live Collaboration System

Real-time multi-agent scientific investigations with shared message bus,
live Rich terminal dashboard, and figure generation.

Usage:
    from collaboration import LiveCollaborationSession

    session = LiveCollaborationSession(
        topic="CRISPR delivery mechanisms",
        n_agents=3,
    )
    results = session.run()
"""

from .message_bus import MessageBus, Message, MsgType
from .live_runner import LiveCollaborationSession, AgentWorker, AgentState, AGENT_DOMAINS

__all__ = [
    "MessageBus",
    "Message",
    "MsgType",
    "LiveCollaborationSession",
    "AgentWorker",
    "AgentState",
    "AGENT_DOMAINS",
]
