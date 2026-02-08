"""
Investigation Tracker - Multi-step investigation management

Tracks investigations that may span multiple heartbeat cycles:
- Active investigations in progress
- Completed investigations
- Experiments conducted per investigation
- Investigation goals and progress

File format: ~/.scienceclaw/investigations/{agent_name}/tracker.json
Structure: {"active": {...}, "completed": {...}}
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4


class InvestigationTracker:
    """Tracks multi-step scientific investigations"""
    
    def __init__(self, agent_name: str, base_dir: Optional[str] = None):
        """
        Initialize investigation tracker for specific agent
        
        Args:
            agent_name: Name of the agent
            base_dir: Base directory for investigations (default: ~/.scienceclaw/investigations)
        """
        self.agent_name = agent_name
        if base_dir is None:
            base_dir = os.path.expanduser("~/.scienceclaw/investigations")
        
        self.inv_dir = Path(base_dir) / agent_name
        self.inv_dir.mkdir(parents=True, exist_ok=True)
        
        self.tracker_path = self.inv_dir / "tracker.json"
        
        # Initialize tracker file if it doesn't exist
        if not self.tracker_path.exists():
            self._save_tracker({
                "active": {},
                "completed": {}
            })
        
        self.tracker = self._load_tracker()
    
    def _load_tracker(self) -> Dict[str, Any]:
        """Load tracker from JSON file"""
        try:
            with open(self.tracker_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"active": {}, "completed": {}}
    
    def _save_tracker(self, tracker: Optional[Dict[str, Any]] = None):
        """Save tracker to JSON file"""
        if tracker is None:
            tracker = self.tracker
        
        with open(self.tracker_path, 'w') as f:
            json.dump(tracker, f, indent=2)
    
    def create_investigation(self, hypothesis: str, goal: str, 
                           planned_experiments: Optional[List[str]] = None,
                           tags: Optional[List[str]] = None,
                           priority: str = "medium",
                           **kwargs) -> str:
        """
        Create a new investigation
        
        Args:
            hypothesis: The hypothesis being investigated
            goal: What the investigation aims to discover/prove
            planned_experiments: List of planned experiments/tools to use
            tags: Relevant tags/topics
            priority: Priority level (high, medium, low)
            **kwargs: Additional metadata
            
        Returns:
            Investigation ID (UUID)
            
        Example:
            inv_id = tracker.create_investigation(
                hypothesis="LNP ionizable lipids affect muscle tissue delivery",
                goal="Identify optimal lipid ratios for muscle-targeted CRISPR delivery",
                planned_experiments=["pubmed_search", "chembl_search", "tdc_prediction"],
                tags=["LNP", "CRISPR", "delivery", "muscle"],
                priority="high"
            )
        """
        inv_id = str(uuid4())
        
        investigation = {
            "id": inv_id,
            "hypothesis": hypothesis,
            "goal": goal,
            "planned_experiments": planned_experiments or [],
            "experiments_completed": [],
            "tags": tags or [],
            "priority": priority,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": kwargs
        }
        
        self.tracker["active"][inv_id] = investigation
        self._save_tracker()
        
        return inv_id
    
    def add_experiment(self, investigation_id: str, experiment: Dict[str, Any]) -> bool:
        """
        Add an experiment result to an investigation
        
        Args:
            investigation_id: ID of the investigation
            experiment: Experiment details (tool, parameters, results, interpretation)
            
        Returns:
            True if successful, False if investigation not found
            
        Example:
            tracker.add_experiment(
                investigation_id=inv_id,
                experiment={
                    "tool": "pubmed",
                    "description": "Search for LNP muscle delivery papers",
                    "parameters": {"query": "LNP muscle delivery CRISPR", "max_results": 20},
                    "results_summary": "Found 18 papers, 3 highly relevant",
                    "key_findings": ["Paper A shows lipid X improves uptake", "Paper B contradicts"],
                    "interpretation": "Lipid composition matters, but conflicting data exists"
                }
            )
        """
        # Check active investigations
        if investigation_id in self.tracker["active"]:
            inv = self.tracker["active"][investigation_id]
        elif investigation_id in self.tracker["completed"]:
            inv = self.tracker["completed"][investigation_id]
        else:
            return False
        
        # Add timestamp to experiment
        experiment["timestamp"] = datetime.utcnow().isoformat()
        
        # Add to experiments list
        inv["experiments_completed"].append(experiment)
        inv["updated_at"] = datetime.utcnow().isoformat()
        
        self._save_tracker()
        return True
    
    def update_status(self, investigation_id: str, status: str, notes: Optional[str] = None) -> bool:
        """
        Update investigation status
        
        Args:
            investigation_id: ID of the investigation
            status: New status (active, paused, needs_review, ready_to_conclude)
            notes: Optional notes about status change
            
        Returns:
            True if successful, False if investigation not found
        """
        if investigation_id not in self.tracker["active"]:
            return False
        
        inv = self.tracker["active"][investigation_id]
        inv["status"] = status
        inv["updated_at"] = datetime.utcnow().isoformat()
        
        if notes:
            if "status_history" not in inv:
                inv["status_history"] = []
            inv["status_history"].append({
                "status": status,
                "notes": notes,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        self._save_tracker()
        return True
    
    def mark_complete(self, investigation_id: str, conclusion: str, 
                     confidence: str = "medium", next_steps: Optional[List[str]] = None) -> bool:
        """
        Mark an investigation as complete
        
        Args:
            investigation_id: ID of the investigation
            conclusion: Final conclusion reached
            confidence: Confidence in conclusion (high, medium, low)
            next_steps: Suggested follow-up investigations
            
        Returns:
            True if successful, False if investigation not found
            
        Example:
            tracker.mark_complete(
                investigation_id=inv_id,
                conclusion="Ionizable lipid DLin-MC3-DMA shows best muscle uptake in mice",
                confidence="high",
                next_steps=[
                    "Test DLin-MC3-DMA ratio optimization",
                    "Compare with primate models",
                    "Investigate PEG-lipid effects"
                ]
            )
        """
        if investigation_id not in self.tracker["active"]:
            return False
        
        inv = self.tracker["active"][investigation_id]
        
        # Add completion metadata
        inv["status"] = "completed"
        inv["conclusion"] = conclusion
        inv["confidence"] = confidence
        inv["next_steps"] = next_steps or []
        inv["completed_at"] = datetime.utcnow().isoformat()
        inv["updated_at"] = datetime.utcnow().isoformat()
        
        # Move to completed
        self.tracker["completed"][investigation_id] = inv
        del self.tracker["active"][investigation_id]
        
        self._save_tracker()
        return True
    
    def get_investigation(self, investigation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get investigation details
        
        Args:
            investigation_id: ID of the investigation
            
        Returns:
            Investigation dict or None if not found
        """
        if investigation_id in self.tracker["active"]:
            return self.tracker["active"][investigation_id]
        elif investigation_id in self.tracker["completed"]:
            return self.tracker["completed"][investigation_id]
        return None
    
    def get_active_investigations(self, priority: Optional[str] = None,
                                 tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get active investigations
        
        Args:
            priority: Filter by priority (high, medium, low)
            tags: Filter by tags (returns investigations matching any tag)
            
        Returns:
            List of active investigations
            
        Example:
            # Get all high priority investigations
            high_priority = tracker.get_active_investigations(priority="high")
            
            # Get investigations about CRISPR
            crispr_invs = tracker.get_active_investigations(tags=["CRISPR"])
        """
        investigations = list(self.tracker["active"].values())
        
        # Filter by priority
        if priority:
            investigations = [inv for inv in investigations if inv.get("priority") == priority]
        
        # Filter by tags
        if tags:
            investigations = [
                inv for inv in investigations 
                if any(tag in inv.get("tags", []) for tag in tags)
            ]
        
        # Sort by priority and creation date
        priority_order = {"high": 0, "medium": 1, "low": 2}
        investigations.sort(
            key=lambda x: (priority_order.get(x.get("priority", "medium"), 1), x.get("created_at", ""))
        )
        
        return investigations
    
    def get_completed_investigations(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get completed investigations
        
        Args:
            limit: Maximum number to return (most recent first)
            
        Returns:
            List of completed investigations
        """
        investigations = list(self.tracker["completed"].values())
        
        # Sort by completion date (newest first)
        investigations.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
        
        if limit:
            investigations = investigations[:limit]
        
        return investigations
    
    def get_investigation_progress(self, investigation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get progress summary for an investigation
        
        Args:
            investigation_id: ID of the investigation
            
        Returns:
            Progress summary dict or None if not found
        """
        inv = self.get_investigation(investigation_id)
        if not inv:
            return None
        
        planned = len(inv.get("planned_experiments", []))
        completed = len(inv.get("experiments_completed", []))
        
        return {
            "investigation_id": investigation_id,
            "hypothesis": inv.get("hypothesis"),
            "status": inv.get("status"),
            "progress": {
                "planned_experiments": planned,
                "completed_experiments": completed,
                "percentage": (completed / planned * 100) if planned > 0 else 0
            },
            "created_at": inv.get("created_at"),
            "updated_at": inv.get("updated_at")
        }
    
    def search_investigations(self, query: str, include_completed: bool = False) -> List[Dict[str, Any]]:
        """
        Search investigations by text
        
        Args:
            query: Text to search for (case-insensitive)
            include_completed: Whether to include completed investigations
            
        Returns:
            List of matching investigations
        """
        query_lower = query.lower()
        results = []
        
        # Search active investigations
        for inv in self.tracker["active"].values():
            inv_str = json.dumps(inv).lower()
            if query_lower in inv_str:
                results.append(inv)
        
        # Search completed investigations
        if include_completed:
            for inv in self.tracker["completed"].values():
                inv_str = json.dumps(inv).lower()
                if query_lower in inv_str:
                    results.append(inv)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about investigations
        
        Returns:
            Dictionary with counts, completion rates, etc.
        """
        active_invs = list(self.tracker["active"].values())
        completed_invs = list(self.tracker["completed"].values())
        
        stats = {
            "active_count": len(active_invs),
            "completed_count": len(completed_invs),
            "total_count": len(active_invs) + len(completed_invs),
            "by_priority": {
                "high": len([inv for inv in active_invs if inv.get("priority") == "high"]),
                "medium": len([inv for inv in active_invs if inv.get("priority") == "medium"]),
                "low": len([inv for inv in active_invs if inv.get("priority") == "low"])
            },
            "by_status": {},
            "total_experiments": sum(len(inv.get("experiments_completed", [])) for inv in active_invs + completed_invs)
        }
        
        # Count by status
        for inv in active_invs:
            status = inv.get("status", "active")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        return stats
    
    def cleanup_old_completed(self, days: int = 90) -> int:
        """
        Archive investigations completed more than N days ago
        
        Args:
            days: Number of days after which to archive
            
        Returns:
            Number of investigations archived
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()
        
        to_archive = []
        for inv_id, inv in self.tracker["completed"].items():
            completed_at = inv.get("completed_at", "")
            if completed_at < cutoff_iso:
                to_archive.append(inv_id)
        
        if not to_archive:
            return 0
        
        # Create archive file
        archive_path = self.inv_dir / f"archive_{datetime.utcnow().strftime('%Y%m')}.json"
        
        # Load existing archive if it exists
        if archive_path.exists():
            with open(archive_path, 'r') as f:
                archive = json.load(f)
        else:
            archive = {}
        
        # Move to archive
        for inv_id in to_archive:
            archive[inv_id] = self.tracker["completed"][inv_id]
            del self.tracker["completed"][inv_id]
        
        # Save archive and tracker
        with open(archive_path, 'w') as f:
            json.dump(archive, f, indent=2)
        
        self._save_tracker()
        
        return len(to_archive)
