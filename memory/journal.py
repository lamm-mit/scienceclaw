"""
Agent Journal - JSONL append-only log for agent observations and experiments

Stores chronological records of:
- Observations (from reading posts, papers, etc.)
- Hypotheses (research questions formed)
- Experiments (tool executions and parameters)
- Conclusions (findings and interpretations)

File format: ~/.scienceclaw/journals/{agent_name}/journal.jsonl
Each line is a JSON object with: timestamp, type, content, metadata
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import re


class AgentJournal:
    """Persistent journal for agent memories and investigations"""
    
    def __init__(self, agent_name: str, base_dir: Optional[str] = None):
        """
        Initialize journal for specific agent
        
        Args:
            agent_name: Name of the agent (used for directory structure)
            base_dir: Base directory for journals (default: ~/.scienceclaw/journals)
        """
        self.agent_name = agent_name
        if base_dir is None:
            base_dir = os.path.expanduser("~/.scienceclaw/journals")
        
        self.journal_dir = Path(base_dir) / agent_name
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        
        self.journal_path = self.journal_dir / "journal.jsonl"
        
        # Create empty file if it doesn't exist
        if not self.journal_path.exists():
            self.journal_path.touch()
    
    def _log_entry(self, entry_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Internal method to log an entry
        
        Args:
            entry_type: Type of entry (observation, hypothesis, experiment, conclusion)
            content: Main content of the entry
            metadata: Additional structured data
            
        Returns:
            The logged entry as a dictionary
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": entry_type,
            "content": content,
            "metadata": metadata or {}
        }
        
        # Append to JSONL file
        with open(self.journal_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return entry
    
    def log_observation(self, content: str, source: Optional[str] = None, 
                       tags: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """
        Log an observation from reading posts, papers, or other sources
        
        Args:
            content: Description of what was observed
            source: Source of observation (post_id, pmid, url, etc.)
            tags: List of relevant tags/topics
            **kwargs: Additional metadata fields
            
        Returns:
            The logged entry
            
        Example:
            journal.log_observation(
                content="Found paper on CRISPR delivery using LNPs",
                source="pmid:12345678",
                tags=["CRISPR", "LNP", "delivery"],
                relevance="high"
            )
        """
        metadata = {
            "source": source,
            "tags": tags or [],
            **kwargs
        }
        return self._log_entry("observation", content, metadata)
    
    def log_hypothesis(self, hypothesis: str, motivation: Optional[str] = None,
                      related_observations: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """
        Log a hypothesis or research question
        
        Args:
            hypothesis: The hypothesis or research question
            motivation: Why this hypothesis is worth investigating
            related_observations: List of observation sources that led to this
            **kwargs: Additional metadata fields
            
        Returns:
            The logged entry
            
        Example:
            journal.log_hypothesis(
                hypothesis="LNP formulation affects CRISPR efficiency in muscle tissue",
                motivation="Multiple papers show variable results with different LNPs",
                related_observations=["pmid:12345678", "pmid:87654321"]
            )
        """
        metadata = {
            "motivation": motivation,
            "related_observations": related_observations or [],
            **kwargs
        }
        return self._log_entry("hypothesis", hypothesis, metadata)
    
    def log_experiment(self, description: str, tool: str, parameters: Dict[str, Any],
                      results: Optional[Any] = None, hypothesis_id: Optional[str] = None,
                      **kwargs) -> Dict[str, Any]:
        """
        Log an experiment (tool execution)
        
        Args:
            description: Human-readable description of experiment
            tool: Name of tool used (blast, pubmed, tdc, etc.)
            parameters: Tool parameters used
            results: Results from tool execution (can be large JSON)
            hypothesis_id: Link to hypothesis being tested
            **kwargs: Additional metadata fields
            
        Returns:
            The logged entry
            
        Example:
            journal.log_experiment(
                description="Search PubMed for LNP CRISPR delivery papers",
                tool="pubmed",
                parameters={"query": "LNP CRISPR delivery", "max_results": 20},
                results={"papers": [...]},
                hypothesis_id="hypothesis_2024-01-15T10:30:00"
            )
        """
        metadata = {
            "tool": tool,
            "parameters": parameters,
            "results": results,
            "hypothesis_id": hypothesis_id,
            **kwargs
        }
        return self._log_entry("experiment", description, metadata)
    
    def log_conclusion(self, conclusion: str, evidence: Optional[List[str]] = None,
                      confidence: Optional[str] = None, next_steps: Optional[List[str]] = None,
                      **kwargs) -> Dict[str, Any]:
        """
        Log a conclusion or finding
        
        Args:
            conclusion: The conclusion reached
            evidence: List of supporting evidence (experiment timestamps, sources)
            confidence: Confidence level (high, medium, low)
            next_steps: Suggested follow-up investigations
            **kwargs: Additional metadata fields
            
        Returns:
            The logged entry
            
        Example:
            journal.log_conclusion(
                conclusion="Ionizable lipids in LNPs significantly affect muscle uptake",
                evidence=["experiment_2024-01-15T11:00:00", "pmid:12345678"],
                confidence="high",
                next_steps=["Test specific ionizable lipid ratios", "Compare with liver uptake"]
            )
        """
        metadata = {
            "evidence": evidence or [],
            "confidence": confidence,
            "next_steps": next_steps or [],
            **kwargs
        }
        return self._log_entry("conclusion", conclusion, metadata)
    
    def search(self, query: str, entry_types: Optional[List[str]] = None,
               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search journal entries by text or type
        
        Args:
            query: Text to search for (case-insensitive, matches content)
            entry_types: Filter by entry types (observation, hypothesis, experiment, conclusion)
            limit: Maximum number of results to return
            
        Returns:
            List of matching entries (newest first)
            
        Example:
            # Find all hypotheses about CRISPR
            results = journal.search("CRISPR", entry_types=["hypothesis"])
            
            # Find recent experiments
            results = journal.search("", entry_types=["experiment"], limit=10)
        """
        if not self.journal_path.exists():
            return []
        
        query_lower = query.lower()
        results = []
        
        with open(self.journal_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line)
                    
                    # Filter by type
                    if entry_types and entry.get("type") not in entry_types:
                        continue
                    
                    # Filter by query (search in content and metadata)
                    if query:
                        entry_str = json.dumps(entry).lower()
                        if query_lower not in entry_str:
                            continue
                    
                    results.append(entry)
                    
                except json.JSONDecodeError:
                    continue
        
        # Reverse to get newest first
        results.reverse()
        
        if limit:
            results = results[:limit]
        
        return results
    
    def get_investigated_topics(self) -> set:
        """
        Get set of topics that have been investigated
        
        Extracts topics from:
        - Tags in observations
        - Hypotheses
        - Tool parameters
        
        Returns:
            Set of unique topic strings
            
        Example:
            topics = journal.get_investigated_topics()
            # {"CRISPR", "LNP", "protein folding", "BBB penetration"}
        """
        topics = set()
        
        if not self.journal_path.exists():
            return topics
        
        with open(self.journal_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line)
                    
                    # Extract from tags
                    if "tags" in entry.get("metadata", {}):
                        topics.update(entry["metadata"]["tags"])
                    
                    # Extract from hypothesis content
                    if entry.get("type") == "hypothesis":
                        # Simple extraction of capitalized words/phrases
                        content = entry.get("content", "")
                        # Extract quoted phrases
                        quoted = re.findall(r'"([^"]+)"', content)
                        topics.update(quoted)
                        # Extract capitalized words (likely proper nouns/concepts)
                        capitalized = re.findall(r'\b[A-Z][A-Za-z0-9-]+\b', content)
                        topics.update(capitalized)
                    
                    # Extract from experiment parameters
                    if entry.get("type") == "experiment":
                        params = entry.get("metadata", {}).get("parameters", {})
                        # Extract query parameters
                        if "query" in params:
                            topics.add(params["query"])
                        # Extract protein/compound names
                        if "protein" in params:
                            topics.add(params["protein"])
                        if "compound" in params:
                            topics.add(params["compound"])
                        if "smiles" in params:
                            topics.add(params["smiles"])
                
                except json.JSONDecodeError:
                    continue
        
        return topics
    
    def get_recent_entries(self, limit: int = 10, entry_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get most recent journal entries
        
        Args:
            limit: Number of entries to return
            entry_types: Filter by entry types
            
        Returns:
            List of recent entries (newest first)
        """
        return self.search("", entry_types=entry_types, limit=limit)
    
    def export_to_json(self, output_path: Optional[str] = None) -> str:
        """
        Export entire journal as single JSON array
        
        Args:
            output_path: Path to write JSON file (default: journal_export.json in journal dir)
            
        Returns:
            Path to exported file
        """
        if output_path is None:
            output_path = self.journal_dir / "journal_export.json"
        else:
            output_path = Path(output_path)
        
        entries = []
        
        if self.journal_path.exists():
            with open(self.journal_path, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        
        with open(output_path, 'w') as f:
            json.dump(entries, f, indent=2)
        
        return str(output_path)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about journal
        
        Returns:
            Dictionary with counts by type, date ranges, etc.
        """
        stats = {
            "total_entries": 0,
            "by_type": {},
            "first_entry": None,
            "last_entry": None,
            "unique_topics": 0
        }
        
        if not self.journal_path.exists():
            return stats
        
        with open(self.journal_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line)
                    stats["total_entries"] += 1
                    
                    entry_type = entry.get("type", "unknown")
                    stats["by_type"][entry_type] = stats["by_type"].get(entry_type, 0) + 1
                    
                    timestamp = entry.get("timestamp")
                    if timestamp:
                        if stats["first_entry"] is None:
                            stats["first_entry"] = timestamp
                        stats["last_entry"] = timestamp
                
                except json.JSONDecodeError:
                    continue
        
        stats["unique_topics"] = len(self.get_investigated_topics())
        
        return stats
