"""
ScienceClaw Multi-Agent Coordination

This package contains components for multi-agent collaboration on
large-scale scientific investigations.

Components:
- SessionManager: Manage collaborative investigation sessions
"""

from .session_manager import SessionManager
from .agent_discovery import AgentDiscoveryService

__all__ = ['SessionManager', 'AgentDiscoveryService']
