"""
Live Collaboration Runner

Runs multiple agents in parallel, each with their own SkillTreeSearcher +
DependencyGraph execution plan.  Agents stream events to a shared MessageBus
so they can react to each other's findings in real-time.

Usage:
    session = LiveCollaborationSession(
        topic="CRISPR delivery mechanisms",
        n_agents=3,
        output_dir="./results",
    )
    results = session.run()

Or via CLI:
    scienceclaw-watch "CRISPR delivery mechanisms" --agents 3
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from collaboration.message_bus import MessageBus, MsgType, Message

try:
    from core.skill_tree_searcher import SkillTreeSearcher, search_skills_for_topic
    from core.skill_dag import DependencyGraph, SkillNode, SkillType, NodeStatus, build_graph_from_plan
    TREE_SEARCH = True
except ImportError:
    TREE_SEARCH = False

try:
    from core.llm_client import get_llm_client
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


# ---------------------------------------------------------------------------
# Agent domain templates
# ---------------------------------------------------------------------------

AGENT_DOMAINS = [
    {
        "suffix": "Bio",
        "domain": "biology",
        "focus": "protein structure, gene function, molecular biology",
        "skills": ["pubmed", "uniprot", "blast", "pdb", "biorxiv-database"],
        "color": "green",
    },
    {
        "suffix": "Chem",
        "domain": "chemistry",
        "focus": "drug discovery, compound properties, ADMET prediction",
        "skills": ["pubchem", "chembl", "tdc", "rdkit", "cas"],
        "color": "cyan",
    },
    {
        "suffix": "Comp",
        "domain": "computational",
        "focus": "structure prediction, bioinformatics, machine learning",
        "skills": ["alphafold-database", "arxiv", "scikit-learn", "deepchem"],
        "color": "magenta",
    },
    {
        "suffix": "Synth",
        "domain": "synthesis",
        "focus": "literature synthesis, meta-analysis, cross-domain integration",
        "skills": ["pubmed", "arxiv", "openalex-database", "websearch"],
        "color": "yellow",
    },
    {
        "suffix": "Path",
        "domain": "pathways",
        "focus": "signaling pathways, network biology, disease mechanisms",
        "skills": ["kegg-database", "reactome-database", "string-database", "pubmed"],
        "color": "blue",
    },
]


# ---------------------------------------------------------------------------
# AgentWorker
# ---------------------------------------------------------------------------

@dataclass
class AgentState:
    name: str
    domain: str
    color: str
    status: str = "idle"           # idle → planning → running → done / error
    current_tool: str = ""
    tools_done: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    figures: List[str] = field(default_factory=list)
    error: Optional[str] = None


class AgentWorker(threading.Thread):
    """
    One agent running in its own thread.

    Investigation flow:
    1.  Use SkillTreeSearcher to find relevant skills for the topic
    2.  Build a DependencyGraph from the plan
    3.  Execute skills phase-by-phase (respecting dependencies)
    4.  After each tool, stream result to message bus
    5.  Read peer findings from message bus → challenge or agree
    6.  Generate a visualization if data warrants it
    7.  Synthesize final finding
    """

    def __init__(
        self,
        name: str,
        domain_cfg: Dict,
        topic: str,
        bus: MessageBus,
        state: AgentState,
        output_dir: Path,
        peer_queue: queue.Queue,
        scienceclaw_dir: Path,
        timeout_per_tool: int = 45,
    ):
        super().__init__(name=name, daemon=True)
        self.agent_name = name
        self.domain_cfg = domain_cfg
        self.topic = topic
        self.bus = bus
        self.state = state
        self.output_dir = output_dir
        self.peer_queue = peer_queue   # receives Finding messages from peers
        self.scienceclaw_dir = scienceclaw_dir
        self.timeout_per_tool = timeout_per_tool
        self.results: Dict[str, Any] = {}   # tool_name → parsed output

    # ------------------------------------------------------------------
    # Thread entry
    # ------------------------------------------------------------------

    def run(self):
        try:
            self._run_investigation()
        except Exception as exc:
            self.state.status = "error"
            self.state.error = str(exc)
            self.bus.agent_status(self.agent_name, "error", str(exc))

    def _run_investigation(self):
        self.state.status = "planning"
        self.bus.agent_status(self.agent_name, "planning",
                               f"Searching skills for: {self.topic}")

        # 1. Skill discovery
        skills = self._discover_skills()

        self.bus.thought(self.agent_name,
                          f"Selected {len(skills)} skills: {', '.join(skills)}")

        # 2. Build execution plan (DAG)
        dag = self._build_dag(skills)
        phases = dag.get_execution_phases()
        self.state.status = "running"
        self.bus.agent_status(self.agent_name, "running",
                               f"{len(phases)} execution phases planned")

        # 3. Execute phase by phase
        for phase in phases:
            for node_id in phase.node_ids:
                node = dag.get_node(node_id)
                if node is None:
                    continue
                self._execute_node(dag, node)

        # 4. React to peer findings
        self._react_to_peers()

        # 5. Generate figure if we have numeric data
        fig_path = self._maybe_generate_figure()
        if fig_path:
            self.state.figures.append(str(fig_path))

        # 6. Synthesize final finding
        self._synthesize()

        self.state.status = "done"
        self.bus.agent_status(self.agent_name, "done", "Investigation complete")

    # ------------------------------------------------------------------
    # Skill discovery
    # ------------------------------------------------------------------

    def _discover_skills(self) -> List[str]:
        """Use SkillTreeSearcher if available, else fall back to domain defaults."""
        if TREE_SEARCH:
            try:
                searcher = SkillTreeSearcher(agent_name=self.agent_name)
                result = searcher.search(
                    topic=self.topic,
                    max_skills=5,
                    domain_hint=self.domain_cfg["domain"],
                )
                if result.skills:
                    return [s.name for s in result.skills[:5]]
            except Exception:
                pass
        # Fallback: domain defaults
        return self.domain_cfg["skills"][:4]

    # ------------------------------------------------------------------
    # DAG construction
    # ------------------------------------------------------------------

    def _build_dag(self, skills: List[str]) -> DependencyGraph:
        """Build a simple linear DAG from the skill list."""
        nodes = []
        for i, skill_name in enumerate(skills):
            depends_on = [f"node_{i-1}"] if i > 0 else []
            # Last skill is primary; rest are helpers
            skill_type = "primary" if i == len(skills) - 1 else "helper"
            nodes.append({
                "id": f"node_{i}",
                "name": skill_name,
                "depends_on": depends_on,
                "purpose": f"Investigate {self.topic} via {skill_name}",
                "skill_type": skill_type,
            })
        try:
            return build_graph_from_plan(nodes)
        except Exception:
            # If DAG fails, make a flat (no-dependency) plan
            for n in nodes:
                n["depends_on"] = []
            return build_graph_from_plan(nodes)

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _execute_node(self, dag: DependencyGraph, node: SkillNode):
        tool = node.name
        self.state.current_tool = tool
        self.bus.tool_started(self.agent_name, tool, {"topic": self.topic})
        dag.update_status(node.id, NodeStatus.RUNNING)

        try:
            output = self._run_skill(tool)
            summary = self._summarize_output(tool, output)
            self.results[tool] = output
            self.bus.tool_result(self.agent_name, tool, summary, output)
            dag.update_status(node.id, NodeStatus.COMPLETED)
            self.state.tools_done.append(tool)
        except Exception as exc:
            dag.fail_node(node.id)
            self.bus.tool_result(self.agent_name, tool,
                                  f"[failed] {exc}", None)

    # Per-skill argument builders ----------------------------------------
    # Returns (script_name, [extra_args]) so _run_skill can build the cmd.
    # script_name=None → use first non-__ .py in the scripts/ directory.

    _SKILL_ARG_MAP: Dict[str, Any] = {
        # UniProt: use --search instead of --query
        "uniprot": {
            "script": "uniprot_fetch.py",
            "args_fn": lambda topic: ["--search", topic[:120], "--max-results", "5"],
        },
        # BLAST: needs a real sequence — use a short representative kinase peptide
        # For non-sequence topics, fall back to a canonical test sequence
        "blast": {
            "script": "blast_search.py",
            "args_fn": lambda topic: [
                "--query", "MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSY",
                "--program", "blastp", "--max-hits", "5",
            ],
        },
        # TDC: needs --smiles; use aspirin as a representative drug-like molecule
        "tdc": {
            "script": "tdc_predict.py",
            "args_fn": lambda topic: [
                "--smiles", "CC(=O)Oc1ccccc1C(=O)O",  # aspirin
                "--model", "BBB_Martins-AttentiveFP",
            ],
        },
        # RDKit: needs --smiles + subcommand
        "rdkit": {
            "script": "rdkit_tools.py",
            "args_fn": lambda topic: [
                "descriptors",
                "--smiles", "CC(=O)Oc1ccccc1C(=O)O",
                "--format", "json",
            ],
        },
        # AlphaFold demo: no query args accepted
        "alphafold-database": {
            "script": "_demo.py",
            "args_fn": lambda topic: ["--format", "json"],
        },
        # PubChem: uses --query (fine as-is)
        "pubchem": {
            "script": "pubchem_search.py",
            "args_fn": lambda topic: ["--query", topic[:120], "--max-results", "5"],
        },
        # ChEMBL: uses --query (fine as-is)
        "chembl": {
            "script": "chembl_search.py",
            "args_fn": lambda topic: ["--query", topic[:120], "--max-results", "5"],
        },
    }

    def _run_skill(self, skill_name: str) -> Dict:
        """Execute a skill script and return parsed JSON output."""
        skill_dir = self.scienceclaw_dir / "skills" / skill_name / "scripts"
        if not skill_dir.exists():
            return {"error": f"skill {skill_name} not found"}

        # Per-skill arg mapping
        mapping = self._SKILL_ARG_MAP.get(skill_name)
        if mapping:
            script = skill_dir / mapping["script"]
            extra_args = mapping["args_fn"](self.topic)
        else:
            # Default: first non-__ script with --query + --max-results
            scripts = sorted(s for s in skill_dir.glob("*.py")
                             if not s.name.startswith("__"))
            if not scripts:
                return {"error": "no scripts"}
            script = scripts[0]
            extra_args = ["--query", self.topic[:120], "--max-results", "5"]

        if not script.exists():
            # Fall back to first available script
            scripts = sorted(s for s in skill_dir.glob("*.py")
                             if not s.name.startswith("__"))
            if not scripts:
                return {"error": "no scripts"}
            script = scripts[0]

        cmd = [sys.executable, str(script)] + extra_args

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout_per_tool,
                cwd=str(self.scienceclaw_dir),
            )
            if result.stdout:
                text = result.stdout.strip()
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"text": text[:2000]}
            return {"text": result.stderr[:500] if result.stderr else "no output"}
        except subprocess.TimeoutExpired:
            return {"error": "timeout"}
        except Exception as exc:
            return {"error": str(exc)}

    def _summarize_output(self, tool: str, output: Dict) -> str:
        """Create a one-line human-readable summary of tool output."""
        if not output or "error" in output:
            return f"{tool}: {output.get('error', 'no results')}"

        # Common output shapes
        if "papers" in output or "results" in output:
            items = output.get("papers") or output.get("results") or []
            n = len(items) if isinstance(items, list) else "?"
            return f"{tool}: {n} results found"
        if "text" in output:
            snippet = output["text"][:120].replace("\n", " ")
            return f"{tool}: {snippet}..."
        if isinstance(output, dict):
            keys = list(output.keys())[:3]
            return f"{tool}: returned {{{', '.join(keys)}, ...}}"
        return f"{tool}: completed"

    # ------------------------------------------------------------------
    # React to peers
    # ------------------------------------------------------------------

    def _react_to_peers(self):
        """Read peer findings and issue challenges or agreements."""
        peer_findings: List[Message] = []
        try:
            while True:
                msg = self.peer_queue.get_nowait()
                if msg.type == MsgType.FINDING and msg.agent != self.agent_name:
                    peer_findings.append(msg)
        except queue.Empty:
            pass

        for peer_msg in peer_findings[:3]:   # react to up to 3 peers
            peer_text = peer_msg.payload.get("text", "")
            # Simple heuristic: if topic keywords overlap heavily → agree, else neutral
            overlap = sum(
                1 for w in self.topic.lower().split()
                if len(w) > 4 and w in peer_text.lower()
            )
            if overlap >= 2:
                self.bus.agreement(self.agent_name, peer_msg.agent, peer_text)
            # Challenge if our domain data contradicts
            elif self.results and overlap == 0:
                self.bus.challenge(
                    self.agent_name, peer_msg.agent, peer_text,
                    f"No corroborating evidence found in {self.domain_cfg['domain']} data"
                )

    # ------------------------------------------------------------------
    # Figure generation
    # ------------------------------------------------------------------

    def _extract_numeric_data(self) -> Dict[str, float]:
        """
        Walk diverse tool output shapes and pull out plottable numeric values.

        Handles:
          - Top-level int/float keys
          - 'count', 'total', 'hits' keys
          - Lists of dicts → extract numeric leaf values from first item
          - TDC predictions → BBB probability
          - PubMed / ChEMBL / PubChem result counts
          - RDKit descriptor values
        """
        data_points: Dict[str, float] = {}

        def _try_add(label: str, value: Any):
            try:
                f = float(value)
                if 0 < abs(f) < 1e9 and label not in data_points:
                    data_points[label] = f
            except (TypeError, ValueError):
                pass

        for tool, output in self.results.items():
            if not isinstance(output, dict) or "error" in output:
                continue

            # Result-count proxies
            for count_key in ("count", "total", "hits", "num_results",
                              "total_results", "n_results"):
                if count_key in output:
                    _try_add(f"{tool} ({count_key})", output[count_key])

            # List values → use length as count, and sample first item's numbers
            for k, v in output.items():
                if isinstance(v, list) and v:
                    _try_add(f"{tool} {k} count", len(v))
                    first = v[0]
                    if isinstance(first, dict):
                        for fk, fv in list(first.items())[:4]:
                            if isinstance(fv, (int, float)):
                                _try_add(f"{tool} {fk}", fv)
                elif isinstance(v, (int, float)):
                    _try_add(f"{tool} {k}", v)

            # TDC predictions: {"predictions": [{"probability": 0.87, ...}]}
            if "predictions" in output:
                preds = output["predictions"]
                if isinstance(preds, list):
                    for i, p in enumerate(preds[:3]):
                        if isinstance(p, dict):
                            for pk in ("probability", "score", "value", "pred"):
                                if pk in p:
                                    _try_add(f"{tool} pred_{i}", p[pk])

            # RDKit descriptors dict: {"MW": 180.16, "LogP": ...}
            if "descriptors" in output and isinstance(output["descriptors"], dict):
                for dk, dv in list(output["descriptors"].items())[:6]:
                    _try_add(f"rdkit {dk}", dv)

        return data_points

    def _maybe_generate_figure(self) -> Optional[Path]:
        """Generate a simple matplotlib figure if we have numeric results."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return None

        data_points = self._extract_numeric_data()

        if len(data_points) < 2:
            # Fallback: generate a tool-completion bar chart from tools_done count
            if len(self.state.tools_done) >= 2:
                data_points = {t: float(i + 1)
                               for i, t in enumerate(self.state.tools_done)}
            else:
                return None

        labels = [k.split(":")[-1][:20] for k in list(data_points.keys())[:8]]
        values = list(data_points.values())[:8]

        fig, ax = plt.subplots(figsize=(8, 4))
        bars = ax.barh(labels, values, color="#4C9BE8")
        ax.set_title(f"{self.agent_name}: {self.topic[:60]}", fontsize=11)
        ax.set_xlabel("Value")
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.01 * max(values),
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:.2f}", va="center", fontsize=8)

        fig_dir = self.output_dir / "figures"
        fig_dir.mkdir(parents=True, exist_ok=True)
        fig_path = fig_dir / f"{self.agent_name}_{int(time.time())}.png"
        plt.tight_layout()
        plt.savefig(fig_path, dpi=120, bbox_inches="tight")
        plt.close(fig)

        self.bus.figure(self.agent_name, str(fig_path),
                         f"{self.agent_name} — {self.topic[:40]}", "bar")
        return fig_path

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def _synthesize(self):
        """Produce a final finding from all tool results."""
        tools_used = self.state.tools_done
        n_tools = len(tools_used)

        if n_tools == 0:
            finding_text = (
                f"Investigation of '{self.topic}' via {self.domain_cfg['domain']} "
                f"tools yielded no results."
            )
        else:
            # Try LLM synthesis
            finding_text = self._llm_synthesize() or self._rule_synthesize()

        self.state.findings.append(finding_text)
        self.bus.finding(self.agent_name, finding_text, confidence=0.75,
                          sources=tools_used)

    def _rule_synthesize(self) -> str:
        tools = ", ".join(self.state.tools_done)
        snippets = []
        for tool, out in list(self.results.items())[:2]:
            summary = self._summarize_output(tool, out)
            snippets.append(summary)
        detail = " | ".join(snippets) if snippets else "data retrieved"
        return (
            f"[{self.domain_cfg['domain'].upper()}] Investigated '{self.topic}' "
            f"using {tools}. Key result: {detail}."
        )

    def _llm_synthesize(self) -> Optional[str]:
        if not LLM_AVAILABLE:
            return None
        try:
            client = get_llm_client(agent_name=self.agent_name)
            summaries = "\n".join(
                f"- {tool}: {self._summarize_output(tool, out)}"
                for tool, out in self.results.items()
            )
            prompt = (
                f"You are a {self.domain_cfg['focus']} scientist named {self.agent_name}.\n"
                f"Topic under investigation: {self.topic}\n\n"
                f"Tool results:\n{summaries}\n\n"
                f"Write one concise scientific finding (2-3 sentences, specific and quantitative "
                f"where possible). Do not use generic language."
            )
            response = client.call(prompt, max_tokens=200, timeout=30)
            return response.strip() if response else None
        except Exception:
            return None


# ---------------------------------------------------------------------------
# LiveCollaborationSession
# ---------------------------------------------------------------------------

class LiveCollaborationSession:
    """
    Orchestrates a live multi-agent collaborative investigation.

    1.  Spawns N AgentWorker threads (one per domain)
    2.  All share a MessageBus — findings appear in real-time
    3.  Each agent reacts to peer findings (challenge / agree)
    4.  Returns consolidated results when all agents finish
    """

    def __init__(
        self,
        topic: str,
        n_agents: int = 3,
        output_dir: Optional[str] = None,
        session_id: Optional[str] = None,
        scienceclaw_dir: Optional[Path] = None,
        timeout_per_tool: int = 45,
        events_file: Optional[str] = None,
    ):
        self.topic = topic
        self.n_agents = min(n_agents, len(AGENT_DOMAINS))
        self.output_dir = Path(output_dir or f"./collab_{int(time.time())}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or f"live-{int(time.time())}"
        self.scienceclaw_dir = scienceclaw_dir or Path(__file__).parent.parent
        self.timeout_per_tool = timeout_per_tool
        self.events_file = Path(events_file) if events_file else None

        self.bus = MessageBus()
        self.workers: List[AgentWorker] = []
        self.states: Dict[str, AgentState] = {}

    def _start_event_writer(self):
        """Subscribe to the bus and write every message as JSONL to events_file."""
        if not self.events_file:
            return
        self.events_file.parent.mkdir(parents=True, exist_ok=True)
        q = self.bus.subscribe()

        def _writer():
            import dataclasses
            with open(self.events_file, "a", buffering=1) as f:
                while True:
                    try:
                        msg = q.get(timeout=1.0)
                    except Exception:
                        continue
                    row = {
                        "type": msg.type.value,
                        "agent": msg.agent,
                        "payload": msg.payload,
                        "timestamp": msg.timestamp,
                        "ref_agent": msg.ref_agent,
                    }
                    f.write(json.dumps(row) + "\n")
                    if msg.type.value == "SessionDone":
                        break

        t = threading.Thread(target=_writer, daemon=True, name="event-writer")
        t.start()

    def build_agents(self) -> List[AgentWorker]:
        """Instantiate AgentWorker threads for the first N domains."""
        workers = []
        # Shared peer queue: all Finding messages flow here
        peer_queue: queue.Queue = self.bus.subscribe()

        for i, domain_cfg in enumerate(AGENT_DOMAINS[:self.n_agents]):
            name = f"Agent{domain_cfg['suffix']}"
            state = AgentState(
                name=name,
                domain=domain_cfg["domain"],
                color=domain_cfg["color"],
            )
            self.states[name] = state
            worker = AgentWorker(
                name=name,
                domain_cfg=domain_cfg,
                topic=self.topic,
                bus=self.bus,
                state=state,
                output_dir=self.output_dir,
                peer_queue=peer_queue,
                scienceclaw_dir=self.scienceclaw_dir,
                timeout_per_tool=self.timeout_per_tool,
            )
            workers.append(worker)
        self.workers = workers
        return workers

    def run(self, dashboard=True) -> Dict[str, Any]:
        """
        Run the session.

        Args:
            dashboard: If True, render a Rich live dashboard in terminal.
                       If False, run silently (useful for testing).

        Returns:
            Results dict with findings, figures, consensus.
        """
        self.build_agents()
        self._start_event_writer()

        # Emit session start event so clients know the agents and topic
        self.bus.publish(Message(
            type=MsgType.AGENT_STATUS,
            agent="orchestrator",
            payload={
                "status": "session_start",
                "detail": self.topic,
                "session_id": self.session_id,
                "agents": list(self.states.keys()),
                "n_agents": self.n_agents,
            }
        ))

        if dashboard:
            from collaboration.dashboard import LiveDashboard
            db = LiveDashboard(
                topic=self.topic,
                states=self.states,
                bus=self.bus,
            )
            # Dashboard runs in its own thread
            dash_thread = threading.Thread(target=db.run, daemon=True)
            dash_thread.start()

        # Start all agent workers
        for worker in self.workers:
            worker.start()

        # Wait for all agents to finish
        for worker in self.workers:
            worker.join(timeout=600)   # 10 min max per agent

        # Signal dashboard to stop
        self.bus.session_done()
        if dashboard:
            time.sleep(1)   # let dashboard render final frame

        return self._collect_results()

    def _collect_results(self) -> Dict[str, Any]:
        findings = [m.payload for m in self.bus.findings()]
        figures = [m.payload for m in self.bus.figures()]
        challenges = [
            m for m in self.bus.history([MsgType.CHALLENGE])
        ]
        agreements = [
            m for m in self.bus.history([MsgType.AGREEMENT])
        ]

        # Save summary JSON
        summary = {
            "session_id": self.session_id,
            "topic": self.topic,
            "agents": list(self.states.keys()),
            "findings": findings,
            "figures": figures,
            "challenges": len(challenges),
            "agreements": len(agreements),
            "output_dir": str(self.output_dir),
        }
        summary_path = self.output_dir / "session_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2))

        return summary
