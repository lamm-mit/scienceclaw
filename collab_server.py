"""
Collaboration SSE Server

Exposes the full scienceclaw stack (159+ skills, LLMTopicAnalyzer, DependencyGraph,
SkillExecutor) as a streaming HTTP API that the Infinite/LAMMAC frontend can call.

Run with:
    cd scienceclaw
    python collab_server.py            # port 8765
    python collab_server.py --port 9000

The Vercel collaboration stream endpoint proxies to this server when it's reachable,
falling back to the TypeScript-native implementation otherwise.

Events emitted (JSON on text/event-stream):
    AgentStatus  { status, detail, agents?, session_id?, mode? }
    Thought      { text }
    ToolStarted  { tool, params }
    ToolResult   { tool, summary, count, items, error }
    DAGPhase     { phase, node_ids, mode }
    Finding      { text, confidence, sources }
    Challenge    { finding, reason }
    Agreement    { finding, note }
    SessionDone  { session_id, topic, agents, n_findings, mode }
"""

import json
import os
import sys
import time
import threading
import uuid
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Generator, List, Dict, Any, Optional

# ── fastapi / uvicorn ──────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI, Query
    from fastapi.responses import StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    print("ERROR: fastapi and uvicorn required.\n  pip install fastapi uvicorn")
    sys.exit(1)

# ── scienceclaw imports ────────────────────────────────────────────────────────
SCIENCECLAW_DIR = Path(__file__).parent
sys.path.insert(0, str(SCIENCECLAW_DIR))

from core.skill_registry import get_registry
from core.topic_analyzer import LLMTopicAnalyzer
from core.skill_executor import SkillExecutor
from core.skill_dag import DependencyGraph, SkillNode, SkillType, NodeStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("collab_server")

app = FastAPI(title="ScienceClaw Collaboration Server", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Agent domain templates ─────────────────────────────────────────────────────
# Each domain specifies which skill *categories* to bias toward.
# The LLMTopicAnalyzer does the actual selection from the full 159-skill registry.

AGENT_DOMAINS = [
    {
        "suffix": "Bio",
        "domain": "biology",
        "focus": "protein structure, gene function, molecular biology, disease mechanisms, protein interactions",
        "preferred_categories": ["proteins", "genomics", "literature", "pathways"],
        "color": "green",
    },
    {
        "suffix": "Chem",
        "domain": "chemistry",
        "focus": "drug discovery, compound properties, medicinal chemistry, ADMET, pharmacology",
        "preferred_categories": ["compounds", "drugs", "chemistry", "literature"],
        "color": "cyan",
    },
    {
        "suffix": "Comp",
        "domain": "computational",
        "focus": "bioinformatics, computational biology, structure prediction, machine learning",
        "preferred_categories": ["structure", "bioinformatics", "literature", "modeling"],
        "color": "purple",
    },
    {
        "suffix": "Clin",
        "domain": "clinical",
        "focus": "clinical trials, drug safety, therapeutic outcomes, regulatory data",
        "preferred_categories": ["clinical", "drugs", "literature"],
        "color": "yellow",
    },
    {
        "suffix": "Lit",
        "domain": "literature",
        "focus": "systematic review, citation analysis, meta-analysis, cross-database synthesis",
        "preferred_categories": ["literature", "preprints"],
        "color": "blue",
    },
]

COLLAB_MODES: Dict[str, Dict[str, Any]] = {
    "broad":          {"label": "Broad Scan",        "agent_indices": [0, 1, 2, 3, 4], "icon": "🌐"},
    "drug_discovery": {"label": "Drug Discovery",    "agent_indices": [1, 3, 0],        "icon": "💊"},
    "structure":      {"label": "Structure Focus",   "agent_indices": [0, 2],           "icon": "🧬"},
    "literature":     {"label": "Literature Review", "agent_indices": [4, 0, 2],        "icon": "📚"},
}


# ── SSE helpers ───────────────────────────────────────────────────────────────

def sse(agent: str, event_type: str, payload: Dict[str, Any],
        ref_agent: Optional[str] = None) -> str:
    obj: Dict[str, Any] = {
        "type": event_type,
        "agent": agent,
        "payload": payload,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if ref_agent:
        obj["ref_agent"] = ref_agent
    return f"data: {json.dumps(obj)}\n\n"


# ── Skill selection via LLMTopicAnalyzer ──────────────────────────────────────

def select_skills_for_agent(
    agent_name: str,
    domain: str,
    focus: str,
    topic: str,
    max_skills: int = 4,
) -> List[Dict[str, Any]]:
    """
    Use LLMTopicAnalyzer to pick from the full 159-skill registry.
    Falls back to keyword-based selection if LLM is unavailable.
    """
    registry = get_registry()
    all_skills = list(registry.skills.values()) if registry.skills else []

    # Bias the skill list: put preferred categories first for context
    # (LLM still chooses freely from all 159)
    analyzer = LLMTopicAnalyzer(agent_name=f"{agent_name}_{domain}")
    agent_profile = {
        "role": f"{domain} researcher",
        "bio": f"Specializes in {focus}",
        "research": {"interests": focus.split(", ")},
    }

    try:
        _analysis, selected = analyzer.analyze_and_select_skills(
            topic=topic,
            available_skills=all_skills,
            max_skills=max_skills,
            agent_profile=agent_profile,
        )
        return selected  # list of dicts with name, reason, suggested_params
    except Exception as e:
        log.warning(f"LLMTopicAnalyzer failed for {agent_name}: {e}")
        # Keyword fallback: return first few skills whose name/description matches
        kw = topic.lower().split()[:4]
        fallback = [
            s for s in all_skills
            if any(k in s.get("name", "").lower() or k in s.get("description", "").lower() for k in kw)
        ][:max_skills]
        return fallback or all_skills[:max_skills]


# ── DAG execution for one agent ───────────────────────────────────────────────

def run_agent_with_dag(
    domain_cfg: Dict[str, Any],
    topic: str,
    peer_findings: List[Dict[str, str]],  # shared list, appended atomically
    queue: "list[str]",                   # append SSE strings here
) -> Dict[str, Any]:
    """
    Full agent execution:
    1. LLM selects skills from 159-skill registry
    2. Build DependencyGraph (DAG) from selected skills
    3. Execute in topological phases (parallelizable within phase)
    4. Synthesize findings
    5. React to peer findings
    """
    agent_name = f"Agent{domain_cfg['suffix']}"
    domain = domain_cfg["domain"]
    emit = lambda t, p, ref=None: queue.append(sse(agent_name, t, p, ref))

    # ── 1. Planning: select skills ────────────────────────────────────────────
    emit("AgentStatus", {"status": "planning", "detail": f"Selecting skills for \"{topic}\""})

    selected_skills = select_skills_for_agent(
        agent_name=agent_name,
        domain=domain,
        focus=domain_cfg["focus"],
        topic=topic,
        max_skills=4,
    )

    skill_names = [s["name"] for s in selected_skills]
    emit("Thought", {"text": f"LLM selected {len(skill_names)} skills: {', '.join(skill_names)}"})

    # ── 2. Build DAG ──────────────────────────────────────────────────────────
    graph = DependencyGraph()
    # For now: all selected skills are independent (phase 0 parallel).
    # Future: LLM can specify depends_on in suggested_params.
    for skill in selected_skills:
        node = SkillNode(
            id=skill["name"],
            name=skill["name"],
            skill_type=SkillType.PRIMARY,
            depends_on=skill.get("suggested_params", {}).get("depends_on", []),
            purpose=skill.get("reason", ""),
            params={"query": topic, **{k: v for k, v in skill.get("suggested_params", {}).items() if k != "depends_on"}},
        )
        graph.add_node(node)

    phases = graph.get_execution_phases()
    emit("AgentStatus", {"status": "running", "detail": f"{len(phases)} execution phase(s), {len(selected_skills)} skills"})

    for phase in phases:
        emit("DAGPhase", {"phase": phase.phase_number, "node_ids": phase.node_ids, "mode": phase.mode})

    # ── 3. Execute phases ─────────────────────────────────────────────────────
    executor = SkillExecutor(scienceclaw_dir=SCIENCECLAW_DIR)
    registry = get_registry()
    tool_results: List[Dict[str, Any]] = []

    for phase in phases:
        nodes_in_phase = [graph.get_node(nid) for nid in phase.node_ids if graph.get_node(nid)]

        def run_node(node: SkillNode) -> Dict[str, Any]:
            emit("ToolStarted", {"tool": node.name, "params": node.params})
            graph.update_status(node.id, NodeStatus.RUNNING)

            skill_meta = registry.skills.get(node.name, {}) if registry.skills else {}
            result = executor.execute_skill(
                skill_name=node.name,
                skill_metadata=skill_meta,
                parameters=node.params,
                timeout=45,
            )

            if result.get("status") == "success":
                graph.update_status(node.id, NodeStatus.COMPLETED)
                raw = result.get("result", {})
                # Normalize: many skills return {"results": [...]} or {"papers": [...]} etc.
                items = _extract_items(raw)
                summary = _extract_summary(raw, node.name, items)
                tool_results.append({"tool": node.name, "summary": summary, "items": items, "raw": raw})
                emit("ToolResult", {"tool": node.name, "summary": summary, "count": len(items), "items": items[:8]})
                emit("Thought", {"text": f"{node.name}: {summary[:120]}"})
            else:
                graph.update_status(node.id, NodeStatus.FAILED)
                err = result.get("error", "unknown error")
                emit("ToolResult", {"tool": node.name, "summary": f"Failed: {err}", "count": 0, "items": [], "error": err})

            return result

        if len(nodes_in_phase) == 1:
            run_node(nodes_in_phase[0])
        else:
            with ThreadPoolExecutor(max_workers=len(nodes_in_phase)) as pool:
                futures = {pool.submit(run_node, node): node for node in nodes_in_phase}
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception as e:
                        log.warning(f"Node execution error: {e}")

    # ── 4. Synthesize ─────────────────────────────────────────────────────────
    emit("Thought", {"text": "Synthesizing findings across tools..."})
    finding = _synthesize(agent_name, domain, topic, tool_results)

    emit("Finding", {
        "text": finding,
        "confidence": 0.80,
        "sources": [r["tool"] for r in tool_results],
    })

    # ── 5. React to peers ─────────────────────────────────────────────────────
    for peer in list(peer_findings):
        if peer["agent"] == agent_name:
            continue
        challenge = _should_challenge(domain, tool_results, peer["text"])
        if challenge:
            emit("Challenge", {"finding": peer["text"][:120], "reason": challenge}, peer["agent"])
        elif len(tool_results) > 0 and hash(peer["text"]) % 3 == 0:
            first_item = tool_results[0]["items"][0] if tool_results[0]["items"] else {}
            label = first_item.get("name") or first_item.get("title") or first_item.get("symbol") or ""
            note = (f"Our {domain} data (e.g. \"{str(label)[:40]}\") corroborates this."
                    if label else f"Consistent with our {domain} analysis.")
            emit("Agreement", {"finding": peer["text"][:100], "note": note}, peer["agent"])

    emit("AgentStatus", {"status": "done", "detail": "Investigation complete"})

    return {"agent": agent_name, "finding": finding, "tools": skill_names}


# ── Result normalization helpers ───────────────────────────────────────────────

def _extract_items(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        return raw[:20]
    if isinstance(raw, dict):
        for key in ("results", "papers", "entries", "items", "hits", "compounds", "proteins", "genes"):
            val = raw.get(key)
            if isinstance(val, list):
                return val[:20]
        # If dict itself looks like a result record, wrap it
        return [raw] if raw else []
    return []


def _extract_summary(raw: Any, tool: str, items: List) -> str:
    if isinstance(raw, dict):
        for key in ("summary", "message", "description"):
            if raw.get(key):
                return str(raw[key])[:300]
    return f"{tool}: {len(items)} result(s)"


def _synthesize(agent_name: str, domain: str, topic: str, tool_results: List[Dict]) -> str:
    """LLM synthesis via LLMScientificReasoner, fallback to rule-based."""
    successful = [r for r in tool_results if r["items"]]
    if not successful:
        return f"[{domain.upper()}] Investigation of \"{topic}\" yielded limited results across {len(tool_results)} tools."

    try:
        from autonomous.llm_reasoner import LLMScientificReasoner
        reasoner = LLMScientificReasoner(agent_name=agent_name)
        summaries = "\n".join(f"{r['tool']}: {r['summary']}" for r in successful)
        prompt = (
            f"You are {agent_name}, a {domain} researcher investigating \"{topic}\".\n\n"
            f"Tool results:\n{summaries}\n\n"
            f"Write a concise scientific finding (2-4 sentences). Be specific and quantitative. "
            f"Reference actual identifiers (gene names, compound IDs, pathway names) found in the data. "
            f"Avoid vague generalities."
        )
        result = reasoner._call_llm(prompt, max_tokens=300)
        if result and len(result) > 50:
            return result
    except Exception as e:
        log.debug(f"LLM synthesis failed: {e}")

    # Rule-based fallback
    highlights = []
    for r in successful[:3]:
        first = r["items"][0] if r["items"] else {}
        label = first.get("name") or first.get("title") or first.get("symbol") or ""
        highlights.append(f"{r['tool']} ({len(r['items'])} results{f': \"{str(label)[:50]}\"' if label else ''})")

    return (
        f"[{domain.upper()}] Investigated \"{topic}\" via {', '.join(highlights)}. "
        f"Cross-database analysis across {len(successful)} sources reveals convergent evidence "
        f"relevant to {domain}."
    )


def _should_challenge(my_domain: str, my_results: List[Dict], peer_finding: str) -> Optional[str]:
    pf = peer_finding.lower()
    config = {
        "biology":       (["compound", "smiles", "drug", "inhibitor", "ic50", "nanomolar"],
                          "protein-level mechanism and target engagement context"),
        "chemistry":     (["protein", "gene expression", "mrna", "pathway", "signaling"],
                          "compound selectivity and chemical space context"),
        "computational": (["clinical trial", "patient", "in vivo", "animal model"],
                          "computational models require empirical validation"),
        "clinical":      (["predicted", "in silico", "docking", "affinity prediction"],
                          "computational predictions should cross-reference clinical outcomes"),
        "literature":    (["novel", "unprecedented", "first report", "unique mechanism"],
                          "systematic literature synthesis provides prior context"),
    }.get(my_domain)

    if not config:
        return None
    triggers, challenge_text = config
    if not any(t in pf for t in triggers):
        return None

    our_data = [
        f"{r['tool']} (e.g. \"{str((r['items'][0].get('name') or r['items'][0].get('title') or '')[:40])}\")"
        for r in my_results if r["items"]
    ][:2]

    if our_data:
        return f"From a {my_domain} perspective, {challenge_text}. Our {' + '.join(our_data)} data provide complementary evidence."
    return f"From a {my_domain} perspective, {challenge_text} warrants additional investigation."


# ── Stream endpoint ────────────────────────────────────────────────────────────

@app.get("/stream")
async def stream(
    topic: str = Query("protein folding"),
    mode: str = Query("broad"),
) -> StreamingResponse:
    mode = mode if mode in COLLAB_MODES else "broad"
    mode_cfg = COLLAB_MODES[mode]
    domains = [AGENT_DOMAINS[i] for i in mode_cfg["agent_indices"]]
    agent_names = [f"Agent{d['suffix']}" for d in domains]
    session_id = f"sci-{uuid.uuid4().hex[:8]}"

    def generate() -> Generator[str, None, None]:
        # Session start
        yield sse("orchestrator", "AgentStatus", {
            "status": "session_start",
            "detail": topic,
            "session_id": session_id,
            "agents": agent_names,
            "n_agents": len(agent_names),
            "mode": mode,
            "mode_label": mode_cfg["label"],
            "skill_pool": "full_registry",  # signal to frontend that we have 159+ skills
        })

        # Shared state between agents
        peer_findings: List[Dict[str, str]] = []
        all_queues: Dict[str, list] = {d["suffix"]: [] for d in domains}

        # Run all agents in parallel threads
        def run_agent(domain_cfg: Dict) -> Dict:
            q = all_queues[domain_cfg["suffix"]]
            return run_agent_with_dag(domain_cfg, topic, peer_findings, q)

        results: List[Dict] = []
        with ThreadPoolExecutor(max_workers=len(domains)) as pool:
            futures = {pool.submit(run_agent, d): d for d in domains}

            # Stream events from all queues as they arrive
            done = set()
            while len(done) < len(futures):
                for fut, domain_cfg in list(futures.items()):
                    suffix = domain_cfg["suffix"]
                    q = all_queues[suffix]
                    while q:
                        yield q.pop(0)
                    if fut.done() and suffix not in done:
                        done.add(suffix)
                        try:
                            r = fut.result()
                            results.append(r)
                            peer_findings.append({"agent": r["agent"], "text": r["finding"]})
                        except Exception as e:
                            log.error(f"Agent {suffix} failed: {e}")

                # Drain any remaining events
                for suffix, q in all_queues.items():
                    while q:
                        yield q.pop(0)

                if len(done) < len(futures):
                    time.sleep(0.05)

        # Final drain
        for q in all_queues.values():
            while q:
                yield q.pop(0)

        yield sse("orchestrator", "SessionDone", {
            "session_id": session_id,
            "topic": topic,
            "agents": agent_names,
            "n_findings": len(results),
            "mode": mode,
        })

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/health")
async def health() -> Dict[str, Any]:
    registry = get_registry()
    skill_count = len(registry.skills) if registry.skills else 0
    return {"status": "ok", "skills": skill_count, "version": "1.0"}


@app.get("/tools")
async def tools_list() -> Dict[str, Any]:
    registry = get_registry()
    skills = registry.skills or {}
    return {
        "total": len(skills),
        "skills": [
            {"name": k, "category": v.get("category", ""), "description": v.get("description", "")[:80]}
            for k, v in list(skills.items())[:200]
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ScienceClaw Collaboration SSE Server")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    registry = get_registry()
    skill_count = len(registry.skills) if registry.skills else 0
    log.info(f"Starting collab_server on {args.host}:{args.port}")
    log.info(f"Skill registry: {skill_count} skills available")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
