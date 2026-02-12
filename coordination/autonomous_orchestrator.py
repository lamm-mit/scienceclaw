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
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
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

    def investigate(self, topic: str, community: str = 'biology') -> Dict[str, Any]:
        """
        Autonomous investigation from topic to final post.

        Args:
            topic: Research topic (e.g., "Alzheimer's disease drug targets")
            community: Target community for posting

        Returns:
            Investigation results including post_id, agents, findings
        """
        logger.info(f"Starting autonomous investigation: {topic}")

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
            'synthesis': synthesis
        }

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
            tasks=self._generate_agent_tasks(agents, strategy),
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

        tasks = session['tasks']
        results = {}
        shared_memory = session['metadata'].get('shared_memory', {})
        discussion = session['metadata'].get('discussion', [])

        # Execute tasks based on collaboration pattern
        pattern = strategy['collaboration_pattern']

        if pattern == 'sequential':
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
        Agent autonomously executes task with reasoning.

        Agent:
        1. Reviews shared memory from previous agents
        2. Reasons about what to investigate
        3. Executes tools
        4. Analyzes results
        5. Generates insights
        6. Updates shared context
        """
        logger.info(f"Agent {agent['name']} reasoning about task...")

        # Agent reasons about task using LLM
        reasoning_result = self._agent_reason(agent, task, shared_memory, discussion)

        # Agent executes tools based on reasoning
        logger.info(f"Agent {agent['name']} executing tools: {reasoning_result['tools_to_use']}")
        tool_results = self._agent_execute_tools(
            agent, reasoning_result['tools_to_use'], reasoning_result['parameters']
        )

        # Agent analyzes results
        logger.info(f"Agent {agent['name']} analyzing results...")
        analysis = self._agent_analyze(agent, task, tool_results, shared_memory)

        # Compile result
        result = {
            'agent': agent['name'],
            'role': task['role'],
            'reasoning': reasoning_result['reasoning'],
            'tools_used': reasoning_result['tools_to_use'],
            'tool_results': tool_results,
            'analysis': analysis['analysis'],
            'key_findings': analysis['key_findings'],
            'summary': analysis['summary'],
            'next_steps': analysis.get('suggestions_for_next_agent', []),
            'timestamp': datetime.now().isoformat()
        }

        # Log to agent's memory
        agent['memory'].log_observation(
            f"Completed {task['role']}: {analysis['summary']}"
        )

        return result

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

        findings_text = "\n\n".join([
            f"## Agent: {agent['name']} ({agent['role']})\n"
            f"**Responsibilities:** {agent['responsibilities']}\n"
            f"**Findings:**\n" + "\n".join(f"- {f}" for f in result.get('key_findings', []))
            for agent in agents
            for role, result in results.items()
            if result.get('agent') == agent['name']
        ])

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
