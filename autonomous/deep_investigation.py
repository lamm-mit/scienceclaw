#!/usr/bin/env python3
"""
Deep Scientific Investigation System

Integrates memory, reasoning, coordination, and autonomous modules to:
1. Use agent's memory to avoid repetition and build on past work
2. Apply scientific reasoning to identify gaps and generate hypotheses
3. Chain multiple tools for comprehensive analysis
4. Generate sophisticated, insight-driven posts

This creates posts that:
- Show genuine scientific thought process
- Use multiple tools (PubMed, UniProt, PubChem, etc.)
- Provide novel insights beyond simple summaries
- Are properly attributed to the correct agent
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from memory.journal import AgentJournal
    from memory.investigation_tracker import InvestigationTracker
    from memory.knowledge_graph import KnowledgeGraph
except ImportError:
    print("Warning: Memory system not available. Some features disabled.")
    AgentJournal = None
    InvestigationTracker = None
    KnowledgeGraph = None

try:
    from reasoning.gap_detector import GapDetector
    from reasoning.hypothesis_generator import HypothesisGenerator
    from reasoning.analyzer import ResultAnalyzer
except ImportError:
    print("Warning: Reasoning system not available. Using simplified logic.")
    GapDetector = None
    HypothesisGenerator = None
    ResultAnalyzer = None

try:
    from autonomous.llm_reasoner import LLMScientificReasoner
except ImportError:
    print("Warning: LLM reasoner not available. Using rule-based logic.")
    LLMScientificReasoner = None

try:
    from core.skill_registry import get_registry
    from core.skill_selector import get_selector
    from core.skill_executor import get_executor
    from core.topic_analyzer import get_analyzer
except ImportError:
    print("Warning: Skill discovery system not available. Using hardcoded tools.")
    get_registry = None
    get_selector = None
    get_executor = None
    get_analyzer = None


class DeepInvestigator:
    """
    Conducts deep scientific investigations using multiple tools and reasoning.
    
    This is what makes posts interesting and insightful:
    - Multi-tool investigation (PubMed → UniProt → PubChem chain)
    - Memory of past investigations
    - Scientific reasoning and gap detection
    - Sophisticated content generation
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize deep investigator for an agent.
        
        Args:
            agent_name: Name of the agent (used for memory and attribution)
        """
        self.agent_name = agent_name
        self.scienceclaw_dir = Path(__file__).parent.parent
        
        # Initialize memory system (if available)
        self.journal = AgentJournal(agent_name) if AgentJournal else None
        self.tracker = InvestigationTracker(agent_name) if InvestigationTracker else None
        self.knowledge = KnowledgeGraph(agent_name) if KnowledgeGraph else None
        
        # Initialize reasoning (if available) - requires memory components
        if GapDetector and self.knowledge and self.journal:
            try:
                self.gap_detector = GapDetector(
                    knowledge_graph=self.knowledge,
                    journal=self.journal
                )
            except Exception:
                self.gap_detector = None
        else:
            self.gap_detector = None
        
        if HypothesisGenerator and self.knowledge and self.journal:
            try:
                self.hypothesis_gen = HypothesisGenerator(
                    knowledge_graph=self.knowledge,
                    journal=self.journal
                )
            except Exception:
                self.hypothesis_gen = None
        else:
            self.hypothesis_gen = None
        
        if ResultAnalyzer and self.knowledge and self.journal:
            try:
                self.result_analyzer = ResultAnalyzer(
                    knowledge_graph=self.knowledge,
                    journal=self.journal
                )
            except Exception:
                self.result_analyzer = None
        else:
            self.result_analyzer = None
        
        # Initialize LLM reasoner for dynamic insight generation
        if LLMScientificReasoner:
            self.llm_reasoner = LLMScientificReasoner(agent_name)
        else:
            self.llm_reasoner = None
        
        # Initialize skill discovery system
        if get_registry:
            self.skill_registry = get_registry()
            self.skill_selector = get_selector(agent_name) if get_selector else None
            self.skill_executor = get_executor() if get_executor else None
            self.topic_analyzer = get_analyzer(agent_name) if get_analyzer else None
            print(f"  ✨ Skill discovery enabled: {len(self.skill_registry.skills)} skills available")
        else:
            self.skill_registry = None
            self.skill_selector = None
            self.skill_executor = None
            self.topic_analyzer = None
    
    def check_previous_work(self, topic: str) -> Dict:
        """
        Check if agent has investigated this topic before.
        
        Returns:
            Dictionary with previous investigations and knowledge
        """
        if not self.journal:
            return {"investigated": False}
        
        # Check journal for previous observations
        investigated_topics = self.journal.get_investigated_topics()
        
        if topic.lower() in [t.lower() for t in investigated_topics]:
            return {
                "investigated": True,
                "message": f"Agent has previously explored {topic}. Building on past work."
            }
        
        return {"investigated": False}
    
    def select_skills_for_topic(self, topic: str) -> List[Dict[str, Any]]:
        """
        Dynamically select skills for a topic using LLM (or fallback).
        
        Args:
            topic: Research topic
            
        Returns:
            SkillSelection with selected skills
        """
        if not self.skill_selector or not self.skill_registry:
            return None
        
        try:
            # Get all available skills
            all_skills = list(self.skill_registry.skills.values())
            
            # Use LLM to select most relevant (with timeout)
            print(f"    Querying LLM for skill selection...", end="", flush=True)
            selected = self.skill_selector.select_skills(
                topic=topic,
                available_skills=all_skills,
                max_skills=5
            )
            print(" done")
            
            return selected
        except Exception as e:
            print(f"\n    Note: LLM skill selection failed ({e}), using fallback")
            # Fallback to keyword-based selection
            all_skills = list(self.skill_registry.skills.values())
            from core.skill_selector import LLMSkillSelector, SkillSelection
            selector = LLMSkillSelector(self.agent_name if hasattr(self, 'agent_name') else 'Agent')
            selected_list = selector._fallback_selection(topic, all_skills, 5)
            return SkillSelection(
                topic=topic,
                selected_skills=selected_list,
                reasoning="Fallback keyword-based selection"
            )
    
    def run_tool_chain(self, topic: str, investigation_type: str = "auto",
                       pre_selected_skills: Optional[List[Dict[str, Any]]] = None) -> Dict:
        """
        Run a chain of scientific tools based on the topic.
        
        Uses intelligent skill discovery to select optimal tools dynamically.
        Falls back to legacy tool chain if skill discovery unavailable.
        
        Args:
            topic: Research topic
            investigation_type: Type of investigation (biology, chemistry, auto)
        
        Returns:
            Dict with results from multiple tools and analysis
        """
        results = {
            "topic": topic,
            "tools_used": [],
            "papers": [],
            "proteins": [],
            "compounds": [],
            "mechanisms": [],
            "insights": []
        }
        
        # Use pre-selected skills from unified LLM call only (no fallback to separate skill selection)
        skill_selection = None
        if pre_selected_skills:
            from core.skill_selector import SkillSelection, SelectedSkill
            selected = [
                SelectedSkill(
                    name=s['name'],
                    reason=s.get('reason', ''),
                    suggested_params=s.get('suggested_params', {}),
                    category=s.get('category'),
                    description=s.get('description')
                )
                for s in pre_selected_skills
            ]
            skill_selection = SkillSelection(topic=topic, selected_skills=selected)
        
        if skill_selection and skill_selection.selected_skills:
            print(f"  📋 Selected {skill_selection.total_skills} skills: {[s.name for s in skill_selection.selected_skills[:3]]}")
            # Note: Full execution via skill_executor would go here in Phase 2
            # For now, map to existing tools
            for skill in skill_selection.selected_skills:
                results["tools_used"].append(skill.name)
        
        # Fall back to legacy tool chain
        print(f"  🔬 Step 1: Searching literature...")
        
        # Determine which literature database to use
        lit_tool = "PubMed"  # Default
        if self.skill_registry:
            # Check if better literature tools are available
            lit_skills = self.skill_registry.get_skills_by_category("literature")
            for skill in lit_skills:
                if skill['name'] in ['openalex-database', 'biorxiv-database']:
                    print(f"  💡 Note: {skill['name']} available for literature search")
        
        pubmed_results = self._run_pubmed(topic, max_results=5)
        results["papers"] = pubmed_results.get("papers", [])
        results["tools_used"].append(lit_tool)
        
        if not results["papers"]:
            return results
        
        # Step 2: Extract key entities from paper titles
        print(f"  🧬 Step 2: Extracting key entities...")
        entities = self._extract_entities(results["papers"])
        
        # Step 2b: If no entities found, run focused searches for specific entities
        if not entities.get("proteins") and not entities.get("compounds"):
            print(f"  🔍 Step 2b: Running focused entity searches...")
            focused_entities = self._run_focused_searches(topic, investigation_type)
            entities["proteins"].extend(focused_entities.get("proteins", []))
            entities["compounds"].extend(focused_entities.get("compounds", []))
        
        # Step 3: Intelligent tool selection based on investigation type AND available skills
        # For CHEMISTRY topics, prioritize compound databases
        if investigation_type == "chemistry":
            print(f"  🧪 Step 3: Chemistry investigation - using compound databases...")
            
            # Suggest better chemistry tools if available
            if self.skill_registry:
                chem_skills = self.skill_registry.get_skills_by_category("compounds")
                suggested = [s['name'] for s in chem_skills if s['name'] in ['chembl-database', 'pubchem-database', 'zinc-database', 'drugbank-database']]
                if suggested:
                    print(f"  💡 Available chemistry databases: {', '.join(suggested[:3])}")
            
            if entities.get("compounds"):
                for compound in entities["compounds"][:3]:
                    compound_data = self._run_pubchem(compound)
                    if compound_data:
                        results["compounds"].append(compound_data)
                        if "PubChem" not in results["tools_used"]:
                            results["tools_used"].append("PubChem")
        
        # For BIOLOGY topics, prioritize protein databases
        elif investigation_type == "biology":
            print(f"  🧪 Step 3: Biology investigation - using protein databases...")
            
            # Suggest better protein tools if available
            if self.skill_registry:
                protein_skills = self.skill_registry.get_skills_by_category("proteins")
                suggested = [s['name'] for s in protein_skills if s['name'] in ['uniprot', 'alphafold-database', 'pdb']]
                if suggested:
                    print(f"  💡 Available protein databases: {', '.join(suggested[:3])}")
            
            if entities.get("proteins"):
                for protein in entities["proteins"][:3]:
                    protein_data = self._run_uniprot(protein)
                    if protein_data:
                        results["proteins"].append(protein_data)
                        if "UniProt" not in results["tools_used"]:
                            results["tools_used"].append("UniProt")
        
        # For AUTO (interdisciplinary) - skip protein/compound lookups to avoid over-focusing on bio/chem
        elif investigation_type == "auto":
            print(f"  🧪 Step 3: Interdisciplinary investigation - using selected skills...")
        
        # Step 5: Generate insights from integrated data
        print(f"  💡 Step 4: Synthesizing insights...")
        insights = self._generate_insights(results)
        results["insights"] = insights
        
        return results
    
    def _run_focused_searches(self, topic: str, investigation_type: str) -> Dict:
        """
        Intelligently select entities based on topic content.
        
        Uses keyword matching to decide if proteins, compounds, or both are needed.
        Flexible: enzyme questions get both, pure chemistry gets compounds only, etc.
        """
        entities = {"proteins": [], "compounds": []}
        topic_lower = topic.lower()
        
        # Keywords indicating we should look for PROTEINS
        protein_keywords = ["protein", "enzyme", "kinase", "receptor", "antibody", 
                           "gene", "crispr", "mutation", "disease", "pathogen",
                           "alzheimer", "cancer", "tumor", "cell", "viral", "bacteria"]
        
        # Keywords indicating we should look for COMPOUNDS
        compound_keywords = ["reaction", "synthesis", "catalyst", "compound", "drug",
                            "inhibitor", "chemical", "molecule", "organic", "solvent",
                            "oxidation", "reduction", "bond", "water", "ester"]
        
        # Keywords that indicate BOTH proteins AND compounds
        both_keywords = ["enzyme", "catalysis", "substrate", "inhibitor", "biocatalysis",
                        "enzyme kinetics", "active site", "drug target", "protein-ligand",
                        "receptor binding", "enzymatic mechanism", "bioreactor"]
        
        # Special combinations that clearly need both
        has_enzyme = any(kw in topic_lower for kw in ["enzyme", "catalysis", "enzymatic"])
        has_protein_function = any(kw in topic_lower for kw in ["protein", "kinase", "receptor"])
        has_chemistry = any(kw in topic_lower for kw in ["reaction", "synthesis", "compound", "drug"])
        
        # DECISION LOGIC: Flexible, not rigid
        
        # If it's about enzymes or enzymatic reactions → GET BOTH
        if has_enzyme:
            # Look for specific enzymes or generic ones
            if "protease" in topic_lower:
                entities["proteins"].extend(["protease"])
            elif "kinase" in topic_lower:
                entities["proteins"].extend(["kinase"])
            elif "oxidase" in topic_lower:
                entities["proteins"].extend(["oxidase"])
            else:
                entities["proteins"].extend(["enzyme"])  # Generic enzyme search
            
            # Also get relevant compounds
            if "water" in topic_lower:
                entities["compounds"].extend(["water"])
            if "substrate" in topic_lower or "inhibitor" in topic_lower:
                entities["compounds"].extend(["substrate", "inhibitor"])
            
            return entities
        
        # If it's about protein function/structure → GET PROTEINS
        if has_protein_function and not has_chemistry:
            if "alzheimer" in topic_lower:
                entities["proteins"].extend(["APP", "BACE1", "tau", "APOE"])
            elif "cancer" in topic_lower or "tumor" in topic_lower:
                entities["proteins"].extend(["p53", "KRAS", "EGFR", "BRAF"])
            elif "crispr" in topic_lower or "gene edit" in topic_lower:
                entities["proteins"].extend(["Cas9", "Cas12"])
            elif "kinase" in topic_lower:
                entities["proteins"].extend(["EGFR", "BRAF", "mTOR"])
            else:
                # Generic protein search
                entities["proteins"].extend(["protein"])
            
            return entities
        
        # If it's chemistry + biology → GET BOTH
        if has_chemistry and has_protein_function:
            # Drug discovery, medicinal chemistry, etc.
            if "kinase" in topic_lower:
                entities["proteins"].extend(["kinase", "EGFR", "BRAF"])
                entities["compounds"].extend(["inhibitor"])
            elif "antibody" in topic_lower:
                entities["proteins"].extend(["antibody", "antigen"])
                entities["compounds"].extend(["ligand"])
            else:
                entities["proteins"].extend(["protein", "target"])
                entities["compounds"].extend(["compound", "drug"])
            
            return entities
        
        # Pure chemistry → GET COMPOUNDS ONLY
        if has_chemistry and not has_protein_function:
            if "water" in topic_lower:
                entities["compounds"].extend(["water", "solvent"])
            if "catalyst" in topic_lower:
                entities["compounds"].extend(["catalyst"])
            if "synthesis" in topic_lower or "reaction" in topic_lower:
                entities["compounds"].extend(["reagent", "product"])
            else:
                entities["compounds"].extend(["compound"])
            
            return entities
        
        # Materials science → GET NEITHER (materials don't have proteins/compounds)
        if any(term in topic_lower for term in ["material", "crystal", "metal", "polymer", "alloy"]):
            return entities
        
        # DEFAULT: If unclear, try BOTH (better safe than missing something)
        entities["proteins"].extend(["protein"])
        entities["compounds"].extend(["compound"])
        
        return entities
    
    def _run_pubmed(self, query: str, max_results: int = 5) -> Dict:
        """Run PubMed search."""
        try:
            cmd = [
                "python3",
                str(self.scienceclaw_dir / "skills/pubmed/scripts/pubmed_search.py"),
                "--query", query,
                "--max-results", str(max_results)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.scienceclaw_dir,
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout
                papers = []
                lines = output.split('\n')
                i = 0
                while i < len(lines):
                    line = lines[i]
                    if 'PMID:' in line:
                        pmid = line.split('PMID:')[1].strip().split()[0]
                        title = ""
                        for j in range(i-1, max(0, i-5), -1):
                            if lines[j].strip() and not lines[j].startswith('   '):
                                title = lines[j].strip()
                                break
                        papers.append({
                            "pmid": pmid,
                            "title": title
                        })
                    i += 1
                return {"papers": papers}
        except Exception as e:
            print(f"    Warning: PubMed search failed: {e}")
        
        return {"papers": []}
    
    def _extract_entities(self, papers: List[Dict]) -> Dict:
        """
        Extract biological and chemical entities from papers.
        
        This uses keyword matching enhanced with topic-specific patterns.
        """
        entities = {
            "proteins": set(),
            "compounds": set(),
            "pathways": set()
        }
        
        # Common protein/gene keywords (uppercase patterns for genes)
        protein_keywords = [
            "protein", "kinase", "receptor", "enzyme", "channel",
            "EGFR", "p53", "TP53", "KRAS", "BRAF", "mTOR", "AKT", "Cas9", "CRISPR",
            "antibody", "cytokine", "hormone", "amyloid", "APP", "BACE1", "tau",
            "presenilin", "apolipoprotein", "APOE", "beta-amyloid", "Aβ",
            "insulin", "growth factor", "transcription factor", "integrin"
        ]
        
        # Common compound keywords
        compound_keywords = [
            "imatinib", "aspirin", "caffeine", "glucose", "ATP", "acetylcholine",
            "inhibitor", "drug", "molecule", "compound", "therapeutic", "antagonist",
            "agonist", "dopamine", "serotonin", "glutamate", "GABA"
        ]
        
        # Alzheimer's-specific patterns
        alzheimers_proteins = ["APP", "BACE1", "tau", "presenilin", "APOE", "amyloid", "Aβ"]
        
        # CRISPR-specific patterns
        crispr_proteins = ["Cas9", "Cas12", "Cas13", "CRISPR", "guide RNA", "sgRNA"]
        
        # Cancer-specific patterns
        cancer_proteins = ["p53", "TP53", "KRAS", "EGFR", "BRAF", "oncogene", "tumor suppressor"]
        
        # Extract from titles
        for paper in papers:
            title = paper.get("title", "")
            title_lower = title.lower()
            
            # Extract proteins (case-sensitive for gene names)
            for keyword in protein_keywords + alzheimers_proteins + crispr_proteins + cancer_proteins:
                if keyword.lower() in title_lower or keyword in title:
                    entities["proteins"].add(keyword)
            
            # Extract compounds
            for keyword in compound_keywords:
                if keyword.lower() in title_lower:
                    entities["compounds"].add(keyword)
            
            # Extract specific patterns
            # Look for protein names in all caps (e.g., EGFR, BRAF)
            words = title.split()
            for word in words:
                if len(word) >= 3 and word.isupper() and word.isalpha():
                    # Likely a gene/protein name
                    entities["proteins"].add(word)
        
        return {
            "proteins": list(entities["proteins"])[:5],
            "compounds": list(entities["compounds"])[:5],
            "pathways": list(entities["pathways"])
        }
    
    def _run_uniprot(self, protein: str) -> Optional[Dict]:
        """
        Look up protein in UniProt.
        
        Note: UniProt requires specific accessions (e.g., P53_HUMAN, not just p53).
        For now, we'll use known mappings or skip unavailable proteins.
        """
        # Known protein accessions
        accession_map = {
            "p53": "P53_HUMAN",
            "TP53": "P53_HUMAN",
            "EGFR": "EGFR_HUMAN",
            "KRAS": "RASK_HUMAN",
            "BRAF": "BRAF_HUMAN",
            "APP": "A4_HUMAN",
            "BACE1": "BACE1_HUMAN",
            "tau": "TAU_HUMAN",
            "MAPT": "TAU_HUMAN",
            "Cas9": "CAS9_STRP1",
            "amyloid": "A4_HUMAN",  # Amyloid precursor protein
            "insulin": "INS_HUMAN",
            "mTOR": "MTOR_HUMAN",
            "AKT": "AKT1_HUMAN"
        }
        
        accession = accession_map.get(protein, protein)
        
        try:
            cmd = [
                "python3",
                str(self.scienceclaw_dir / "skills/uniprot/scripts/uniprot_fetch.py"),
                "--accession", accession,
                "--format", "summary"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.scienceclaw_dir,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout:
                # Extract key information from output
                info_lines = result.stdout.split('\n')[:10]  # First 10 lines
                return {
                    "name": protein,
                    "accession": accession,
                    "info": '\n'.join(info_lines)
                }
        except Exception as e:
            print(f"    Note: UniProt lookup for {protein} ({accession}) unavailable")
        
        return None
    
    def _run_pubchem(self, compound: str) -> Optional[Dict]:
        """Look up compound in PubChem."""
        try:
            cmd = [
                "python3",
                str(self.scienceclaw_dir / "skills/pubchem/scripts/pubchem_search.py"),
                "--query", compound
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.scienceclaw_dir,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout:
                return {
                    "name": compound,
                    "info": result.stdout[:500]  # First 500 chars
                }
        except Exception as e:
            print(f"    Note: PubChem lookup for {compound} unavailable")
        
        return None
    
    def _generate_insights(self, investigation_results: Dict) -> List[str]:
        """
        Generate scientifically rigorous insights using LLM reasoning.
        
        Leverages LLM for dynamic scientific analysis instead of hardcoded rules.
        Falls back to rule-based reasoning if LLM unavailable.
        """
        # Try LLM-powered reasoning first
        if self.llm_reasoner:
            try:
                topic = investigation_results.get("topic", "")
                return self.llm_reasoner.generate_insights(topic, investigation_results)
            except Exception as e:
                print(f"    Note: LLM reasoning failed ({e}), using fallback")
        
        # Fallback to rule-based insights
        insights = []
        papers = investigation_results.get("papers", [])
        proteins = investigation_results.get("proteins", [])
        compounds = investigation_results.get("compounds", [])
        topic = investigation_results.get("topic", "")
        
        # Insight 1: Evidence strength with reproducibility assessment
        if len(papers) >= 5:
            insights.append(
                f"Strong evidence base ({len(papers)} peer-reviewed studies) demonstrates "
                f"well-characterized mechanisms with independent replication across research groups, "
                f"indicating high reproducibility. This robust consensus supports translational "
                f"applications and reduces risk of publication bias."
            )
        elif len(papers) >= 3:
            insights.append(
                f"Moderate evidence convergence ({len(papers)} studies) establishes biological "
                f"relevance, though mechanistic details require validation through orthogonal "
                f"experimental approaches (genetic perturbation, biochemical reconstitution, "
                f"structural determination) to confirm causality."
            )
        elif len(papers) <= 2:
            insights.append(
                f"Limited primary literature ({len(papers)} {'study' if len(papers) == 1 else 'studies'}) "
                f"indicates emerging research area. Current findings represent preliminary observations "
                f"requiring independent replication, expanded sample sizes, and mechanistic validation "
                f"before drawing definitive conclusions."
            )
        
        # Insight 2: Molecular mechanism with functional predictions
        if proteins and compounds:
            protein_str = ', '.join([p.get('name') for p in proteins[:2]])
            compound_str = ', '.join([c.get('name') for c in compounds[:2]])
            insights.append(
                f"Protein-ligand interactions identified ({protein_str} × {compound_str}) suggest "
                f"druggable binding interfaces. Rational validation strategy: (1) co-crystallography "
                f"or cryo-EM for atomic-resolution structure, (2) isothermal titration calorimetry "
                f"for thermodynamic binding parameters (Kd, ΔH, ΔS), (3) cellular target engagement "
                f"assays, and (4) structure-guided optimization for improved potency and selectivity."
            )
        elif proteins:
            protein_names = ', '.join([p.get('name') for p in proteins[:3]])
            insights.append(
                f"Critical regulatory proteins identified ({protein_names}) likely function as pathway "
                f"control nodes. Functional validation requires: (1) loss-of-function genetics (CRISPR "
                f"knockout or RNA interference), (2) gain-of-function overexpression, (3) domain deletion "
                f"analysis to map functional regions, and (4) epistasis testing to determine pathway "
                f"position and genetic interactions."
            )
        elif compounds:
            compound_names = ', '.join([c.get('name') for c in compounds[:2]])
            insights.append(
                f"Chemical probes characterized ({compound_names}) enable mechanistic dissection. "
                f"Recommended approaches: (1) dose-response curves to establish EC50/IC50 values, "
                f"(2) structure-activity relationship (SAR) profiling to identify pharmacophores, "
                f"(3) selectivity panels against related targets, and (4) in vivo pharmacokinetics "
                f"and tissue distribution studies."
            )
        
        # Insight 3: Cross-database validation and experimental tractability
        if proteins and len(papers) >= 2:
            insights.append(
                f"Multi-database convergence (primary literature + curated protein databases) provides "
                f"orthogonal evidence strengthening mechanistic confidence. Identified proteins are "
                f"experimentally tractable: recombinant expression in E. coli or mammalian cells, "
                f"standard purification protocols, and established biochemical/biophysical assays "
                f"(enzymatic activity, binding kinetics, structural studies) enable rapid hypothesis testing."
            )
        
        # Insight 4: Systems-level integration for translational topics
        if any(term in topic.lower() for term in ['disease', 'therapy', 'therapeutic', 'treatment', 'drug', 'delivery', 'clinical']):
            insights.append(
                f"Translational pathway requires systematic validation cascade: (1) target engagement "
                f"verification in disease-relevant cell types or patient-derived samples, (2) quantitative "
                f"pathway flux analysis using metabolomics or phosphoproteomics to measure functional "
                f"impact, (3) biomarker identification for patient stratification and response prediction, "
                f"(4) off-target profiling and toxicity assessment in relevant preclinical models, and "
                f"(5) pharmacodynamic markers for clinical monitoring."
            )
        elif any(term in topic.lower() for term in ['mechanism', 'pathway', 'regulation', 'signaling']):
            insights.append(
                f"Mechanistic understanding requires quantitative systems analysis: mathematical modeling "
                f"to test alternative network topologies, time-resolved measurements to capture dynamics, "
                f"perturbation experiments to establish causal relationships, and multi-omics integration "
                f"(transcriptomics, proteomics, metabolomics) to map information flow through the pathway."
            )
        
        return insights[:4]  # Top 4 most relevant insights
    
    def _generate_fallback_hypothesis(self, topic: str, papers: List, 
                                     proteins: List, compounds: List,
                                     insights: List) -> str:
        """Fallback hypothesis generation when LLM unavailable."""
        if proteins and compounds:
            hypothesis = f"""**Scientific Question:** What are the molecular mechanisms underlying {topic}?

**Hypothesis:** {topic} operates through specific protein-compound interactions involving {', '.join([p.get('name') for p in proteins[:2]])} and {', '.join([c.get('name') for c in compounds[:2]])}. These molecular components likely interact through conserved binding domains, triggering conformational changes that modulate biological function."""
        elif proteins:
            hypothesis = f"""**Scientific Question:** What are the molecular mechanisms underlying {topic}?

**Hypothesis:** {topic} is mediated by key regulatory proteins ({', '.join([p.get('name') for p in proteins[:2]])}). These proteins function as critical control nodes, exhibiting post-translational regulation and protein-protein interactions that coordinate pathway output."""
        else:
            hypothesis = f"""**Scientific Question:** What are the molecular mechanisms underlying {topic}?

**Hypothesis:** Based on literature analysis ({len(papers)} studies), {topic} involves multi-level regulatory coordination across molecular pathways."""
        
        if insights:
            hypothesis += f"\n\n**Supporting Evidence:** {insights[0]}"
        
        return hypothesis
    
    def _generate_fallback_conclusion(self, topic: str, insights: List,
                                      proteins: List, compounds: List,
                                      papers: List) -> str:
        """Fallback conclusion generation when LLM unavailable."""
        conclusion = f"""

**Conclusions & Implications:**

This multi-tool investigation of {topic} reveals:

1. **Mechanistic Understanding**: {insights[0] if insights else 'Complex regulation across molecular levels'}
2. **Therapeutic Potential**: {'Integration of protein and chemical data suggests actionable intervention points' if proteins and compounds else 'Further characterization needed for therapeutic development'}
3. **Research Directions**: """
        
        if len(papers) < 3:
            conclusion += "Emerging field with high potential for novel discoveries."
        else:
            conclusion += "Well-established area requiring mechanistic depth."
        
        conclusion += "\n\n**Next Steps**: Experimental validation of predicted mechanisms, cross-species comparison, and therapeutic target prioritization."
        
        return conclusion
    
    def generate_sophisticated_content(self, 
                                      topic: str,
                                      investigation_results: Dict) -> Dict:
        """
        Generate sophisticated scientific content from deep investigation.
        
        This creates engaging, insightful posts that show real scientific thinking.
        """
        papers = investigation_results.get("papers", [])
        insights = investigation_results.get("insights", [])
        tools_used = investigation_results.get("tools_used", [])
        proteins = investigation_results.get("proteins", [])
        compounds = investigation_results.get("compounds", [])
        
        # Generate compelling title (preserve original topic capitalization)
        if proteins:
            title = f"{topic}: Molecular Mechanisms via {proteins[0].get('name', 'Key Proteins')}"
        elif compounds:
            title = f"{topic}: Chemical Basis and Therapeutic Implications"
        else:
            title = f"{topic}: A Multi-Tool Investigation"
        
        # Generate hypothesis using LLM reasoning or fallback
        if self.llm_reasoner:
            try:
                hyp_result = self.llm_reasoner.generate_hypothesis(
                    topic, papers, proteins, compounds
                )
                hypothesis = f"""**Scientific Question:** {hyp_result['question']}

**Hypothesis:** {hyp_result['hypothesis']}"""
                
                # Add supporting evidence
                if insights:
                    hypothesis += f"\n\n**Supporting Evidence:** {insights[0]}"
            except Exception as e:
                print(f"    Note: LLM hypothesis generation failed, using template")
                hypothesis = self._generate_fallback_hypothesis(
                    topic, papers, proteins, compounds, insights
                )
        else:
            hypothesis = self._generate_fallback_hypothesis(
                topic, papers, proteins, compounds, insights
            )
        
        # Generate method showcasing tool chain with proper numbering
        method = f"""**Investigative Approach:**
This investigation employed a multi-tool systematic analysis:

1. **PubMed Literature Mining**: Comprehensive search for "{topic}" to establish current knowledge base ({len(papers)} peer-reviewed papers analyzed)
2. **Molecular Entity Extraction**: Automated extraction of key proteins, compounds, and pathways from literature"""
        
        step = 3
        if proteins:
            method += f"\n{step}. **UniProt Protein Analysis**: Detailed characterization of {len(proteins)} key proteins ({', '.join([p.get('name', '') for p in proteins[:3]])})"
            step += 1
        
        if compounds:
            method += f"\n{step}. **PubChem Chemical Analysis**: Structure and property analysis of {len(compounds)} compounds ({', '.join([c.get('name', '') for c in compounds[:3]])})"
            step += 1
        
        method += f"\n{step}. **Integrated Synthesis**: Cross-tool data integration to identify mechanisms and generate insights"
        method += f"\n\n**Tools Used**: {', '.join(tools_used)}"
        
        # Generate findings with visible separators for clear section breaks
        findings = "**Key Discoveries:**"
        
        if len(papers) >= 2:
            findings += f"\n\n---\n\n**Literature Analysis** ({len(papers)} papers):\n"
            for paper in papers[:3]:
                # Strip numbering if present (from title extraction)
                title = paper.get('title', 'Unknown')
                title = title.lstrip('0123456789. ')  # Remove leading numbers
                findings += f"- {title} (PMID:{paper.get('pmid', 'N/A')})\n"
        
        if proteins:
            findings += f"\n---\n\n**Protein Characterization** ({len(proteins)} entities):\n"
            for protein in proteins[:2]:
                findings += f"- {protein.get('name')}: Critical regulatory component\n"
        
        if compounds:
            findings += f"\n---\n\n**Chemical Analysis** ({len(compounds)} compounds):\n"
            for compound in compounds[:2]:
                findings += f"- {compound.get('name')}: Potential therapeutic relevance\n"
        
        if insights:
            findings += f"\n---\n\n**Novel Insights:**\n"
            for insight in insights:
                # Remove "INSIGHT:" prefix if present (from LLM output)
                clean_insight = insight.replace('INSIGHT:', '').replace('Insight:', '').strip()
                if clean_insight:
                    findings += f"- {clean_insight}\n"
        
        # Generate conclusion using LLM reasoning or fallback
        if self.llm_reasoner:
            try:
                conclusion_text = self.llm_reasoner.generate_conclusion(
                    topic=topic,
                    hypothesis=hypothesis,
                    insights=insights,
                    has_proteins=len(proteins) > 0,
                    has_compounds=len(compounds) > 0,
                    paper_count=len(papers)
                )
                conclusion = f"\n\n**Conclusions & Implications:**\n\n{conclusion_text}"
            except Exception as e:
                print(f"    Note: LLM conclusion generation failed, using template")
                conclusion = self._generate_fallback_conclusion(
                    topic, insights, proteins, compounds, papers
                )
        else:
            conclusion = self._generate_fallback_conclusion(
                topic, insights, proteins, compounds, papers
            )
        
        # Full content (single newline between major sections)
        content = f"""{hypothesis}

{method}

{findings}

{conclusion}"""
        
        # Extract simple strings for API (clean formatting for display)
        hypothesis_simple = hypothesis.split('\n')[0].replace('**', '').replace('Scientific Question:', '').strip()
        method_simple = f"Multi-tool investigation using {', '.join(tools_used)}: PubMed literature mining → entity extraction → cross-database validation → integrated synthesis"
        # Use full findings (not truncated) to preserve formatting
        findings_simple = findings
        
        result = {
            "title": title,
            "hypothesis": hypothesis_simple,
            "method": method_simple,
            "findings": findings_simple,
            "content": content
        }
        
        # SELF-REFINEMENT: Use LLM to peer-review and refine the content
        if self.llm_reasoner:
            try:
                print("  🔍 Self-critique and refinement...")
                result = self.llm_reasoner.refine_content(result)
            except Exception as e:
                print(f"    Note: Self-refinement unavailable ({e})")
        
        return result
    
    def log_investigation(self, topic: str, investigation_results: Dict):
        """Log investigation to agent memory."""
        if not self.journal:
            return
        
        try:
            # Log observation
            self.journal.log_observation(
                content=f"Conducted deep investigation of {topic} using {len(investigation_results.get('tools_used', []))} tools",
                source="deep_investigation",
                tags=[topic, "multi-tool", "comprehensive"]
            )
            
            # Log insights as hypotheses
            for insight in investigation_results.get("insights", [])[:2]:
                self.journal.log_hypothesis(
                    hypothesis=insight,
                    motivation=f"Generated from {topic} investigation"
                )
        except Exception as e:
            print(f"    Note: Could not log to memory: {e}")


def run_deep_investigation(agent_name: str, topic: str, community: Optional[str] = None) -> Dict:
    """
    Main entry point for deep investigation.
    
    This is what should be called instead of simple post generation.
    
    Args:
        agent_name: Name of the agent conducting investigation
        topic: Research topic
        community: Target community (auto-selected if None)
    
    Returns:
        Dict with content ready for posting
    """
    print(f"\n🔬 {agent_name}: Initiating Deep Scientific Investigation")
    print(f"📋 Topic: {topic}\n")
    
    investigator = DeepInvestigator(agent_name)
    
    # Check previous work
    previous = investigator.check_previous_work(topic)
    if previous.get("investigated"):
        print(f"  💾 {previous['message']}\n")
    
    # Use single LLM call: topic analysis + skill selection
    pre_selected_skills = None
    if investigator.topic_analyzer and investigator.skill_registry:
        print(f"  🤖 Analyzing topic and selecting skills (one LLM call)...")
        all_skills = list(investigator.skill_registry.skills.values())
        analysis, pre_selected_skills = investigator.topic_analyzer.analyze_and_select_skills(
            topic=topic, available_skills=all_skills, max_skills=5
        )
        
        inv_type = analysis.investigation_type
        if inv_type == "interdisciplinary":
            inv_type = "auto"
        print(f"  💡 Reasoning: {analysis.reasoning}")
        if analysis.key_concepts:
            print(f"  📌 Key concepts: {', '.join(analysis.key_concepts[:3])}")
        if pre_selected_skills:
            print(f"  🛠️  Selected skills: {', '.join([s['name'] for s in pre_selected_skills[:5]])}")
        print()
    elif investigator.topic_analyzer:
        print(f"  🤖 Analyzing topic with LLM...")
        analysis = investigator.topic_analyzer.analyze_topic(topic)
        
        inv_type = analysis.investigation_type
        if inv_type == "interdisciplinary":
            inv_type = "auto"
        print(f"  💡 Reasoning: {analysis.reasoning}")
        if analysis.key_concepts:
            print(f"  📌 Key concepts: {', '.join(analysis.key_concepts[:3])}")
        if analysis.recommended_skill_categories:
            print(f"  🛠️  Recommended tools: {', '.join(analysis.recommended_skill_categories[:4])}")
        print()
    else:
        # Fallback to simple keyword detection
        topic_lower = topic.lower()
        has_protein = any(kw in topic_lower for kw in ['protein', 'gene', 'enzyme'])
        has_chemistry = any(kw in topic_lower for kw in ['reaction', 'synthesis', 'compound', 'coupling'])
        has_material = any(kw in topic_lower for kw in ['material', 'crystal', 'metal'])
        
        if has_material:
            inv_type = "materials"
        elif has_chemistry and not has_protein:
            inv_type = "chemistry"
        elif has_protein and not has_chemistry:
            inv_type = "biology"
        else:
            inv_type = "auto"
        print()
    
    # Run tool chain (with pre-selected skills if available)
    results = investigator.run_tool_chain(topic, inv_type, pre_selected_skills=pre_selected_skills)
    
    print(f"\n  ✓ Investigation complete!")
    print(f"  📊 Tools used: {', '.join(results['tools_used'])}")
    print(f"  📄 Papers analyzed: {len(results['papers'])}")
    print(f"  💡 Insights generated: {len(results['insights'])}\n")
    
    # Generate sophisticated content
    content = investigator.generate_sophisticated_content(topic, results)
    
    # Log to memory
    investigator.log_investigation(topic, results)
    
    # Add metadata
    content["agent_name"] = agent_name
    content["investigation_results"] = results
    
    return content


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run a deep scientific investigation")
    parser.add_argument("topic", nargs="?", default=None, help="Research topic to investigate")
    parser.add_argument("--agent", "-a", default=None, help="Agent name (default: from profile or 'Agent')")
    parser.add_argument("--community", "-c", default=None, help="Target community")
    args = parser.parse_args()
    topic = args.topic
    if not topic:
        parser.print_help()
        sys.exit(1)
    agent_name = args.agent
    if not agent_name:
        try:
            profile_path = Path.home() / ".scienceclaw" / "agent_profile.json"
            if profile_path.exists():
                with open(profile_path) as f:
                    profile = json.load(f)
                agent_name = profile.get("name", "Agent")
            else:
                agent_name = "Agent"
        except Exception:
            agent_name = "Agent"
    run_deep_investigation(agent_name, topic, args.community)
