"""
Live Dashboard - Rich terminal UI for watching multi-agent collaboration.

Layout:
┌──────────────────────────────────────────────────────────────────────────┐
│  ScienceClaw Live Collaboration  │  Topic: CRISPR delivery mechanisms    │
│  Session: live-1234567890        │  Agents: 3   Elapsed: 00:02:14        │
├─────────────────┬─────────────────┬───────────────────────────────────────┤
│  AgentBio       │  AgentChem      │  AgentComp                            │
│  ● running      │  ● running      │  ✓ done                               │
│  Tool: pubmed   │  Tool: tdc      │                                       │
│  ████░░░░  2/4  │  ██░░░░░░  1/4  │  ██████████  4/4                     │
│                 │                 │                                       │
│  Findings: 1    │  Findings: 0    │  Findings: 1                          │
├─────────────────┴─────────────────┴───────────────────────────────────────┤
│  Live Discussion                                                           │
│  12:34:01  AgentBio    [tool]     pubmed: 8 results found                 │
│  12:34:05  AgentChem   [tool]     tdc: returned {smiles, predictions, ...}│
│  12:34:09  AgentBio    [finding]  CRISPR-Cas9 delivery efficiency...      │
│  12:34:11  AgentComp   [agree]    ← AgentBio: corroborates structure...  │
├────────────────────────────────────────────────────────────────────────────┤
│  Figures                                                                   │
│  ./collab_xxx/figures/AgentComp_1234.png  — AgentComp — CRISPR...         │
└────────────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import queue
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskID, TextColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from collaboration.message_bus import MessageBus, Message, MsgType
from collaboration.live_runner import AgentState


# Emoji / symbol per message type
_TYPE_ICON = {
    MsgType.AGENT_STATUS: "●",
    MsgType.TOOL_STARTED: "⚙",
    MsgType.TOOL_RESULT:  "✓",
    MsgType.FINDING:      "💡",
    MsgType.CHALLENGE:    "⚔",
    MsgType.AGREEMENT:    "✅",
    MsgType.FIGURE:       "📊",
    MsgType.THOUGHT:      "💭",
    MsgType.SESSION_DONE: "🏁",
}

_TYPE_STYLE = {
    MsgType.TOOL_STARTED: "dim",
    MsgType.TOOL_RESULT:  "dim",
    MsgType.FINDING:      "bold yellow",
    MsgType.CHALLENGE:    "bold red",
    MsgType.AGREEMENT:    "bold green",
    MsgType.FIGURE:       "bold cyan",
    MsgType.THOUGHT:      "italic dim",
    MsgType.AGENT_STATUS: "dim",
    MsgType.SESSION_DONE: "bold white",
}


class LiveDashboard:
    """
    Renders a live Rich dashboard consuming events from MessageBus.

    Designed to run in its own thread alongside AgentWorker threads.
    """

    def __init__(
        self,
        topic: str,
        states: Dict[str, AgentState],
        bus: MessageBus,
        session_id: str = "",
        refresh_rate: float = 0.3,
    ):
        self.topic = topic
        self.states = states
        self.bus = bus
        self.session_id = session_id or "live-session"
        self.refresh_rate = refresh_rate

        self.console = Console()
        self._sub: queue.Queue = bus.subscribe()
        self._feed: List[Message] = []      # discussion feed (last N messages)
        self._feed_max = 20
        self._done = False
        self._start_time = time.time()

        # Per-agent progress tracking
        self._agent_tool_count: Dict[str, int] = {n: 0 for n in states}
        self._agent_total_tools: Dict[str, int] = {n: 4 for n in states}

    # ------------------------------------------------------------------
    # Main run loop (called in dashboard thread)
    # ------------------------------------------------------------------

    def run(self):
        layout = self._build_layout()

        with Live(layout, console=self.console, refresh_per_second=int(1 / self.refresh_rate),
                  screen=True) as live:
            while not self._done:
                self._drain_bus()
                self._update_layout(layout)
                live.update(layout)
                time.sleep(self.refresh_rate)

            # Final frame
            self._drain_bus()
            self._update_layout(layout)
            live.update(layout)
            time.sleep(0.5)

    # ------------------------------------------------------------------
    # Bus draining
    # ------------------------------------------------------------------

    def _drain_bus(self):
        try:
            while True:
                msg: Message = self._sub.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass

    def _handle_message(self, msg: Message):
        # Update agent state tracking
        if msg.type == MsgType.TOOL_RESULT:
            self._agent_tool_count[msg.agent] = \
                self._agent_tool_count.get(msg.agent, 0) + 1
        if msg.type == MsgType.SESSION_DONE:
            self._done = True

        # Add to feed (skip pure status noise)
        if msg.type not in (MsgType.AGENT_STATUS,):
            self._feed.append(msg)
            if len(self._feed) > self._feed_max:
                self._feed = self._feed[-self._feed_max:]

    # ------------------------------------------------------------------
    # Layout construction
    # ------------------------------------------------------------------

    def _build_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="agents", size=10),
            Layout(name="feed"),
            Layout(name="figures", size=5),
        )
        return layout

    def _update_layout(self, layout: Layout):
        layout["header"].update(self._render_header())
        layout["agents"].update(self._render_agents())
        layout["feed"].update(self._render_feed())
        layout["figures"].update(self._render_figures())

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _render_header(self) -> Panel:
        elapsed = int(time.time() - self._start_time)
        mm, ss = divmod(elapsed, 60)
        hh, mm = divmod(mm, 60)

        done_count = sum(1 for s in self.states.values() if s.status == "done")
        total = len(self.states)

        header = Text()
        header.append("ScienceClaw Live Collaboration", style="bold cyan")
        header.append("   |   Topic: ", style="dim")
        header.append(self.topic[:60], style="white")
        header.append(f"   |   Agents: {done_count}/{total} done", style="dim")
        header.append(f"   |   Elapsed: {hh:02d}:{mm:02d}:{ss:02d}", style="dim")

        return Panel(header, box=box.SIMPLE)

    # ------------------------------------------------------------------
    # Agent panels
    # ------------------------------------------------------------------

    def _render_agents(self) -> Columns:
        panels = []
        for name, state in self.states.items():
            panels.append(self._render_agent_panel(name, state))
        return Columns(panels, equal=True, expand=True)

    def _render_agent_panel(self, name: str, state: AgentState) -> Panel:
        color = state.color

        # Status line
        status_icon = {
            "idle":     "○",
            "planning": "◐",
            "running":  "●",
            "done":     "✓",
            "error":    "✗",
        }.get(state.status, "?")
        status_style = {
            "running": "bold green",
            "done":    "bold white",
            "error":   "bold red",
            "planning":"bold yellow",
        }.get(state.status, "dim")

        lines = Text()
        lines.append(f"{status_icon} {state.status.upper()}\n", style=status_style)

        if state.current_tool and state.status == "running":
            lines.append(f"Tool: {state.current_tool}\n", style=f"bold {color}")

        # Progress bar (simple text)
        done = self._agent_tool_count.get(name, 0)
        total = self._agent_total_tools.get(name, 4)
        filled = int(done / max(total, 1) * 10)
        bar = "█" * filled + "░" * (10 - filled)
        lines.append(f"[{bar}] {done}/{total}\n", style=color)

        lines.append(f"\nFindings: {len(state.findings)}", style="yellow")
        if state.figures:
            lines.append(f"  Figures: {len(state.figures)}", style="cyan")

        if state.error:
            lines.append(f"\n⚠ {state.error[:40]}", style="red")

        return Panel(lines, title=f"[bold {color}]{name}[/]",
                     border_style=color, box=box.ROUNDED)

    # ------------------------------------------------------------------
    # Discussion feed
    # ------------------------------------------------------------------

    def _render_feed(self) -> Panel:
        table = Table(box=None, show_header=False, padding=(0, 1),
                      expand=True, show_edge=False)
        table.add_column("time", style="dim", width=9, no_wrap=True)
        table.add_column("agent", width=14, no_wrap=True)
        table.add_column("type", width=10, no_wrap=True)
        table.add_column("message", overflow="fold")

        for msg in self._feed[-14:]:
            ts = msg.timestamp[11:19]  # HH:MM:SS
            icon = _TYPE_ICON.get(msg.type, "·")
            style = _TYPE_STYLE.get(msg.type, "")
            agent_color = self.states.get(msg.agent, AgentState("", "", "white")).color

            # Format message text
            p = msg.payload
            if msg.type == MsgType.TOOL_RESULT:
                text = p.get("summary", "")
            elif msg.type == MsgType.FINDING:
                text = p.get("text", "")[:120]
            elif msg.type == MsgType.CHALLENGE:
                text = f"⚔ {msg.ref_agent}: {p.get('reason', '')[:80]}"
            elif msg.type == MsgType.AGREEMENT:
                text = f"✅ {msg.ref_agent}: corroborates"
            elif msg.type == MsgType.FIGURE:
                text = f"📊 {p.get('title', '')} → {p.get('path', '')}"
            elif msg.type == MsgType.THOUGHT:
                text = p.get("text", "")[:100]
            elif msg.type == MsgType.TOOL_STARTED:
                text = f"starting {p.get('tool', '')}..."
            else:
                text = str(p)[:100]

            type_label = f"[{msg.type.value[0:8]}]"

            table.add_row(
                ts,
                Text(msg.agent, style=f"bold {agent_color}"),
                Text(type_label, style=style),
                Text(text, style=style),
            )

        return Panel(table, title="[bold]Live Discussion[/]",
                     border_style="dim", box=box.ROUNDED)

    # ------------------------------------------------------------------
    # Figures panel
    # ------------------------------------------------------------------

    def _render_figures(self) -> Panel:
        fig_msgs = self.bus.figures()
        if not fig_msgs:
            content = Text("No figures yet.", style="dim italic")
        else:
            lines = []
            for msg in fig_msgs[-4:]:
                p = msg.payload
                agent_color = self.states.get(
                    msg.agent, AgentState("", "", "white")).color
                line = Text()
                line.append(f"[{msg.agent}] ", style=f"bold {agent_color}")
                line.append(p.get("title", ""), style="white")
                line.append(" → ", style="dim")
                line.append(p.get("path", ""), style="cyan underline")
                lines.append(line)
            content = Text("\n").join(lines)  # type: ignore[arg-type]

        return Panel(content, title="[bold cyan]Figures Generated[/]",
                     border_style="cyan", box=box.ROUNDED)
