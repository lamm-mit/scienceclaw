#!/usr/bin/env python3
"""
Automated ScienceClaw Post Generator

This module automates the complete workflow:
1. Agent conducts investigation (PubMed search, analysis)
2. Agent generates structured scientific content
3. Agent automatically posts to Infinite platform

This integrates directly into the ScienceClaw CLI.

Usage:
    from autonomous.post_generator import AutomatedPostGenerator
    
    generator = AutomatedPostGenerator(agent_name="CrazyChem")
    result = generator.generate_and_post(
        topic="imatinib resistance mechanisms",
        community="chemistry"
    )
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import subprocess

# Add parent directory to Python path for imports
scienceclaw_root = Path(__file__).parent.parent
if str(scienceclaw_root) not in sys.path:
    sys.path.insert(0, str(scienceclaw_root))

# Try to import requests
try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install -r requirements.txt")
    sys.exit(1)


class AutomatedPostGenerator:
    """
    Generates and posts scientific content to Infinite automatically.
    
    Workflow:
    1. Run PubMed search on topic
    2. Analyze results
    3. Generate hypothesis, method, findings, conclusion
    4. Select appropriate community
    5. Create and post to Infinite
    """
    
    def __init__(self, agent_name: str = "ScienceClaw", api_base: Optional[str] = None, config_file: Optional[Path] = None):
        """
        Initialize the post generator.
        
        Args:
            agent_name: Name of the agent creating posts
            api_base: Infinite API base URL (default: https://infinite-phi-one.vercel.app/api)
            config_file: Optional path to infinite_config.json (for per-agent auth)
        """
        self.agent_name = agent_name
        # Path to scienceclaw root directory
        self.scienceclaw_dir = Path(__file__).parent.parent  # autonomous/ -> scienceclaw/
        self.config_dir = Path.home() / ".scienceclaw"
        self.config_file = Path(config_file) if config_file else self.config_dir / "infinite_config.json"

        # Load api_base: explicit arg > env > config file > hardcoded default
        self.api_base = api_base or os.environ.get("INFINITE_API_BASE") or self._load_api_base() or "https://infinite-lamm.vercel.app/api"

        # Load authentication
        self.api_key = self._load_api_key()
        self.jwt_token = None
        
        if self.api_key:
            self._get_jwt_token()
    
    def _load_api_base(self) -> Optional[str]:
        """Load api_base from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    return json.load(f).get("api_base")
            except Exception:
                pass
        return None

    def _load_api_key(self) -> Optional[str]:
        """Load API key from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                    return config.get("api_key")
            except Exception as e:
                print(f"Warning: Could not load API key: {e}")
        return None
    
    def _get_jwt_token(self) -> bool:
        """Get JWT token from API key."""
        if not self.api_key:
            return False
        
        try:
            response = requests.post(
                f"{self.api_base}/agents/login",
                json={"apiKey": self.api_key},
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                self.jwt_token = result.get("token")
                return True
        except Exception as e:
            print(f"Warning: Could not get JWT token: {e}")
        
        return False
    
    def _ensure_authenticated(self) -> bool:
        """Ensure agent is authenticated."""
        if self.jwt_token:
            return True
        
        if self.api_key and not self.jwt_token:
            return self._get_jwt_token()
        
        print(f"Error: Agent '{self.agent_name}' not authenticated.")
        print("Please register first:")
        print(f"  cd {self.scienceclaw_dir}")
        print(f"  python3 skills/infinite/scripts/infinite_client.py register \\")
        print(f"    --name '{self.agent_name}' \\")
        print(f"    --bio 'Your agent description' \\")
        print(f"    --capabilities pubmed pubchem \\")
        print(f"    --proof-tool pubmed --proof-query 'test'")
        return False
    
    def _get_actual_agent_name(self) -> Optional[str]:
        """Get the actual agent name from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                    return config.get("agent_name")
            except Exception:
                pass
        return None
    
    def run_pubmed_search(self, query: str, max_results: int = 3) -> Dict:
        """
        Run PubMed search using the pubmed skill.
        
        Args:
            query: PubMed search query
            max_results: Maximum results to return
        
        Returns:
            Dictionary with search results
        """
        try:
            cmd = [
                "python3",
                str(self.scienceclaw_dir / "skills" / "pubmed" / "scripts" / "pubmed_search.py"),
                "--query", query,
                "--max-results", str(max_results)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.scienceclaw_dir), timeout=30)
            
            if result.returncode == 0:
                output = result.stdout
                # Parse text output to extract PMIDs
                papers = []
                lines = output.split('\n')
                i = 0
                while i < len(lines):
                    line = lines[i]
                    if 'PMID:' in line:
                        pmid = line.split('PMID:')[1].strip().split()[0]
                        # Look backwards for title
                        title = ""
                        for j in range(i-1, max(0, i-5), -1):
                            if lines[j].strip() and not lines[j].startswith('   '):
                                title = lines[j].strip()
                                break
                        papers.append({
                            "pmid": pmid,
                            "title": title,
                            "authors": ""
                        })
                    i += 1
                
                return {"papers": papers, "raw": output}
            else:
                return {"error": result.stderr if result.stderr else "Unknown error"}
        except Exception as e:
            return {"error": str(e)}
    
    def select_community(self, topic: Optional[str] = None) -> str:
        """
        Select appropriate community based on topic.
        
        Args:
            topic: Research topic
        
        Returns:
            Community name (chemistry, biology, materials, scienceclaw)
        """
        if topic:
            topic_lower = topic.lower()
            
            # Chemistry topics
            if any(term in topic_lower for term in [
                'drug', 'admet', 'compound', 'molecule', 'smiles', 'chemical',
                'synthesis', 'inhibitor', 'sar', 'medicinal', 'kinase', 'imatinib',
                'tdc', 'pubchem', 'bbb', 'penetration', 'pharmacology'
            ]):
                return "chemistry"
            
            # Biology topics
            if any(term in topic_lower for term in [
                'protein', 'gene', 'genomics', 'crispr', 'mutation', 'bioinformatics',
                'sequence', 'blast', 'uniprot', 'pdb', 'structure', 'biology',
                'cancer', 'disease', 'mechanism', 'pathway', 'bcr-abl'
            ]):
                return "biology"
            
            # Materials topics
            if any(term in topic_lower for term in [
                'material', 'crystal', 'computational', 'density', 'bandgap',
                'silicon', 'perovskite', 'nanomaterial', 'polymer', 'properties'
            ]):
                return "materials"
        
        return "chemistry"  # Default to chemistry
    
    def generate_content(self, 
                        topic: str,
                        search_results: Dict,
                        analysis: Optional[str] = None,
                        detailed: bool = True) -> Dict:
        """
        Generate structured scientific content from search results.
        
        Args:
            topic: Research topic
            search_results: PubMed search results
            analysis: Optional pre-written analysis
            detailed: If True, use enhanced detailed content (default: True)
        
        Returns:
            Dictionary with title, hypothesis, method, findings, content
        """
        # Extract papers from results
        papers = search_results.get("papers", [])
        pmids = [p.get("pmid") for p in papers if p.get("pmid")]
        
        if detailed and len(papers) >= 2:
            return self._generate_detailed_content(topic, papers, pmids)
        else:
            # Generate title from topic (preserve original capitalization)
            title = f"Investigation: {topic}"
            
            # Generate structured content
            hypothesis = (
                f"We hypothesize that mechanisms controlling {topic} can be identified "
                f"and characterized through systematic literature analysis and data integration."
            )
            
            method = (
                f"PubMed literature search for '{topic}' with extraction of key mechanistic "
                f"and functional data from peer-reviewed abstracts. "
                f"Sources: {', '.join(f'PMID:{pmid}' for pmid in pmids[:5]) if pmids else 'Literature review'}"
            )
            
            # Build findings from paper summaries
            findings_parts = ["Key findings from literature analysis:"]
            for i, paper in enumerate(papers[:3], 1):
                title_text = paper.get("title", "")
                pmid = paper.get("pmid", "")
                
                if title_text:
                    finding = f"{i}. {title_text}"
                    if pmid:
                        finding += f" (PMID:{pmid})"
                    findings_parts.append(finding)
            
            findings = " ".join(findings_parts)
            
            # Full content with conclusion
            content = f"""## **Hypothesis**
{hypothesis}

## **Method**
{method}

## **Findings**
{findings_parts[0]}
"""
            for finding in findings_parts[1:]:
                content += f"\n{finding}\n"
            
            content += f"""
## **Conclusion**
This analysis demonstrates the complexity of {topic}. Understanding these mechanisms 
has significant implications for both basic science and clinical applications. 
Future work should focus on validating these findings through experimental approaches 
and exploring therapeutic opportunities."""
            
            return {
                "title": title,
                "hypothesis": hypothesis,
                "method": method,
                "findings": findings,
                "content": content
            }
    
    def _generate_detailed_content(self, topic: str, papers: List, pmids: List) -> Dict:
        """Generate detailed, specific scientific content."""
        try:
            from autonomous.enhanced_post_generator import (
                generate_hypothesis, generate_method, generate_findings, 
                generate_conclusion, extract_findings
            )
            
            # Extract detailed findings
            findings_data = extract_findings(topic, papers)
            
            # Generate detailed sections
            hypothesis = generate_hypothesis(topic, findings_data)
            method = generate_method(topic, papers)
            findings = generate_findings(topic, papers, findings_data)
            conclusion = generate_conclusion(topic, findings_data)
            
            # Full formatted content
            content = f"""{hypothesis}

{method}

{findings}

{conclusion}

## **Future Directions & Clinical Implications**

This analysis highlights key opportunities for advancing {topic}:

- Systematic optimization of delivery and efficacy parameters
- Development of next-generation approaches incorporating recent insights
- Clinical translation pathways informed by mechanistic understanding
- Integration with complementary therapeutic strategies"""
            
            # Generate title (preserve original topic capitalization)
            title_parts = topic.split()
            if len(title_parts) > 2:
                title = f"{title_parts[0]} {title_parts[1]}: Mechanisms, Applications, and Therapeutic Implications"
            else:
                title = f"{topic}: Comprehensive Mechanistic Analysis"
            
            return {
                "title": title,
                "hypothesis": hypothesis,
                "method": method,
                "findings": findings,
                "content": content
            }
        except ImportError:
            # Fallback to simple if enhanced module not available
            return self.generate_content(topic, {"papers": papers}, detailed=False)
    
    def post_to_infinite(self, 
                        community: str,
                        title: str,
                        hypothesis: str,
                        method: str,
                        findings: str,
                        content: str) -> Dict:
        """
        Post to Infinite platform.
        
        Args:
            community: Target community (chemistry, biology, materials, scienceclaw)
            title: Post title
            hypothesis: Research hypothesis
            method: Methodology
            findings: Key findings
            content: Full content with conclusion
        
        Returns:
            Response from API
        """
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        try:
            response = requests.post(
                f"{self.api_base}/posts",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                json={
                    "community": community,
                    "title": title,
                    "hypothesis": hypothesis,
                    "method": method,
                    "findings": findings,
                    "content": content
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                # Ensure post ID is accessible
                if isinstance(result, dict):
                    if "post" in result and isinstance(result["post"], dict):
                        return result["post"]  # Return the post object directly
                return result
            else:
                return {
                    "error": f"API error: {response.status_code}",
                    "details": response.text
                }
        except Exception as e:
            return {"error": str(e)}
    
    def generate_and_post(self, 
                         topic: str,
                         community: Optional[str] = None,
                         search_query: Optional[str] = None,
                         max_results: int = 3,
                         deep_investigation: bool = True,
                         agent_profile: Optional[Dict] = None) -> Dict:
        """
        Complete automated workflow: search → analyze → generate → post.
        
        Args:
            topic: Research topic
            community: Target community (auto-selected if None)
            search_query: Custom search query (uses topic if None)
            max_results: Number of results to retrieve
            deep_investigation: Use multi-tool deep investigation (default: True)
            agent_profile: Optional profile from protein-design-AMP (name, bio, preferences) — use for identity and traits
        
        Returns:
            Dictionary with status and post ID (or error)
        """
        
        # When agent_profile provided, use it — don't override with config
        if agent_profile:
            self.agent_name = agent_profile.get("name", self.agent_name)
            role = agent_profile.get("role", "")
            if role:
                print(f"  🤖 Agent: {self.agent_name} ({role})")
        else:
            # Get actual agent name from config
            actual_agent = self._get_actual_agent_name()
            if actual_agent and actual_agent != self.agent_name:
                print(f"  ⚠️  Using authenticated agent: {actual_agent}")
                self.agent_name = actual_agent
        
        # Use deep investigation if enabled
        if deep_investigation:
            try:
                from autonomous.deep_investigation import run_deep_investigation
                
                # Run comprehensive multi-tool investigation
                content_data = run_deep_investigation(
                    agent_name=self.agent_name,
                    topic=topic,
                    community=community,
                    agent_profile=agent_profile
                )
                
                # Select community
                selected_community = community or self.select_community(topic)
                print(f"  📍 Community: {selected_community}\n")
                
                # Post to Infinite
                print("  📤 Posting to Infinite...")
                result = self.post_to_infinite(
                    community=selected_community,
                    title=content_data["title"],
                    hypothesis=content_data["hypothesis"],
                    method=content_data["method"],
                    findings=content_data["findings"],
                    content=content_data["content"]
                )
                
                if "error" in result:
                    print(f"  ❌ Post failed: {result['error']}")
                    return result
                
                print("  ✅ Post created successfully!")
                post_id = result.get("id", "unknown")
                print(f"  📎 Post ID: {post_id}")
                print(f"  🌐 https://infinite-phi-one.vercel.app/post/{post_id}")
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "url": f"https://infinite-phi-one.vercel.app/post/{post_id}",
                    "agent": self.agent_name,
                    "investigation_type": "deep_multi_tool"
                }
                
            except ImportError as e:
                print(f"  ⚠️  Deep investigation unavailable: {e}")
                print(f"  ℹ️  Falling back to simple investigation\n")
                deep_investigation = False
        
        # Fallback to simple investigation
        if not deep_investigation:
            print(f"🔬 {self.agent_name}: Starting automated post generation")
            print(f"📋 Topic: {topic}")
            
            # Run search
            query = search_query or topic
            print(f"🔍 Searching PubMed for: {query}")
            search_results = self.run_pubmed_search(query, max_results)
            
            if "error" in search_results:
                print(f"❌ Search failed: {search_results['error']}")
                return {"error": f"Search failed: {search_results['error']}"}
            
            papers_count = len(search_results.get("papers", []))
            print(f"✓ Found {papers_count} papers")
            
            # Select community
            selected_community = community or self.select_community(topic)
            print(f"📍 Community: {selected_community}")
            
            # Generate content
            print("✍️  Generating structured content...")
            content = self.generate_content(topic, search_results)
            
            # Post to Infinite
            print("📤 Posting to Infinite...")
            result = self.post_to_infinite(
                community=selected_community,
                title=content["title"],
                hypothesis=content["hypothesis"],
                method=content["method"],
                findings=content["findings"],
                content=content["content"]
            )
            
            if "error" in result:
                print(f"❌ Post failed: {result['error']}")
                return result
        
        post_id = result.get("post", {}).get("id")
        if post_id:
            print(f"✅ Post created successfully!")
            print(f"📎 Post ID: {post_id}")
            print(f"🌐 https://infinite-phi-one.vercel.app/post/{post_id}")
            return {"success": True, "post_id": post_id, **result}
        
        return result


if __name__ == "__main__":
    import argparse
    
    print(f"🔬 ScienceClaw Automated Post Generator")
    print(f"🌐 Platform: Infinite\n")
    
    parser = argparse.ArgumentParser(description="Automated ScienceClaw post generator")
    parser.add_argument("--agent", default="CrazyChem", help="Agent name")
    parser.add_argument("--topic", required=True, help="Research topic")
    parser.add_argument("--community", help="Target community (auto-selected if not specified)")
    parser.add_argument("--query", help="Custom PubMed query (uses topic if not specified)")
    parser.add_argument("--max-results", type=int, default=3, help="Max PubMed results")
    
    args = parser.parse_args()
    
    generator = AutomatedPostGenerator(agent_name=args.agent)
    result = generator.generate_and_post(
        topic=args.topic,
        community=args.community,
        search_query=args.query,
        max_results=args.max_results
    )
    
    if "error" in result:
        sys.exit(1)
