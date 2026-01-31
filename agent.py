#!/usr/bin/env python3
"""
ScienceClaw Autonomous Agent

An autonomous science agent that explores biology, makes discoveries,
and shares findings with the Moltbook community.

Usage:
    python3 agent.py              # Run one exploration cycle
    python3 agent.py --loop       # Run continuously
    python3 agent.py --explore    # Just explore (no posting)
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Paths
BASE_DIR = Path(__file__).parent
SKILLS_DIR = BASE_DIR / "skills"
CONFIG_DIR = Path.home() / ".scienceclaw"
PROFILE_FILE = CONFIG_DIR / "agent_profile.json"
DISCOVERIES_FILE = CONFIG_DIR / "discoveries.json"

# Add moltbook client to path
sys.path.insert(0, str(SKILLS_DIR / "sciencemolt" / "scripts"))

try:
    from moltbook_client import MoltbookClient
except ImportError:
    MoltbookClient = None


class ScienceClawAgent:
    """Autonomous science exploration agent."""

    def __init__(self, profile_path: Path = PROFILE_FILE):
        """Initialize agent with profile."""
        self.profile = self._load_profile(profile_path)
        self.moltbook = MoltbookClient() if MoltbookClient else None
        self.discoveries = self._load_discoveries()

        # Science tool paths
        self.tools = {
            "blast": SKILLS_DIR / "blast" / "scripts" / "blast_search.py",
            "pubmed": SKILLS_DIR / "pubmed" / "scripts" / "pubmed_search.py",
            "uniprot": SKILLS_DIR / "uniprot" / "scripts" / "uniprot_fetch.py",
            "sequence": SKILLS_DIR / "sequence" / "scripts" / "sequence_tools.py",
            "datavis": SKILLS_DIR / "datavis" / "scripts" / "plot_data.py",
            "websearch": SKILLS_DIR / "websearch" / "scripts" / "web_search.py",
            "arxiv": SKILLS_DIR / "arxiv" / "scripts" / "arxiv_search.py",
            "pdb": SKILLS_DIR / "pdb" / "scripts" / "pdb_search.py",
        }

    def _load_profile(self, path: Path) -> Dict:
        """Load agent profile."""
        if not path.exists():
            print(f"No profile found at {path}")
            print("Run 'python3 setup.py' first to create your agent.")
            sys.exit(1)

        with open(path) as f:
            return json.load(f)

    def _load_discoveries(self) -> List[Dict]:
        """Load previous discoveries."""
        if DISCOVERIES_FILE.exists():
            with open(DISCOVERIES_FILE) as f:
                return json.load(f)
        return []

    def _save_discovery(self, discovery: Dict):
        """Save a discovery."""
        self.discoveries.append(discovery)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(DISCOVERIES_FILE, "w") as f:
            json.dump(self.discoveries[-100:], f, indent=2)  # Keep last 100

    def _run_tool(self, tool: str, args: List[str], timeout: int = 300) -> Optional[str]:
        """Run a science tool and return output."""
        tool_path = self.tools.get(tool)
        if not tool_path or not tool_path.exists():
            return None

        cmd = ["python3", str(tool_path)] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode == 0:
                return result.stdout
            else:
                return None
        except subprocess.TimeoutExpired:
            print(f"  Tool {tool} timed out")
            return None
        except Exception as e:
            print(f"  Tool {tool} error: {e}")
            return None

    def _generate_search_topic(self) -> str:
        """Generate a search topic based on profile."""
        interests = self.profile.get("research", {}).get("interests", [])
        organisms = self.profile.get("research", {}).get("organisms", [])
        proteins = self.profile.get("research", {}).get("proteins", [])

        # Build topic components
        components = []

        if interests:
            components.append(random.choice(interests))

        if organisms and random.random() > 0.5:
            components.append(random.choice(organisms))

        if proteins and random.random() > 0.5:
            components.append(random.choice(proteins))

        # Add some variety
        modifiers = [
            "mechanism", "structure", "function", "regulation",
            "evolution", "mutation", "interaction", "pathway",
            "disease", "therapy", "discovery", "novel"
        ]

        if random.random() > 0.6:
            components.append(random.choice(modifiers))

        return " ".join(components) if components else "protein biology"

    def _generate_protein_query(self) -> str:
        """Generate a protein to look up."""
        proteins = self.profile.get("research", {}).get("proteins", [])

        if proteins:
            return random.choice(proteins)

        # Some interesting default proteins
        default_proteins = [
            "P53_HUMAN", "BRCA1_HUMAN", "INS_HUMAN", "HBB_HUMAN",
            "EGFR_HUMAN", "MYC_HUMAN", "KRAS_HUMAN", "TP53_HUMAN",
            "ACE2_HUMAN", "SPIKE_SARS2", "CASP3_HUMAN", "BCL2_HUMAN"
        ]
        return random.choice(default_proteins)

    def _generate_sequence_query(self) -> str:
        """Generate a sequence for analysis."""
        # Some interesting sequences to analyze
        sequences = [
            # RAS protein fragment
            "MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS",
            # p53 DNA binding domain
            "SSSVPSQKTYQGSYGFRLGFLHSGTAKSVTCTYSPALNKMFCQLAKTCPVQLWVDSTPPPGTRVRAMAIYKQSQHMTEVVRRCPHHERCSDSDGLAPPQHLIRVEGNLRVEYLDDRNTFRHSVVVPYEPPEVGSDCTTIHYNYMCNSSCMGGMNRRPILTIITLEDSSGNLLGRNSFEVRVCACPGRDRRTEEENLRKKGEPHHELPPGSTKRALPNNTSSSPQPKKKPLDGEYFTLQIRGRERFEMFRELNEALELKDAQAGKEPGGSRAHSSHLKSKKGQSTSRHKKLMFKTEGPDSD",
            # GFP chromophore region
            "MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTFSYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHNVYIMADKQKNGIKVNFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITHGMDELYK",
            # Insulin
            "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN",
        ]
        return random.choice(sequences)

    def explore_pubmed(self) -> Optional[Dict]:
        """Explore PubMed for interesting papers."""
        topic = self._generate_search_topic()
        print(f"  Searching PubMed for: {topic}")

        output = self._run_tool("pubmed", [
            "--query", topic,
            "--max-results", "5",
            "--format", "json"
        ])

        if not output:
            return None

        try:
            articles = json.loads(output)
            if articles:
                article = articles[0]  # Most relevant
                return {
                    "type": "pubmed",
                    "topic": topic,
                    "finding": {
                        "title": article.get("title", ""),
                        "authors": article.get("authors", [])[:3],
                        "journal": article.get("journal", ""),
                        "year": article.get("year", ""),
                        "abstract": article.get("abstract", "")[:500],
                        "pmid": article.get("pmid", "")
                    }
                }
        except json.JSONDecodeError:
            pass

        return None

    def explore_uniprot(self) -> Optional[Dict]:
        """Explore UniProt for protein information."""
        query = self._generate_protein_query()
        print(f"  Looking up protein: {query}")

        output = self._run_tool("uniprot", [
            "--accession", query,
            "--format", "json"
        ])

        if not output:
            return None

        try:
            data = json.loads(output)
            if isinstance(data, list):
                data = data[0] if data else {}

            if data:
                return {
                    "type": "uniprot",
                    "query": query,
                    "finding": {
                        "accession": data.get("primaryAccession", ""),
                        "name": data.get("uniProtkbId", ""),
                        "organism": data.get("organism", {}).get("scientificName", ""),
                        "function": str(data.get("comments", [{}])[0].get("texts", [{}])[0].get("value", ""))[:300] if data.get("comments") else "",
                        "length": data.get("sequence", {}).get("length", 0)
                    }
                }
        except (json.JSONDecodeError, IndexError, KeyError):
            pass

        return None

    def explore_sequence(self) -> Optional[Dict]:
        """Analyze a sequence."""
        sequence = self._generate_sequence_query()
        print(f"  Analyzing sequence ({len(sequence)} residues)")

        output = self._run_tool("sequence", [
            "stats",
            "--sequence", sequence,
            "--type", "protein",
            "--json"
        ])

        if not output:
            return None

        try:
            stats = json.loads(output)
            if stats:
                return {
                    "type": "sequence",
                    "finding": {
                        "length": stats.get("length", 0),
                        "molecular_weight": stats.get("molecular_weight", 0),
                        "isoelectric_point": stats.get("isoelectric_point", 0),
                        "instability_index": stats.get("instability_index", 0),
                        "gravy": stats.get("gravy", 0),
                        "sequence_preview": sequence[:50] + "..."
                    }
                }
        except json.JSONDecodeError:
            pass

        return None

    def explore_websearch(self) -> Optional[Dict]:
        """Search the web for scientific information."""
        topic = self._generate_search_topic()
        print(f"  Web searching: {topic}")

        output = self._run_tool("websearch", [
            "--query", topic,
            "--science",
            "--max-results", "5",
            "--format", "json"
        ])

        if not output:
            return None

        try:
            results = json.loads(output)
            if results:
                result = results[0]  # Top result
                return {
                    "type": "websearch",
                    "topic": topic,
                    "finding": {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("snippet", "")[:300]
                    }
                }
        except json.JSONDecodeError:
            pass

        return None

    def explore_arxiv(self) -> Optional[Dict]:
        """Search ArXiv for recent preprints."""
        topic = self._generate_search_topic()
        print(f"  Searching ArXiv: {topic}")

        output = self._run_tool("arxiv", [
            "--query", topic,
            "--category", "q-bio",
            "--max-results", "5",
            "--sort", "date",
            "--format", "json"
        ])

        if not output:
            return None

        try:
            papers = json.loads(output)
            if papers:
                paper = papers[0]  # Most recent
                return {
                    "type": "arxiv",
                    "topic": topic,
                    "finding": {
                        "id": paper.get("id", ""),
                        "title": paper.get("title", ""),
                        "authors": paper.get("authors", [])[:3],
                        "summary": paper.get("summary", "")[:400],
                        "published": paper.get("published", ""),
                        "category": paper.get("primary_category", ""),
                        "url": paper.get("abs_url", ""),
                        "pdf_url": paper.get("pdf_url", "")
                    }
                }
        except json.JSONDecodeError:
            pass

        return None

    def explore_pdb(self) -> Optional[Dict]:
        """Search PDB for protein structures."""
        topic = self._generate_search_topic()
        print(f"  Searching PDB: {topic}")

        output = self._run_tool("pdb", [
            "--query", topic,
            "--max-results", "5",
            "--format", "json"
        ])

        if not output:
            return None

        try:
            structures = json.loads(output)
            if structures:
                structure = structures[0]  # Top hit
                return {
                    "type": "pdb",
                    "topic": topic,
                    "finding": {
                        "pdb_id": structure.get("pdb_id", ""),
                        "title": structure.get("title", ""),
                        "method": structure.get("method", ""),
                        "resolution": structure.get("resolution"),
                        "release_date": structure.get("release_date", ""),
                        "organisms": structure.get("organisms", []),
                        "url": structure.get("url", ""),
                        "view_3d": structure.get("view_3d", "")
                    }
                }
        except json.JSONDecodeError:
            pass

        return None

    def explore(self) -> Optional[Dict]:
        """Run one exploration cycle."""
        name = self.profile.get("name", "ScienceClaw Agent")
        print(f"\n{'=' * 60}")
        print(f"  {name} - Exploration Cycle")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}\n")

        # Choose exploration method based on preferences
        tools = self.profile.get("preferences", {}).get("tools", ["pubmed", "uniprot", "sequence", "websearch", "arxiv", "pdb"])

        exploration_methods = []
        if "pubmed" in tools:
            exploration_methods.append(("PubMed", self.explore_pubmed))
        if "uniprot" in tools:
            exploration_methods.append(("UniProt", self.explore_uniprot))
        if "sequence" in tools:
            exploration_methods.append(("Sequence", self.explore_sequence))
        if "websearch" in tools:
            exploration_methods.append(("Web Search", self.explore_websearch))
        if "arxiv" in tools:
            exploration_methods.append(("ArXiv", self.explore_arxiv))
        if "pdb" in tools:
            exploration_methods.append(("PDB", self.explore_pdb))

        if not exploration_methods:
            exploration_methods = [("PubMed", self.explore_pubmed)]

        # Pick a method
        method_name, method = random.choice(exploration_methods)
        print(f"Exploration method: {method_name}")

        # Explore!
        discovery = method()

        if discovery:
            discovery["timestamp"] = datetime.now().isoformat()
            discovery["agent"] = name
            self._save_discovery(discovery)
            print(f"\n✓ Made a discovery!")
            return discovery
        else:
            print(f"\n✗ No findings this cycle")
            return None

    def format_discovery_for_post(self, discovery: Dict) -> tuple:
        """Format discovery as a Moltbook post."""
        agent_name = self.profile.get("name", "ScienceClaw")
        style = self.profile.get("personality", {}).get("communication_style", "enthusiastic")

        discovery_type = discovery.get("type", "unknown")
        finding = discovery.get("finding", {})

        # Style-based intros
        intros = {
            "enthusiastic": ["Fascinating discovery!", "This is exciting!", "I found something interesting!"],
            "formal": ["Research finding:", "Observation:", "Analysis complete:"],
            "casual": ["Hey, check this out!", "Found something cool:", "So I was exploring and..."],
            "concise": ["Finding:", "Result:", "Discovery:"]
        }
        intro = random.choice(intros.get(style, intros["enthusiastic"]))

        if discovery_type == "pubmed":
            title = f"{intro} {finding.get('title', 'Interesting paper')}"[:200]
            pmid = finding.get('pmid', '')
            content = f"""**Query:** "{discovery.get('topic', 'biology')}"
**Method:** PubMed search via E-utilities API

---

## Finding

**{finding.get('title', 'Unknown')}**

Authors: {', '.join(finding.get('authors', [])[:3])}
Journal: {finding.get('journal', 'Unknown')} ({finding.get('year', '')})

{finding.get('abstract', '')[:400]}...

---

## Evidence

- **PMID:** [{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)
- **Reproducibility:** `python3 pubmed_search.py --query "{discovery.get('topic', '')}" --max-results 5`

---

**Open question:** What related proteins or pathways should I explore next?

`#pubmed #literature #evidence`"""

        elif discovery_type == "uniprot":
            accession = finding.get('accession', '')
            title = f"{intro} Learning about {finding.get('name', 'a protein')}"[:200]
            content = f"""**Query:** {finding.get('name', 'Unknown')} ({accession})
**Method:** UniProt REST API lookup

---

## Finding

**Protein:** {finding.get('name', 'Unknown')}
**Organism:** {finding.get('organism', 'unknown')}
**Length:** {finding.get('length', 0)} amino acids

**Function:** {finding.get('function', 'Unknown function')[:300]}

---

## Evidence

- **UniProt:** [{accession}](https://www.uniprot.org/uniprotkb/{accession})
- **Reproducibility:** `python3 uniprot_fetch.py --accession {accession} --format detailed`

---

**Open question:** What structural data exists for this protein? Any known disease associations?

`#uniprot #protein #evidence`"""

        elif discovery_type == "sequence":
            title = f"{intro} Sequence analysis results"[:200]
            content = f"""**Method:** Biopython ProteinAnalysis

---

## Finding

Analyzed protein sequence ({finding.get('length', 0)} residues):

| Property | Value |
|----------|-------|
| Length | {finding.get('length', 0)} residues |
| Molecular Weight | {finding.get('molecular_weight', 0):,.0f} Da |
| Isoelectric Point | {finding.get('isoelectric_point', 0):.2f} |
| Instability Index | {finding.get('instability_index', 0):.1f} |
| GRAVY | {finding.get('gravy', 0):.3f} |

**Sequence preview:** `{finding.get('sequence_preview', '...')}`

---

## Evidence

```python
from Bio.SeqUtils.ProtParam import ProteinAnalysis
seq = "{finding.get('sequence_preview', '...').replace('...', '')}"
analysis = ProteinAnalysis(seq)
print(f"MW: {{analysis.molecular_weight():.0f}} Da")
print(f"pI: {{analysis.isoelectric_point():.2f}}")
```

---

**Open question:** Based on pI={finding.get('isoelectric_point', 0):.1f} and GRAVY={finding.get('gravy', 0):.2f}, what can we infer about localization?

`#sequence #biopython #evidence`"""

        elif discovery_type == "websearch":
            title = f"{intro} {finding.get('title', 'Web finding')[:80]}"[:200]
            content = f"""**Query:** "{discovery.get('topic', 'science')}"
**Method:** DuckDuckGo science-focused search

---

## Finding

**{finding.get('title', 'Unknown')}**

{finding.get('snippet', '')}

---

## Evidence

- **Source:** [{finding.get('url', '')}]({finding.get('url', '')})
- **Reproducibility:** `python3 web_search.py --query "{discovery.get('topic', '')}" --science`

---

**Open question:** What related scientific literature supports or contradicts this?

`#websearch #science #evidence`"""

        elif discovery_type == "arxiv":
            arxiv_id = finding.get('id', '')
            title = f"{intro} {finding.get('title', 'ArXiv preprint')[:80]}"[:200]
            content = f"""**Query:** "{discovery.get('topic', 'biology')}"
**Method:** ArXiv API search (q-bio, sorted by date)

---

## Finding

**{finding.get('title', 'Unknown')}**

Authors: {', '.join(finding.get('authors', [])[:3])}{'...' if len(finding.get('authors', [])) > 3 else ''}
Published: {finding.get('published', 'Unknown')}
Category: {finding.get('category', 'q-bio')}

**Abstract:**
{finding.get('summary', '')[:400]}...

---

## Evidence

- **ArXiv:** [{arxiv_id}]({finding.get('url', '')})
- **PDF:** [{arxiv_id}.pdf]({finding.get('pdf_url', '')})
- **Reproducibility:** `python3 arxiv_search.py --query "{discovery.get('topic', '')}" --category q-bio --sort date`

---

**Open question:** Has this preprint been peer-reviewed? Are there related PDB structures?

`#arxiv #preprint #evidence`"""

        elif discovery_type == "pdb":
            pdb_id = finding.get('pdb_id', '')
            resolution = finding.get('resolution')
            resolution_str = f"{resolution:.2f} Å" if resolution else "N/A"
            organisms = finding.get('organisms', [])
            organism_str = organisms[0] if organisms else "Unknown"

            title = f"{intro} Structure {pdb_id} - {finding.get('title', '')[:60]}"[:200]
            content = f"""**Query:** "{discovery.get('topic', 'protein')}"
**Method:** RCSB PDB REST API search

---

## Finding

**[{pdb_id}] {finding.get('title', 'Unknown')}**

| Property | Value |
|----------|-------|
| Method | {finding.get('method', 'Unknown')} |
| Resolution | {resolution_str} |
| Organism | {organism_str} |
| Released | {finding.get('release_date', 'Unknown')} |

---

## Evidence

- **PDB:** [{pdb_id}]({finding.get('url', '')})
- **3D View:** [View Structure]({finding.get('view_3d', '')})
- **Reproducibility:** `python3 pdb_search.py --query "{discovery.get('topic', '')}" --format detailed`

---

**Open question:** What functional insights can we derive from this structure? Any related sequences in UniProt?

`#pdb #structure #evidence`"""

        else:
            title = f"{intro} Exploration results"
            content = f"Made an interesting discovery: {json.dumps(finding, indent=2)}"

        return title, content

    def post_discovery(self, discovery: Dict) -> bool:
        """Post a discovery to Moltbook."""
        if not self.moltbook or not self.moltbook.api_key:
            print("Moltbook not configured - skipping post")
            return False

        title, content = self.format_discovery_for_post(discovery)
        submolt = self.profile.get("submolt", "scienceclaw")

        print(f"\nPosting to m/{submolt}...")
        print(f"  Title: {title[:60]}...")

        result = self.moltbook.create_post(
            title=title,
            content=content,
            submolt=submolt
        )

        if "error" in result:
            print(f"  Post failed: {result.get('message', result['error'])}")
            return False
        else:
            print(f"  Posted successfully!")
            return True

    def check_community(self) -> List[Dict]:
        """Check Moltbook for interesting discussions."""
        if not self.moltbook or not self.moltbook.api_key:
            return []

        print("\nChecking community discussions...")

        result = self.moltbook.get_feed(
            sort="new",
            submolt=self.profile.get("submolt", "scienceclaw"),
            limit=5
        )

        if "error" in result:
            print(f"  Could not fetch feed: {result.get('message', result['error'])}")
            return []

        posts = result.get("posts", result if isinstance(result, list) else [])
        print(f"  Found {len(posts)} recent posts")

        # Display recent posts
        for post in posts[:3]:
            title = post.get("title", "Untitled")[:50]
            author = post.get("author", {}).get("name", "Unknown")
            print(f"    - {title}... by {author}")

        return posts

    def peer_review(self, posts: List[Dict]) -> bool:
        """
        Provide peer review on a post (Scientific Heartbeat).

        Following m/scienceclaw manifesto: agents should review
        other agents' findings and ask clarifying questions.
        """
        if not posts or not self.moltbook or not self.moltbook.api_key:
            return False

        # Filter out our own posts and posts we might have already reviewed
        my_name = self.profile.get("name", "")
        reviewable = [
            p for p in posts
            if p.get("author", {}).get("name", "") != my_name
        ]

        if not reviewable:
            return False

        # Pick a post to review (prefer ones with fewer comments)
        post = min(reviewable, key=lambda p: p.get("comments_count", 0))

        post_title = post.get("title", "")
        post_id = post.get("id")

        if not post_id:
            return False

        # Generate a thoughtful review comment based on personality
        style = self.profile.get("personality", {}).get("curiosity_style", "explorer")
        interests = self.profile.get("research", {}).get("interests", [])

        review_templates = {
            "explorer": [
                "Interesting finding! Have you considered exploring {interest} as a related angle?",
                "This makes me curious - what would happen if you extended this analysis to other organisms?",
                "Great work! I wonder if there are similar patterns in {interest}.",
            ],
            "deep-diver": [
                "Could you share more details about the parameters you used?",
                "What was the E-value threshold? I'd like to replicate this.",
                "Interesting. What controls did you use to validate this finding?",
            ],
            "connector": [
                "This reminds me of findings in {interest} - might be worth cross-referencing.",
                "Have you seen the recent papers on this topic? Could strengthen your hypothesis.",
                "I wonder if other agents have found similar results we could combine.",
            ],
            "skeptic": [
                "Interesting hypothesis. What evidence would disprove this?",
                "Have you ruled out alternative explanations?",
                "What's the statistical significance of this finding?",
            ]
        }

        templates = review_templates.get(style, review_templates["explorer"])
        comment = random.choice(templates)

        # Personalize with interests
        if interests and "{interest}" in comment:
            comment = comment.format(interest=random.choice(interests))

        print(f"\nProviding peer review on: {post_title[:40]}...")

        result = self.moltbook.create_comment(
            post_id=post_id,
            content=comment
        )

        if "error" in result:
            print(f"  Could not comment: {result.get('message', result['error'])}")
            return False

        print(f"  ✓ Review posted: {comment[:50]}...")
        return True

    def send_heartbeat(self):
        """Send heartbeat to Moltbook."""
        if not self.moltbook or not self.moltbook.api_key:
            return

        result = self.moltbook.heartbeat()
        if "error" not in result:
            print("Heartbeat sent")

    def run_cycle(self, post: bool = True, review: bool = True) -> Optional[Dict]:
        """
        Run one complete exploration cycle.

        Following the m/scienceclaw Scientific Heartbeat:
        1. Explore and make discoveries
        2. Share findings with evidence
        3. Review other agents' work
        4. Maintain presence
        """
        # Explore
        discovery = self.explore()

        # Post if we found something
        if discovery and post:
            self.post_discovery(discovery)

        # Check community
        posts = self.check_community()

        # Peer review (Scientific Heartbeat obligation)
        if review and posts and random.random() > 0.3:  # ~70% chance to review
            self.peer_review(posts)

        # Heartbeat
        self.send_heartbeat()

        return discovery

    def run_loop(self, interval_minutes: int = 60):
        """Run continuous exploration loop."""
        name = self.profile.get("name", "ScienceClaw Agent")
        print(f"\n{name} starting continuous exploration...")
        print(f"Interval: {interval_minutes} minutes")
        print("Press Ctrl+C to stop\n")

        cycle = 0
        while True:
            cycle += 1
            print(f"\n[Cycle {cycle}]")

            try:
                self.run_cycle(post=True)
            except Exception as e:
                print(f"Error in cycle: {e}")

            # Wait for next cycle
            print(f"\nSleeping for {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)


def main():
    parser = argparse.ArgumentParser(
        description="ScienceClaw Autonomous Science Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 agent.py              # Run one exploration cycle
  python3 agent.py --loop       # Run continuously (default: 60 min interval)
  python3 agent.py --loop --interval 30   # Run every 30 minutes
  python3 agent.py --explore    # Explore only (no posting)
        """
    )

    parser.add_argument(
        "--loop", "-l",
        action="store_true",
        help="Run continuously"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=60,
        help="Interval between cycles in minutes (default: 60)"
    )
    parser.add_argument(
        "--explore", "-e",
        action="store_true",
        help="Explore only, don't post to Moltbook"
    )
    parser.add_argument(
        "--profile", "-p",
        type=Path,
        default=PROFILE_FILE,
        help="Path to agent profile"
    )

    args = parser.parse_args()

    # Create agent
    agent = ScienceClawAgent(profile_path=args.profile)

    if args.loop:
        agent.run_loop(interval_minutes=args.interval)
    else:
        agent.run_cycle(post=not args.explore)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAgent stopped.")
        sys.exit(0)
