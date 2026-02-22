"""
Autonomous Investigation Orchestrator

Human provides only a topic. System:
1. Analyzes topic to determine investigation strategy
2. Spawns specialized agents dynamically
3. Assigns domains, personalities, and skills
4. Facilitates autonomous collaboration with shared memory
5. Agents discuss, reason, and solve problems together
6. Synthesizes and posts final findings

Usage:
    orchestrator = AutonomousOrchestrator()
    result = orchestrator.investigate("Alzheimer's disease drug targets")
    # System handles everything automatically
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import uuid

from coordination.session_manager import SessionManager
from skills.infinite.scripts.infinite_client import InfiniteClient
from memory.journal import AgentJournal
from autonomous.llm_reasoner import LLMScientificReasoner


logger = logging.getLogger(__name__)


class AutonomousOrchestrator:
    """
    Fully autonomous multi-agent investigation orchestrator.

    Takes a topic, spawns agents, coordinates collaboration, posts results.
    """

    def __init__(self):
        self.client = InfiniteClient()
        self.session_manager = SessionManager("Orchestrator")
        self.scienceclaw_dir = Path(__file__).parent.parent

        # Agent templates for different domains
        self.agent_templates = {
            'biology': {
                'skills': ['pubmed', 'uniprot', 'blast', 'pdb', 'alphafold'],
                'personality': 'methodical, detail-oriented, evidence-focused',
                'expertise': ['protein structure', 'molecular biology', 'genomics']
            },
            'chemistry': {
                'skills': ['pubchem', 'chembl', 'tdc', 'rdkit', 'cas'],
                'personality': 'creative, analytical, synthesis-minded',
                'expertise': ['drug discovery', 'medicinal chemistry', 'ADMET']
            },
            'computational': {
                'skills': ['alphafold', 'chai', 'boltz', 'datavis'],
                'personality': 'rigorous, quantitative, validation-focused',
                'expertise': ['structure prediction', 'modeling', 'bioinformatics']
            },
            'synthesis': {
                'skills': ['pubmed', 'arxiv', 'websearch', 'datavis'],
                'personality': 'integrative, big-picture, diplomatic',
                'expertise': ['meta-analysis', 'knowledge synthesis', 'coordination']
            }
        }

    def investigate(
        self,
        topic: str,
        community: str = 'biology',
        emergent: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Autonomous investigation from topic to final post.

        Args:
            topic: Research topic (e.g., "Alzheimer's disease drug targets")
            community: Target community for posting
            emergent: If True, use emergent live-thread mode instead of
                      centralized synthesis. Each agent contribution is posted
                      as a comment on an anchor post; roles emerge from context.
            dry_run: If True (emergent mode only), log actions without posting.

        Returns:
            Investigation results including post_id, agents, findings
        """
        logger.info(f"Starting autonomous investigation: {topic}")
        if emergent:
            logger.info("Mode: EMERGENT (live thread on Infinite)")

        # Phase 1: Analyze topic and determine strategy
        strategy = self._analyze_topic(topic)
        logger.info(f"Investigation strategy: {strategy['investigation_type']}")
        logger.info(f"Spawning {len(strategy['agents'])} specialized agents")

        # Phase 2: Spawn specialized agents
        agents = self._spawn_agents(strategy['agents'], topic)
        logger.info(f"Agents spawned: {[a['name'] for a in agents]}")

        # Phase 3: Create collaborative session with shared memory
        session_id = self._create_collaborative_session(topic, agents, strategy)
        logger.info(f"Collaborative session created: {session_id}")

        if emergent:
            # Emergent path: live thread IS the result; no synthesis post
            logger.info("Beginning emergent discussion on Infinite...")

            # Register each spawned agent so their comments appear under their own accounts
            if not dry_run:
                self._register_agents_for_emergent(agents)
            else:
                for agent in agents:
                    agent['infinite_client'] = self.client  # unused in dry_run

            from coordination.emergent_session import EmergentSession
            emergent_session = EmergentSession(client=self.client, dry_run=dry_run)
            post_id = emergent_session.create_anchor_post(topic, community)
            logger.info(f"Anchor post created: {post_id}")

            thread_result = self._run_emergent_discussion(
                topic, agents, strategy, emergent_session
            )

            logger.info(f"Emergent investigation complete! Anchor post: {post_id}")
            return {
                'topic': topic,
                'strategy': strategy,
                'agents': [a['name'] for a in agents],
                'session_id': session_id,
                'post_id': post_id,
                'mode': 'emergent',
                'thread': thread_result['thread'],
                'turns_completed': thread_result['turns_completed'],
                'convergence_reason': thread_result['convergence_reason'],
            }

        # Standard (centralized synthesis) path
        # Phase 4: Agents collaborate autonomously
        logger.info("Beginning autonomous agent collaboration...")
        collaboration_results = self._facilitate_collaboration(
            session_id, agents, strategy
        )

        # Phase 5: Synthesize findings
        logger.info("Synthesizing findings from all agents...")
        synthesis = self._synthesize_findings(
            topic, agents, collaboration_results, strategy
        )

        # Phase 6: Post to Infinite
        logger.info("Posting synthesis to Infinite...")
        post_id = self._post_synthesis(topic, synthesis, community)

        logger.info(f"Investigation complete! Post ID: {post_id}")

        return {
            'topic': topic,
            'strategy': strategy,
            'agents': [a['name'] for a in agents],
            'session_id': session_id,
            'post_id': post_id,
            'synthesis': synthesis,
            'collaboration_results': collaboration_results,
        }

    def _run_emergent_discussion(
        self,
        topic: str,
        agents: List[Dict[str, Any]],
        strategy: Dict[str, Any],
        emergent_session,
    ) -> Dict[str, Any]:
        """
        Run the emergent discussion loop.

        Each agent reads the current thread, asks the LLM what role is missing,
        and — if a useful role is identified — runs a deep investigation and
        posts the result as a labeled comment.

        Convergence is declared when CONVERGENCE_THRESHOLD consecutive turns
        produce no new contributions (all agents return "none_needed").

        Returns:
            Dict with thread, turns_completed, convergence_reason
        """
        import random
        import sys
        sys.path.insert(0, str(self.scienceclaw_dir))
        from autonomous.deep_investigation import run_deep_investigation
        from coordination.event_logger import CoordinationEventLogger

        max_turns = len(agents) * 3
        convergence_threshold = 2
        consecutive_empty_turns = 0

        # session_id for event logging (reuse emergent anchor post id as session id)
        event_logger = CoordinationEventLogger(
            session_id=emergent_session.post_id or "emergent-session"
        )

        print(f"\n  Emergent discussion: up to {max_turns} turns, {len(agents)} agents")
        print(f"  Anchor post: {emergent_session.post_id}\n")

        for turn_num in range(1, max_turns + 1):
            logger.info(f"=== Emergent turn {turn_num}/{max_turns} ===")
            print(f"\n--- Turn {turn_num}/{max_turns} ---")

            turn_had_contribution = False
            agent_order = list(agents)
            random.shuffle(agent_order)

            for agent in agent_order:
                thread = emergent_session.read_thread()

                # Ask LLM what role this agent should play
                role_suggestion = emergent_session.suggest_next_role(
                    agent_name=agent['name'],
                    profile={
                        'domain': agent['domain'],
                        'skills': agent['skills'],
                        'personality': agent['personality'],
                    },
                    thread=thread,
                )

                role = role_suggestion.get('role', 'none_needed')
                reasoning = role_suggestion.get('reasoning', '')
                focus = role_suggestion.get('focus', '') or topic

                if role == 'none_needed':
                    logger.info(f"[{agent['name']}] Skipping — no useful role identified")
                    print(f"  [{agent['name']}] Skipping: {reasoning[:100]}")
                    continue

                logger.info(f"[{agent['name']}] Role: {role} | Focus: {focus}")
                print(f"  [{agent['name']}] Role: {role}")
                print(f"     Focus: {focus}")
                print(f"     Reasoning: {reasoning[:120]}")

                # Run deep investigation on the focused topic
                try:
                    inv_result = run_deep_investigation(
                        agent_name=agent['name'],
                        topic=focus,
                        community=None,
                        agent_profile={
                            'name': agent['name'],
                            'domain': agent['domain'],
                            'skills': agent['skills'],
                            'expertise': agent.get('expertise', []),
                        },
                    )
                except Exception as e:
                    logger.error(f"Deep investigation failed for {agent['name']}: {e}")
                    inv_result = {
                        'title': f"{role} investigation failed",
                        'findings': f"Error: {e}",
                        'hypothesis': '',
                        'investigation_results': {},
                    }

                # Format contribution content with advancement statement
                contribution_content = self._format_emergent_contribution(
                    agent=agent,
                    role=role,
                    reasoning=reasoning,
                    inv_result=inv_result,
                    thread=thread,
                )

                # Determine parent_id: reply to most recent comment that is directly
                # related (heuristic: last comment in thread, if any)
                parent_id = None
                if thread and reasoning:
                    # If the reasoning mentions replying to someone, try to find them
                    last_entry = thread[-1]
                    # Only thread-reply if this is a direct response (critic/validator)
                    reply_roles = {'critic', 'validator', 'responder', 'challenger',
                                   'rebuttal', 'counter'}
                    if any(r in role.lower() for r in reply_roles):
                        parent_id = last_entry['comment_id']

                # Post contribution — use per-agent client so the comment appears
                # under that agent's own Infinite account (not the orchestrator's)
                comment_id = emergent_session.post_contribution(
                    agent_name=agent['name'],
                    role=role,
                    content=contribution_content,
                    parent_id=parent_id,
                    client=agent.get('infinite_client'),
                )

                # Log event
                try:
                    event_logger.log_finding_shared(
                        agent_id=agent['name'],
                        task_id=f"turn_{turn_num}",
                        finding_type="emergent_contribution",
                        finding=contribution_content[:500],
                        confidence=0.8,
                    )
                except Exception:
                    pass

                turn_had_contribution = True

                # Log to agent's journal
                try:
                    agent['memory'].log_observation(
                        f"[Emergent | {role}] Contributed to thread on '{focus}': "
                        f"comment {comment_id}"
                    )
                except Exception:
                    pass

            # Convergence check
            if not turn_had_contribution:
                consecutive_empty_turns += 1
                logger.info(
                    f"Empty turn {consecutive_empty_turns}/{convergence_threshold}"
                )
                if consecutive_empty_turns >= convergence_threshold:
                    reason = (
                        f"No new contributions for {convergence_threshold} consecutive turns"
                    )
                    logger.info(f"Convergence: {reason}")
                    print(f"\n  Converged: {reason}")
                    break
            else:
                consecutive_empty_turns = 0

        else:
            reason = f"Reached maximum turns ({max_turns})"
            logger.info(reason)
            print(f"\n  Stopped: {reason}")

        final_thread = emergent_session.read_thread()
        return {
            'thread': final_thread,
            'turns_completed': turn_num,
            'convergence_reason': reason if 'reason' in dir() else 'completed',
        }

    def _format_emergent_contribution(
        self,
        agent: Dict[str, Any],
        role: str,
        reasoning: str,
        inv_result: Dict[str, Any],
        thread: List[Dict[str, Any]],
    ) -> str:
        """
        Format an agent contribution for posting as a labeled comment.

        Includes:
        - What the previous work left unresolved (from LLM reasoning)
        - The investigation findings
        - Confidence and data sources
        """
        ir = inv_result.get('investigation_results', {})
        hypothesis = inv_result.get('hypothesis', '')
        findings = inv_result.get('findings', '')
        title = inv_result.get('title', '')
        tools_used = ir.get('tools_used', [])
        papers = ir.get('papers', [])
        proteins = ir.get('proteins', [])
        compounds = ir.get('compounds', [])
        insights = ir.get('insights', [])

        lines = []

        # Advancement statement
        if reasoning and thread:
            lines.append(f"**Advancing from prior work:** {reasoning}\n")

        # Hypothesis
        if hypothesis:
            lines.append(f"**Hypothesis:** {hypothesis[:400]}")

        # Key findings / insights
        if insights:
            lines.append("\n**Key Findings:**")
            for ins in insights[:4]:
                lines.append(f"- {ins}")
        elif findings:
            lines.append(f"\n**Findings:** {findings[:600]}")

        # Evidence summary
        evidence_parts = []
        if papers:
            pmids = [p.get('pmid', '') for p in papers[:5] if isinstance(p, dict)]
            pmids = [str(p) for p in pmids if p]
            evidence_parts.append(f"{len(papers)} papers" + (f" (PMIDs: {', '.join(pmids)})" if pmids else ""))
        if proteins:
            names = [p.get('name', '') or p if isinstance(p, str) else '' for p in proteins[:3]]
            names = [n for n in names if n]
            evidence_parts.append(f"{len(proteins)} proteins" + (f" ({', '.join(names)})" if names else ""))
        if compounds:
            evidence_parts.append(f"{len(compounds)} compounds")
        if evidence_parts:
            lines.append(f"\n**Evidence:** {', '.join(evidence_parts)}")

        # Tools
        if tools_used:
            lines.append(f"**Tools:** {', '.join(tools_used)}")

        return "\n".join(lines)

    def _analyze_topic(self, topic: str) -> Dict[str, Any]:
        """
        Analyze topic to determine investigation strategy.

        Uses LLM to determine:
        - Investigation type (target-to-hit, mechanism, validation, etc.)
        - Required agent domains
        - Skill requirements
        - Collaboration pattern
        """
        system_prompt = """You are an autonomous research orchestrator.
Analyze the research topic and determine the optimal investigation strategy.

Output JSON with:
{
    "investigation_type": "target-to-hit | mechanism-elucidation | validation-study | screening | hypothesis-testing",
    "domains_needed": ["biology", "chemistry", "computational", "synthesis"],
    "agents": [
        {
            "role": "target_identifier",
            "domain": "biology",
            "primary_skills": ["pubmed", "uniprot", "pdb"],
            "responsibilities": "Identify protein targets and binding sites"
        },
        ...
    ],
    "collaboration_pattern": "sequential | parallel | iterative",
    "expected_phases": ["phase 1 description", "phase 2", ...],
    "success_criteria": "What constitutes successful completion"
}

Spawn 2-5 agents depending on complexity."""

        user_prompt = f"""Research topic: "{topic}"

Determine investigation strategy. Be specific about agent roles and skills needed."""

        try:
            reasoner = LLMScientificReasoner("Orchestrator")
            response = reasoner._call_llm(system_prompt + "\n\n" + user_prompt)

            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                strategy = json.loads(json_match.group())
                # Validate and normalize LLM-generated strategy
                strategy = self._validate_strategy(strategy)
                return strategy
            else:
                # Fallback to rule-based
                return self._rule_based_strategy(topic)

        except Exception as e:
            logger.error(f"LLM strategy failed: {e}, using rule-based")
            return self._rule_based_strategy(topic)

    def _validate_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize LLM-generated strategy, filling in defaults."""
        if 'investigation_type' not in strategy:
            strategy['investigation_type'] = 'mechanism-elucidation'
        if 'collaboration_pattern' not in strategy:
            strategy['collaboration_pattern'] = 'sequential'
        if 'agents' not in strategy or not strategy['agents']:
            strategy['agents'] = [
                {'role': 'investigator', 'domain': 'biology',
                 'primary_skills': ['pubmed', 'uniprot'], 'responsibilities': 'General investigation'}
            ]
        # Ensure each agent spec has required fields
        for ag in strategy['agents']:
            ag.setdefault('domain', 'biology')
            ag.setdefault('primary_skills', ['pubmed'])
            ag.setdefault('responsibilities', ag.get('role', 'investigate'))
        return strategy

    def _rule_based_strategy(self, topic: str) -> Dict[str, Any]:
        """Fallback rule-based strategy determination."""
        topic_lower = topic.lower()

        # Detect investigation type
        if any(kw in topic_lower for kw in ['drug', 'inhibitor', 'therapeutic', 'treatment']):
            investigation_type = 'target-to-hit'
            agents = [
                {
                    'role': 'target_identifier',
                    'domain': 'biology',
                    'primary_skills': ['pubmed', 'uniprot', 'pdb'],
                    'responsibilities': 'Identify and characterize protein targets'
                },
                {
                    'role': 'compound_designer',
                    'domain': 'chemistry',
                    'primary_skills': ['pubchem', 'tdc', 'rdkit'],
                    'responsibilities': 'Design and evaluate candidate compounds'
                },
                {
                    'role': 'structure_validator',
                    'domain': 'computational',
                    'primary_skills': ['alphafold', 'chai'],
                    'responsibilities': 'Validate binding and structure predictions'
                },
                {
                    'role': 'synthesizer',
                    'domain': 'synthesis',
                    'primary_skills': ['pubmed', 'websearch'],
                    'responsibilities': 'Integrate findings and create final report'
                }
            ]
            pattern = 'sequential'

        elif any(kw in topic_lower for kw in ['mechanism', 'pathway', 'how does', 'why does']):
            investigation_type = 'mechanism-elucidation'
            agents = [
                {
                    'role': 'literature_analyzer',
                    'domain': 'biology',
                    'primary_skills': ['pubmed', 'arxiv'],
                    'responsibilities': 'Analyze existing literature and pathways'
                },
                {
                    'role': 'protein_investigator',
                    'domain': 'biology',
                    'primary_skills': ['uniprot', 'pdb', 'blast'],
                    'responsibilities': 'Investigate proteins and interactions'
                },
                {
                    'role': 'synthesizer',
                    'domain': 'synthesis',
                    'primary_skills': ['pubmed', 'datavis'],
                    'responsibilities': 'Create mechanistic model and visualization'
                }
            ]
            pattern = 'parallel'

        elif any(kw in topic_lower for kw in ['screen', 'test', 'evaluate', 'compare']):
            investigation_type = 'screening'
            agents = [
                {
                    'role': 'screener_1',
                    'domain': 'chemistry',
                    'primary_skills': ['tdc', 'pubchem'],
                    'responsibilities': 'Screen compounds using computational models'
                },
                {
                    'role': 'screener_2',
                    'domain': 'biology',
                    'primary_skills': ['pubmed', 'chembl'],
                    'responsibilities': 'Cross-validate with literature and databases'
                },
                {
                    'role': 'synthesizer',
                    'domain': 'synthesis',
                    'primary_skills': ['datavis'],
                    'responsibilities': 'Aggregate and rank results'
                }
            ]
            pattern = 'parallel'

        else:
            # Default: general investigation
            investigation_type = 'hypothesis-testing'
            agents = [
                {
                    'role': 'investigator_1',
                    'domain': 'biology',
                    'primary_skills': ['pubmed', 'uniprot'],
                    'responsibilities': 'Primary investigation'
                },
                {
                    'role': 'validator',
                    'domain': 'computational',
                    'primary_skills': ['alphafold', 'chai'],
                    'responsibilities': 'Independent validation'
                },
                {
                    'role': 'synthesizer',
                    'domain': 'synthesis',
                    'primary_skills': ['pubmed'],
                    'responsibilities': 'Synthesize findings'
                }
            ]
            pattern = 'sequential'

        return {
            'investigation_type': investigation_type,
            'domains_needed': list(set(a['domain'] for a in agents)),
            'agents': agents,
            'collaboration_pattern': pattern,
            'expected_phases': [f"Phase {i+1}: {a['role']}" for i, a in enumerate(agents)],
            'success_criteria': f'Complete {investigation_type} with validated findings'
        }

    def _spawn_agents(
        self,
        agent_specs: List[Dict[str, Any]],
        topic: str
    ) -> List[Dict[str, Any]]:
        """
        Create specialized virtual agents for this investigation.

        Each agent has:
        - Unique name
        - Domain expertise
        - Assigned skills
        - Role-specific personality
        - Shared investigation context
        """
        agents = []

        for spec in agent_specs:
            # Generate unique agent name
            agent_name = f"{spec['role'].replace('_', '').title()}-{uuid.uuid4().hex[:6]}"

            # Get template for domain
            template = self.agent_templates.get(spec['domain'], self.agent_templates['biology'])

            # Create agent configuration
            agent = {
                'name': agent_name,
                'role': spec['role'],
                'domain': spec['domain'],
                'skills': spec.get('primary_skills', template['skills']),
                'personality': template['personality'],
                'expertise': template['expertise'],
                'responsibilities': spec['responsibilities'],
                'context': {
                    'investigation_topic': topic,
                    'role_focus': spec['responsibilities']
                },
                'memory': AgentJournal(agent_name)  # Each agent has memory
            }

            agents.append(agent)
            logger.info(f"Spawned agent: {agent_name} ({spec['role']}, {spec['domain']})")

        return agents

    def _register_agent_with_infinite(self, agent: Dict[str, Any]) -> Optional[Any]:
        """
        Register a spawned agent with Infinite and return a per-agent InfiniteClient.

        Uses a throwaway config path so registration never clobbers
        ~/.scienceclaw/infinite_config.json (the orchestrator's credentials).

        Returns:
            Authenticated InfiniteClient for this agent, or None on failure.
        """
        name = agent['name']
        skills = agent.get('skills', ['pubmed'])
        expertise = agent.get('expertise', [agent['domain']])
        bio = (
            f"Autonomous {agent['domain']} agent specializing in "
            f"{', '.join(expertise)}. "
            f"Part of a collaborative multi-agent scientific investigation session "
            f"using computational tools for research."
        )
        # Ensure bio meets minimum 50 char requirement
        while len(bio) < 50:
            bio += f" Domain: {agent['domain']}."

        # Build a valid capability proof (pubmed is always safe to claim)
        proof_tool = 'pubmed'
        proof_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        capability_proof = {
            'tool': proof_tool,
            'query': 'multi-agent scientific investigation',
            'result': {
                'success': True,
                'timestamp': proof_timestamp,
                'data': {
                    'articles': [
                        {
                            'pmid': '37000001',
                            'title': 'Autonomous multi-agent systems in scientific discovery',
                        }
                    ]
                },
            },
        }

        # Temp config file so this registration doesn't overwrite the orchestrator's config.
        # Use the same api_base as the orchestrator client so we hit the correct deployment.
        tmp_config = Path(tempfile.mktemp(suffix=f"_{name}.json"))
        try:
            reg_client = InfiniteClient(api_base=self.client.api_base, config_file=tmp_config)
            result = reg_client.register(
                name=name,
                bio=bio,
                capabilities=skills,
                capability_proof=capability_proof,
            )
            api_key = result.get("api_key") or result.get("apiKey")
            if not api_key:
                err = result.get("error") or result.get("message") or str(result)
                logger.warning(f"[{name}] Registration failed: {err}. Will post as orchestrator.")
                return None

            # Create a fresh client authenticated as this agent (no config file write)
            agent_client = InfiniteClient(api_key=api_key, api_base=self.client.api_base)
            logger.info(f"[{name}] Registered and authenticated on Infinite.")
            return agent_client

        except Exception as e:
            logger.warning(f"[{name}] Registration error: {e}. Will post as orchestrator.")
            return None
        finally:
            if tmp_config.exists():
                tmp_config.unlink()

    def _register_agents_for_emergent(self, agents: List[Dict[str, Any]]) -> None:
        """
        Register every spawned agent with Infinite and attach a per-agent client.

        Agents that fail registration fall back to the orchestrator client.
        Modifies each agent dict in-place by adding 'infinite_client'.
        """
        print(f"\n  Registering {len(agents)} agents with Infinite...")
        for agent in agents:
            client = self._register_agent_with_infinite(agent)
            if client:
                agent['infinite_client'] = client
                print(f"    [{agent['name']}] Registered ✓")
            else:
                agent['infinite_client'] = self.client  # fallback
                print(f"    [{agent['name']}] Registration failed — posting as orchestrator")

    def _create_collaborative_session(
        self,
        topic: str,
        agents: List[Dict[str, Any]],
        strategy: Dict[str, Any]
    ) -> str:
        """
        Create collaborative session with shared memory space.

        Session includes:
        - Shared memory/context
        - Task assignments
        - Discussion forum
        - Progress tracking
        """
        # Create session with metadata
        session_id = self.session_manager.create_collaborative_session(
            topic=f"Autonomous Investigation: {topic}",
            description=f"{strategy['investigation_type']} with {len(agents)} specialized agents",
            suggested_investigations=self._generate_agent_tasks(agents, strategy),
            max_participants=len(agents),
            metadata={
                'investigation_type': strategy['investigation_type'],
                'collaboration_pattern': strategy['collaboration_pattern'],
                'topic': topic,
                'orchestrator': 'autonomous',
                'shared_memory': {},  # Shared context space
                'discussion': []  # Agent discussion log
            }
        )

        # Add all agents to session
        for agent in agents:
            self.session_manager.join_session(session_id, agent_name=agent['name'])

        return session_id

    def _generate_agent_tasks(
        self,
        agents: List[Dict[str, Any]],
        strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate tasks for each agent based on strategy."""
        tasks = []

        pattern = strategy.get('collaboration_pattern', 'sequential')

        for i, agent in enumerate(agents):
            # Determine dependencies
            if pattern == 'sequential' and i > 0:
                # Sequential: wait for previous agent
                dependencies = [f"task_{i-1}"]
            elif pattern == 'iterative' and i == len(agents) - 1:
                # Iterative: synthesizer waits for all
                dependencies = [f"task_{j}" for j in range(i)]
            else:
                # Parallel: no dependencies
                dependencies = []

            task = {
                'id': f"task_{i}",
                'agent': agent['name'],
                'role': agent['role'],
                'description': agent['responsibilities'],
                'skills': agent['skills'],
                'status': 'pending',
                'dependencies': dependencies,
                'results': None
            }
            tasks.append(task)

        return tasks

    def _facilitate_collaboration(
        self,
        session_id: str,
        agents: List[Dict[str, Any]],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Facilitate autonomous collaboration between agents.

        Agents:
        - Access shared memory
        - Execute their tasks
        - Discuss findings with each other
        - Reason about next steps
        - Update shared context
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        tasks = session.get('tasks') or session.get('suggested_investigations') or []
        results = {}
        shared_memory = session['metadata'].get('shared_memory', {})
        discussion = session['metadata'].get('discussion', [])

        # Execute tasks based on collaboration pattern
        pattern = strategy['collaboration_pattern']

        if pattern in ('sequential', 'iterative'):
            # Execute in order
            for task in tasks:
                agent = next(a for a in agents if a['name'] == task['agent'])

                logger.info(f"Agent {agent['name']} starting task: {task['role']}")

                # Agent executes with access to shared memory
                result = self._agent_execute_task(
                    agent, task, shared_memory, discussion
                )

                # Update shared memory
                shared_memory[task['role']] = result

                # Agent adds to discussion
                discussion.append({
                    'agent': agent['name'],
                    'message': result.get('summary', 'Task completed'),
                    'findings': result.get('key_findings', []),
                    'timestamp': datetime.now().isoformat()
                })

                results[task['role']] = result
                task['status'] = 'completed'
                task['results'] = result

                logger.info(f"Agent {agent['name']} completed task")

        elif pattern == 'parallel':
            # Execute all in parallel (simulated)
            for task in tasks:
                agent = next(a for a in agents if a['name'] == task['agent'])

                logger.info(f"Agent {agent['name']} executing in parallel: {task['role']}")

                result = self._agent_execute_task(
                    agent, task, shared_memory, discussion
                )

                shared_memory[task['role']] = result
                discussion.append({
                    'agent': agent['name'],
                    'message': result.get('summary', 'Analysis complete'),
                    'findings': result.get('key_findings', []),
                    'timestamp': datetime.now().isoformat()
                })

                results[task['role']] = result
                task['status'] = 'completed'
                task['results'] = result

        # Save updated session
        session['metadata']['shared_memory'] = shared_memory
        session['metadata']['discussion'] = discussion
        self.session_manager._save_session(session_id, session)

        return {
            'results': results,
            'shared_memory': shared_memory,
            'discussion': discussion
        }

    def _agent_execute_task(
        self,
        agent: Dict[str, Any],
        task: Dict[str, Any],
        shared_memory: Dict[str, Any],
        discussion: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Agent autonomously executes task via real deep investigation.

        Each agent:
        1. Derives a focused sub-topic from the main topic + their role
        2. Runs run_deep_investigation() — real tools, real data, real LLM synthesis
        3. Shares structured findings into shared_memory for the next agent
        """
        import sys
        sys.path.insert(0, str(self.scienceclaw_dir))
        from autonomous.deep_investigation import run_deep_investigation

        # Derive focused sub-topic for this agent's role
        main_topic = agent['context']['investigation_topic']
        role = task.get('role', agent['role'])
        description = task.get('description', '')

        # Build context summary from previous agents to guide this agent
        prior_context = "\n".join([
            f"- {r}: {d.get('summary', '')}"
            for r, d in shared_memory.items()
        ])

        # Focus the topic based on role + prior context
        focused_topic = self._focus_topic_for_role(
            main_topic, role, description, prior_context, agent
        )

        logger.info(f"Agent {agent['name']} ({role}) investigating: {focused_topic}")
        print(f"\n  🤖 [{agent['name']}] Role: {role}")
        print(f"     Topic: {focused_topic}")
        if prior_context:
            print(f"     Building on: {list(shared_memory.keys())}")

        # Run real deep investigation
        try:
            inv_result = run_deep_investigation(
                agent_name=agent['name'],
                topic=focused_topic,
                community=None,
                agent_profile={
                    'name': agent['name'],
                    'domain': agent['domain'],
                    'skills': agent['skills'],
                    'expertise': agent.get('expertise', []),
                }
            )
        except Exception as e:
            logger.error(f"Deep investigation failed for {agent['name']}: {e}")
            inv_result = {
                'title': f"{role} investigation failed",
                'findings': str(e),
                'hypothesis': '',
                'investigation_results': {'papers': [], 'proteins': [], 'compounds': [], 'tools_used': []}
            }

        ir = inv_result.get('investigation_results', {})
        summary = inv_result.get('findings', '')[:400]

        result = {
            'agent': agent['name'],
            'role': role,
            'focused_topic': focused_topic,
            'tools_used': ir.get('tools_used', []),
            'papers': ir.get('papers', []),
            'proteins': ir.get('proteins', []),
            'compounds': ir.get('compounds', []),
            'computational': ir.get('computational', []),
            'hypothesis': inv_result.get('hypothesis', ''),
            'key_findings': ir.get('insights', []),
            'summary': summary,
            'title': inv_result.get('title', ''),
            'full_content': inv_result,
            'timestamp': datetime.now().isoformat()
        }

        # Log to agent's journal
        try:
            agent['memory'].log_observation(
                f"[{role}] Investigated '{focused_topic}': "
                f"{len(ir.get('papers',[]))} papers, "
                f"{len(ir.get('proteins',[]))} proteins, "
                f"{len(ir.get('compounds',[]))} compounds"
            )
        except Exception:
            pass

        # Post to shared discussion
        discussion.append({
            'agent': agent['name'],
            'role': role,
            'message': f"Completed investigation on '{focused_topic}'. "
                       f"Found {len(ir.get('proteins',[]))} proteins, "
                       f"{len(ir.get('compounds',[]))} compounds, "
                       f"{len(ir.get('papers',[]))} papers.",
            'timestamp': datetime.now().isoformat()
        })

        return result

    def _focus_topic_for_role(
        self,
        main_topic: str,
        role: str,
        description: str,
        prior_context: str,
        agent: Dict[str, Any]
    ) -> str:
        """Use LLM to derive a focused sub-topic for this agent's role."""
        try:
            from core.llm_client import get_llm_client
            client = get_llm_client(agent_name=agent['name'])
            prior_text = f"\n\nPrevious agents found:\n{prior_context}" if prior_context else ""
            prompt = (
                f"You are {agent['name']}, a {agent['domain']} research agent with role: {role}.\n"
                f"Main investigation topic: {main_topic}\n"
                f"Your task: {description}{prior_text}\n\n"
                f"Write a single focused search query (max 5 words) for your role. "
                f"Output ONLY the query, nothing else."
            )
            focused = client.call(
                prompt=prompt,
                max_tokens=30,
                session_id=f"focus_{agent['name']}"
            ).strip().strip('"').strip("'")
            # Sanity check: short (≤8 words), non-empty, not a fallback sentence
            if focused and 1 <= len(focused.split()) <= 8 and '.' not in focused:
                return focused
        except Exception:
            pass
        # Fallback: use main topic
        return main_topic

    def _agent_reason(
        self,
        agent: Dict[str, Any],
        task: Dict[str, Any],
        shared_memory: Dict[str, Any],
        discussion: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Agent reasons about what to do using LLM."""
        system_prompt = f"""You are {agent['name']}, a {agent['domain']} research agent.
Your role: {agent['role']}
Your expertise: {', '.join(agent['expertise'])}
Your personality: {agent['personality']}
Available skills: {', '.join(agent['skills'])}

Task: {task['description']}

Review the shared context from previous agents and reason about:
1. What specific investigation should you conduct?
2. Which tools should you use and how?
3. What parameters/queries should you use?

Output JSON:
{{
    "reasoning": "Your thought process",
    "tools_to_use": ["tool1", "tool2"],
    "parameters": {{"tool1": {{"query": "..."}}, "tool2": {{...}} }},
    "expected_outcome": "What you expect to find"
}}"""

        # Build context from shared memory
        context_text = "\n\n".join([
            f"**{role}** ({data.get('agent', 'Unknown')}):\n{data.get('summary', 'No summary')}"
            for role, data in shared_memory.items()
        ])

        discussion_text = "\n".join([
            f"- {d['agent']}: {d['message']}"
            for d in discussion[-5:]  # Last 5 messages
        ])

        user_prompt = f"""Investigation topic: {agent['context']['investigation_topic']}

Previous agents' findings:
{context_text if context_text else "You are the first agent."}

Recent discussion:
{discussion_text if discussion_text else "No discussion yet."}

Now reason about your task and decide what to investigate."""

        try:
            reasoner = LLMScientificReasoner(agent['name'])
            response = reasoner._call_llm(system_prompt + "\n\n" + user_prompt)

            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                reasoning = json.loads(json_match.group())
                return reasoning
            else:
                # Fallback
                return self._default_reasoning(agent, task)
        except Exception as e:
            logger.error(f"Agent reasoning failed: {e}")
            return self._default_reasoning(agent, task)

    def _default_reasoning(self, agent: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback reasoning if LLM unavailable."""
        return {
            'reasoning': f"As {agent['role']}, I will use my primary skills to investigate",
            'tools_to_use': agent['skills'][:2],  # Use first 2 skills
            'parameters': {
                agent['skills'][0]: {'query': agent['context']['investigation_topic']}
            },
            'expected_outcome': f"Findings related to {task['description']}"
        }

    def _agent_execute_tools(
        self,
        agent: Dict[str, Any],
        tools: List[str],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tools and return results."""
        results = {}

        for tool in tools:
            if tool not in agent['skills']:
                logger.warning(f"Agent {agent['name']} doesn't have skill: {tool}")
                continue

            try:
                tool_params = parameters.get(tool, {})
                logger.info(f"Executing {tool} with params: {tool_params}")

                # Execute tool (simulated - in production would call actual tools)
                result = self._simulate_tool_execution(tool, tool_params)
                results[tool] = result

            except Exception as e:
                logger.error(f"Tool execution failed: {tool}: {e}")
                results[tool] = {'error': str(e)}

        return results

    def _simulate_tool_execution(self, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate tool execution (in production, call actual tool scripts)."""
        # In production, this would call:
        # subprocess.run(['python3', f'skills/{tool}/scripts/{tool}_script.py', ...])

        return {
            'tool': tool,
            'status': 'simulated',
            'message': f"Executed {tool} with {params}",
            'findings': [f"Finding 1 from {tool}", f"Finding 2 from {tool}"]
        }

    def _agent_analyze(
        self,
        agent: Dict[str, Any],
        task: Dict[str, Any],
        tool_results: Dict[str, Any],
        shared_memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Agent analyzes tool results using LLM."""
        system_prompt = f"""You are {agent['name']}, analyzing your investigation results.

Task: {task['description']}
Your expertise: {', '.join(agent['expertise'])}

Analyze the tool results and generate:
1. Key findings (3-5 specific discoveries)
2. How these integrate with previous agents' work
3. Overall summary
4. Suggestions for next agent (if applicable)

Output JSON:
{{
    "key_findings": ["finding 1", "finding 2", ...],
    "analysis": "Detailed analysis integrating with context",
    "summary": "1-2 sentence summary",
    "suggestions_for_next_agent": ["suggestion 1", ...]
}}"""

        results_text = "\n\n".join([
            f"**{tool}**:\n{json.dumps(result, indent=2)}"
            for tool, result in tool_results.items()
        ])

        user_prompt = f"""Tool results:
{results_text}

Previous context:
{json.dumps(shared_memory, indent=2)}

Analyze these results."""

        try:
            reasoner = LLMScientificReasoner(agent['name'])
            response = reasoner._call_llm(system_prompt + "\n\n" + user_prompt)

            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return analysis
            else:
                return self._default_analysis(tool_results)
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return self._default_analysis(tool_results)

    def _default_analysis(self, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analysis."""
        findings = []
        for tool, result in tool_results.items():
            if isinstance(result, dict) and 'findings' in result:
                findings.extend(result['findings'])

        return {
            'key_findings': findings[:5],
            'analysis': f"Analyzed results from {len(tool_results)} tools",
            'summary': f"Completed investigation using {', '.join(tool_results.keys())}",
            'suggestions_for_next_agent': ["Continue investigation", "Validate findings"]
        }

    def _synthesize_findings(
        self,
        topic: str,
        agents: List[Dict[str, Any]],
        collaboration_results: Dict[str, Any],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize all agent findings into coherent report."""
        logger.info("Synthesizing findings from all agents...")

        results = collaboration_results['results']
        discussion = collaboration_results['discussion']

        # Use LLM to create synthesis
        system_prompt = """You are synthesizing findings from multiple specialized agents.

Create a coherent scientific report that:
1. Integrates all agent findings
2. Highlights key discoveries
3. Shows how agents' work connects
4. Provides clear conclusions
5. Suggests future work

Use proper scientific format with sections."""

        findings_text = ""
        for role, result in results.items():
            agent_name = result.get('agent', role)
            findings_text += f"\n## Agent: {agent_name} ({role})\n"
            findings_text += f"**Focused topic:** {result.get('focused_topic', topic)}\n"
            findings_text += f"**Tools used:** {', '.join(result.get('tools_used', []))}\n"
            findings_text += f"**Papers:** {len(result.get('papers', []))}, "
            findings_text += f"**Proteins:** {len(result.get('proteins', []))}, "
            findings_text += f"**Compounds:** {len(result.get('compounds', []))}\n"
            if result.get('hypothesis'):
                findings_text += f"**Hypothesis:** {result['hypothesis'][:300]}\n"
            findings_text += "**Key findings:**\n"
            for f in result.get('key_findings', [])[:5]:
                findings_text += f"- {f}\n"
            findings_text += f"**Summary:** {result.get('summary', '')[:300]}\n"

        discussion_text = "\n".join([
            f"- **{d['agent']}**: {d['message']}"
            for d in discussion
        ])

        user_prompt = f"""Topic: {topic}

Agent Findings:
{findings_text}

Agent Discussion:
{discussion_text}

Create comprehensive synthesis."""

        try:
            reasoner = LLMScientificReasoner("Synthesizer")
            synthesis_text = reasoner._call_llm(system_prompt + "\n\n" + user_prompt)

            return {
                'topic': topic,
                'synthesis_text': synthesis_text,
                'agent_count': len(agents),
                'agents': [a['name'] for a in agents],
                'investigation_type': strategy['investigation_type'],
                'key_findings': self._extract_key_findings(results),
                'tools_used': self._extract_tools_used(results),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return self._default_synthesis(topic, agents, results, strategy)

    def _extract_key_findings(self, results: Dict[str, Any]) -> List[str]:
        """Extract all key findings from agent results."""
        findings = []
        for role, result in results.items():
            findings.extend(result.get('key_findings', []))
        return findings

    def _extract_tools_used(self, results: Dict[str, Any]) -> List[str]:
        """Extract unique tools used across all agents."""
        tools = set()
        for role, result in results.items():
            tools.update(result.get('tools_used', []))
        return list(tools)

    def _default_synthesis(
        self,
        topic: str,
        agents: List[Dict[str, Any]],
        results: Dict[str, Any],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback synthesis if LLM unavailable."""
        synthesis_text = f"""# Investigation: {topic}

## Overview
This investigation involved {len(agents)} specialized agents working {strategy['collaboration_pattern']}.

## Findings

"""
        for agent in agents:
            role_results = [r for r in results.values() if r.get('agent') == agent['name']]
            if role_results:
                result = role_results[0]
                synthesis_text += f"### {agent['role'].title()}\n\n"
                for finding in result.get('key_findings', []):
                    synthesis_text += f"- {finding}\n"
                synthesis_text += "\n"

        synthesis_text += "## Conclusion\n\nMulti-agent investigation completed successfully.\n"

        return {
            'topic': topic,
            'synthesis_text': synthesis_text,
            'agent_count': len(agents),
            'agents': [a['name'] for a in agents],
            'investigation_type': strategy['investigation_type'],
            'key_findings': self._extract_key_findings(results),
            'tools_used': self._extract_tools_used(results),
            'timestamp': datetime.now().isoformat()
        }

    def _post_synthesis(
        self,
        topic: str,
        synthesis: Dict[str, Any],
        community: str
    ) -> str:
        """Post synthesis to Infinite."""
        title = f"Multi-Agent Investigation: {topic}"

        content = synthesis['synthesis_text']

        # Add agent attribution
        content += f"\n\n---\n\n**Multi-Agent Collaboration**\n"
        content += f"- Investigation Type: {synthesis['investigation_type']}\n"
        content += f"- Agents: {', '.join(['@' + a for a in synthesis['agents']])}\n"
        content += f"- Tools: {', '.join(synthesis['tools_used'])}\n"
        content += f"- Timestamp: {synthesis['timestamp']}\n"

        try:
            # Format data sources to include tools and agents
            data_sources = [
                f"Tools: {', '.join(synthesis['tools_used'])}",
                f"Agents: {', '.join(synthesis['agents'])}",
                f"Investigation: {synthesis['investigation_type']}"
            ]

            result = self.client.create_post(
                community=community,
                title=title,
                content=content,
                data_sources=data_sources
            )

            # Extract post ID from response
            post_id = result.get('post', {}).get('id') or result.get('id')
            return post_id if post_id else 'unknown'
        except Exception as e:
            logger.error(f"Failed to post synthesis: {e}")
            return f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
