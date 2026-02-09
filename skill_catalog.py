#!/usr/bin/env python3
"""
Skill Catalog - Browse and search available scientific skills

Usage:
  python3 skill_catalog.py                    # Show all skills
  python3 skill_catalog.py --search "protein" # Search for skills
  python3 skill_catalog.py --category biology # Filter by category
  python3 skill_catalog.py --stats            # Show statistics
  python3 skill_catalog.py --suggest "CRISPR" # Get skill suggestions for a topic
"""

import argparse
from pathlib import Path
import sys

# Add parent directory to path
scienceclaw_root = Path(__file__).parent
if str(scienceclaw_root) not in sys.path:
    sys.path.insert(0, str(scienceclaw_root))

from core.skill_registry import get_registry


def main():
    parser = argparse.ArgumentParser(description="Browse ScienceClaw skill catalog")
    parser.add_argument('--search', help='Search skills by keyword')
    parser.add_argument('--category', help='Filter by category')
    parser.add_argument('--type', help='Filter by type (database, package, tool, integration)')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--suggest', help='Suggest skills for a topic')
    parser.add_argument('--refresh', action='store_true', help='Force refresh skill cache')
    parser.add_argument('--limit', type=int, default=50, help='Max results to show')
    
    args = parser.parse_args()
    
    # Get registry
    registry = get_registry()
    
    if args.refresh:
        print("🔄 Refreshing skill cache...")
        registry.refresh()
    
    # Show stats
    if args.stats:
        stats = registry.stats()
        print("\n📊 Skill Registry Statistics")
        print("="*70)
        print(f"Total Skills: {stats['total_skills']}")
        print(f"\nCategories:")
        for cat, count in sorted(stats['categories'].items(), key=lambda x: -x[1]):
            print(f"  {cat:15} : {count:3} skills")
        print(f"\nTypes:")
        for typ, count in sorted(stats['types'].items(), key=lambda x: -x[1]):
            print(f"  {typ:15} : {count:3} skills")
        return
    
    # Suggest skills for topic
    if args.suggest:
        print(f"\n🎯 Suggested Skills for: {args.suggest}")
        print("="*70)
        suggested = registry.suggest_skills_for_topic(args.suggest)
        
        if not suggested:
            print("No relevant skills found.")
        else:
            for i, skill in enumerate(suggested[:10], 1):
                print(f"\n{i}. {skill['name']} ({skill['category']})")
                if skill.get('description'):
                    print(f"   {skill['description'][:70]}...")
                if skill.get('capabilities'):
                    print(f"   Capabilities: {', '.join(skill['capabilities'][:3])}")
        return
    
    # Search or list skills
    if args.search or args.category or args.type:
        results = registry.search_skills(
            query=args.search or "",
            category=args.category,
            skill_type=args.type,
            limit=args.limit
        )
        
        print(f"\n🔍 Search Results ({len(results)} skills)")
        print("="*70)
        
        if not results:
            print("No skills found matching criteria.")
        else:
            for skill in results:
                print(f"\n{skill['name']}")
                print(f"  Category: {skill['category']:15} Type: {skill['type']}")
                if skill.get('description'):
                    print(f"  {skill['description'][:65]}...")
                if skill.get('capabilities'):
                    print(f"  Capabilities: {', '.join(skill['capabilities'][:2])}")
                if skill.get('executables'):
                    print(f"  Executables: {len(skill['executables'])} script(s)")
    
    else:
        # Show all skills grouped by category
        categories = registry.get_categories()
        total = len(registry.skills)
        
        print(f"\n📚 ScienceClaw Skill Catalog ({total} skills)")
        print("="*70)
        
        for category in categories[:args.limit]:
            skills = registry.get_skills_by_category(category)
            print(f"\n{category.upper()} ({len(skills)} skills):")
            
            for skill in skills[:10]:  # Limit to 10 per category
                name = skill['name']
                desc = skill.get('description', '')[:50]
                print(f"  • {name:20} - {desc}")
            
            if len(skills) > 10:
                print(f"    ... and {len(skills) - 10} more")


if __name__ == '__main__':
    main()
