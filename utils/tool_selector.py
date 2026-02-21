#!/usr/bin/env python3
"""
Tool Selector

Recommends appropriate scientific tools based on hypothesis types and
research questions.

Maps research domains to ScienceClaw's 18 available tools:
- Biology: blast, pubmed, uniprot, pdb, sequence, arxiv
- Chemistry: pubchem, chembl, tdc, cas, nistwebbook, rdkit
- Materials: materials (Materials Project)
- Utils: datavis, websearch
- Platforms: infinite

Author: ScienceClaw Team
"""

from typing import List, Dict, Any, Set


# Tool registry with capabilities
TOOL_REGISTRY = {
    # Biology tools
    "blast": {
        "domain": "biology",
        "capabilities": ["sequence_homology", "protein_search", "gene_search"],
        "input": "protein or DNA sequence",
        "output": "homologous sequences with alignment scores",
        "use_cases": ["find similar proteins", "identify gene function", "evolutionary analysis"]
    },
    "pubmed": {
        "domain": "biology",
        "capabilities": ["literature_search", "paper_discovery", "citation_analysis"],
        "input": "search query or keywords",
        "output": "list of research papers with abstracts",
        "use_cases": ["background research", "find existing studies", "literature review"]
    },
    "uniprot": {
        "domain": "biology",
        "capabilities": ["protein_annotation", "protein_function", "protein_structure"],
        "input": "protein name or accession",
        "output": "protein annotations and metadata",
        "use_cases": ["protein function lookup", "domain analysis", "functional annotation"]
    },
    "pdb": {
        "domain": "biology",
        "capabilities": ["protein_structure", "structure_visualization", "binding_sites"],
        "input": "PDB ID or protein name",
        "output": "3D structure coordinates",
        "use_cases": ["view protein structure", "analyze binding sites", "structural comparison"]
    },
    "sequence": {
        "domain": "biology",
        "capabilities": ["sequence_analysis", "motif_search", "sequence_translation"],
        "input": "DNA or protein sequence",
        "output": "sequence properties and analysis",
        "use_cases": ["sequence validation", "motif finding", "translation"]
    },
    "arxiv": {
        "domain": "biology",
        "capabilities": ["preprint_search", "recent_research", "methodology_discovery"],
        "input": "search query",
        "output": "preprint papers",
        "use_cases": ["find cutting-edge research", "methodology discovery"]
    },
    
    # Chemistry tools
    "pubchem": {
        "domain": "chemistry",
        "capabilities": ["compound_search", "chemical_properties", "structure_lookup"],
        "input": "compound name or SMILES",
        "output": "chemical properties and identifiers",
        "use_cases": ["find compound properties", "get chemical structure", "CID lookup"]
    },
    "chembl": {
        "domain": "chemistry",
        "capabilities": ["bioactivity_data", "drug_discovery", "target_analysis"],
        "input": "compound or target name",
        "output": "bioactivity measurements and assays",
        "use_cases": ["drug activity lookup", "target bioactivity", "SAR analysis"]
    },
    "tdc": {
        "domain": "chemistry",
        "capabilities": ["admet_prediction", "toxicity_prediction", "bbb_prediction"],
        "input": "SMILES string",
        "output": "predicted ADMET properties",
        "use_cases": ["predict BBB penetration", "predict toxicity", "drug-likeness"]
    },
    "cas": {
        "domain": "chemistry",
        "capabilities": ["chemical_lookup", "cas_number_search", "compound_properties"],
        "input": "CAS number or compound name",
        "output": "compound information",
        "use_cases": ["CAS number lookup", "chemical identity verification"]
    },
    "nistwebbook": {
        "domain": "chemistry",
        "capabilities": ["spectroscopy_data", "thermochemistry", "reaction_data"],
        "input": "compound name or formula",
        "output": "spectroscopic and thermodynamic data",
        "use_cases": ["IR/MS spectra lookup", "thermodynamic properties"]
    },
    "rdkit": {
        "domain": "chemistry",
        "capabilities": ["cheminformatics", "descriptor_calculation", "similarity_search"],
        "input": "SMILES or molecular structure",
        "output": "molecular descriptors and properties",
        "use_cases": ["calculate descriptors", "substructure search", "similarity"]
    },
    
    # Materials science
    "materials": {
        "domain": "materials",
        "capabilities": ["materials_properties", "crystal_structure", "band_gap"],
        "input": "material formula or ID",
        "output": "material properties from Materials Project",
        "use_cases": ["material property lookup", "band gap calculation", "structure data"]
    },
    
    # Utility tools
    "datavis": {
        "domain": "utility",
        "capabilities": ["data_visualization", "plotting", "graph_generation"],
        "input": "data arrays or CSV",
        "output": "plots and visualizations",
        "use_cases": ["plot experimental data", "create graphs", "visualize trends"]
    },
    "websearch": {
        "domain": "utility",
        "capabilities": ["web_search", "general_information", "recent_news"],
        "input": "search query",
        "output": "web search results",
        "use_cases": ["find general information", "web lookup", "news search"]
    },
    
    # Platform tools
    "infinite": {
        "domain": "platform",
        "capabilities": ["community_interaction", "post_creation", "peer_discussion"],
        "input": "post content",
        "output": "community response",
        "use_cases": ["share findings on Infinite", "peer collaboration"]
    }
}


def recommend_tools_for_hypothesis(
    hypothesis: str,
    agent_profile: Dict[str, Any]
) -> List[str]:
    """
    Recommend tools for investigating a hypothesis.
    
    Uses keyword matching and agent profile to suggest relevant tools.
    
    Args:
        hypothesis: Research hypothesis or question
        agent_profile: Agent's profile (interests, preferred_tools)
    
    Returns:
        List of recommended tool names (ordered by relevance)
    """
    hypothesis_lower = hypothesis.lower()
    
    # Extract keywords from hypothesis
    keywords = _extract_keywords(hypothesis_lower)
    
    # Score each tool
    scores = {}
    for tool_name, tool_info in TOOL_REGISTRY.items():
        score = 0.0
        
        # Match capabilities
        for capability in tool_info["capabilities"]:
            if any(kw in capability for kw in keywords):
                score += 2.0
        
        # Match use cases
        for use_case in tool_info["use_cases"]:
            if any(kw in use_case for kw in keywords):
                score += 1.0
        
        # Match domain
        domain = tool_info["domain"]
        if domain in hypothesis_lower:
            score += 1.0
        
        # Boost if in agent's preferred tools
        preferred_tools = agent_profile.get("preferred_tools", [])
        if tool_name in preferred_tools:
            score += 3.0
        
        # Boost based on agent profile
        profile_type = agent_profile.get("profile", "mixed")
        if profile_type == "biology" and domain == "biology":
            score += 1.0
        elif profile_type == "chemistry" and domain == "chemistry":
            score += 1.0
        elif profile_type == "mixed":
            score += 0.5  # Slight boost for all tools
        
        if score > 0:
            scores[tool_name] = score
    
    # Sort by score and return
    sorted_tools = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [tool for tool, score in sorted_tools]


def _extract_keywords(text: str) -> Set[str]:
    """Extract relevant keywords from hypothesis text."""
    # Biology keywords
    bio_keywords = {
        "protein", "gene", "sequence", "dna", "rna", "structure",
        "binding", "homolog", "blast", "mutation", "domain", "fold",
        "enzyme", "receptor", "ligand", "pathway"
    }
    
    # Chemistry keywords
    chem_keywords = {
        "compound", "molecule", "drug", "chemical", "smiles", "synthesis",
        "reaction", "admet", "toxicity", "bbb", "solubility", "activity",
        "bioactivity", "inhibitor", "agonist", "antagonist", "spectrum"
    }
    
    # Materials keywords
    mat_keywords = {
        "material", "crystal", "band", "gap", "semiconductor", "metal",
        "oxide", "conductivity", "lattice"
    }
    
    # General science keywords
    general_keywords = {
        "predict", "analyze", "search", "find", "identify", "measure",
        "calculate", "compare", "visualize", "model"
    }
    
    all_keywords = bio_keywords | chem_keywords | mat_keywords | general_keywords
    
    # Find matching keywords
    found_keywords = set()
    for keyword in all_keywords:
        if keyword in text:
            found_keywords.add(keyword)
    
    return found_keywords


def get_tool_pipeline(hypothesis: str, agent_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate a multi-step tool pipeline for a hypothesis.
    
    Creates a sequence of tools to execute in order, with suggested
    parameters and dependencies.
    
    Args:
        hypothesis: Research hypothesis
        agent_profile: Agent profile
    
    Returns:
        List of tool steps with metadata
    """
    recommended = recommend_tools_for_hypothesis(hypothesis, agent_profile)
    
    if not recommended:
        return []
    
    # Build pipeline
    pipeline = []
    
    # Typical patterns:
    # 1. Background research (pubmed/arxiv) -> specific analysis
    # 2. Compound lookup (pubchem) -> property prediction (tdc)
    # 3. Sequence search (blast) -> structure lookup (pdb)
    
    hypothesis_lower = hypothesis.lower()
    
    # Pattern 1: Literature + specific tool
    if "pubmed" in recommended:
        pipeline.append({
            "tool": "pubmed",
            "purpose": "background_research",
            "description": "Search for relevant literature"
        })
        recommended.remove("pubmed")
    
    # Pattern 2: Compound workflow
    if "pubchem" in recommended and "tdc" in recommended:
        pipeline.append({
            "tool": "pubchem",
            "purpose": "compound_lookup",
            "description": "Get compound structure and properties"
        })
        pipeline.append({
            "tool": "tdc",
            "purpose": "admet_prediction",
            "description": "Predict ADMET properties",
            "depends_on": "pubchem"
        })
        recommended.remove("pubchem")
        recommended.remove("tdc")
    
    # Pattern 3: Sequence workflow
    if "blast" in recommended and "pdb" in recommended:
        pipeline.append({
            "tool": "blast",
            "purpose": "sequence_search",
            "description": "Find homologous sequences"
        })
        pipeline.append({
            "tool": "pdb",
            "purpose": "structure_lookup",
            "description": "Get 3D structure of homologs",
            "depends_on": "blast"
        })
        recommended.remove("blast")
        recommended.remove("pdb")
    
    # Add remaining tools
    for tool in recommended[:3]:  # Limit to 3 additional tools
        if tool not in ["infinite"]:  # Skip platform tools
            pipeline.append({
                "tool": tool,
                "purpose": "analysis",
                "description": f"Analyze using {tool}"
            })
    
    return pipeline


def get_tool_info(tool_name: str) -> Dict[str, Any]:
    """Get detailed information about a tool."""
    return TOOL_REGISTRY.get(tool_name, {})


def list_tools_by_domain(domain: str) -> List[str]:
    """List all tools in a specific domain."""
    return [
        name for name, info in TOOL_REGISTRY.items()
        if info["domain"] == domain
    ]


# Test function
def test_tool_selector():
    """Test the tool selector with sample hypotheses."""
    
    sample_profile = {
        "profile": "mixed",
        "preferred_tools": ["blast", "pubmed", "tdc"],
        "interests": ["protein structure", "drug discovery"]
    }
    
    test_cases = [
        "Can we identify the protein structure of BRCA1?",
        "What is the BBB penetration of aspirin?",
        "Find homologous sequences to MTEYKLVVV protein",
        "Analyze the band gap of silicon dioxide materials"
    ]
    
    print("Testing recommend_tools_for_hypothesis():\n")
    for hypothesis in test_cases:
        print(f"Hypothesis: {hypothesis}")
        tools = recommend_tools_for_hypothesis(hypothesis, sample_profile)
        print(f"  Recommended: {tools[:5]}")
        
        pipeline = get_tool_pipeline(hypothesis, sample_profile)
        if pipeline:
            print(f"  Pipeline: {[step['tool'] for step in pipeline]}")
        print()
    
    print("\nTesting list_tools_by_domain():")
    for domain in ["biology", "chemistry", "materials", "utility"]:
        tools = list_tools_by_domain(domain)
        print(f"  {domain}: {tools}")
    
    print("\n✓ Tool selector tests complete")


if __name__ == "__main__":
    test_tool_selector()
