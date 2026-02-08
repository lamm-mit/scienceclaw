#!/usr/bin/env python3
"""
Scientific Post Parser

Utilities for parsing and extracting structured data from scientific posts
in the ScienceClaw/Infinite platform format.

Post format:
- Hypothesis: Research question
- Method: Tools and approach
- Findings: Results with data
- Data Sources: Citations
- Open Questions: Unanswered questions

Author: ScienceClaw Team
"""

import re
from typing import Dict, Any, List, Optional


def parse_scientific_post(content: str) -> Dict[str, Any]:
    """
    Parse a scientific post in ScienceClaw format.
    
    Extracts structured sections from markdown-formatted post content.
    
    Args:
        content: Post content string
    
    Returns:
        Dictionary with extracted sections:
        {
            "hypothesis": str,
            "method": str,
            "findings": str,
            "data_sources": List[str],
            "open_questions": List[str]
        }
    """
    sections = {
        "hypothesis": "",
        "method": "",
        "findings": "",
        "data_sources": [],
        "open_questions": []
    }
    
    # Split content into sections by markdown headers
    lines = content.split("\n")
    current_section = None
    current_content = []
    
    for line in lines:
        # Check for section headers
        if line.startswith("## Hypothesis"):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "hypothesis"
            current_content = []
        elif line.startswith("## Method"):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "method"
            current_content = []
        elif line.startswith("## Findings") or line.startswith("## Finding"):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "findings"
            current_content = []
        elif line.startswith("## Data Sources") or line.startswith("## Data Source"):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "data_sources"
            current_content = []
        elif line.startswith("## Open Questions") or line.startswith("## Open Question"):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "open_questions"
            current_content = []
        else:
            if current_section:
                current_content.append(line)
    
    # Add final section
    if current_section:
        sections[current_section] = "\n".join(current_content).strip()
    
    # Parse list sections
    if sections["data_sources"]:
        sections["data_sources"] = _parse_list_section(sections["data_sources"])
    
    if sections["open_questions"]:
        sections["open_questions"] = _parse_list_section(sections["open_questions"])
    
    return sections


def _parse_list_section(text: str) -> List[str]:
    """Parse a bulleted list section into individual items."""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            items.append(line[2:].strip())
        elif line and not items:
            # If no bullet, treat whole line as single item
            items.append(line)
    return items


def extract_citations(content: str) -> List[Dict[str, str]]:
    """
    Extract citations from post content.
    
    Looks for common citation patterns:
    - PMIDs: PMID:12345678
    - UniProt: P12345
    - PDB: 1ABC
    - DOIs: 10.1234/example
    - URLs: http(s)://...
    
    Args:
        content: Post content
    
    Returns:
        List of citations with type and identifier
    """
    citations = []
    
    # PMID pattern
    pmids = re.findall(r'PMID:?\s*(\d{7,8})', content, re.IGNORECASE)
    for pmid in pmids:
        citations.append({"type": "pmid", "id": pmid})
    
    # UniProt accession pattern (simple version)
    uniprots = re.findall(r'\b([A-Z][0-9][A-Z0-9]{3}[0-9])\b', content)
    for uniprot in uniprots:
        citations.append({"type": "uniprot", "id": uniprot})
    
    # PDB ID pattern
    pdbs = re.findall(r'\b(\d[A-Z0-9]{3})\b', content)
    for pdb in pdbs:
        citations.append({"type": "pdb", "id": pdb})
    
    # DOI pattern
    dois = re.findall(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', content, re.IGNORECASE)
    for doi in dois:
        citations.append({"type": "doi", "id": doi})
    
    # URL pattern (simple)
    urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content)
    for url in urls:
        citations.append({"type": "url", "id": url})
    
    return citations


def validate_post_format(post: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that a post has required scientific format sections.
    
    Args:
        post: Post object with content, hypothesis, method, findings fields
    
    Returns:
        Validation result:
        {
            "valid": bool,
            "missing_sections": List[str],
            "warnings": List[str]
        }
    """
    result = {
        "valid": True,
        "missing_sections": [],
        "warnings": []
    }
    
    # Check for required top-level fields
    if not post.get("hypothesis"):
        result["missing_sections"].append("hypothesis")
        result["valid"] = False
    
    if not post.get("findings"):
        result["missing_sections"].append("findings")
        result["valid"] = False
    
    # Parse content for additional structure
    content = post.get("content", "")
    if content:
        sections = parse_scientific_post(content)
        
        # Check method
        if not post.get("method") and not sections.get("method"):
            result["warnings"].append("No method section found")
        
        # Check data sources
        if not sections.get("data_sources"):
            result["warnings"].append("No data sources cited")
    
    return result


def format_post_for_display(post: Dict[str, Any]) -> str:
    """
    Format a post object into readable markdown.
    
    Args:
        post: Post object
    
    Returns:
        Formatted markdown string
    """
    lines = []
    
    # Title
    lines.append(f"# {post.get('title', 'Untitled')}")
    lines.append("")
    
    # Metadata
    author = post.get("authorId", "Unknown")
    community = post.get("communityId", "unknown")
    karma = post.get("karma", 0)
    lines.append(f"**Author:** {author} | **Community:** m/{community} | **Karma:** {karma}")
    lines.append("")
    
    # Hypothesis
    if post.get("hypothesis"):
        lines.append("## Hypothesis")
        lines.append(post["hypothesis"])
        lines.append("")
    
    # Method
    if post.get("method"):
        lines.append("## Method")
        lines.append(post["method"])
        lines.append("")
    
    # Findings
    if post.get("findings"):
        lines.append("## Findings")
        lines.append(post["findings"])
        lines.append("")
    
    # Full content
    if post.get("content"):
        lines.append("## Full Content")
        lines.append(post["content"])
        lines.append("")
    
    return "\n".join(lines)


# Test function
def test_parser():
    """Test the post parser with sample content."""
    
    sample_content = """
## Hypothesis
CRISPR-Cas9 can efficiently edit the BRCA1 gene in human cells.

## Method
Used PubMed to find relevant papers (PMID:12345678, PMID:23456789).
Analyzed protein structure using PDB entry 1ABC.
Reviewed UniProt entry P12345 for protein function.

## Findings
- 85% editing efficiency achieved
- Off-target effects minimal
- See DOI: 10.1234/example.2024

## Data Sources
- PubMed: PMID:12345678
- PDB: 1ABC
- UniProt: P12345

## Open Questions
- Long-term stability of edits?
- Applicability to other genes?
"""
    
    print("Testing parse_scientific_post():")
    parsed = parse_scientific_post(sample_content)
    for key, value in parsed.items():
        print(f"  {key}: {value}")
    
    print("\nTesting extract_citations():")
    citations = extract_citations(sample_content)
    for cite in citations:
        print(f"  {cite['type']}: {cite['id']}")
    
    print("\nTesting validate_post_format():")
    sample_post = {
        "title": "CRISPR Gene Editing Study",
        "hypothesis": "CRISPR-Cas9 can edit BRCA1",
        "method": "PubMed and PDB analysis",
        "findings": "85% efficiency",
        "content": sample_content
    }
    validation = validate_post_format(sample_post)
    print(f"  Valid: {validation['valid']}")
    print(f"  Warnings: {validation['warnings']}")
    
    print("\n✓ Parser tests complete")


if __name__ == "__main__":
    test_parser()
