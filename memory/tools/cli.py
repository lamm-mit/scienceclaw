#!/usr/bin/env python3
"""
Memory CLI - Command-line interface for inspecting agent memory

Usage:
    python3 -m memory.tools.cli journal --agent BioAgent-7 --recent 10
    python3 -m memory.tools.cli investigations --agent BioAgent-7 --active
    python3 -m memory.tools.cli graph --agent BioAgent-7 --search "CRISPR"
    python3 -m memory.tools.cli stats --agent BioAgent-7
    python3 -m memory.tools.cli export --agent BioAgent-7 --format json

Or using the convenience script:
    cd scienceclaw
    python3 memory/tools/cli.py journal --agent BioAgent-7 --recent 10
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memory import AgentJournal, InvestigationTracker, KnowledgeGraph


def cmd_journal(args):
    """Handle journal commands"""
    journal = AgentJournal(args.agent)
    
    if args.recent:
        entries = journal.get_recent_entries(limit=args.recent, entry_types=args.type)
        print(f"\nRecent journal entries for {args.agent}:")
        print("=" * 80)
        for entry in entries:
            print(f"\n[{entry['type'].upper()}] {entry['timestamp']}")
            print(f"  {entry['content']}")
            if entry.get('metadata'):
                print(f"  Metadata: {json.dumps(entry['metadata'], indent=4)}")
    
    elif args.search:
        results = journal.search(args.search, entry_types=args.type, limit=args.limit)
        print(f"\nSearch results for '{args.search}' in {args.agent}'s journal:")
        print("=" * 80)
        print(f"Found {len(results)} entries")
        for entry in results:
            print(f"\n[{entry['type'].upper()}] {entry['timestamp']}")
            print(f"  {entry['content'][:200]}...")
    
    elif args.topics:
        topics = journal.get_investigated_topics()
        print(f"\nInvestigated topics for {args.agent}:")
        print("=" * 80)
        for topic in sorted(topics):
            print(f"  - {topic}")
        print(f"\nTotal: {len(topics)} topics")
    
    elif args.export:
        path = journal.export_to_json()
        print(f"✓ Exported journal to {path}")
    
    else:
        stats = journal.get_stats()
        print(f"\nJournal statistics for {args.agent}:")
        print("=" * 80)
        print(f"Total entries: {stats['total_entries']}")
        print(f"By type:")
        for entry_type, count in stats['by_type'].items():
            print(f"  {entry_type}: {count}")
        print(f"\nDate range: {stats['first_entry']} to {stats['last_entry']}")
        print(f"Unique topics: {stats['unique_topics']}")


def cmd_investigations(args):
    """Handle investigation commands"""
    tracker = InvestigationTracker(args.agent)
    
    if args.active:
        investigations = tracker.get_active_investigations(priority=args.priority)
        print(f"\nActive investigations for {args.agent}:")
        print("=" * 80)
        
        if not investigations:
            print("No active investigations")
        else:
            for inv in investigations:
                print(f"\n[{inv['priority'].upper()}] {inv['id'][:8]}")
                print(f"  Hypothesis: {inv['hypothesis']}")
                print(f"  Goal: {inv['goal']}")
                progress = tracker.get_investigation_progress(inv['id'])
                print(f"  Progress: {progress['progress']['completed_experiments']}/{progress['progress']['planned_experiments']} experiments ({progress['progress']['percentage']:.0f}%)")
                print(f"  Status: {inv['status']}")
                print(f"  Created: {inv['created_at']}")
    
    elif args.completed:
        investigations = tracker.get_completed_investigations(limit=args.limit)
        print(f"\nCompleted investigations for {args.agent}:")
        print("=" * 80)
        
        if not investigations:
            print("No completed investigations")
        else:
            for inv in investigations:
                print(f"\n{inv['id'][:8]} - Completed {inv['completed_at']}")
                print(f"  Hypothesis: {inv['hypothesis']}")
                print(f"  Conclusion: {inv['conclusion']}")
                print(f"  Confidence: {inv['confidence']}")
                print(f"  Experiments: {len(inv.get('experiments_completed', []))}")
    
    elif args.id:
        inv = tracker.get_investigation(args.id)
        if not inv:
            print(f"Investigation {args.id} not found")
            return
        
        print(f"\nInvestigation Details:")
        print("=" * 80)
        print(json.dumps(inv, indent=2))
    
    else:
        stats = tracker.get_stats()
        print(f"\nInvestigation statistics for {args.agent}:")
        print("=" * 80)
        print(f"Active: {stats['active_count']}")
        print(f"Completed: {stats['completed_count']}")
        print(f"Total: {stats['total_count']}")
        print(f"\nBy priority:")
        for priority, count in stats['by_priority'].items():
            print(f"  {priority}: {count}")
        print(f"\nBy status:")
        for status, count in stats['by_status'].items():
            print(f"  {status}: {count}")
        print(f"\nTotal experiments: {stats['total_experiments']}")


def cmd_graph(args):
    """Handle knowledge graph commands"""
    kg = KnowledgeGraph(args.agent)
    
    if args.search:
        results = kg.search_nodes(args.search, node_types=args.type)
        print(f"\nSearch results for '{args.search}' in {args.agent}'s knowledge graph:")
        print("=" * 80)
        print(f"Found {len(results)} nodes")
        for node in results[:args.limit]:
            print(f"\n[{node['type'].upper()}] {node['name']}")
            print(f"  ID: {node['id']}")
            print(f"  Created: {node['created_at']}")
            if node.get('properties'):
                print(f"  Properties: {json.dumps(node['properties'], indent=4)}")
    
    elif args.visualize:
        viz = kg.visualize_neighborhood(args.visualize, max_depth=args.depth)
        print(viz)
    
    elif args.contradictions:
        contradictions = kg.find_contradictions()
        print(f"\nContradictions in {args.agent}'s knowledge graph:")
        print("=" * 80)
        
        if not contradictions:
            print("No contradictions found")
        else:
            for contr in contradictions:
                print(f"\nFinding A: {contr['finding_a']['name']}")
                print(f"Finding B: {contr['finding_b']['name']}")
                print(f"Evidence: {contr['edge'].get('evidence', 'N/A')}")
    
    elif args.export:
        path = kg.export_graph(format=args.format or "json")
        print(f"✓ Exported knowledge graph to {path}")
    
    else:
        stats = kg.get_stats()
        print(f"\nKnowledge graph statistics for {args.agent}:")
        print("=" * 80)
        print(f"Total nodes: {stats['total_nodes']}")
        print(f"Total edges: {stats['total_edges']}")
        print(f"\nNodes by type:")
        for node_type, count in stats['nodes_by_type'].items():
            print(f"  {node_type}: {count}")
        print(f"\nEdges by type:")
        for edge_type, count in stats['edges_by_type'].items():
            print(f"  {edge_type}: {count}")


def cmd_stats(args):
    """Show all memory statistics"""
    journal = AgentJournal(args.agent)
    tracker = InvestigationTracker(args.agent)
    kg = KnowledgeGraph(args.agent)
    
    j_stats = journal.get_stats()
    t_stats = tracker.get_stats()
    k_stats = kg.get_stats()
    
    print(f"\n{'='*80}")
    print(f"Memory Statistics for {args.agent}")
    print(f"{'='*80}")
    
    print(f"\nJOURNAL:")
    print(f"  Total entries: {j_stats['total_entries']}")
    print(f"  Unique topics: {j_stats['unique_topics']}")
    print(f"  By type: {j_stats['by_type']}")
    
    print(f"\nINVESTIGATIONS:")
    print(f"  Active: {t_stats['active_count']}")
    print(f"  Completed: {t_stats['completed_count']}")
    print(f"  Total experiments: {t_stats['total_experiments']}")
    
    print(f"\nKNOWLEDGE GRAPH:")
    print(f"  Nodes: {k_stats['total_nodes']}")
    print(f"  Edges: {k_stats['total_edges']}")
    print(f"  Nodes by type: {k_stats['nodes_by_type']}")
    print(f"  Edges by type: {k_stats['edges_by_type']}")
    
    print(f"\n{'='*80}\n")


def cmd_export(args):
    """Export all memory to files"""
    journal = AgentJournal(args.agent)
    tracker = InvestigationTracker(args.agent)
    kg = KnowledgeGraph(args.agent)
    
    output_dir = Path(args.output or f"memory_export_{args.agent}")
    output_dir.mkdir(exist_ok=True)
    
    # Export journal
    j_path = output_dir / "journal.json"
    journal.export_to_json(str(j_path))
    print(f"✓ Exported journal to {j_path}")
    
    # Export tracker (copy tracker.json)
    t_path = output_dir / "investigations.json"
    import shutil
    shutil.copy(tracker.tracker_path, t_path)
    print(f"✓ Exported investigations to {t_path}")
    
    # Export knowledge graph
    k_path = output_dir / "knowledge_graph.json"
    kg.export_graph(format="json", output_path=str(k_path))
    print(f"✓ Exported knowledge graph to {k_path}")
    
    # Export Cytoscape format
    cy_path = output_dir / "knowledge_graph_cytoscape.json"
    kg.export_graph(format="cytoscape", output_path=str(cy_path))
    print(f"✓ Exported knowledge graph (Cytoscape) to {cy_path}")
    
    print(f"\n✓ All memory exported to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="ScienceClaw Memory System CLI")
    parser.add_argument("--agent", required=True, help="Agent name")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Journal commands
    journal_parser = subparsers.add_parser("journal", help="View journal entries")
    journal_parser.add_argument("--recent", type=int, help="Show N recent entries")
    journal_parser.add_argument("--search", help="Search journal entries")
    journal_parser.add_argument("--type", nargs="+", help="Filter by entry type")
    journal_parser.add_argument("--topics", action="store_true", help="Show investigated topics")
    journal_parser.add_argument("--export", action="store_true", help="Export journal to JSON")
    journal_parser.add_argument("--limit", type=int, default=20, help="Limit results")
    
    # Investigation commands
    inv_parser = subparsers.add_parser("investigations", help="View investigations")
    inv_parser.add_argument("--active", action="store_true", help="Show active investigations")
    inv_parser.add_argument("--completed", action="store_true", help="Show completed investigations")
    inv_parser.add_argument("--id", help="Show specific investigation details")
    inv_parser.add_argument("--priority", help="Filter by priority")
    inv_parser.add_argument("--limit", type=int, default=10, help="Limit results")
    
    # Knowledge graph commands
    graph_parser = subparsers.add_parser("graph", help="View knowledge graph")
    graph_parser.add_argument("--search", help="Search nodes")
    graph_parser.add_argument("--type", nargs="+", help="Filter by node type")
    graph_parser.add_argument("--visualize", help="Visualize neighborhood of node ID")
    graph_parser.add_argument("--depth", type=int, default=2, help="Visualization depth")
    graph_parser.add_argument("--contradictions", action="store_true", help="Show contradictions")
    graph_parser.add_argument("--export", action="store_true", help="Export graph")
    graph_parser.add_argument("--format", choices=["json", "cytoscape"], help="Export format")
    graph_parser.add_argument("--limit", type=int, default=20, help="Limit results")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show all memory statistics")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export all memory")
    export_parser.add_argument("--output", help="Output directory")
    
    args = parser.parse_args()
    
    if args.command == "journal":
        cmd_journal(args)
    elif args.command == "investigations":
        cmd_investigations(args)
    elif args.command == "graph":
        cmd_graph(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "export":
        cmd_export(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
