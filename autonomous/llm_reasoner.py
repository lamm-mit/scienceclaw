"""
LLM-Powered Scientific Reasoner

Uses OpenClaw/LLM to generate scientific insights dynamically through ReAct reasoning:
- Observation → Thought → Action cycle
- Self-critique and refinement
- Peer review of generated content
- Integration with reasoning system (GapDetector, HypothesisGenerator, ResultAnalyzer)

This replaces hardcoded scientific reasoning with dynamic LLM-generated analysis.
"""

import json
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path


class LLMScientificReasoner:
    """
    Uses LLM to generate scientific insights and refine content.
    
    Implements ReAct (Reasoning + Acting) pattern:
    1. Observe: Analyze tool outputs
    2. Think: Generate scientific reasoning
    3. Act: Refine and validate
    4. Critique: Peer-review own work
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize LLM reasoner.
        
        Args:
            agent_name: Name of the agent (for context)
        """
        self.agent_name = agent_name
        self.scienceclaw_dir = Path(__file__).parent.parent
        
    def _call_llm(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Call LLM via unified client for reasoning.
        
        Args:
            prompt: Scientific reasoning prompt
            max_tokens: Maximum response length
            
        Returns:
            LLM response text
        """
        try:
            import sys
            from pathlib import Path
            # Add parent to path for imports
            sys.path.insert(0, str(Path(__file__).parent.parent))
            
            from core.llm_client import get_llm_client
            client = get_llm_client(agent_name=self.agent_name)
            response = client.call(
                prompt=prompt,
                max_tokens=max_tokens,
                session_id=f"scientific_reasoning_{self.agent_name}"
            )
            
            # Only use fallback if response is too short/generic
            if len(response) < 50:
                return self._fallback_reasoning(prompt)
            return response
                
        except Exception as e:
            print(f"    Note: LLM reasoning unavailable ({e}), using fallback")
            return self._fallback_reasoning(prompt)
    
    def _fallback_reasoning(self, prompt: str) -> str:
        """Simple fallback reasoning when LLM unavailable."""
        # Extract key info from prompt for basic response
        if "mechanistic hypothesis" in prompt.lower():
            return "Multi-level regulatory mechanisms involving coordinated molecular interactions."
        elif "scientific insights" in prompt.lower():
            return "Multiple lines of evidence converge, suggesting biological relevance."
        else:
            return "Further experimental validation required to establish causal relationships."
    
    def generate_hypothesis(self, 
                          topic: str,
                          papers: List[Dict],
                          proteins: List[Dict],
                          compounds: List[Dict]) -> Dict[str, str]:
        """
        Generate scientifically rigorous hypothesis using LLM reasoning.
        
        Args:
            topic: Research topic
            papers: Literature from PubMed
            proteins: Protein data from UniProt
            compounds: Compound data from PubChem
            
        Returns:
            Dict with 'question' and 'hypothesis' keys
        """
        # Build context for LLM
        context = f"""Topic: {topic}

Literature Evidence ({len(papers)} papers):
{chr(10).join([f"- {p.get('title', 'Unknown')}" for p in papers[:5]])}

"""
        
        if proteins:
            context += f"\nProteins Identified: {', '.join([p.get('name') for p in proteins[:3]])}\n"
        
        if compounds:
            context += f"\nCompounds Identified: {', '.join([c.get('name') for c in compounds[:3]])}\n"
        
        prompt = f"""{context}

You are {self.agent_name}, a scientific researcher. Your task is to generate a rigorous, mechanistic hypothesis.

**Requirements:**
1. **Mechanistic**: Explain HOW and WHY (not just WHAT)
2. **Testable**: Make falsifiable predictions
3. **Specific**: Reference identified components (proteins, compounds, reactions)
4. **Grounded**: Use evidence from literature
5. **Technical**: Use precise scientific terminology

**For Chemistry topics**: Explain reaction mechanisms, solvent effects, catalyst roles, transition states.
**For Biology topics**: Explain signaling cascades, protein interactions, regulatory networks.
**For Drug discovery**: Explain target binding, pharmacokinetics, mechanism of action.

First state the scientific question. Then provide a detailed hypothesis with specific mechanistic predictions.

Use this exact format:
QUESTION: [Your scientific question]
HYPOTHESIS: [Detailed mechanistic explanation with specific predictions about what happens and why]

Now generate the hypothesis:"""
        
        response = self._call_llm(prompt, max_tokens=500)
        
        # Parse response
        question = ""
        hypothesis = ""
        
        for line in response.split('\n'):
            if line.startswith('QUESTION:'):
                question = line.replace('QUESTION:', '').strip()
            elif line.startswith('HYPOTHESIS:'):
                hypothesis = line.replace('HYPOTHESIS:', '').strip()
        
        # Fallback if parsing fails
        if not question:
            question = f"What are the molecular mechanisms underlying {topic}?"
        if not hypothesis:
            hypothesis = response[:500]  # Use raw response
        
        return {
            "question": question,
            "hypothesis": hypothesis
        }
    
    def generate_insights(self,
                         topic: str,
                         investigation_results: Dict) -> List[str]:
        """
        Generate scientific insights using LLM reasoning.
        
        Uses ReAct pattern:
        - Observation: Review all tool outputs
        - Thought: Identify patterns, mechanisms, gaps
        - Action: Synthesize novel insights
        
        Args:
            topic: Research topic
            investigation_results: Results from multi-tool investigation
            
        Returns:
            List of scientific insights
        """
        papers = investigation_results.get("papers", [])
        proteins = investigation_results.get("proteins", [])
        compounds = investigation_results.get("compounds", [])
        tools_used = investigation_results.get("tools_used", [])
        
        # Build comprehensive context
        context = f"""OBSERVATION - Multi-Tool Investigation Results for: {topic}

Tools Used: {', '.join(tools_used)}

Literature Evidence ({len(papers)} papers):
{chr(10).join([f"- {p.get('title', 'Unknown')}" for p in papers[:5]])}
"""
        
        if proteins:
            context += f"\n\nProtein Characterization ({len(proteins)} entities):"
            for p in proteins[:3]:
                context += f"\n- {p.get('name')}: {p.get('info', 'Characterized')[:100]}"
        
        if compounds:
            context += f"\n\nChemical Analysis ({len(compounds)} compounds):"
            for c in compounds[:3]:
                context += f"\n- {c.get('name')}: {c.get('info', 'Characterized')[:100]}"
        
        prompt = f"""{context}

You are {self.agent_name}. Analyze this investigation and generate deep scientific insights.

**Insight Requirements:**
1. **Mechanistic**: Explain mechanisms, not just observations
2. **Evidence-based**: Reference specific papers, data, findings
3. **Novel**: Go beyond literature summaries
4. **Actionable**: Suggest experimental validation or applications
5. **Technical**: Use precise scientific terminology, parameters, quantitative details when possible

**What NOT to do:**
- Don't say "multiple lines of evidence converge" (generic/vague)
- Don't repeat the literature titles
- Don't make unsupported claims
- Don't be generic

**What TO do:**
- Explain WHY something happens
- Give specific numbers, mechanisms, kinetics if available
- Suggest specific experiments to test predictions
- Make mechanistic predictions

Generate 3-4 unique insights. Start each with "INSIGHT:" and make them substantive (not one-liners).

Insights:"""
        
        response = self._call_llm(prompt, max_tokens=800)
        
        # Parse insights
        insights = []
        for line in response.split('\n'):
            if line.strip().startswith('INSIGHT:'):
                insight = line.replace('INSIGHT:', '').strip()
                if len(insight) > 50:  # Filter out incomplete insights
                    insights.append(insight)
        
        # Fallback: extract meaningful sentences if no INSIGHT: markers
        if len(insights) < 2:
            sentences = response.split('. ')
            insights = [s.strip() + '.' for s in sentences if len(s) > 50][:4]
        
        return insights[:4]
    
    def refine_content(self, content: Dict[str, str]) -> Dict[str, str]:
        """
        Refine generated content through self-critique.
        
        Implements peer-review loop:
        1. Initial generation
        2. Self-critique
        3. Refinement
        
        Args:
            content: Dict with title, hypothesis, method, findings, content
            
        Returns:
            Refined content dict
        """
        prompt = f"""You are {self.agent_name}, conducting peer review of your own scientific post.

TITLE: {content.get('title', '')}

HYPOTHESIS:
{content.get('hypothesis', '')}

METHOD:
{content.get('method', '')}

FINDINGS:
{content.get('findings', '')}

CRITIQUE THIS WORK:
1. Are the hypotheses testable and mechanistically specific?
2. Are the findings clearly stated with evidence?
3. Is the scientific reasoning rigorous and accurate?
4. Are there any vague claims or overgeneralizations?
5. Does it demonstrate professional-level scientific thinking?

For each weakness found, suggest a specific improvement.

Format your response:
CRITIQUE: [What needs improvement]
IMPROVED_HYPOTHESIS: [Refined hypothesis if needed, or "OK" if good]
IMPROVED_FINDINGS: [Refined findings if needed, or "OK" if good]

Generate critique:"""
        
        critique_response = self._call_llm(prompt, max_tokens=600)
        
        # Parse and apply improvements
        improved = content.copy()
        
        for line in critique_response.split('\n'):
            if line.startswith('IMPROVED_HYPOTHESIS:') and 'OK' not in line:
                refined = line.replace('IMPROVED_HYPOTHESIS:', '').strip()
                if len(refined) > 50:
                    improved['hypothesis'] = refined
            # Don't refine findings - it already has proper formatting with blank lines
        
        return improved
    
    def generate_conclusion(self,
                          topic: str,
                          hypothesis: str,
                          insights: List[str],
                          has_proteins: bool,
                          has_compounds: bool,
                          paper_count: int) -> str:
        """
        Generate scientifically rigorous conclusions.
        
        Args:
            topic: Research topic
            hypothesis: Generated hypothesis
            insights: List of insights
            has_proteins: Whether proteins were characterized
            has_compounds: Whether compounds were characterized
            paper_count: Number of papers analyzed
            
        Returns:
            Conclusion text with forward-looking perspective
        """
        prompt = f"""Based on this investigation of {topic}:

HYPOTHESIS: {hypothesis}

KEY INSIGHTS:
{chr(10).join([f'- {ins}' for ins in insights[:3]])}

DATA INTEGRATED:
- {paper_count} peer-reviewed papers
- {'Protein characterization: Yes' if has_proteins else 'No protein data'}
- {'Chemical analysis: Yes' if has_compounds else 'No chemical data'}

Generate a scientifically rigorous conclusion that:
1. Summarizes mechanistic understanding gained
2. Discusses therapeutic/translational potential
3. Identifies specific next experimental steps
4. Acknowledges limitations and future research directions

Use professional scientific language. Be specific about proposed experiments.

CONCLUSION:"""
        
        conclusion = self._call_llm(prompt, max_tokens=600)
        
        return conclusion.strip()
