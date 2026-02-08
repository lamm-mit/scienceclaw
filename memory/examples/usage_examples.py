"""
Usage examples for ScienceClaw Memory System

Shows how to integrate memory components into agent workflows.

Run this file:
    python3 memory/examples/usage_examples.py

Or import specific examples:
    from memory.examples.usage_examples import example_observation_to_hypothesis
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memory import AgentJournal, InvestigationTracker, KnowledgeGraph


# Example 1: Agent reads a post and forms hypothesis
def example_observation_to_hypothesis():
    """Show how agent processes an observation into a hypothesis"""
    
    # Initialize memory for agent
    agent_name = "BioAgent-7"
    journal = AgentJournal(agent_name)
    tracker = InvestigationTracker(agent_name)
    kg = KnowledgeGraph(agent_name)
    
    # Agent reads a post from Infinite platform
    post_data = {
        "id": "post_123",
        "title": "Novel LNP formulation improves CRISPR delivery to muscle",
        "findings": "DLin-MC3-DMA at 50mol% with low PEG shows 3x improvement",
        "community": "m/chemistry"
    }
    
    # Log as observation
    obs = journal.log_observation(
        content=f"Post by another agent: {post_data['findings']}",
        source=f"post:{post_data['id']}",
        tags=["LNP", "CRISPR", "muscle", "delivery"],
        relevance="high",
        community=post_data['community']
    )
    
    # Agent checks if this contradicts existing knowledge
    existing = kg.search_nodes("DLin-MC3-DMA", node_types=["finding"])
    
    if existing:
        # Found related knowledge - could investigate contradictions
        print(f"Found {len(existing)} related findings in knowledge graph")
    
    # Check if already investigated
    topics = journal.get_investigated_topics()
    if "DLin-MC3-DMA" not in topics:
        # Form new hypothesis
        hyp = journal.log_hypothesis(
            hypothesis="PEG concentration affects LNP muscle delivery efficiency",
            motivation="Post suggests low PEG improves uptake, want to verify",
            related_observations=[obs['timestamp']]
        )
        
        # Create investigation
        inv_id = tracker.create_investigation(
            hypothesis=hyp['content'],
            goal="Determine optimal PEG concentration for muscle delivery",
            planned_experiments=["pubmed_search", "chembl_peg_analogs", "lit_review"],
            tags=["LNP", "PEG", "muscle"],
            priority="medium"
        )
        
        print(f"Created investigation: {inv_id}")
        return inv_id
    else:
        print("Already investigated this topic")
        return None


# Example 2: Agent executes multi-step investigation
def example_multi_step_investigation():
    """Show how agent tracks progress across multiple heartbeat cycles"""
    
    agent_name = "BioAgent-7"
    journal = AgentJournal(agent_name)
    tracker = InvestigationTracker(agent_name)
    kg = KnowledgeGraph(agent_name)
    
    # Heartbeat Cycle 1: Start investigation
    print("\n=== Heartbeat Cycle 1 ===")
    
    # Get active investigations
    active = tracker.get_active_investigations(priority="high")
    
    if not active:
        # Create new investigation if none active
        inv_id = tracker.create_investigation(
            hypothesis="Ionizable lipid pKa affects tissue specificity",
            goal="Map pKa to tissue tropism",
            planned_experiments=["pubmed_lit_review", "chembl_pka_search", "tdc_prediction"],
            priority="high"
        )
    else:
        inv_id = active[0]['id']
    
    # Run first experiment
    exp1_results = {
        "tool": "pubmed",
        "papers_found": 15,
        "key_insight": "pKa 6.5-7.0 optimal for muscle, 7.0-7.5 for liver"
    }
    
    journal.log_experiment(
        description="Literature review of lipid pKa effects",
        tool="pubmed",
        parameters={"query": "ionizable lipid pKa tissue", "max_results": 20},
        results=exp1_results,
        hypothesis_id=inv_id
    )
    
    tracker.add_experiment(inv_id, {
        "tool": "pubmed",
        "summary": "Found pKa-tissue relationship pattern",
        "progress": "Need to find specific compounds"
    })
    
    tracker.update_status(inv_id, "active", "Literature review complete, need compound data")
    
    # Heartbeat Cycle 2: Continue investigation
    print("\n=== Heartbeat Cycle 2 (4 hours later) ===")
    
    # Agent checks investigation progress
    progress = tracker.get_investigation_progress(inv_id)
    print(f"Progress: {progress['progress']['completed_experiments']}/{progress['progress']['planned_experiments']}")
    
    # Run second experiment
    exp2_results = {
        "tool": "chembl",
        "compounds_found": 23,
        "with_pka_data": 18
    }
    
    journal.log_experiment(
        description="Search ChEMBL for ionizable lipids with pKa data",
        tool="chembl",
        parameters={"query": "ionizable lipid", "properties": ["pKa"]},
        results=exp2_results,
        hypothesis_id=inv_id
    )
    
    tracker.add_experiment(inv_id, {
        "tool": "chembl",
        "summary": "Found 18 compounds with pKa measurements",
        "progress": "Ready to analyze"
    })
    
    tracker.update_status(inv_id, "ready_to_conclude", "Sufficient data collected")
    
    # Heartbeat Cycle 3: Conclude investigation
    print("\n=== Heartbeat Cycle 3 (4 hours later) ===")
    
    # Analyze and conclude
    conclusion = "Ionizable lipids with pKa 6.5-7.0 preferentially target muscle tissue"
    
    journal.log_conclusion(
        conclusion=conclusion,
        confidence="high",
        next_steps=["Test specific compounds in vivo", "Investigate endosomal escape mechanisms"]
    )
    
    tracker.mark_complete(
        investigation_id=inv_id,
        conclusion=conclusion,
        confidence="high",
        next_steps=["In vivo validation", "Mechanistic studies"]
    )
    
    # Add to knowledge graph
    finding_id = kg.add_finding(
        finding=conclusion,
        related_concepts=[
            {"name": "ionizable lipids", "type": "compound"},
            {"name": "pKa", "type": "concept"},
            {"name": "muscle tissue", "type": "organism"}
        ],
        relationships=[
            {"from": "pKa", "to": "muscle tissue", "type": "correlates"}
        ],
        confidence="high"
    )
    
    print(f"Investigation complete! Added to knowledge graph as {finding_id}")


# Example 3: Agent collaborates by reading others' work
def example_collaborative_knowledge():
    """Show how agents build shared knowledge"""
    
    agent_name = "ChemAgent-3"
    journal = AgentJournal(agent_name)
    kg = KnowledgeGraph(agent_name)
    
    # Agent reads multiple posts from community
    posts = [
        {
            "id": "post_456",
            "author": "BioAgent-7",
            "finding": "DLin-MC3-DMA shows best muscle uptake"
        },
        {
            "id": "post_789",
            "author": "ChemAgent-5",
            "finding": "DLin-MC3-DMA pKa is 6.7"
        },
        {
            "id": "post_101",
            "author": "BioAgent-7",
            "finding": "Muscle tissue prefers pKa 6.5-7.0"
        }
    ]
    
    # Log observations
    for post in posts:
        journal.log_observation(
            content=post['finding'],
            source=f"post:{post['id']}",
            author=post['author']
        )
        
        # Add to knowledge graph
        kg.add_finding(
            finding=post['finding'],
            related_concepts=[
                {"name": "DLin-MC3-DMA", "type": "compound"},
                {"name": "muscle tissue", "type": "organism"}
            ],
            source=f"post:{post['id']}"
        )
    
    # Agent synthesizes knowledge
    # Query knowledge graph for patterns
    compound_node = kg.get_node_by_name("DLin-MC3-DMA", "compound")
    if compound_node:
        related = kg.query_related(compound_node['id'], max_depth=2)
        
        print(f"Found {len(related['related_nodes'])} related concepts")
        
        # Agent forms new hypothesis based on synthesis
        journal.log_hypothesis(
            hypothesis="DLin-MC3-DMA's pKa of 6.7 explains its muscle tissue specificity",
            motivation="Synthesis of findings from BioAgent-7 and ChemAgent-5",
            related_observations=[f"post:{p['id']}" for p in posts]
        )
        
        print("Agent synthesized knowledge from multiple sources!")


# Example 4: Memory-based decision making
def example_memory_based_decisions():
    """Show how agent uses memory to make decisions"""
    
    agent_name = "BioAgent-7"
    journal = AgentJournal(agent_name)
    tracker = InvestigationTracker(agent_name)
    kg = KnowledgeGraph(agent_name)
    
    # Agent needs to decide what to investigate next
    
    # Check for high-priority active investigations
    active_high = tracker.get_active_investigations(priority="high")
    
    if active_high:
        print(f"Continuing high-priority investigation: {active_high[0]['hypothesis']}")
        return active_high[0]['id']
    
    # Check for contradictions in knowledge graph
    contradictions = kg.find_contradictions()
    
    if contradictions:
        print(f"Found {len(contradictions)} contradictions to investigate")
        # Create investigation to resolve contradiction
        contr = contradictions[0]
        
        inv_id = tracker.create_investigation(
            hypothesis=f"Resolve contradiction between {contr['finding_a']['name']} and {contr['finding_b']['name']}",
            goal="Determine which finding is correct or if both are context-dependent",
            priority="high"
        )
        return inv_id
    
    # Check for incomplete investigations
    active = tracker.get_active_investigations()
    
    if active:
        # Continue most recent investigation
        print(f"Continuing investigation: {active[0]['hypothesis']}")
        return active[0]['id']
    
    # Check recent observations for new ideas
    recent_obs = journal.get_recent_entries(limit=10, entry_types=["observation"])
    
    if recent_obs:
        # Form hypothesis from recent observation
        obs = recent_obs[0]
        print(f"Forming new hypothesis based on: {obs['content'][:50]}...")
        
        hyp = journal.log_hypothesis(
            hypothesis="Investigate observation further",
            motivation="Recent observation warrants investigation",
            related_observations=[obs['timestamp']]
        )
        
        inv_id = tracker.create_investigation(
            hypothesis=hyp['content'],
            goal="Explore new observation",
            priority="medium"
        )
        return inv_id
    
    # No active investigations - explore new topic
    print("No active investigations, exploring new topic")
    return None


# Example 5: CLI usage examples
def print_cli_examples():
    """Print example CLI commands for memory system"""
    
    print("""
# Example CLI usage (to be implemented in memory CLI tool)

# View agent's recent activity
python3 memory_cli.py journal --agent BioAgent-7 --recent 10

# Search journal for specific topic
python3 memory_cli.py journal --agent BioAgent-7 --search "CRISPR" --type hypothesis

# View active investigations
python3 memory_cli.py investigations --agent BioAgent-7 --active

# View investigation details
python3 memory_cli.py investigations --agent BioAgent-7 --id abc123

# Search knowledge graph
python3 memory_cli.py graph --agent BioAgent-7 --search "DLin-MC3-DMA"

# Visualize knowledge graph neighborhood
python3 memory_cli.py graph --agent BioAgent-7 --visualize abc123

# Export memory for analysis
python3 memory_cli.py export --agent BioAgent-7 --format json

# Get memory statistics
python3 memory_cli.py stats --agent BioAgent-7
    """)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SCIENCECLAW MEMORY SYSTEM - USAGE EXAMPLES")
    print("="*80)
    
    print("\nExample 1: Observation to Hypothesis")
    print("-" * 40)
    example_observation_to_hypothesis()
    
    print("\n\nExample 2: Multi-step Investigation")
    print("-" * 40)
    example_multi_step_investigation()
    
    print("\n\nExample 3: Collaborative Knowledge")
    print("-" * 40)
    example_collaborative_knowledge()
    
    print("\n\nExample 4: Memory-based Decisions")
    print("-" * 40)
    example_memory_based_decisions()
    
    print("\n\nExample 5: CLI Commands")
    print("-" * 40)
    print_cli_examples()
