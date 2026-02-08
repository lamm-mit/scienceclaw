"""
Quick example showing how memory system integrates with agent workflow

This demonstrates the integration pattern used by the autonomous heartbeat daemon.

Run this file:
    python3 memory/examples/integration_example.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memory import AgentJournal, InvestigationTracker, KnowledgeGraph


def heartbeat_routine_with_memory(agent_name: str):
    """
    Example of how heartbeat_daemon.py could use the memory system
    """
    
    # Initialize memory components
    journal = AgentJournal(agent_name)
    tracker = InvestigationTracker(agent_name)
    kg = KnowledgeGraph(agent_name)
    
    print(f"\n=== Heartbeat for {agent_name} ===\n")
    
    # Step 1: Check for high-priority active investigations
    active_investigations = tracker.get_active_investigations(priority="high")
    
    if active_investigations:
        inv = active_investigations[0]
        print(f"Continuing investigation: {inv['hypothesis']}")
        
        # Get progress
        progress = tracker.get_investigation_progress(inv['id'])
        print(f"Progress: {progress['progress']['percentage']:.0f}% complete")
        
        # Execute next planned experiment
        remaining = [exp for exp in inv['planned_experiments'] 
                    if exp not in [e.get('tool') for e in inv['experiments_completed']]]
        
        if remaining:
            next_tool = remaining[0]
            print(f"Next: Execute {next_tool}")
            # ... execute tool ...
            return
    
    # Step 2: Check for contradictions in knowledge graph
    contradictions = kg.find_contradictions()
    
    if contradictions:
        contr = contradictions[0]
        print(f"Found contradiction to investigate:")
        print(f"  A: {contr['finding_a']['name']}")
        print(f"  B: {contr['finding_b']['name']}")
        
        # Create investigation to resolve
        inv_id = tracker.create_investigation(
            hypothesis=f"Resolve contradiction between findings",
            goal="Determine which finding is correct or if context-dependent",
            planned_experiments=["pubmed_search", "data_analysis"],
            priority="high"
        )
        print(f"Created investigation: {inv_id[:8]}")
        return
    
    # Step 3: Check recent observations from Infinite platform
    # (This would fetch from Infinite API)
    recent_posts = [
        {
            "id": "post_123",
            "author": "ChemAgent-5",
            "title": "Novel LNP formulation improves delivery",
            "findings": "DLin-MC3-DMA at 50mol% shows 3x improvement"
        }
    ]
    
    for post in recent_posts:
        # Check if already investigated
        topics = journal.get_investigated_topics()
        
        if "DLin-MC3-DMA" not in topics:
            # Log observation
            obs = journal.log_observation(
                content=f"{post['author']}: {post['findings']}",
                source=f"post:{post['id']}",
                tags=["LNP", "DLin-MC3-DMA", "delivery"]
            )
            
            # Form hypothesis
            hyp = journal.log_hypothesis(
                hypothesis="DLin-MC3-DMA concentration affects delivery efficiency",
                motivation=f"Observation from {post['author']} warrants investigation",
                related_observations=[obs['timestamp']]
            )
            
            # Create investigation
            inv_id = tracker.create_investigation(
                hypothesis=hyp['content'],
                goal="Determine optimal DLin-MC3-DMA concentration",
                planned_experiments=["pubmed_search", "chembl_search", "tdc_admet"],
                tags=["DLin-MC3-DMA", "LNP"],
                priority="medium"
            )
            
            print(f"New investigation from observation: {inv_id[:8]}")
            print(f"Hypothesis: {hyp['content']}")
            return
    
    # Step 4: No urgent work - explore new topic based on interests
    # (This would use agent profile interests)
    print("No active work - exploring new topic from interests")
    # ... autonomous exploration ...


if __name__ == "__main__":
    # Simulate heartbeat
    heartbeat_routine_with_memory("BioAgent-7")
    
    print("\n" + "="*80)
    print("\nThis is a simplified example. Full integration would:")
    print("  1. Actually execute tools (pubmed, blast, etc.)")
    print("  2. Fetch real posts from Infinite API")
    print("  3. Use agent's personality/interests from profile")
    print("  4. Post findings back to Infinite")
    print("  5. Update knowledge graph with findings")
    print("  6. Make more sophisticated decisions")
    print("="*80 + "\n")
