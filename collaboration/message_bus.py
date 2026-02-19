"""
Message Bus - Thread-safe inter-agent communication for live collaboration.

Agents publish typed messages during investigation; other agents subscribe
and can react to each other's findings in real-time (within the same session).

Message types:
  AgentStatus     - agent lifecycle (started, thinking, done)
  ToolStarted     - agent began executing a tool
  ToolResult      - tool produced output (summary + data)
  Finding         - agent posted a significant finding
  Challenge       - agent challenged another agent's finding
  Agreement       - agent confirmed another finding
  FigureGenerated - agent produced a plot/figure file
  Thought         - agent's intermediate reasoning step
  SessionDone     - session is complete
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Message types
# ---------------------------------------------------------------------------

class MsgType(str, Enum):
    AGENT_STATUS    = "AgentStatus"
    TOOL_STARTED    = "ToolStarted"
    TOOL_RESULT     = "ToolResult"
    FINDING         = "Finding"
    CHALLENGE       = "Challenge"
    AGREEMENT       = "Agreement"
    FIGURE          = "FigureGenerated"
    THOUGHT         = "Thought"
    SESSION_DONE    = "SessionDone"


@dataclass
class Message:
    type: MsgType
    agent: str
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    ref_agent: Optional[str] = None   # for Challenge / Agreement — who we're referencing


# ---------------------------------------------------------------------------
# MessageBus
# ---------------------------------------------------------------------------

class MessageBus:
    """
    Pub/sub message bus for live agent collaboration.

    All agents share one bus.  Any agent can publish; any agent (or the
    dashboard) can subscribe.  Subscribers receive messages via a per-
    subscriber queue so no messages are dropped.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: List[queue.Queue] = []
        self._history: List[Message] = []      # full log for replay

    # ------------------------------------------------------------------
    # Subscribe / publish
    # ------------------------------------------------------------------

    def subscribe(self) -> queue.Queue:
        """
        Create a new subscriber queue.  The caller should poll this queue
        with get(timeout=...) or get_nowait().  Returns the queue.
        """
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
            # Replay history so late-joining subscribers catch up
            for msg in self._history:
                q.put(msg)
        return q

    def publish(self, msg: Message):
        """Publish a message to all subscribers."""
        with self._lock:
            self._history.append(msg)
            for q in self._subscribers:
                q.put(msg)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def agent_status(self, agent: str, status: str, detail: str = ""):
        self.publish(Message(
            type=MsgType.AGENT_STATUS, agent=agent,
            payload={"status": status, "detail": detail}
        ))

    def tool_started(self, agent: str, tool: str, params: Dict = None):
        self.publish(Message(
            type=MsgType.TOOL_STARTED, agent=agent,
            payload={"tool": tool, "params": params or {}}
        ))

    def tool_result(self, agent: str, tool: str, summary: str, data: Any = None):
        self.publish(Message(
            type=MsgType.TOOL_RESULT, agent=agent,
            payload={"tool": tool, "summary": summary, "data": data}
        ))

    def finding(self, agent: str, text: str, confidence: float = 0.8,
                sources: List[str] = None):
        self.publish(Message(
            type=MsgType.FINDING, agent=agent,
            payload={"text": text, "confidence": confidence,
                     "sources": sources or []}
        ))

    def challenge(self, agent: str, ref_agent: str, finding_text: str,
                  reason: str):
        self.publish(Message(
            type=MsgType.CHALLENGE, agent=agent, ref_agent=ref_agent,
            payload={"finding": finding_text, "reason": reason}
        ))

    def agreement(self, agent: str, ref_agent: str, finding_text: str):
        self.publish(Message(
            type=MsgType.AGREEMENT, agent=agent, ref_agent=ref_agent,
            payload={"finding": finding_text}
        ))

    def figure(self, agent: str, path: str, title: str, fig_type: str = "plot"):
        self.publish(Message(
            type=MsgType.FIGURE, agent=agent,
            payload={"path": path, "title": title, "type": fig_type}
        ))

    def thought(self, agent: str, text: str):
        self.publish(Message(
            type=MsgType.THOUGHT, agent=agent,
            payload={"text": text}
        ))

    def session_done(self, agent: str = "orchestrator"):
        self.publish(Message(
            type=MsgType.SESSION_DONE, agent=agent, payload={}
        ))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def findings(self) -> List[Message]:
        """Return all Finding messages published so far."""
        with self._lock:
            return [m for m in self._history if m.type == MsgType.FINDING]

    def figures(self) -> List[Message]:
        """Return all FigureGenerated messages published so far."""
        with self._lock:
            return [m for m in self._history if m.type == MsgType.FIGURE]

    def history(self, types: Optional[List[MsgType]] = None) -> List[Message]:
        with self._lock:
            if types:
                return [m for m in self._history if m.type in types]
            return list(self._history)
