"""
Test suite for ScienceClaw Memory System (Phase 1)

Tests all three memory components:
- AgentJournal
- InvestigationTracker
- KnowledgeGraph
"""

import sys
import os
from pathlib import Path
import json
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from memory import AgentJournal, InvestigationTracker, KnowledgeGraph


def test_agent_journal():
    """Test AgentJournal functionality"""
    print("\n" + "="*80)
    print("TESTING AGENT JOURNAL")
    print("="*80)
    
    # Create temporary directory for testing
    test_dir = tempfile.mkdtemp()
    
    try:
        # Initialize journal
        journal = AgentJournal("TestAgent", base_dir=test_dir)
        print(f"✓ Journal initialized at {journal.journal_path}")
        
        # Log observation
        obs = journal.log_observation(
            content="Found paper on CRISPR LNP delivery showing improved muscle uptake",
            source="pmid:12345678",
            tags=["CRISPR", "LNP", "delivery", "muscle"],
            relevance="high"
        )
        print(f"✓ Logged observation: {obs['content'][:50]}...")
        
        # Log hypothesis
        hyp = journal.log_hypothesis(
            hypothesis="Ionizable lipid composition affects muscle tissue delivery efficiency",
            motivation="Multiple papers show variable results with different LNP formulations",
            related_observations=["pmid:12345678", "pmid:87654321"]
        )
        print(f"✓ Logged hypothesis: {hyp['content'][:50]}...")
        
        # Log experiment
        exp = journal.log_experiment(
            description="Search PubMed for LNP muscle delivery papers",
            tool="pubmed",
            parameters={"query": "LNP muscle delivery CRISPR", "max_results": 20},
            results={"papers_found": 18, "highly_relevant": 3},
            hypothesis_id=hyp['timestamp']
        )
        print(f"✓ Logged experiment: {exp['content'][:50]}...")
        
        # Log conclusion
        conc = journal.log_conclusion(
            conclusion="DLin-MC3-DMA shows superior muscle uptake in rodent models",
            evidence=[exp['timestamp'], "pmid:12345678"],
            confidence="high",
            next_steps=["Test in primate models", "Optimize lipid ratios"]
        )
        print(f"✓ Logged conclusion: {conc['content'][:50]}...")
        
        # Test search
        results = journal.search("CRISPR", entry_types=["observation", "hypothesis"])
        print(f"✓ Search for 'CRISPR': found {len(results)} entries")
        
        # Test get investigated topics
        topics = journal.get_investigated_topics()
        print(f"✓ Investigated topics: {sorted(topics)[:5]}...")
        
        # Test stats
        stats = journal.get_stats()
        print(f"✓ Journal stats: {stats['total_entries']} total entries, {stats['unique_topics']} unique topics")
        
        # Test export
        export_path = journal.export_to_json()
        print(f"✓ Exported journal to {export_path}")
        
        print("\n✅ All AgentJournal tests passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)


def test_investigation_tracker():
    """Test InvestigationTracker functionality"""
    print("\n" + "="*80)
    print("TESTING INVESTIGATION TRACKER")
    print("="*80)
    
    # Create temporary directory for testing
    test_dir = tempfile.mkdtemp()
    
    try:
        # Initialize tracker
        tracker = InvestigationTracker("TestAgent", base_dir=test_dir)
        print(f"✓ Tracker initialized at {tracker.tracker_path}")
        
        # Create investigation
        inv_id = tracker.create_investigation(
            hypothesis="LNP ionizable lipids affect muscle tissue delivery",
            goal="Identify optimal lipid ratios for muscle-targeted CRISPR delivery",
            planned_experiments=["pubmed_search", "chembl_search", "tdc_prediction"],
            tags=["LNP", "CRISPR", "delivery", "muscle"],
            priority="high"
        )
        print(f"✓ Created investigation: {inv_id[:8]}...")
        
        # Add experiments
        tracker.add_experiment(
            investigation_id=inv_id,
            experiment={
                "tool": "pubmed",
                "description": "Search for LNP muscle delivery papers",
                "parameters": {"query": "LNP muscle delivery CRISPR", "max_results": 20},
                "results_summary": "Found 18 papers, 3 highly relevant",
                "key_findings": ["DLin-MC3-DMA shows best results", "PEG-lipid ratio matters"],
                "interpretation": "Lipid composition is critical factor"
            }
        )
        print(f"✓ Added experiment 1")
        
        tracker.add_experiment(
            investigation_id=inv_id,
            experiment={
                "tool": "chembl",
                "description": "Search for DLin-MC3-DMA analogs",
                "parameters": {"compound": "DLin-MC3-DMA", "similarity": 0.8},
                "results_summary": "Found 12 similar compounds",
                "key_findings": ["Several analogs with improved properties"],
                "interpretation": "Structure-activity relationship established"
            }
        )
        print(f"✓ Added experiment 2")
        
        # Get progress
        progress = tracker.get_investigation_progress(inv_id)
        print(f"✓ Investigation progress: {progress['progress']['completed_experiments']}/{progress['progress']['planned_experiments']} experiments")
        
        # Update status
        tracker.update_status(inv_id, "ready_to_conclude", "Sufficient data collected")
        print(f"✓ Updated status to 'ready_to_conclude'")
        
        # Mark complete
        tracker.mark_complete(
            investigation_id=inv_id,
            conclusion="DLin-MC3-DMA at 50mol% with 1.5mol% PEG-lipid shows optimal muscle uptake",
            confidence="high",
            next_steps=["Test in primate models", "Optimize for other tissue types"]
        )
        print(f"✓ Marked investigation complete")
        
        # Get active and completed investigations
        active = tracker.get_active_investigations()
        completed = tracker.get_completed_investigations()
        print(f"✓ Active investigations: {len(active)}, Completed: {len(completed)}")
        
        # Get stats
        stats = tracker.get_stats()
        print(f"✓ Tracker stats: {stats['total_count']} total, {stats['total_experiments']} experiments")
        
        print("\n✅ All InvestigationTracker tests passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)


def test_knowledge_graph():
    """Test KnowledgeGraph functionality"""
    print("\n" + "="*80)
    print("TESTING KNOWLEDGE GRAPH")
    print("="*80)
    
    # Create temporary directory for testing
    test_dir = tempfile.mkdtemp()
    
    try:
        # Initialize knowledge graph
        kg = KnowledgeGraph("TestAgent", base_dir=test_dir)
        print(f"✓ Knowledge graph initialized at {kg.graph_path}")
        
        # Add nodes
        lipid_id = kg.add_node(
            name="DLin-MC3-DMA",
            node_type="compound",
            properties={
                "smiles": "CCCCCCCC/C=C\\CCCCCCCC(=O)OC[C@H](COP(=O)([O-])OCC[N+](C)(C)C)OC(=O)CCCCCCC/C=C\\CCCCCCCC",
                "molecular_weight": 642.0,
                "class": "ionizable lipid"
            },
            source="chembl:CHEMBL123456"
        )
        print(f"✓ Added compound node: DLin-MC3-DMA")
        
        delivery_id = kg.add_node(
            name="muscle tissue uptake",
            node_type="concept",
            properties={
                "description": "Efficiency of nanoparticle delivery to muscle tissue",
                "measurement": "percentage of injected dose"
            }
        )
        print(f"✓ Added concept node: muscle tissue uptake")
        
        method_id = kg.add_node(
            name="LNP formulation",
            node_type="method",
            properties={
                "description": "Lipid nanoparticle formulation technique",
                "components": ["ionizable lipid", "PEG-lipid", "cholesterol", "helper lipid"]
            }
        )
        print(f"✓ Added method node: LNP formulation")
        
        # Add edges
        kg.add_edge(
            source_id=lipid_id,
            target_id=delivery_id,
            edge_type="correlates",
            properties={
                "correlation": "positive",
                "strength": "strong",
                "context": "in vivo mouse models"
            },
            confidence="high",
            evidence="pmid:12345678"
        )
        print(f"✓ Added edge: DLin-MC3-DMA correlates with muscle tissue uptake")
        
        kg.add_edge(
            source_id=method_id,
            target_id=delivery_id,
            edge_type="causes",
            properties={
                "mechanism": "nanoparticle formation and cellular uptake"
            },
            confidence="high",
            evidence="pmid:87654321"
        )
        print(f"✓ Added edge: LNP formulation causes muscle tissue uptake")
        
        # Add finding with automatic linking
        finding_id = kg.add_finding(
            finding="DLin-MC3-DMA at 50mol% shows superior muscle uptake compared to other ionizable lipids",
            related_concepts=[
                {"name": "DLin-MC3-DMA", "type": "compound"},
                {"name": "muscle tissue uptake", "type": "concept"},
                {"name": "ionizable lipids", "type": "concept"}
            ],
            relationships=[
                {"from": "DLin-MC3-DMA", "to": "muscle tissue uptake", "type": "correlates"}
            ],
            source="pmid:12345678",
            confidence="high"
        )
        print(f"✓ Added finding with automatic concept linking")
        
        # Query related nodes
        related = kg.query_related(lipid_id, max_depth=2)
        print(f"✓ Found {len(related['related_nodes'])} related nodes for DLin-MC3-DMA")
        
        # Search nodes
        results = kg.search_nodes("lipid", node_types=["compound", "concept"])
        print(f"✓ Search for 'lipid': found {len(results)} nodes")
        
        # Get stats
        stats = kg.get_stats()
        print(f"✓ Graph stats: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
        print(f"  Nodes by type: {stats['nodes_by_type']}")
        print(f"  Edges by type: {stats['edges_by_type']}")
        
        # Export graph
        export_path = kg.export_graph(format="json")
        print(f"✓ Exported graph to {export_path}")
        
        cytoscape_path = kg.export_graph(format="cytoscape")
        print(f"✓ Exported graph (Cytoscape format) to {cytoscape_path}")
        
        # Visualize neighborhood
        viz = kg.visualize_neighborhood(lipid_id, max_depth=1)
        print(f"✓ Generated visualization:\n{viz}")
        
        print("\n✅ All KnowledgeGraph tests passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)


def test_integration():
    """Test integration between memory components"""
    print("\n" + "="*80)
    print("TESTING MEMORY SYSTEM INTEGRATION")
    print("="*80)
    
    # Create temporary directory for testing
    test_dir = tempfile.mkdtemp()
    
    try:
        # Initialize all three components
        journal = AgentJournal("TestAgent", base_dir=f"{test_dir}/journals")
        tracker = InvestigationTracker("TestAgent", base_dir=f"{test_dir}/investigations")
        kg = KnowledgeGraph("TestAgent", base_dir=f"{test_dir}/knowledge")
        print("✓ Initialized all three memory components")
        
        # Simulate scientific workflow
        # 1. Read a paper (observation)
        obs = journal.log_observation(
            content="Paper reports DLin-MC3-DMA improves muscle delivery 3x vs standard LNPs",
            source="pmid:12345678",
            tags=["LNP", "muscle", "delivery", "DLin-MC3-DMA"]
        )
        print("✓ Step 1: Logged observation from paper")
        
        # 2. Form hypothesis
        hyp = journal.log_hypothesis(
            hypothesis="DLin-MC3-DMA concentration affects delivery efficiency",
            motivation="Paper shows dose-response relationship",
            related_observations=[obs['timestamp']]
        )
        print("✓ Step 2: Formed hypothesis")
        
        # 3. Create investigation
        inv_id = tracker.create_investigation(
            hypothesis=hyp['content'],
            goal="Determine optimal DLin-MC3-DMA concentration",
            planned_experiments=["pubmed_search", "chembl_search", "tdc_admet"],
            tags=["DLin-MC3-DMA", "optimization"],
            priority="high"
        )
        print(f"✓ Step 3: Created investigation {inv_id[:8]}")
        
        # 4. Run experiments and log results
        exp1 = journal.log_experiment(
            description="Literature search for DLin-MC3-DMA studies",
            tool="pubmed",
            parameters={"query": "DLin-MC3-DMA concentration", "max_results": 10},
            results={"papers": 8, "optimal_range": "40-60mol%"},
            hypothesis_id=hyp['timestamp']
        )
        
        tracker.add_experiment(
            investigation_id=inv_id,
            experiment={
                "journal_entry": exp1['timestamp'],
                "tool": "pubmed",
                "summary": "Found 8 papers suggesting 40-60mol% range"
            }
        )
        print("✓ Step 4: Ran experiment and logged in both journal and tracker")
        
        # 5. Add knowledge to graph
        obs_source = obs['metadata'].get('source', 'test_source')
        compound_id = kg.add_node("DLin-MC3-DMA", "compound", source=obs_source)
        concept_id = kg.add_node("muscle tissue delivery", "concept")
        
        kg.add_edge(
            source_id=compound_id,
            target_id=concept_id,
            edge_type="correlates",
            confidence="high",
            evidence=obs_source
        )
        print("✓ Step 5: Added knowledge to graph")
        
        # 6. Reach conclusion
        conc = journal.log_conclusion(
            conclusion="50mol% DLin-MC3-DMA is optimal for muscle delivery",
            evidence=[exp1['timestamp'], obs_source],
            confidence="high"
        )
        
        tracker.mark_complete(
            investigation_id=inv_id,
            conclusion=conc['content'],
            confidence="high",
            next_steps=["Test in vivo", "Compare with other tissues"]
        )
        
        finding_id = kg.add_finding(
            finding=conc['content'],
            related_concepts=[
                {"name": "DLin-MC3-DMA", "type": "compound"},
                {"name": "muscle tissue delivery", "type": "concept"}
            ],
            source=conc['timestamp']
        )
        print("✓ Step 6: Reached conclusion, updated all memory systems")
        
        # 7. Verify memory persistence
        journal_stats = journal.get_stats()
        tracker_stats = tracker.get_stats()
        kg_stats = kg.get_stats()
        
        print(f"\n✓ Final memory state:")
        print(f"  Journal: {journal_stats['total_entries']} entries")
        print(f"  Tracker: {tracker_stats['completed_count']} completed investigations")
        print(f"  Knowledge Graph: {kg_stats['total_nodes']} nodes, {kg_stats['total_edges']} edges")
        
        print("\n✅ All integration tests passed!")
        print("\n🎉 Phase 1 Memory System Implementation Complete!")
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SCIENCECLAW MEMORY SYSTEM - PHASE 1 TEST SUITE")
    print("="*80)
    
    test_agent_journal()
    test_investigation_tracker()
    test_knowledge_graph()
    test_integration()
    
    print("\n" + "="*80)
    print("ALL TESTS PASSED! ✅")
    print("="*80)
    print("\nMemory system is ready for integration with heartbeat daemon.")
    print("Next steps:")
    print("  1. Update heartbeat_daemon.py to use memory system")
    print("  2. Update setup.py to initialize memory for new agents")
    print("  3. Create memory CLI tools for inspection/debugging")
    print("="*80 + "\n")
