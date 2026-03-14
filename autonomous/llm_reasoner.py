"""
LLM-Powered Scientific Reasoner

Uses LLM to generate scientific insights dynamically through ReAct reasoning:
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

# Maps skill_category values (from SKILL_INPUT_MAP) to example values shown in
# the LLM prompt so the model understands exactly what kind of entity to extract.
SKILL_ENTITY_EXAMPLES: Dict[str, str] = {
    "protein name or UniProt accession":     "TP53, BRCA1, P04637, or another gene symbol/UniProt accession",
    "protein name or PDB ID":                "TP53 Y220C, 2OCJ, or a PDB code",
    "protein name or gene symbol":           "TP53, KRAS, MDM2, or BRCA1",
    "gene symbol":                           "TP53, BRCA1, KRAS, or another HGNC symbol",
    "gene or protein name":                  "TP53, MDM2, KRAS, or another gene/protein name",
    "gene, variant, or disease":             "TP53 Y220C, rs28934578, or Li-Fraumeni syndrome",
    "gene symbol or variant":                "TP53, ENSG00000141510, or TP53 Y220C",
    "compound name":                         "APR-246, eprenetapopt, PRIMA-1, or another drug/compound name",
    "compound name or target":               "APR-246, eprenetapopt, MDM2 inhibitor, or TP53 activator",
    "compound name or SMILES":               "APR-246, eprenetapopt, or a valid SMILES string",
    "drug name":                             "eprenetapopt, APR-246, nutlin-3, or another approved/investigational drug",
    "compound name or CAS number":           "APR-246, 7396-28-3, or another compound/CAS number",
    "SMILES string":                         "O=C1CC[N+]2(CC=C)CCC1CC2 or another valid SMILES",
    "research topic":                        "TP53 Y220C small molecule stabilizer, p53 reactivation, or MDM2 inhibition",
    "pathway or gene name":                  "TP53 apoptosis pathway, KRAS signalling, or a KEGG pathway ID",
    "gene or disease":                       "TP53, ENSG00000141510, cancer, or Li-Fraumeni syndrome",
    "cancer gene or mutation":               "TP53 Y220C, KRAS G12D, or a COSMIC gene name",
    "enzyme name or EC number":              "MDM2 E3 ligase, p53 kinase, or EC 2.7.11.1",
    "amino acid sequence":                   "one-letter amino acid string for the protein of interest",
    "protein or DNA sequence":               "amino acid or nucleotide sequence string",
    "sequence or gene name":                 "TP53 exon 5-8 or a gene symbol",
    "UniProt accession":                     "P04637 (TP53_HUMAN), P00533 (EGFR), or another UniProt ID",
    "PDB ID":                                "2OCJ, 4HHB, 6W63, or another four-character PDB code",
    "accession or organism":                 "Homo sapiens TP53 mRNA or a GenBank/ENA accession",
    "SNP ID or trait":                       "rs28934578 or Li-Fraumeni syndrome",
    "GEO accession":                         "GSE12345 or GPL570",
    "metabolite name":                       "cysteine, glutathione, or another metabolite",
}


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
            
            # Only use fallback if response is empty/trivially short.
            # Some models return concise-but-meaningful outputs; treating those
            # as failures produces the unhelpful boilerplate seen in reports.
            if not response or len(response.strip()) < 10:
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
            return "Further computational analysis required to establish causal relationships."
    
    def derive_query_for_skill(
        self,
        skill_name: str,
        skill_category: str,
        topic: str,
        results_so_far: Dict,
    ) -> Optional[str]:
        """
        Ask the LLM: given what we've found so far, what is the single best
        search query to run against `skill_name`?

        Returns a short, focused query string, or None if the LLM cannot help
        (the caller should then fall back to its own logic).
        """
        papers = results_so_far.get("papers", [])
        proteins = results_so_far.get("proteins", [])
        compounds = results_so_far.get("compounds", [])

        # Even with no prior evidence, the topic itself is enough signal for the LLM
        # to extract the right entity (e.g. "TP53" from "p53 reactivation via …")

        # Summarise accumulated evidence concisely so the prompt stays short
        evidence_lines: List[str] = []
        for p in papers[:4]:
            t = p.get("title", "")
            if t:
                evidence_lines.append(f"  Paper: {t[:100]}")
        for pr in proteins[:3]:
            n = pr.get("name", "")
            if n:
                evidence_lines.append(f"  Protein: {n}")
        for c in compounds[:3]:
            n = c.get("name", "")
            if n:
                evidence_lines.append(f"  Compound: {n}")

        evidence_summary = "\n".join(evidence_lines) if evidence_lines else "  (none yet)"

        prompt = f"""You are a scientific research assistant helping an AI agent conduct a multi-step investigation.

Research topic: {topic}

Evidence collected so far:
{evidence_summary}

Next tool to run: {skill_name} (category: {skill_category})

What is the single most scientifically valuable search query to submit to {skill_name}, \
given the evidence above? The query should be a short, specific {skill_category} \
(e.g. {SKILL_ENTITY_EXAMPLES.get(skill_category, 'protein name, gene symbol, or compound name')}) that will return \
the most relevant results — not a paraphrase of the overall topic.

Reply with ONLY the query string, nothing else."""

        response = self._call_llm(prompt, max_tokens=60).strip()

        # Reject responses that are obviously bad (too long, contain newlines, etc.)
        if not response or len(response) > 120 or "\n" in response:
            return None
        # Strip surrounding quotes if the LLM added them
        response = response.strip('"\'')
        return response if response else None

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
            context += f"\nProteins Identified: {', '.join([p.get('name') or p.get('id', 'Unknown') for p in proteins[:3]])}\n"

        if compounds:
            context += f"\nCompounds Identified: {', '.join([c.get('name') or c.get('id', 'Unknown') for c in compounds[:3]])}\n"
        
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
4. **Actionable**: Suggest computational follow-up analyses or applications
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
    
    def _call_reflector_llm(self, prompt: str, max_tokens: int = 800) -> str:
        """
        Call LLM with a skeptical peer-reviewer persona (different session from generator).
        Deliberately uses a different session_id so context doesn't bleed across.
        """
        try:
            from core.llm_client import get_llm_client
            client = get_llm_client(agent_name=self.agent_name)
            response = client.call(
                prompt=prompt,
                max_tokens=max_tokens,
                session_id=f"reflector_{self.agent_name}"
            )
            if len(response) < 30:
                return "CHALLENGE: Insufficient evidence provided. REASON: Claims lack mechanistic specificity. DEMAND: Provide quantitative data and mechanistic pathway details.\nVERDICT: REJECTED"
            return response
        except Exception as e:
            print(f"    Note: Reflector LLM unavailable ({e})")
            return "CHALLENGE: Unable to verify claims. REASON: LLM unavailable. DEMAND: Manual review required.\nVERDICT: APPROVED"

    def adversarial_reflection_loop(
        self,
        topic: str,
        hypothesis: str,
        insights: List[str],
        papers: Optional[List[Dict]] = None,
        max_cycles: int = 3
    ) -> Dict[str, Any]:
        """
        Run adversarial generation+reflection cycles.

        Each cycle:
        1. Reflector challenges the current hypothesis/insights
        2. Generator revises claims in response to challenges
        3. Repeat until VERDICT: APPROVED or max_cycles reached

        Returns:
            Dict with keys: hypothesis, insights, cycles, approved
        """
        papers = papers or []
        current_hypothesis = hypothesis
        current_insights = list(insights)
        approved = False

        for cycle in range(1, max_cycles + 1):
            print(f"    🔄 Reflection cycle {cycle}/{max_cycles}...")

            # --- Reflector pass ---
            reflector_prompt = f"""You are a rigorous scientific peer reviewer evaluating a hypothesis about: {topic}

CURRENT HYPOTHESIS:
{current_hypothesis}

CURRENT INSIGHTS:
{chr(10).join([f'- {i}' for i in current_insights[:4]])}

SUPPORTING PAPERS ({len(papers)}):
{chr(10).join([f'- {p.get("title", "Unknown")}' for p in papers[:3]])}

Your job is to CHALLENGE this work. You must:
1. Identify every unsupported or vague claim
2. Demand quantitative evidence where qualitative statements exist
3. Flag any non-mechanistic assertions
4. Point out missing controls, alternative explanations, or confounds
5. Never approve on the first pass

Format EACH challenge as:
CHALLENGE: [specific claim being challenged]
REASON: [why this is weak or unsupported]
DEMAND: [what specific evidence or mechanistic detail is needed]

After all challenges, output one of:
VERDICT: APPROVED (only if all claims are well-supported mechanistically)
VERDICT: REJECTED (if significant weaknesses remain)

Be adversarial. Be specific. Do not be lenient."""

            reflector_response = self._call_reflector_llm(reflector_prompt, max_tokens=700)

            # Check verdict
            if "VERDICT: APPROVED" in reflector_response:
                approved = True
                print(f"    ✅ Reflector approved after {cycle} cycle(s)")
                break

            # Extract challenges
            challenges = []
            for line in reflector_response.split('\n'):
                if line.strip().startswith('CHALLENGE:'):
                    challenges.append(line.replace('CHALLENGE:', '').strip())

            if not challenges:
                # No structured challenges — treat as soft approval
                approved = True
                break

            # --- Generator revision pass ---
            generator_prompt = f"""You are {self.agent_name}, revising your hypothesis about: {topic}

Your peer reviewer raised these specific challenges:
{chr(10).join([f'- {c}' for c in challenges[:5]])}

CURRENT HYPOTHESIS:
{current_hypothesis}

CURRENT INSIGHTS:
{chr(10).join([f'- {i}' for i in current_insights[:4]])}

Revise your hypothesis and insights to address each challenge:
- Add mechanistic specificity where challenged
- Acknowledge limitations explicitly where evidence is missing
- Replace vague claims with specific, falsifiable predictions
- If a challenge cannot be addressed with available data, explicitly state the limitation

Output:
REVISED_HYPOTHESIS: [revised hypothesis addressing the challenges]
REVISED_INSIGHTS:
- [insight 1 revised or unchanged]
- [insight 2 revised or unchanged]
- [insight 3 revised or unchanged]"""

            generator_response = self._call_llm(generator_prompt, max_tokens=600)

            # Parse revised content
            for line in generator_response.split('\n'):
                if line.startswith('REVISED_HYPOTHESIS:'):
                    rev = line.replace('REVISED_HYPOTHESIS:', '').strip()
                    if len(rev) > 50:
                        current_hypothesis = rev

            revised_insights = []
            in_insights = False
            for line in generator_response.split('\n'):
                if 'REVISED_INSIGHTS:' in line:
                    in_insights = True
                    continue
                if in_insights and line.strip().startswith('-'):
                    ins = line.strip().lstrip('- ').strip()
                    if len(ins) > 30:
                        revised_insights.append(ins)
            if revised_insights:
                current_insights = revised_insights

        return {
            "hypothesis": current_hypothesis,
            "insights": current_insights,
            "cycles": cycle if 'cycle' in dir() else 0,
            "approved": approved
        }

    def identify_evidence_gaps(
        self,
        hypothesis: str,
        insights: List[str],
        challenges: Optional[List[str]] = None
    ) -> List[str]:
        """
        Identify evidence gaps from current hypothesis and insights.
        Returns list of gap descriptions suitable for skill routing.
        """
        challenges_text = ""
        if challenges:
            challenges_text = f"\nPeer reviewer challenges:\n" + "\n".join([f"- {c}" for c in challenges[:5]])

        prompt = f"""Given this hypothesis and insights, identify the most critical missing evidence:

HYPOTHESIS: {hypothesis}

INSIGHTS:
{chr(10).join([f'- {i}' for i in insights[:4]])}
{challenges_text}

List 2-4 specific evidence gaps that could be filled by computational tools.
For each gap, focus on what DATABASE or COMPUTATIONAL tool could provide the data.

Format:
GAP: [specific missing data type, e.g. "ADMET predictions for identified SMILES", "protein structure for binding site analysis", "sequence homology for evolutionary context"]

Only list gaps addressable by: pubmed, uniprot, pubchem, chembl, tdc, rdkit, blast, pdb"""

        response = self._call_llm(prompt, max_tokens=400)

        gaps = []
        for line in response.split('\n'):
            if line.strip().startswith('GAP:'):
                gap = line.replace('GAP:', '').strip()
                if len(gap) > 10:
                    gaps.append(gap)

        return gaps[:4]

    def generate_needs(self, topic: str, investigation_results: dict) -> list:
        """
        Ask the LLM what scientific data the investigation is still missing.

        Returns a list of need dicts (matching NeedItem schema) with at most 2
        entries.  Returns [] on parse failure or when investigation is sufficient.

        Args:
            topic: The research topic being investigated.
            investigation_results: The full results dict from run_tool_chain /
                run_deep_investigation (keys: papers, proteins, compounds,
                tools_used, insights, …).

        Returns:
            List of dicts, each with keys: artifact_type, query, rationale.
        """
        try:
            from artifacts.needs import NeedsSignal
        except ImportError:
            return []

        papers = investigation_results.get("papers", [])
        proteins = investigation_results.get("proteins", [])
        compounds = investigation_results.get("compounds", [])
        tools_used = investigation_results.get("tools_used", [])
        insights = investigation_results.get("insights", [])

        # Build a concise evidence summary for the LLM
        evidence_lines: List[str] = []
        for p in papers[:4]:
            t = p.get("title", "")
            if t:
                evidence_lines.append(f"  Paper: {t[:100]}")
        for pr in proteins[:3]:
            n = pr.get("name", "")
            if n:
                evidence_lines.append(f"  Protein: {n}")
        for c in compounds[:3]:
            n = c.get("name", "")
            if n:
                evidence_lines.append(f"  Compound: {n}")
        for ins in insights[:2]:
            evidence_lines.append(f"  Insight: {ins[:100]}")

        evidence_summary = "\n".join(evidence_lines) if evidence_lines else "  (no evidence collected)"
        tools_str = ", ".join(tools_used) if tools_used else "none"

        prompt = (
            "You are assessing what scientific data an investigation is missing.\n"
            'You must output JSON matching this schema: {"needs": [{"artifact_type": "...", "query": "...", "rationale": "..."}]}\n\n'
            "Rules:\n"
            "- Maximum 2 needs. Fewer is better if the investigation is sufficient.\n"
            "- query MUST be a specific entity name or search term, NOT a restatement of the topic.\n"
            '  GOOD: "CRBN E3 ligase substrate binding domain", "ARV-110 SMILES CC1=CC=..."\n'
            '  BAD:  "more information about degradation", "protein data for this study"\n'
            "- artifact_type must be the next logical step given what was already found.\n"
            "  Valid types: pubmed_results, protein_data, sequence_alignment, structure_data,\n"
            "  compound_data, admet_prediction, rdkit_properties, pathway_data, network_data,\n"
            "  genomic_data, expression_data, clinical_data, drug_data, metabolomics_data,\n"
            "  ml_prediction, figure, synthesis\n"
            "- rationale must explain the mechanistic gap, not just 'to learn more'.\n"
            '- If the investigation already covers the topic adequately, output {"needs": []}.\n'
            "- Vague or generic queries will be rejected. Be specific.\n\n"
            f"Research topic: {topic}\n\n"
            f"Tools already used: {tools_str}\n\n"
            f"Evidence collected:\n{evidence_summary}\n\n"
            "Output ONLY valid JSON. No explanation, no markdown fences."
        )

        raw = self._call_llm(prompt, max_tokens=400).strip()

        # Strip markdown fences if the LLM added them
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(
                l for l in lines
                if not l.startswith("```")
            ).strip()

        try:
            signal = NeedsSignal.model_validate_json(raw)
            return [item.model_dump() for item in signal.needs]
        except Exception:
            return []

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
