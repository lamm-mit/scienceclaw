#!/usr/bin/env python3
"""
Skill Diversity Check - Basic Quality Control

Simple checks to ensure agents use multiple tools, not hardcoded category rules.
The real diversity comes from usage tracking and LLM awareness, not forced categories.
"""

from typing import List, Dict, Any


def ensure_minimum_skills(
    selected_skills: List[Dict[str, Any]],
    min_skills: int = 3
) -> List[Dict[str, Any]]:
    """
    Ensure at least minimum number of skills selected.

    This is the ONLY enforcement - no category rules, just minimum count.
    The LLM and usage tracker handle actual diversity.

    Args:
        selected_skills: Skills selected by LLM
        min_skills: Minimum number required (default 3)

    Returns:
        Skills list (unchanged if meets minimum, warning if not)
    """
    if len(selected_skills) < min_skills:
        print(f"  ⚠ Only {len(selected_skills)} skills selected (target: {min_skills}+)")
    else:
        print(f"  ✓ {len(selected_skills)} skills selected")

    return selected_skills


def measure_diversity(selected_skills: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Measure diversity metrics WITHOUT category enforcement.

    Just counts unique skills - no hardcoded category rules.

    Returns:
        Dict with basic metrics:
        - skill_count: Number of skills
        - unique_skills: Number of unique skill names
    """
    unique_names = set(s.get('name') for s in selected_skills if s.get('name'))

    return {
        'skill_count': len(selected_skills),
        'unique_skills': len(unique_names),
        'skills': [s.get('name') for s in selected_skills]
    }


# Test function
if __name__ == "__main__":
    print("\n=== Testing Simplified Skill Diversity ===\n")

    # Test 1: Minimum skills check
    print("Test 1: Minimum skills enforcement")
    selected = [
        {'name': 'pubmed', 'category': 'literature'},
        {'name': 'uniprot', 'category': 'proteins'}
    ]
    result = ensure_minimum_skills(selected, min_skills=3)
    print(f"  Result: {len(result)} skills\n")

    # Test 2: Diversity metrics
    print("Test 2: Diversity measurement")
    diverse_skills = [
        {'name': 'pubmed', 'category': 'literature'},
        {'name': 'uniprot', 'category': 'proteins'},
        {'name': 'tdc', 'category': 'drug_discovery'},
        {'name': 'chembl', 'category': 'compounds'}
    ]
    metrics = measure_diversity(diverse_skills)
    print(f"  Metrics: {metrics}\n")

    print("✓ Simplified skill diversity tests complete")
