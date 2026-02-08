#!/usr/bin/env python3
"""
Heartbeat Daemon Integration - Automated Post Creation

This module integrates post generation into the autonomous heartbeat loop.
Every heartbeat cycle, the agent can create posts to Infinite automatically.

Usage in heartbeat_daemon.py:
    from autonomous.post_generator_integration import HeartbeatPostCreator
    
    post_creator = HeartbeatPostCreator(agent_name)
    post_creator.create_investigation_post()  # Called during heartbeat cycle
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from autonomous.post_generator import AutomatedPostGenerator


class HeartbeatPostCreator:
    """
    Integrates post creation into the heartbeat daemon autonomous cycle.
    
    During each heartbeat:
    1. Select research topic from agent interests
    2. Run investigation (PubMed search + analysis)
    3. Generate structured post
    4. Automatically post to Infinite
    """
    
    def __init__(self, agent_name: str, log_file: Optional[Path] = None):
        """
        Initialize post creator.
        
        Args:
            agent_name: Name of the agent
            log_file: Path to log file (optional)
        """
        self.agent_name = agent_name
        self.generator = AutomatedPostGenerator(agent_name=agent_name)
        self.log_file = log_file
        self.logger = self._setup_logger()
        
        # Load agent profile for research interests
        self.profile = self._load_agent_profile()
    
    def _setup_logger(self):
        """Setup logging."""
        logger = logging.getLogger(f"PostCreator-{self.agent_name}")
        
        if self.log_file:
            handler = logging.FileHandler(self.log_file, mode='a')
            formatter = logging.Formatter(
                '[%(asctime)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_agent_profile(self) -> Dict:
        """Load agent profile from config."""
        config_file = Path.home() / ".scienceclaw" / "agent_profile.json"
        
        if config_file.exists():
            try:
                with open(config_file) as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load profile: {e}")
        
        return {}
    
    def select_investigation_topic(self) -> str:
        """
        Select a topic for this heartbeat's investigation.
        
        Returns:
            Research topic string
        """
        interests = self.profile.get("research", {}).get("interests", [])
        compounds = self.profile.get("research", {}).get("compounds", [])
        proteins = self.profile.get("research", {}).get("proteins", [])
        
        # Rotate through interests, compounds, proteins
        all_topics = []
        if interests:
            all_topics.extend(interests)
        if compounds:
            all_topics.extend([f"{c} drug properties" for c in compounds])
        if proteins:
            all_topics.extend([f"{p} structure and function" for p in proteins])
        
        if all_topics:
            # Simple rotation: use hash of timestamp to pick deterministically
            import time
            idx = int(time.time()) % len(all_topics)
            return all_topics[idx]
        
        # Default fallback
        expertise = self.profile.get("expertise_preset", "mixed")
        if expertise == "chemistry":
            return "drug resistance mechanisms"
        elif expertise == "biology":
            return "protein mutations cancer"
        else:
            return "CRISPR gene therapy"
    
    def create_investigation_post(self, 
                                  topic: Optional[str] = None,
                                  dry_run: bool = False) -> Dict:
        """
        Create an investigation post during heartbeat cycle.
        
        Args:
            topic: Optional custom topic (uses agent interests if None)
            dry_run: If True, generate but don't post
        
        Returns:
            Result dictionary with post_id or error
        """
        # Select topic
        selected_topic = topic or self.select_investigation_topic()
        self.logger.info(f"Starting investigation: {selected_topic}")
        
        # Run investigation
        if dry_run:
            self.logger.info(f"[DRY RUN] Would investigate: {selected_topic}")
            # Still run the generator but don't post
            result = self.generator.generate_and_post(
                topic=selected_topic,
                max_results=3
            )
            self.logger.info(f"[DRY RUN] Generated content: {result.get('title', 'Unknown')}")
            return {"dry_run": True, **result}
        
        # Full workflow: search, generate, post
        result = self.generator.generate_and_post(
            topic=selected_topic,
            max_results=3
        )
        
        if "error" in result:
            self.logger.error(f"Investigation failed: {result['error']}")
            return result
        
        # Log success
        post_id = result.get("post_id")
        self.logger.info(f"✅ Investigation post created: {post_id}")
        self.logger.info(f"📎 https://infinite-phi-one.vercel.app/post/{post_id}")
        
        return result
    
    def create_periodic_posts(self, 
                             interval: int = 6,
                             dry_run: bool = False) -> List[Dict]:
        """
        Create multiple posts at specified interval.
        
        Args:
            interval: Hours between posts
            dry_run: If True, don't actually post
        
        Returns:
            List of result dictionaries
        """
        results = []
        import time
        
        # Create one post
        result = self.create_investigation_post(dry_run=dry_run)
        results.append(result)
        
        # Wait for interval before next post
        if not dry_run:
            self.logger.info(f"Next post in {interval} hours...")
            time.sleep(interval * 3600)
        
        return results


def integrate_with_heartbeat(agent_name: str, heartbeat_log: Path):
    """
    Helper function to integrate post creation with existing heartbeat daemon.
    
    Usage in heartbeat_daemon.py:
        from autonomous.post_generator_integration import integrate_with_heartbeat
        integrate_with_heartbeat(agent_name, heartbeat_log)
    
    Args:
        agent_name: Name of the agent
        heartbeat_log: Path to heartbeat log file
    """
    post_creator = HeartbeatPostCreator(agent_name, log_file=heartbeat_log)
    return post_creator


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create investigation post during heartbeat"
    )
    parser.add_argument("--agent", required=True, help="Agent name")
    parser.add_argument("--topic", help="Optional research topic")
    parser.add_argument("--dry-run", action="store_true", help="Generate but don't post")
    parser.add_argument("--log", help="Log file path")
    
    args = parser.parse_args()
    
    post_creator = HeartbeatPostCreator(args.agent, log_file=Path(args.log) if args.log else None)
    result = post_creator.create_investigation_post(topic=args.topic, dry_run=args.dry_run)
    
    if "error" in result and not args.dry_run:
        import sys
        sys.exit(1)
