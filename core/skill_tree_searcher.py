"""
Skill Tree Searcher - Hierarchical skill discovery for ScienceClaw.

Adapted from AgentSkillOS (github.com/ynulihao/AgentSkillOS) searcher.py.

Key differences from the original:
- Tree is built from local SKILL.md files (not GitHub repos)
- LLM is ScienceClaw's LLMClient (not litellm)
- No GUI / web callbacks
- Tree YAML is auto-generated from the skill registry on first use

Algorithm (same as AgentSkillOS):
1. Build 3-level capability tree: Domain → Function → Skill
2. Recursive LLM-guided descent: at each node, LLM picks which branches to explore
3. Parallel exploration of sibling branches (ThreadPoolExecutor)
4. Leaf-level skill selection: LLM filters skills in the chosen function
5. Optional pruning: LLM deduplicates across branches
6. Returns selected skills with reasons, ready for DAG planning
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

import yaml

from core.llm_client import get_llm_client
from core.skill_registry import get_registry


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    """A leaf-level skill in the capability tree."""
    id: str            # skill directory name, e.g. "pubmed"
    name: str          # human-readable name
    description: str
    category: str
    path: str          # absolute path to skill dir


@dataclass
class TreeNode:
    """An interior node (Domain or Function) in the capability tree."""
    id: str
    name: str
    description: str = ""
    children: List["TreeNode"] = field(default_factory=list)
    skills: List[Skill] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def count_all_skills(self) -> int:
        if self.is_leaf:
            return len(self.skills)
        return sum(c.count_all_skills() for c in self.children)

    def collect_all_skills(self) -> List[Skill]:
        if self.is_leaf:
            return list(self.skills)
        result = []
        for c in self.children:
            result.extend(c.collect_all_skills())
        return result


@dataclass
class SearchResult:
    """Result of a tree search."""
    selected_skills: List[Skill]
    llm_calls: int = 0
    parallel_rounds: int = 0
    explored_nodes: List[str] = field(default_factory=list)
    reasons: Dict[str, str] = field(default_factory=dict)  # skill_id -> reason


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

NODE_SELECTION_PROMPT = """\
You are helping select relevant branches of a scientific skill tree for a research query.

Research query: {query}

Available branches:
{options}

Select the branches most likely to contain useful skills for this query.
Return a JSON array of branch IDs. Only include branches that are genuinely relevant.
Example: {example}

Return ONLY the JSON array, no explanation.
"""

SKILL_SELECTION_PROMPT = """\
You are selecting specific scientific tools/skills for a research query.

Research query: {query}

Available skills:
{options}

Select the skills that would be most useful for investigating this query.
For each selected skill, provide a brief reason.

Return a JSON array of objects with "id" and "reason" fields.
Example: [{{"id": "pubmed", "reason": "Search literature on this topic"}}, ...]

Return ONLY the JSON array, no explanation.
"""

SKILL_PRUNE_PROMPT = """\
You have collected skills from multiple branches of a capability tree for this query:

Research query: {query}

Skills collected:
{skills_list}

Some skills may be redundant (e.g. both "pubmed" and "pubmed-database" do similar things).
Prune to keep the best representative from each functional group.
Return a JSON array of skill IDs to KEEP (remove redundant ones).

Return ONLY the JSON array of IDs to keep, no explanation.
"""

DAG_PLAN_PROMPT = """\
You are planning a multi-step scientific investigation as a dependency graph.

Research query: {query}

Selected skills to use:
{skills_list}

Create an execution plan as a directed acyclic graph (DAG).
Skills that need output from another skill should list it in depends_on.

Common patterns:
- Literature search (pubmed/arxiv) runs first, feeds protein/compound searches
- Protein databases (uniprot/pdb) run after literature to characterize found proteins
- Compound databases (pubchem/chembl) run after literature to characterize compounds
- Prediction tools (tdc/rdkit/deepchem) run after compound databases
- Integration/synthesis runs last, depends on everything else

Return a JSON array of node objects:
[
  {{
    "id": "unique_id",
    "name": "skill_name",
    "depends_on": ["other_id", ...],
    "purpose": "one sentence why this skill is included",
    "skill_type": "primary" or "helper",
    "params": {{"key": "value"}}
  }},
  ...
]

Rules:
- Every skill in the list must appear as exactly one node
- depends_on must only reference IDs defined in the same array
- skill_type "primary" = produces final investigation content; "helper" = feeds data to primary
- params should include the main query/search term appropriate for this skill

Return ONLY the JSON array, no explanation.
"""


# ---------------------------------------------------------------------------
# Tree builder
# ---------------------------------------------------------------------------

# 3-level taxonomy: Domain -> Function -> skills (by category)
# Domains and functions are defined here; skills are assigned from the registry.
CAPABILITY_TAXONOMY = {
    "biology": {
        "description": "Biological databases, sequence analysis, and molecular biology tools",
        "functions": {
            "literature": {
                "description": "Scientific literature search and retrieval",
                "exact_names": {"pubmed", "arxiv", "biorxiv-database", "pubmed-database",
                                "openalex-database", "citation-management", "research-lookup",
                                "literature-review", "scholar-evaluation", "peer-review",
                                "offer-k-dense-web", "firecrawl-scraper", "browser-automation"},
            },
            "proteins": {
                "description": "Protein sequence, structure, and function databases",
                "exact_names": {"uniprot", "uniprot-database", "pdb", "pdb-database",
                                "alphafold-database", "sequence", "esm"},
            },
            "genomics": {
                "description": "Genomics, transcriptomics, and gene databases",
                "exact_names": {"blast", "ensembl-database", "ena-database", "gene-database",
                                "gwas-database", "deeptools", "scanpy", "pydeseq2",
                                "biopython", "pysam", "scikit-bio", "anndata", "scvi-tools",
                                "arboreto", "gget", "etetoolkit", "flowio", "pathml",
                                "histolab", "neuropixels-analysis", "geniml", "hypogenic",
                                "gtars", "hypothesis-generation"},
            },
            "pathways": {
                "description": "Biological pathways, networks, and interaction databases",
                "exact_names": {"reactome-database", "string-database", "kegg", "kegg-database",
                                "cobrapy", "bioservices", "opentargets-database",
                                "metabolomics-workbench-database", "hmdb-database"},
            },
            "clinical": {
                "description": "Clinical data, trials, variants, and disease databases",
                "exact_names": {"clinicaltrials-database", "clinvar-database", "clinpgx-database",
                                "cosmic-database", "brenda-database", "clinical-decision-support",
                                "clinical-reports", "treatment-plans", "pyhealth", "pydicom"},
            },
        }
    },
    "chemistry": {
        "description": "Chemical databases, drug discovery, and cheminformatics tools",
        "functions": {
            "compound_databases": {
                "description": "Chemical compound databases and property lookup",
                "exact_names": {"pubchem", "pubchem-database", "chembl", "chembl-database",
                                "drugbank-database", "zinc-database", "cas", "nistwebbook",
                                "brenda-database", "uspto-database", "matchms",
                                "fda-database", "geo-database", "fred-economic-data"},
            },
            "drug_discovery": {
                "description": "ADMET prediction, virtual screening, and drug-likeness",
                "exact_names": {"tdc", "pytdc", "deepchem", "diffdock", "torchdrug",
                                "molfeat", "datamol", "rowan", "medchem", "benchling-integration"},
            },
            "cheminformatics": {
                "description": "Chemical structure analysis, fingerprints, and molecular properties",
                "exact_names": {"rdkit", "pyopenms", "neurokit2"},
            },
        }
    },
    "materials": {
        "description": "Materials science databases and simulation tools",
        "functions": {
            "materials_science": {
                "description": "Crystal structures, materials properties, and thermodynamics",
                "exact_names": {"materials", "pymatgen", "aeon", "ase", "qmmm_adaptive",
                                "astropy", "matlab", "mopac", "fluidsim"},
            },
            "quantum": {
                "description": "Quantum chemistry and quantum computing tools",
                "exact_names": {"qiskit", "qutip", "cirq", "pennylane"},
            },
        }
    },
    "computational": {
        "description": "Machine learning, data analysis, and scientific computing tools",
        "functions": {
            "machine_learning": {
                "description": "ML frameworks, model training, and prediction",
                "exact_names": {"scikit-learn", "pytorch-lightning", "transformers",
                                "stable-baselines3", "shap", "umap-learn", "pymc",
                                "statsmodels", "statistical-analysis", "torch_geometric",
                                "scikit-survival", "pufferlib", "pymoo",
                                "prompt-engineering-patterns", "tooluniverse"},
            },
            "data_analysis": {
                "description": "Data processing, visualization, and bioinformatics pipelines",
                "exact_names": {"dask", "vaex", "zarr-python", "seaborn", "datavis",
                                "matplotlib", "scientific-visualization", "scientific-schematics",
                                "datacommons-client", "exploratory-data-analysis",
                                "infographics", "sympy", "polars", "plotly", "networkx",
                                "data-storytelling", "diagramming", "xlsx", "pdf", "docx"},
            },
            "simulation": {
                "description": "Molecular dynamics and systems biology simulation",
                "exact_names": {"openmm", "simpy"},
            },
            "scientific_writing": {
                "description": "Research communication, writing, and presentation tools",
                "exact_names": {"scientific-writing", "scientific-slides", "scientific-brainstorming",
                                "scientific-critical-thinking", "research-grants", "venue-templates",
                                "document-skills", "markitdown", "pptx-posters", "latex-posters",
                                "geopandas", "fabric"},
            },
        }
    },
    "platform": {
        "description": "Platform integrations, web search, and community tools",
        "functions": {
            "search": {
                "description": "Web search and general information retrieval",
                "exact_names": {"websearch", "perplexity-search"},
            },
            "platforms": {
                "description": "Lab management, collaboration, and data sharing platforms",
                "exact_names": {"infinite", "benchling-integration",
                                "dnanexus-integration", "adaptyv", "cellxgene-census",
                                "denario", "pylabrobot", "omero-integration",
                                "modal", "market-research-reports", "iso-13485-certification",
                                "latchbio-integration", "labarchive-integration",
                                "protocolsio-integration", "opentrons-integration",
                                "imaging-data-commons", "lamindb", "paper-2-web",
                                "get-available-resources", "generate-image"},
            },
        }
    },
}


def build_capability_tree(registry=None) -> TreeNode:
    """
    Build a 3-level capability tree from the skill registry.

    Returns the root TreeNode with Domain -> Function -> Skill hierarchy.
    """
    if registry is None:
        registry = get_registry()

    all_skills = registry.skills  # dict: name -> metadata

    # Build a lookup: skill_name -> Skill object
    skill_objects: Dict[str, Skill] = {}
    for name, meta in all_skills.items():
        skill_objects[name] = Skill(
            id=name,
            name=name.replace("-", " ").replace("_", " ").title(),
            description=meta.get("description", ""),
            category=meta.get("category", "general"),
            path=meta.get("path", ""),
        )

    # Track assigned skills to catch stragglers
    assigned: set = set()

    root = TreeNode(id="root", name="ScienceClaw Skills", description="All available scientific skills")

    for domain_id, domain_def in CAPABILITY_TAXONOMY.items():
        domain_node = TreeNode(
            id=domain_id,
            name=domain_id.title(),
            description=domain_def["description"],
        )

        for func_id, func_def in domain_def["functions"].items():
            func_node = TreeNode(
                id=f"{domain_id}.{func_id}",
                name=func_id.replace("_", " ").title(),
                description=func_def["description"],
            )

            exact_names = func_def.get("exact_names", set())

            for skill_name, skill_obj in skill_objects.items():
                if skill_name not in assigned and skill_name in exact_names:
                    func_node.skills.append(skill_obj)
                    assigned.add(skill_name)

            if func_node.skills:
                domain_node.children.append(func_node)

        if domain_node.children:
            root.children.append(domain_node)

    # Catch any unassigned skills into a "general" bucket
    unassigned = [s for name, s in skill_objects.items() if name not in assigned]
    if unassigned:
        other_node = TreeNode(
            id="other",
            name="Other",
            description="General and uncategorized skills",
        )
        leaf = TreeNode(
            id="other.general",
            name="General",
            description="Miscellaneous scientific tools",
        )
        leaf.skills = unassigned
        other_node.children.append(leaf)
        root.children.append(other_node)

    return root


# ---------------------------------------------------------------------------
# Searcher
# ---------------------------------------------------------------------------

class SkillTreeSearcher:
    """
    Multi-level tree search with LLM-guided navigation.

    Replicates the AgentSkillOS Searcher algorithm:
    - Recursive descent through Domain → Function → Skill
    - LLM selects which branches to explore at each level
    - Parallel exploration of sibling branches
    - Optional pruning of redundant skills
    - Returns selected skills + DAG execution plan
    """

    def __init__(
        self,
        agent_name: str = "Agent",
        max_parallel: int = 3,
        expand_threshold: int = 3,     # auto-expand if <= N children (no LLM call)
        early_stop_skill_count: int = 5, # if only child has <= N skills, select all directly
        prune_enabled: bool = True,
        on_event: Optional[Callable[[str, dict], None]] = None,
    ):
        self.agent_name = agent_name
        self.max_parallel = max_parallel
        self.expand_threshold = expand_threshold
        self.early_stop_skill_count = early_stop_skill_count
        self.prune_enabled = prune_enabled
        self.on_event = on_event or (lambda event, data: None)

        self._llm = get_llm_client(agent_name=agent_name)
        self._tree: Optional[TreeNode] = None
        self._lock = threading.Lock()

        # Counters (reset per search)
        self._llm_calls = 0
        self._parallel_rounds = 0
        self._explored_nodes: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, verbose: bool = False) -> SearchResult:
        """
        Execute a hierarchical skill search for the given query.

        Returns a SearchResult with selected skills and stats.
        """
        self._llm_calls = 0
        self._parallel_rounds = 0
        self._explored_nodes = []

        if self._tree is None:
            if verbose:
                print("  [tree] Building capability tree from skill registry...")
            self._tree = build_capability_tree()
            if verbose:
                total = self._tree.count_all_skills()
                print(f"  [tree] Tree built: {len(self._tree.children)} domains, {total} skills")

        selected = self._search_node(query, self._tree, depth=0, verbose=verbose)

        if self.prune_enabled and len(selected) > 1:
            if verbose:
                print(f"  [tree] Pruning {len(selected)} skills...")
            selected = self._prune_skills(query, selected, verbose)

        reasons: Dict[str, str] = {}
        # Reasons populated during _select_skills; stored in skill.description temporarily
        # (see _select_skills_with_reasons)

        self.on_event("search_complete", {
            "query": query,
            "selected_count": len(selected),
            "llm_calls": self._llm_calls,
        })

        return SearchResult(
            selected_skills=selected,
            llm_calls=self._llm_calls,
            parallel_rounds=self._parallel_rounds,
            explored_nodes=list(self._explored_nodes),
            reasons=reasons,
        )

    def plan_dag(self, query: str, skills: List[Skill], verbose: bool = False) -> List[dict]:
        """
        Ask the LLM to produce a DAG execution plan for the selected skills.

        Returns a list of node dicts suitable for build_graph_from_plan().
        """
        skills_list = "\n".join(
            f"- {s.id}: {s.description[:120]}"
            for s in skills
        )
        prompt = DAG_PLAN_PROMPT.format(query=query, skills_list=skills_list)
        response = self._call_llm(prompt, max_tokens=1500)

        nodes = self._parse_json(response)
        if isinstance(nodes, list):
            return nodes

        if verbose:
            print("  [dag] LLM returned non-list response, using sequential fallback")
        return self._sequential_fallback_plan(skills)

    def search_and_plan(self, query: str, verbose: bool = False) -> tuple[SearchResult, List[dict]]:
        """
        Convenience method: search for skills then produce a DAG plan.

        Returns (SearchResult, dag_nodes_list).
        """
        result = self.search(query, verbose=verbose)
        if not result.selected_skills:
            return result, []

        dag_nodes = self.plan_dag(query, result.selected_skills, verbose=verbose)
        return result, dag_nodes

    # ------------------------------------------------------------------
    # Recursive tree descent
    # ------------------------------------------------------------------

    def _search_node(self, query: str, node: TreeNode, depth: int, verbose: bool) -> List[Skill]:
        self._explored_nodes.append(node.id)
        self.on_event("node_enter", {"id": node.id, "depth": depth})

        # Leaf node: select from skills directly
        if node.is_leaf:
            if not node.skills:
                return []
            return self._select_skills(query, node.skills, depth, verbose)

        children = node.children

        # Root node: always expand all domains
        if node.id == "root":
            selected_children = self._select_children(query, children, depth, verbose)
        # Auto-expand small sets (no LLM call needed)
        elif len(children) <= self.expand_threshold:
            selected_children = children
        else:
            selected_children = self._select_children(query, children, depth, verbose)

        if not selected_children:
            return []

        # Early stopping: if single child has very few skills, grab them all
        if len(selected_children) == 1:
            only = selected_children[0]
            total = only.count_all_skills()
            if total <= self.early_stop_skill_count:
                all_skills = only.collect_all_skills()
                return self._select_skills(query, all_skills, depth + 1, verbose)

        # Recurse: parallel for multiple children
        if len(selected_children) > 1:
            results = self._parallel_search(query, selected_children, depth + 1, verbose)
            self._parallel_rounds += 1
        else:
            results = self._search_node(query, selected_children[0], depth + 1, verbose)

        return results

    def _parallel_search(self, query: str, children: List[TreeNode],
                         depth: int, verbose: bool) -> List[Skill]:
        results: List[Skill] = []
        max_w = min(len(children), self.max_parallel)

        with ThreadPoolExecutor(max_workers=max_w) as executor:
            futures = {
                executor.submit(self._search_node, query, child, depth, verbose): child
                for child in children
            }
            for future in as_completed(futures):
                try:
                    child_results = future.result()
                    with self._lock:
                        results.extend(child_results)
                except Exception as e:
                    if verbose:
                        print(f"  [tree] Branch search error: {e}")

        return results

    # ------------------------------------------------------------------
    # LLM-guided selection
    # ------------------------------------------------------------------

    def _select_children(self, query: str, children: List[TreeNode],
                         depth: int, verbose: bool) -> List[TreeNode]:
        """LLM picks which child branches to explore."""
        child_map = {c.id: c for c in children}

        options_lines = []
        for c in children:
            skill_count = c.count_all_skills()
            line = f"- {c.id}: {c.name} ({skill_count} skills)"
            if c.description:
                line += f" — {c.description}"
            options_lines.append(line)

        example = json.dumps([c.id for c in children[:2]])
        prompt = NODE_SELECTION_PROMPT.format(
            query=query,
            options="\n".join(options_lines),
            example=example,
        )

        response = self._call_llm(prompt, max_tokens=300)
        selected_ids = self._parse_id_list(response)

        if verbose:
            indent = "  " * depth
            print(f"{indent}[tree] Selected branches: {selected_ids}")

        self.on_event("children_selected", {"ids": selected_ids, "depth": depth})

        # Fall back to all children if LLM returns nothing valid
        valid = [child_map[sid] for sid in selected_ids if sid in child_map]
        return valid if valid else children

    def _select_skills(self, query: str, skills: List[Skill],
                       depth: int, verbose: bool) -> List[Skill]:
        """LLM picks relevant skills from a leaf node."""
        if not skills:
            return []

        # For very small sets, return all without an LLM call
        if len(skills) <= 2:
            return skills

        skill_map = {s.id: s for s in skills}

        options_lines = []
        for s in skills:
            desc = s.description[:150]
            if len(s.description) > 150:
                desc += "..."
            options_lines.append(f"- {s.id}: {desc}")

        prompt = SKILL_SELECTION_PROMPT.format(
            query=query,
            options="\n".join(options_lines),
        )

        response = self._call_llm(prompt, max_tokens=500)
        selected = self._parse_skill_selection(response)

        if verbose:
            indent = "  " * depth
            ids = [item["id"] for item in selected]
            print(f"{indent}[tree] Selected skills: {ids}")

        self.on_event("skills_selected", {"skills": selected, "depth": depth})

        result = []
        for item in selected:
            sid = item.get("id", "")
            if sid in skill_map:
                result.append(skill_map[sid])

        return result if result else skills[:3]  # fallback: top 3

    def _prune_skills(self, query: str, skills: List[Skill], verbose: bool) -> List[Skill]:
        """LLM removes redundant skills from the final list."""
        skill_map = {s.id: s for s in skills}

        skills_lines = []
        for s in skills:
            skills_lines.append(f"- {s.id}: {s.description[:200]}")

        prompt = SKILL_PRUNE_PROMPT.format(
            query=query,
            skills_list="\n".join(skills_lines),
        )

        response = self._call_llm(prompt, max_tokens=300)
        keep_ids = self._parse_id_list(response)

        if verbose:
            print(f"  [tree] After pruning: {keep_ids}")

        self.on_event("prune_complete", {"kept": keep_ids})

        result = [skill_map[sid] for sid in keep_ids if sid in skill_map]
        # Safety: if LLM returns garbage, keep all
        return result if result else skills

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        with self._lock:
            self._llm_calls += 1
        return self._llm.call(prompt, max_tokens=max_tokens, temperature=0.2)

    def _parse_json(self, text: str):
        """Extract and parse the first JSON value from LLM output."""
        # Strip markdown code fences
        text = text.strip()
        for fence in ("```json", "```"):
            if text.startswith(fence):
                text = text[len(fence):]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Find first [ or {
        for start_char, end_char in (("[", "]"), ("{", "}")):
            idx = text.find(start_char)
            if idx != -1:
                # Find matching closing bracket
                depth = 0
                for i, ch in enumerate(text[idx:], idx):
                    if ch == start_char:
                        depth += 1
                    elif ch == end_char:
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[idx:i + 1])
                            except json.JSONDecodeError:
                                break
        try:
            return json.loads(text)
        except Exception:
            return None

    def _parse_id_list(self, text: str) -> List[str]:
        """Parse a JSON array of string IDs from LLM output."""
        parsed = self._parse_json(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if isinstance(item, str)]
        return []

    def _parse_skill_selection(self, text: str) -> List[dict]:
        """Parse a JSON array of {id, reason} objects from LLM output."""
        parsed = self._parse_json(text)
        if isinstance(parsed, list):
            result = []
            for item in parsed:
                if isinstance(item, dict) and "id" in item:
                    result.append({"id": item["id"], "reason": item.get("reason", "")})
                elif isinstance(item, str):
                    result.append({"id": item, "reason": ""})
            return result
        return []

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _sequential_fallback_plan(self, skills: List[Skill]) -> List[dict]:
        """
        Simple fallback DAG: literature search first, everything else after.
        Used when the LLM fails to return a valid plan.
        """
        literature = {"pubmed", "arxiv", "biorxiv-database", "openalex-database", "pubmed-database"}
        nodes = []
        lit_ids = []

        for i, skill in enumerate(skills):
            node_id = f"node_{i}"
            is_lit = skill.id in literature
            depends = [] if is_lit else lit_ids
            nodes.append({
                "id": node_id,
                "name": skill.id,
                "depends_on": depends,
                "purpose": f"Investigate using {skill.id}",
                "skill_type": "primary" if is_lit else "helper",
                "params": {},
            })
            if is_lit:
                lit_ids.append(node_id)

        return nodes


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def search_skills_for_topic(
    topic: str,
    agent_name: str = "Agent",
    verbose: bool = False,
    plan_dag: bool = True,
) -> tuple[List[Skill], List[dict]]:
    """
    High-level entry point: search for skills and optionally plan a DAG.

    Returns:
        (selected_skills, dag_nodes)
        dag_nodes is empty if plan_dag=False
    """
    searcher = SkillTreeSearcher(agent_name=agent_name)
    result = searcher.search(topic, verbose=verbose)

    dag_nodes: List[dict] = []
    if plan_dag and result.selected_skills:
        dag_nodes = searcher.plan_dag(topic, result.selected_skills, verbose=verbose)

    return result.selected_skills, dag_nodes
