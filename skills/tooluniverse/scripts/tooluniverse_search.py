#!/usr/bin/env python3
"""
ToolUniverse search - discover 600+ computational biology and chemistry tools
via semantic search and standardized API.
"""

import argparse
import json
import sys

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


MOCK_TOOLS = {
    "biology": [
        {"name": "AlphaFold", "description": "Deep learning protein structure prediction from amino acid sequence", "api_endpoint": "https://alphafold.ebi.ac.uk/api"},
        {"name": "UniProt", "description": "Universal protein sequence and functional information database", "api_endpoint": "https://rest.uniprot.org"},
        {"name": "BLAST", "description": "Basic Local Alignment Search Tool for sequence similarity", "api_endpoint": "https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi"},
        {"name": "DESeq2", "description": "Differential expression analysis for RNA-seq count data", "api_endpoint": "https://bioconductor.org/packages/DESeq2"},
        {"name": "Ensembl", "description": "Genome browser and annotation database for vertebrate genomes", "api_endpoint": "https://rest.ensembl.org"},
        {"name": "STRING", "description": "Protein-protein interaction network database", "api_endpoint": "https://string-db.org/api"},
        {"name": "KEGG", "description": "Kyoto Encyclopedia of Genes and Genomes - pathway database", "api_endpoint": "https://rest.kegg.jp"},
        {"name": "PDB", "description": "Protein Data Bank - 3D structural data of biological molecules", "api_endpoint": "https://data.rcsb.org"},
    ],
    "chemistry": [
        {"name": "PubChem", "description": "Open chemistry database with molecular properties and bioassays", "api_endpoint": "https://pubchem.ncbi.nlm.nih.gov/rest/pug"},
        {"name": "ChEMBL", "description": "Bioactive molecules with drug-like properties and bioactivity data", "api_endpoint": "https://www.ebi.ac.uk/chembl/api/data"},
        {"name": "RDKit", "description": "Open-source cheminformatics library for molecular analysis", "api_endpoint": "local://rdkit"},
        {"name": "NIST WebBook", "description": "Thermochemical, spectroscopic and reaction kinetics data", "api_endpoint": "https://webbook.nist.gov/cgi/cbook.cgi"},
        {"name": "CAS SciFinder", "description": "Chemical Abstracts Service registry of compounds and reactions", "api_endpoint": "https://commonchemistry.cas.org/api"},
        {"name": "TDC", "description": "Therapeutics Data Commons - ADMET prediction models", "api_endpoint": "https://tdcommons.ai/api"},
    ],
    "genomics": [
        {"name": "GATK", "description": "Genome Analysis Toolkit for variant discovery and genotyping", "api_endpoint": "https://gatk.broadinstitute.org"},
        {"name": "BWA", "description": "Burrows-Wheeler Aligner for short read alignment to reference genome", "api_endpoint": "local://bwa"},
        {"name": "STAR", "description": "Spliced Transcripts Alignment to a Reference - RNA-seq aligner", "api_endpoint": "local://star"},
        {"name": "DESeq2", "description": "Differential expression analysis for RNA-seq count data", "api_endpoint": "https://bioconductor.org/packages/DESeq2"},
        {"name": "Salmon", "description": "Fast and bias-aware quantification of transcript expression", "api_endpoint": "local://salmon"},
    ],
    "proteomics": [
        {"name": "MaxQuant", "description": "Quantitative proteomics software for mass spectrometry data", "api_endpoint": "local://maxquant"},
        {"name": "Perseus", "description": "Computational platform for comprehensive analysis of proteomics data", "api_endpoint": "local://perseus"},
        {"name": "MSFragger", "description": "Ultra-fast database search tool for mass spectrometry data", "api_endpoint": "local://msfragger"},
        {"name": "AlphaFold", "description": "Deep learning protein structure prediction", "api_endpoint": "https://alphafold.ebi.ac.uk/api"},
    ],
    "materials": [
        {"name": "Materials Project", "description": "Computed properties of materials from DFT calculations", "api_endpoint": "https://api.materialsproject.org"},
        {"name": "AFLOW", "description": "Automatic FLOW for materials discovery database", "api_endpoint": "http://aflow.org/API"},
        {"name": "NOMAD", "description": "Novel Materials Discovery Repository for computational data", "api_endpoint": "https://nomad-lab.eu/prod/v1/api"},
        {"name": "ASE", "description": "Atomic Simulation Environment for computational chemistry", "api_endpoint": "local://ase"},
    ],
}

ALL_TOOLS = []
for tools in MOCK_TOOLS.values():
    for tool in tools:
        if tool not in ALL_TOOLS:
            ALL_TOOLS.append(tool)


def search_tooluniverse_api(query: str, category: str = None, max_results: int = 10) -> list:
    """Attempt live search against ToolUniverse API."""
    url = "https://tooluniverse.org/api/tools"
    params = {"query": query, "limit": max_results}
    if category:
        params["category"] = category

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    tools = data.get("tools", data.get("results", []))
    return tools[:max_results]


def search_mock(query: str, category: str = None, max_results: int = 10) -> list:
    """Fallback: semantic-style search over mock tool registry."""
    query_lower = query.lower()
    query_tokens = set(query_lower.split())

    if category and category in MOCK_TOOLS:
        candidate_pool = MOCK_TOOLS[category]
    else:
        candidate_pool = ALL_TOOLS

    def score(tool):
        text = (tool["name"] + " " + tool["description"]).lower()
        hits = sum(1 for token in query_tokens if token in text)
        return hits

    scored = sorted(candidate_pool, key=score, reverse=True)
    return scored[:max_results]


def main():
    parser = argparse.ArgumentParser(
        description="Search ToolUniverse for computational biology and chemistry tools"
    )
    parser.add_argument("--query", required=True, help="Natural language search query")
    parser.add_argument("--category", default=None,
                        choices=["biology", "chemistry", "genomics", "proteomics", "materials"],
                        help="Filter by tool category")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum number of results")
    args = parser.parse_args()

    tools = []
    source = "mock"

    if HAS_REQUESTS:
        try:
            tools = search_tooluniverse_api(args.query, args.category, args.max_results)
            source = "live"
        except Exception:
            tools = search_mock(args.query, args.category, args.max_results)
    else:
        tools = search_mock(args.query, args.category, args.max_results)

    result = {
        "tools": tools,
        "query": args.query,
        "category": args.category,
        "total": len(tools),
        "source": source,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
