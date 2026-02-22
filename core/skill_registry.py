"""
Skill Registry - Centralized catalog of all ScienceClaw skills

Automatically discovers and indexes skills from:
- scienceclaw/skills/ (existing 18 skills)
- Future: Claude Scientific Skills (140+ skills)

Provides:
- Skill metadata (name, description, category, capabilities)
- Skill search and matching
- Dependency management
- Execution interfaces
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import re


class SkillRegistry:
    """
    Central registry for all scientific skills.
    
    Discovers skills by scanning directories and parsing SKILL.md files.
    Enables dynamic skill selection based on research topic.
    """
    
    def __init__(self, scienceclaw_dir: Optional[Path] = None):
        """
        Initialize skill registry.
        
        Args:
            scienceclaw_dir: Root directory of scienceclaw (auto-detected if None)
        """
        if scienceclaw_dir is None:
            scienceclaw_dir = Path(__file__).parent.parent
        
        self.scienceclaw_dir = Path(scienceclaw_dir)
        self.skills_dir = self.scienceclaw_dir / "skills"
        self.cache_file = Path.home() / ".scienceclaw" / "skill_registry.json"
        self.config_file = Path.home() / ".scienceclaw" / "skill_config.json"
        
        # Skill catalog (loaded from cache or discovered)
        self.skills: Dict[str, Dict[str, Any]] = {}
        
        # Load or build registry
        if self.cache_file.exists():
            self._load_cache()
        else:
            self.discover_skills()
        
        # Filter out hidden skills (e.g. require credentials you don't have yet)
        self._apply_hidden_skills()
    
    def discover_skills(self, force_refresh: bool = False):
        """
        Discover all available skills by scanning directories.
        
        Args:
            force_refresh: Force re-scan even if cache exists
        """
        if force_refresh or not self.skills:
            print("🔍 Discovering scientific skills...")
            self.skills = {}
            
            # Scan skills directory
            if self.skills_dir.exists():
                for skill_dir in self.skills_dir.iterdir():
                    if skill_dir.is_dir() and not skill_dir.name.startswith('.'):
                        skill_meta = self._parse_skill(skill_dir)
                        if skill_meta:
                            self.skills[skill_meta['name']] = skill_meta
            
            print(f"  ✓ Discovered {len(self.skills)} skills")
            self._save_cache()
            self._apply_hidden_skills()
        
        return self.skills
    
    def _get_hidden_skills(self) -> List[str]:
        """
        Load list of skill names to hide (e.g. require credentials).
        Sources: ~/.scienceclaw/skill_config.json, or SCIENCECLAW_HIDDEN_SKILLS env.
        Default: adaptyv, drugbank-database (require API/DB credentials).
        """
        # Env override (comma-separated)
        env_val = os.environ.get("SCIENCECLAW_HIDDEN_SKILLS", "").strip()
        if env_val:
            return [s.strip() for s in env_val.split(",") if s.strip()]
        # Config file
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    cfg = json.load(f)
                return list(cfg.get("hidden_skills", []))
            except Exception:
                pass
        # Default: skills that commonly require credentials
        return ["adaptyv", "drugbank-database", "pubchem", "pytdc"]
    
    def _apply_hidden_skills(self):
        """Remove hidden skills from the registry (in-place)."""
        hidden = self._get_hidden_skills()
        if not hidden:
            return
        for name in hidden:
            self.skills.pop(name, None)
    
    def _parse_skill(self, skill_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Parse skill metadata from directory structure.
        
        Looks for:
        - SKILL.md (documentation)
        - scripts/ directory (executables)
        - requirements.txt (dependencies)
        
        Args:
            skill_dir: Path to skill directory
            
        Returns:
            Skill metadata dict or None if invalid
        """
        skill_name = skill_dir.name
        skill_md = skill_dir / "SKILL.md"
        scripts_dir = skill_dir / "scripts"
        
        # Basic metadata
        metadata = {
            "name": skill_name,
            "path": str(skill_dir),
            "type": "unknown",
            "category": "general",
            "description": "",
            "capabilities": [],
            "keywords": [],
            "executables": [],
            "dependencies": []
        }
        
        # Parse SKILL.md if exists
        if skill_md.exists():
            try:
                with open(skill_md) as f:
                    content = f.read()
                    
                    # Check for YAML frontmatter (Claude skills format)
                    if content.startswith('---'):
                        # Parse YAML frontmatter
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            frontmatter = parts[1]
                            content_body = parts[2]
                            
                            # Extract description from frontmatter
                            for line in frontmatter.split('\n'):
                                if line.strip().startswith('description:'):
                                    desc = line.split('description:', 1)[1].strip()
                                    metadata['description'] = desc
                                    break
                            
                            content = content_body  # Use body for further parsing
                    
                    # If no frontmatter or no description found, extract from content
                    if not metadata['description']:
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.strip() and not line.startswith('#'):
                                metadata['description'] = line.strip()
                                break
                    
                    # Extract capabilities (look for "Capabilities:" or "Core Capabilities" section)
                    capabilities_match = re.search(
                        r'(?:## )?(?:Core )?(?:Capabilities|Features|What it does)[:]*\s*\n((?:(?:###|[-*]|\d+\.)\s+.+\n?)+)',
                        content, re.IGNORECASE
                    )
                    if capabilities_match:
                        caps_text = capabilities_match.group(1)
                        # Extract capability titles (### headers or list items)
                        for line in caps_text.split('\n'):
                            line_stripped = line.strip()
                            if line_stripped.startswith('###'):
                                cap = line_stripped.replace('###', '').strip()
                                # Remove numbering like "1. "
                                cap = re.sub(r'^\d+\.\s+', '', cap)
                                metadata['capabilities'].append(cap)
                            elif line_stripped.startswith(('-', '*')):
                                cap = line_stripped.lstrip('- * ')
                                metadata['capabilities'].append(cap)
                            
                            if len(metadata['capabilities']) >= 5:
                                break  # Limit to first 5 capabilities
                    
                    # Extract keywords from content
                    metadata['keywords'] = self._extract_keywords(content)
                    
            except Exception as e:
                print(f"    Warning: Could not parse {skill_md}: {e}")
        
        # Find executable scripts
        if scripts_dir.exists():
            for script in scripts_dir.glob("*.py"):
                if not script.name.startswith('__'):
                    metadata['executables'].append(str(script))
        
        # Determine category from name/keywords
        metadata['category'] = self._categorize_skill(skill_name, metadata['keywords'])
        
        # Determine type (database, package, integration)
        metadata['type'] = self._determine_type(skill_name, metadata['description'])
        
        # Check for requirements
        req_file = skill_dir / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file) as f:
                    metadata['dependencies'] = [
                        line.strip() for line in f
                        if line.strip() and not line.startswith('#')
                    ]
            except Exception:
                pass
        
        return metadata
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract scientific keywords from skill documentation."""
        keywords = set()
        
        # Domain keywords
        domains = {
            'biology': ['protein', 'gene', 'dna', 'rna', 'cell', 'sequence', 'genome'],
            'chemistry': ['compound', 'molecule', 'synthesis', 'reaction', 'drug', 'chemical'],
            'bioinformatics': ['blast', 'alignment', 'annotation', 'phylogen'],
            'drug_discovery': ['screening', 'docking', 'admet', 'binding', 'inhibitor'],
            'clinical': ['clinical', 'patient', 'trial', 'disease', 'therapy'],
            'materials': ['material', 'crystal', 'metal', 'polymer', 'structure'],
            'computation': ['machine learning', 'deep learning', 'neural', 'prediction']
        }
        
        text_lower = text.lower()
        for domain, terms in domains.items():
            for term in terms:
                if term in text_lower:
                    keywords.add(domain)
                    keywords.add(term)
        
        return list(keywords)
    
    def _categorize_skill(self, name: str, keywords: List[str]) -> str:
        """Determine skill category from name and keywords."""
        name_lower = name.lower()
        keywords_str = ' '.join(keywords).lower()
        
        if any(term in name_lower for term in ['pubmed', 'arxiv', 'biorxiv', 'openalex', 'osti']):
            return 'literature'
        elif any(term in name_lower for term in ['corpus', 'minerals-data', 'bgs', 'comtrade',
                 'claimm', 'supply-chain', 'export-restrictions', 'commodity-profile',
                 'substitution', 'minerals-viz', 'scholar-search', 'meta-search']):
            return 'minerals'
        elif any(term in name_lower for term in ['material', 'ase']):
            return 'materials'
        elif any(term in name_lower for term in ['uniprot', 'pdb', 'alphafold', 'protein']):
            return 'proteins'
        elif any(term in name_lower for term in ['pubchem', 'chembl', 'drugbank', 'zinc']):
            return 'compounds'
        elif any(term in name_lower for term in ['kegg', 'reactome', 'string', 'pathway']):
            return 'pathways'
        elif any(term in name_lower for term in ['blast', 'sequence', 'alignment']):
            return 'bioinformatics'
        elif any(term in name_lower for term in ['tdc', 'admet', 'screening']):
            return 'drug_discovery'
        elif 'biology' in keywords_str:
            return 'biology'
        elif 'chemistry' in keywords_str:
            return 'chemistry'
        else:
            return 'general'
    
    def _determine_type(self, name: str, description: str) -> str:
        """Determine skill type (database, package, integration, tool)."""
        combined = (name + ' ' + description).lower()
        
        if any(term in combined for term in ['api', 'database', 'query', 'search', 'fetch']):
            return 'database'
        elif any(term in combined for term in ['python', 'library', 'package', 'analysis']):
            return 'package'
        elif any(term in combined for term in ['platform', 'integration', 'service']):
            return 'integration'
        else:
            return 'tool'
    
    def search_skills(self, 
                     query: str = "",
                     category: Optional[str] = None,
                     skill_type: Optional[str] = None,
                     limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for skills matching query.
        
        Args:
            query: Search query (matches name, description, keywords)
            category: Filter by category (proteins, compounds, literature, etc.)
            skill_type: Filter by type (database, package, tool, integration)
            limit: Maximum results to return
            
        Returns:
            List of matching skill metadata dicts
        """
        results = []
        query_lower = query.lower() if query else ""
        
        for skill_name, skill_meta in self.skills.items():
            # Filter by category
            if category and skill_meta.get('category') != category:
                continue
            
            # Filter by type
            if skill_type and skill_meta.get('type') != skill_type:
                continue
            
            # Search in name, description, keywords
            if query:
                searchable = (
                    skill_meta.get('name', '').lower() + ' ' +
                    skill_meta.get('description', '').lower() + ' ' +
                    ' '.join(skill_meta.get('keywords', []))
                )
                
                if query_lower not in searchable:
                    continue
            
            results.append(skill_meta)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Get skill metadata by name."""
        return self.skills.get(name)
    
    def get_skills_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all skills in a category."""
        return [
            skill for skill in self.skills.values()
            if skill.get('category') == category
        ]
    
    def get_categories(self) -> List[str]:
        """Get list of all skill categories."""
        return sorted(list(set(
            skill.get('category', 'general')
            for skill in self.skills.values()
        )))
    
    def suggest_skills_for_topic(self, topic: str) -> List[Dict[str, Any]]:
        """
        Suggest relevant skills for a research topic.
        
        Uses keyword matching to recommend skills.
        
        Args:
            topic: Research topic
            
        Returns:
            List of suggested skills (ordered by relevance)
        """
        topic_lower = topic.lower()
        scored_skills = []
        
        # Always include core literature search tools with high base score
        literature_tools = ['pubmed', 'openalex-database', 'biorxiv-database', 'arxiv']
        
        for skill_name, skill_meta in self.skills.items():
            score = 0
            
            # Boost core literature tools (always useful for any topic)
            if skill_name in literature_tools:
                score += 4
            
            # Match keywords
            for keyword in skill_meta.get('keywords', []):
                if keyword.lower() in topic_lower:
                    score += 2
            
            # Match category with boosted scoring
            category = skill_meta.get('category', '')
            
            # Detect topic type and boost relevant categories
            if any(kw in topic_lower for kw in ['coupling', 'synthesis', 'reaction', 'catalyst', 'chemical', 'organic', 'molecule']):
                # Chemistry topic
                if category in ['compounds', 'chemistry']:
                    score += 5
            elif any(kw in topic_lower for kw in ['protein', 'gene', 'enzyme', 'kinase']):
                # Biology topic
                if category in ['proteins', 'biology']:
                    score += 5
            elif any(kw in topic_lower for kw in ['drug', 'inhibitor', 'therapeutic']):
                # Drug discovery topic
                if category in ['compounds', 'drug_discovery']:
                    score += 5
            elif any(kw in topic_lower for kw in ['mineral', 'rare earth', 'separation', 'extraction', 'materials', 'supply chain', 'lithium', 'cobalt', 'nickel', 'copper', 'gallium', 'graphite', 'germanium', 'trade', 'import', 'export', 'production', 'hhi', 'concentration', 'supply risk', 'restriction', 'substitut', 'deposit', 'ore']):
                # Materials science / critical minerals topic
                if category in ['minerals', 'materials', 'literature', 'chemistry']:
                    score += 5

            # General category matching
            if category.lower() in topic_lower:
                score += 3
            
            # Match name
            if skill_name.lower() in topic_lower:
                score += 5
            
            # Match description
            desc = skill_meta.get('description', '').lower()
            for word in topic_lower.split():
                if len(word) > 3 and word in desc:
                    score += 1
            
            if score > 0:
                scored_skills.append((score, skill_meta))
        
        # Sort by score descending
        scored_skills.sort(reverse=True, key=lambda x: x[0])
        
        # Return top 10
        return [skill for score, skill in scored_skills[:10]]
    
    def _save_cache(self):
        """Save registry to cache file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'skills': self.skills,
                    'version': '1.0',
                    'last_updated': str(Path(self.skills_dir).stat().st_mtime)
                }, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save skill cache: {e}")
    
    def _load_cache(self):
        """Load registry from cache file."""
        try:
            with open(self.cache_file) as f:
                data = json.load(f)
                self.skills = data.get('skills', {})
        except Exception as e:
            print(f"Warning: Could not load skill cache: {e}")
            self.discover_skills()
    
    def refresh(self):
        """Force refresh of skill registry."""
        self.discover_skills(force_refresh=True)
    
    def stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        categories = {}
        types = {}
        
        for skill in self.skills.values():
            cat = skill.get('category', 'unknown')
            typ = skill.get('type', 'unknown')
            
            categories[cat] = categories.get(cat, 0) + 1
            types[typ] = types.get(typ, 0) + 1
        
        return {
            'total_skills': len(self.skills),
            'categories': categories,
            'types': types,
            'registry_version': '1.0'
        }


# Global registry instance
_registry = None

def get_registry() -> SkillRegistry:
    """Get the global skill registry instance."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
