"""
Hypothesis Validation Workflow

Orchestrates multi-agent, multi-iteration hypothesis validation.

Flow:
  1. ProposerAgent generates initial hypothesis from topic
  2. ValidatorPanel (N agents, each with own personality) scores it
  3. Comments are posted to a single Infinite thread post
  4. Loop until consensus score ≥ threshold (with max_iterations safety cap):
       - If score < threshold → refine hypothesis → re-validate
       - If score ≥ threshold → accepted; ReactingAgents run deep_investigation
  5. If safety cap reached before acceptance → reactions still run on best hypothesis
  6. All activity (drafts, verdicts, refinements, reactions) posted as comments
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


# ------------------------------------------------------------------ #
# Data structures                                                       #
# ------------------------------------------------------------------ #

@dataclass
class HypothesisIteration:
    iteration: int
    hypothesis: dict
    validator_results: list          # List[ValidationResult]
    consensus_score: float
    accepted: bool
    reactions: List[dict] = field(default_factory=list)
    post_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ------------------------------------------------------------------ #
# Workflow                                                              #
# ------------------------------------------------------------------ #

class HypothesisValidationWorkflow:
    """
    Orchestrates the full hypothesis validation loop.

    A single Infinite post is created upfront; every iteration draft,
    validator verdict, refinement, and reaction appears as a comment
    on that post so the community sees the full thinking process.
    """

    def __init__(self):
        self._client_cache: Dict[str, Any] = {}   # agent_name → InfiniteClient
        self._reasoner_cache: Dict[str, Any] = {}
        self.thread_post_id: Optional[str] = None
        self.proposer_agent: str = "ProposerAgent"  # set at run() time

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def run(
        self,
        topic: str,
        proposer_agent: str,
        validator_agents: List[dict],   # [{name, personality}]
        reacting_agents: List[dict],    # [{name, domain, tools}]
        community: str = "materials",
        max_iterations: int = 3,
        validation_threshold: float = 0.75,
        post_live: bool = True,
    ) -> dict:
        """
        Run the full hypothesis validation workflow.

        Returns dict with:
          - accepted: bool
          - final_hypothesis: dict
          - history: List[HypothesisIteration]
          - thread_post_id: str | None
          - consensus_score: float
        """
        print(f"\n{'='*60}")
        print(f"Hypothesis Validation Workflow")
        print(f"Topic: {topic}")
        print(f"Proposer: {proposer_agent}")
        print(f"Validators: {[v['name'] for v in validator_agents]}")
        print(f"Reactors: {[r['name'] for r in reacting_agents]}")
        print(f"{'='*60}\n")

        self.proposer_agent = proposer_agent
        history: List[HypothesisIteration] = []
        hypothesis = self._propose(topic, proposer_agent)
        best_hypothesis = hypothesis
        best_score = 0.0

        # Create single thread post upfront
        if post_live:
            self.thread_post_id = self._create_thread_post(topic, community, proposer_agent, validator_agents, reacting_agents)

        iteration = 0
        accepted = False

        while not accepted:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            print(f"Hypothesis: {hypothesis.get('statement', '')[:120]}")

            # Run validator panel
            validator_results = self._run_validator_panel(hypothesis, validator_agents, iteration)
            consensus_score = self._compute_consensus(validator_results, validation_threshold)

            accepted = self._should_accept(validator_results, consensus_score, validation_threshold)
            reactions = []

            # Track best so far (for safety-cap fallback)
            if consensus_score > best_score:
                best_score = consensus_score
                best_hypothesis = hypothesis

            print(f"Consensus score: {consensus_score:.2f} — {'ACCEPTED ✅' if accepted else f'needs refinement (target ≥ {validation_threshold})'}")

            # Post iteration comments
            if post_live and self.thread_post_id:
                self._comment_iteration(self.thread_post_id, iteration, hypothesis, validator_results)

            iter_record = HypothesisIteration(
                iteration=iteration,
                hypothesis=dict(hypothesis),
                validator_results=validator_results,
                consensus_score=consensus_score,
                accepted=accepted,
                post_id=self.thread_post_id,
            )

            if accepted:
                # Run reacting agents — hypothesis satisfied
                reactions = self._react(hypothesis, reacting_agents)
                iter_record.reactions = reactions

                if post_live and self.thread_post_id:
                    self._comment_reactions(self.thread_post_id, reactions)
                    self._comment_final(self.thread_post_id, hypothesis, consensus_score)

                history.append(iter_record)
                print(f"\n✅ Hypothesis satisfied at iteration {iteration}!")
                break

            history.append(iter_record)

            if iteration >= max_iterations:
                # Safety cap reached — run reactions on best hypothesis anyway
                print(f"\n⚠ Safety cap ({max_iterations} iterations) reached at score={best_score:.2f}.")
                print(f"  Running reactions on best hypothesis and posting final summary.")
                hypothesis = best_hypothesis
                reactions = self._react(hypothesis, reacting_agents)
                history[-1].reactions = reactions

                if post_live and self.thread_post_id:
                    self._comment_reactions(self.thread_post_id, reactions)
                    self._comment_final(self.thread_post_id, hypothesis, best_score)
                break

            # Refine and loop again
            hypothesis = self._refine(hypothesis, validator_results, reactions)
            if post_live and self.thread_post_id:
                self._comment_refinement(self.thread_post_id, iteration, hypothesis)

        final = history[-1].hypothesis if history else hypothesis
        final_score = history[-1].consensus_score if history else 0.0
        final_accepted = history[-1].accepted if history else False

        return {
            "accepted": final_accepted,
            "final_hypothesis": final,
            "history": history,
            "thread_post_id": self.thread_post_id,
            "consensus_score": final_score,
        }

    # ------------------------------------------------------------------ #
    # Proposal                                                             #
    # ------------------------------------------------------------------ #

    def _propose(self, topic: str, agent_name: str) -> dict:
        """Generate initial hypothesis from topic using LLM."""
        print(f"[{agent_name}] Generating initial hypothesis for: {topic}")
        try:
            reasoner = self._get_reasoner(agent_name)
            prompt = f"""You are {agent_name}, a scientific researcher proposing a testable hypothesis.

Topic: {topic}

Generate a specific, testable scientific hypothesis in this EXACT format:
STATEMENT: <one sentence mechanistic hypothesis>
PLANNED_TOOLS: pubmed, materials, rdkit
SUCCESS_CRITERIA: <measurable outcome that would confirm or refute the hypothesis>
RATIONALE: <2-3 sentences of scientific reasoning>
"""
            response = reasoner._call_llm(prompt, max_tokens=400)
            return self._parse_hypothesis(response, topic)
        except Exception as e:
            print(f"  LLM unavailable ({e}), using fallback hypothesis")
            return self._fallback_hypothesis(topic)

    def _parse_hypothesis(self, response: str, topic: str) -> dict:
        data = {}
        for line in response.strip().splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                data[key.strip().upper()] = val.strip()

        statement = data.get("STATEMENT", f"Investigation of {topic}")
        tools_raw = data.get("PLANNED_TOOLS", "pubmed")
        planned_tools = [t.strip() for t in tools_raw.split(",") if t.strip()]
        success_criteria = data.get("SUCCESS_CRITERIA", "Measurable improvement observed")
        rationale = data.get("RATIONALE", "")

        return {
            "statement": statement,
            "planned_tools": planned_tools,
            "success_criteria": success_criteria,
            "rationale": rationale,
            "topic": topic,
            "iteration_history": [],
        }

    def _fallback_hypothesis(self, topic: str) -> dict:
        """Rule-based fallback when LLM is unavailable."""
        try:
            from reasoning.hypothesis_generator import HypothesisGenerator
            gen = HypothesisGenerator()
            gap = {"description": topic, "type": "knowledge_gap", "topic": topic}
            hyps = gen.generate_hypotheses([gap])
            if hyps:
                h = hyps[0]
                return {
                    "statement": h.get("statement", f"Investigating {topic}"),
                    "planned_tools": h.get("planned_tools", ["pubmed"]),
                    "success_criteria": h.get("success_criteria", "Positive correlation observed"),
                    "rationale": "",
                    "topic": topic,
                    "iteration_history": [],
                }
        except Exception:
            pass
        return {
            "statement": f"Systematic investigation of {topic} will reveal key mechanistic drivers.",
            "planned_tools": ["pubmed", "materials"],
            "success_criteria": "At least 3 quantitative metrics identified from literature.",
            "rationale": "",
            "topic": topic,
            "iteration_history": [],
        }

    # ------------------------------------------------------------------ #
    # Validator panel                                                      #
    # ------------------------------------------------------------------ #

    def _run_validator_panel(self, hypothesis: dict, validator_agents: List[dict], iteration: int) -> list:
        """Run all validators and return their results."""
        from reasoning.hypothesis_validator import HypothesisValidator

        results = []
        for v_config in validator_agents:
            name = v_config["name"]
            personality = v_config.get("personality", "skeptic")
            print(f"  [{name} / {personality}] validating...")
            validator = HypothesisValidator(agent_name=name, personality=personality)
            result = validator.validate(hypothesis, iteration=iteration)
            print(f"    score={result.score:.2f}: {result.critique[:80]}")
            results.append(result)
        return results

    def _compute_consensus(self, results: list, threshold: float) -> float:
        if not results:
            return 0.0
        return sum(r.score for r in results) / len(results)

    def _should_accept(self, results: list, consensus_score: float, threshold: float) -> bool:
        """
        Accept if:
        - consensus_score >= threshold AND no validator scored < 0.5
        OR
        - any single validator scored >= threshold AND no validator scored < 0.5
        """
        if not results:
            return False
        min_score = min(r.score for r in results)
        if min_score < 0.5:
            return False
        if consensus_score >= threshold:
            return True
        if any(r.score >= threshold for r in results):
            return True
        return False

    # ------------------------------------------------------------------ #
    # Refinement                                                           #
    # ------------------------------------------------------------------ #

    def _refine(self, hypothesis: dict, panel_results: list, reactions: list) -> dict:
        """
        Use LLM to produce a meaningfully improved hypothesis.

        The prompt explicitly shows:
        - Current score vs threshold gap (so the LLM knows how much improvement is needed)
        - Per-validator breakdown (which personality flagged which weakness)
        - Concrete tool suggestions per validator
        - Full iteration history (so the LLM doesn't repeat already-tried phrasings)
        - Specific instructions to add quantitative specifics that the weakest scorer flagged
        """
        proposer = self.proposer_agent
        current_score = sum(r.score for r in panel_results) / len(panel_results) if panel_results else 0.0
        threshold = 0.75  # matches workflow default; passed via panel_results context

        # Per-validator breakdown sorted weakest-first so the LLM addresses the biggest blockers
        sorted_results = sorted(panel_results, key=lambda r: r.score)
        validator_breakdown = "\n".join(
            f"  [{r.validator_agent} / {r.personality}] score={r.score:.2f}\n"
            f"    Critique: {r.critique}\n"
            f"    Suggested tools: {', '.join(r.refined_tools) or 'none'}\n"
            f"    Suggested criteria: {r.refined_success_criteria or '(none)'}\n"
            f"    Missing capabilities: {', '.join(r.missing_capabilities) or 'none'}"
            for r in sorted_results
        )

        # All suggested tools, deduped, ordered by frequency (most-cited first)
        from collections import Counter
        tool_counts = Counter(t for r in panel_results for t in r.refined_tools)
        suggested_tools = [t for t, _ in tool_counts.most_common()]

        # Prior attempts so the LLM can avoid cycling
        prior_attempts = hypothesis.get("iteration_history", [])
        prior_text = ""
        if prior_attempts:
            prior_text = "\nPREVIOUS ATTEMPTS (do NOT repeat these phrasings):\n" + "\n".join(
                f"  Attempt {i+1}: {a.get('statement', '')[:120]}"
                for i, a in enumerate(prior_attempts)
            )

        # Weakest validator's criteria suggestion (most important fix)
        weakest = sorted_results[0] if sorted_results else None
        priority_fix = ""
        if weakest and weakest.score < 0.6:
            priority_fix = (
                f"\nPRIORITY FIX (from {weakest.validator_agent}, score={weakest.score:.2f}):\n"
                f"  {weakest.critique}\n"
                f"  This validator is your biggest blocker — address this first."
            )

        prompt = f"""You are a scientific proposer refining a hypothesis to satisfy a validator panel.

CURRENT SCORE: {current_score:.2f} (target ≥ {threshold})
SCORE GAP: {threshold - current_score:.2f} — you must produce a meaningfully better hypothesis.

CURRENT HYPOTHESIS
  Statement: {hypothesis.get('statement', '')}
  Planned tools: {', '.join(hypothesis.get('planned_tools', []))}
  Success criteria: {hypothesis.get('success_criteria', '')}

VALIDATOR PANEL FEEDBACK (weakest first):
{validator_breakdown}
{priority_fix}
TOOLS SUGGESTED BY VALIDATORS (most-cited first): {', '.join(suggested_tools) or 'none'}
{prior_text}

INSTRUCTIONS:
1. Address every critique above — do not leave any weakness unresolved.
2. Make the statement specific and mechanistic: include molecule names, doping percentages,
   temperature ranges, crystal planes, or other quantitative details relevant to the topic.
3. Choose planned_tools that can actually produce data for your success_criteria
   (prefer tools from the validators' suggestions above).
4. Make success_criteria fully measurable: specify a numeric threshold, unit, and method.
5. Do NOT repeat any previous attempt's phrasing.

Respond in this EXACT format (no extra text):
STATEMENT: <specific, mechanistic, quantitative one-sentence hypothesis>
PLANNED_TOOLS: tool1, tool2, tool3
SUCCESS_CRITERIA: <measurable outcome with numeric threshold and method>
RATIONALE: <2-3 sentences explaining exactly how this addresses the validators' critiques>
"""
        try:
            reasoner = self._get_reasoner(proposer)
            response = reasoner._call_llm(prompt, max_tokens=500)
            new_h = self._parse_hypothesis(response, hypothesis.get("topic", ""))
        except Exception as e:
            print(f"  Refinement LLM failed ({e}), applying validator suggestions directly")
            new_h = {
                "statement": hypothesis.get("statement", ""),
                "planned_tools": suggested_tools or hypothesis.get("planned_tools", ["pubmed"]),
                "success_criteria": (
                    weakest.refined_success_criteria if weakest and weakest.refined_success_criteria
                    else hypothesis.get("success_criteria", "")
                ),
                "rationale": "Fallback: merged validator tool suggestions.",
                "topic": hypothesis.get("topic", ""),
            }

        # Carry forward iteration history
        prior = list(hypothesis.get("iteration_history", []))
        prior.append({
            "statement": hypothesis.get("statement", ""),
            "planned_tools": hypothesis.get("planned_tools", []),
            "success_criteria": hypothesis.get("success_criteria", ""),
            "score": current_score,
        })
        new_h["iteration_history"] = prior
        new_h["topic"] = hypothesis.get("topic", "")
        return new_h

    # ------------------------------------------------------------------ #
    # Reactions                                                            #
    # ------------------------------------------------------------------ #

    def _react(self, hypothesis: dict, reacting_agents: List[dict]) -> List[dict]:
        """Each reacting agent runs deep_investigation on the accepted hypothesis."""
        from autonomous.deep_investigation import run_deep_investigation

        reactions = []
        topic = hypothesis.get("statement", hypothesis.get("topic", "research topic"))
        for agent_config in reacting_agents:
            name = agent_config["name"]
            domain = agent_config.get("domain", "science")
            print(f"  [{name}] running deep investigation (domain={domain})...")
            try:
                content = run_deep_investigation(
                    agent_name=name,
                    topic=topic,
                    community=domain,
                    agent_profile=agent_config,
                )
                reactions.append({"agent": name, "domain": domain, "content": content})
            except Exception as e:
                reactions.append({"agent": name, "domain": domain, "content": f"Investigation error: {e}"})
        return reactions

    # ------------------------------------------------------------------ #
    # Infinite posting                                                     #
    # ------------------------------------------------------------------ #

    def _client_for(self, agent_name: str):
        """Return an InfiniteClient authenticated as agent_name, cached per agent."""
        if agent_name not in self._client_cache:
            try:
                from skills.infinite.scripts.infinite_client import InfiniteClient
                from pathlib import Path
                config_path = Path.home() / ".scienceclaw" / "agents" / f"{agent_name}_config.json"
                if config_path.exists():
                    client = InfiniteClient(config_file=config_path)
                else:
                    # Fall back to default config if agent not individually registered
                    print(f"  [{agent_name}] no dedicated config found, using default credentials")
                    client = InfiniteClient()
                self._client_cache[agent_name] = client
            except Exception as e:
                print(f"  InfiniteClient unavailable for {agent_name}: {e}")
                self._client_cache[agent_name] = None
        return self._client_cache[agent_name]

    def _create_thread_post(
        self,
        topic: str,
        community: str,
        proposer: str,
        validators: List[dict],
        reactors: List[dict],
    ) -> Optional[str]:
        """Proposer opens the thread with their initial thinking on the topic."""
        client = self._client_for(proposer)
        if not client:
            return None

        # Ask the LLM to write a natural opening post instead of a templated one
        try:
            reasoner = self._get_reasoner(proposer)
            others = [v["name"] for v in validators] + [r["name"] for r in reactors]
            prompt = f"""You are {proposer}, an autonomous science agent starting a research thread.

Topic you're investigating: {topic}

Write a short, natural opening post for the community — like a scientist sharing what they're
thinking about and inviting colleagues to weigh in. Mention that {', '.join(others)} will be
joining the discussion. Keep it conversational, 3-5 sentences, no bullet points or headers.
Just write the post body (no title).
"""
            body = reasoner._call_llm(prompt, max_tokens=400).strip()
        except Exception as e:
            print(f"  [{proposer}] could not generate opening post: {e}")
            return None

        try:
            result = client.create_post(
                community=community,
                title=topic,
                content=body,
            )
            post_id = result.get("id") or result.get("post", {}).get("id")
            if post_id:
                print(f"  [{proposer}] opened thread: {post_id}")
            return post_id
        except Exception as e:
            print(f"  Could not open thread: {e}")
            return None

    def _comment_iteration(self, post_id: str, iteration: int, hypothesis: dict, validator_results: list) -> None:
        """Proposer shares their current thinking; each validator replies in their own voice."""
        proposer = self.proposer_agent

        # Proposer's comment — their current best thinking, not a form
        proposer_client = self._client_for(proposer)
        if proposer_client:
            statement = hypothesis.get("statement", "")
            tools = ", ".join(hypothesis.get("planned_tools", []))
            criteria = hypothesis.get("success_criteria", "")
            try:
                reasoner = self._get_reasoner(proposer)
                prompt = f"""You are {proposer}. Write a short, natural comment sharing your current thinking.

Your hypothesis: {statement}
Tools you plan to use: {tools}
What you'd consider a clear result: {criteria}

2-4 sentences, scientist-to-scientist tone. No headers, no bullet points.
"""
                proposer_text = reasoner._call_llm(prompt, max_tokens=400).strip()
                self._agent_comment(post_id, proposer, proposer_text)
            except Exception as e:
                print(f"  [{proposer}] could not generate iteration comment: {e}")

        # Each validator replies as themselves
        for vr in validator_results:
            client = self._client_for(vr.validator_agent)
            if not client:
                continue
            try:
                reasoner = self._get_reasoner(vr.validator_agent)
                prompt = f"""You are {vr.validator_agent}, a {vr.personality} scientist reviewing a colleague's hypothesis.

Their hypothesis: {hypothesis.get('statement', '')}
Your internal assessment (score {vr.score:.2f}/1.0): {vr.critique}
Better tools you'd suggest: {', '.join(vr.refined_tools) or 'none'}

Write a natural, direct comment as yourself — push back where needed, suggest what's missing.
2-4 sentences. No score numbers, no structured fields, just your honest scientific take.
"""
                comment_text = reasoner._call_llm(prompt, max_tokens=400).strip()
                self._agent_comment(post_id, vr.validator_agent, comment_text)
            except Exception as e:
                print(f"  [{vr.validator_agent}] could not generate comment: {e}")

    def _comment_refinement(self, post_id: str, iteration: int, hypothesis: dict) -> None:
        """Proposer replies with their updated thinking after feedback."""
        proposer = self.proposer_agent
        client = self._client_for(proposer)
        if not client:
            return
        try:
            reasoner = self._get_reasoner(proposer)
            prompt = f"""You are {proposer}. You've just updated your hypothesis based on feedback from colleagues.

Updated hypothesis: {hypothesis.get('statement', '')}
Updated tools: {', '.join(hypothesis.get('planned_tools', []))}
Updated criteria: {hypothesis.get('success_criteria', '')}

Write a short reply saying what you changed and why, in natural scientist language.
2-3 sentences. No headers or bullet points.
"""
            text = reasoner._call_llm(prompt, max_tokens=400).strip()
            self._agent_comment(post_id, proposer, text)
        except Exception as e:
            print(f"  [{proposer}] could not generate refinement comment: {e}")

    def _comment_reactions(self, post_id: str, reactions: List[dict]) -> None:
        """Each reacting agent posts a structured investigation comment and uploads figures."""
        for r in reactions:
            agent = r["agent"]
            raw = r.get("content")
            if not raw:
                continue

            # ── Format a clean, structured comment ──────────────────────────
            try:
                reasoner = self._get_reasoner(agent)
                prompt = f"""You are {agent}, a scientific agent who just completed an investigation.
Below is the raw output of your investigation. Rewrite it as a clean, readable comment for a
scientific community thread. Use these sections (in order, using plain headers like "## Tools Used"):

## Tools Used
## Key Findings
## Mechanistic Insight
## Open Questions

Be specific and quantitative. Omit empty sections. Keep total length under 500 words.
No meta-commentary about "the investigation" — just the science.

RAW INVESTIGATION OUTPUT:
{str(raw)[:3000]}
"""
                comment_text = reasoner._call_llm(prompt, max_tokens=700).strip()
            except Exception as e:
                print(f"  [{agent}] could not format reaction comment: {e}")
                continue

            if comment_text:
                self._agent_comment(post_id, agent, comment_text)

            # ── Collect figures for batch upload by the post owner ───────────
            figure_paths = []
            if isinstance(raw, dict):
                figure_paths = raw.get("figures", [])
            if figure_paths:
                self._upload_figures_to_post(post_id, self.proposer_agent, figure_paths, label=agent)

    def _upload_figures_to_post(self, post_id: str, agent_name: str, figure_paths: list, label: str = "") -> None:
        """Convert PNG files to SVG wrappers and append them to the post figures field.
        Always uses the post owner (proposer) to authenticate the PATCH request.
        """
        import base64

        # Always use proposer's client — they own the post
        client = self._client_for(self.proposer_agent)
        if not client:
            return

        figures_payload = []
        for fp in figure_paths:
            try:
                from pathlib import Path as _Path
                p = _Path(fp)
                if not p.exists() or not fp.endswith(".png"):
                    continue
                png_b64 = base64.b64encode(p.read_bytes()).decode()
                # Wrap PNG in a minimal SVG so the existing frontend renderer can display it
                svg = (
                    f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                    f'width="800" height="600" viewBox="0 0 800 600">'
                    f'<image href="data:image/png;base64,{png_b64}" width="800" height="600"/>'
                    f'</svg>'
                )
                title = p.stem.replace("_", " ").title()
                src = label or agent_name
                figures_payload.append({"tool": src, "title": title, "svg": svg})
                print(f"  [{src}] prepared figure: {p.name}")
            except Exception as e:
                print(f"  figure prep failed {fp}: {e}")

        if figures_payload:
            src = label or agent_name
            result = client.add_figures(post_id, figures_payload)
            if "error" in result:
                print(f"  [{src}] figure upload failed: {result}")
            else:
                print(f"  [{src}] uploaded {len(figures_payload)} figure(s) to post")

    def _comment_final(self, post_id: str, hypothesis: dict, consensus_score: float) -> None:
        """Proposer posts a closing comment when the hypothesis is accepted."""
        proposer = self.proposer_agent
        client = self._client_for(proposer)
        if not client:
            return
        try:
            reasoner = self._get_reasoner(proposer)
            prompt = f"""You are {proposer}. The group has converged on a solid hypothesis after discussion.

Final hypothesis: {hypothesis.get('statement', '')}
Tools agreed on: {', '.join(hypothesis.get('planned_tools', []))}
Success criteria: {hypothesis.get('success_criteria', '')}

Write a short closing comment — what you concluded and what the next steps are.
2-4 sentences, natural tone. No structured fields.
"""
            text = reasoner._call_llm(prompt, max_tokens=400).strip()
            self._agent_comment(post_id, proposer, text)
        except Exception as e:
            print(f"  [{proposer}] could not generate final comment: {e}")

    def _agent_comment(self, post_id: str, agent_name: str, content: str) -> None:
        """Post a comment as a specific agent."""
        client = self._client_for(agent_name)
        if not client:
            return
        try:
            client.create_comment(post_id, content)
        except Exception as e:
            print(f"  [{agent_name}] comment failed: {e}")

    def _safe_comment(self, post_id: str, content: str) -> None:
        """Fallback comment using default client (for system messages like safety cap notice)."""
        try:
            default = next(iter(self._client_cache.values()), None)
            if default:
                default.create_comment(post_id, content)
        except Exception as e:
            print(f"  Comment failed: {e}")

    # ------------------------------------------------------------------ #
    # LLM reasoner cache                                                   #
    # ------------------------------------------------------------------ #

    def _get_reasoner(self, agent_name: str):
        if agent_name not in self._reasoner_cache:
            from autonomous.llm_reasoner import LLMScientificReasoner
            self._reasoner_cache[agent_name] = LLMScientificReasoner(agent_name=agent_name)
        return self._reasoner_cache[agent_name]
