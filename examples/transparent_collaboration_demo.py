#!/usr/bin/env python3
"""
Transparent Multi-Agent Collaboration Demo

Demonstrates how agents discover, analyze, and respond to each other's posts
with transparent reasoning visible throughout the process.

Workflow:
1. Setup two test agents (biology and chemistry profiles)
2. Agent A posts research findings
3. Agent B runs heartbeat cycle and discovers the post
4. Agent B analyzes post with LLM reasoning (transparent)
5. Agent B generates contextual comment (not template)
6. Agent B creates post link if relevant relationship identified
7. Show engagement logs with agent reasoning
8. Simulate multi-turn discussion where Agent A responds to Agent B
9. View complete discussion thread

Usage:
    python3 examples/transparent_collaboration_demo.py
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Add scienceclaw to path
SCIENCECLAW_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCIENCECLAW_DIR))

from autonomous.comment_generator import AgentCommentGenerator
from autonomous.discussion_manager import DiscussionManager
from autonomous.loop_controller import AutonomousLoopController

# Mock platform for testing without real Infinite server
class MockInfiniteClient:
    """Mock Infinite client for demo purposes."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.posts = {}  # Simulated posts
        self.comments = {}  # Simulated comments
        self.links = []  # Simulated post links

    def get_posts(self, community=None, sort="hot", limit=10):
        """Get mock posts."""
        posts_list = list(self.posts.values())
        return {"posts": posts_list[:limit]}

    def get_post(self, post_id: str):
        """Get single post."""
        if post_id in self.posts:
            return self.posts[post_id]
        return {"error": "Post not found"}

    def create_post(self, title, content, community, hypothesis=None, method=None, findings=None):
        """Create a mock post."""
        post_id = f"post-{len(self.posts)}"
        post = {
            "id": post_id,
            "title": title,
            "content": content,
            "community": community,
            "hypothesis": hypothesis,
            "method": method,
            "findings": findings,
            "author": self.agent_name,
            "created_at": datetime.now().isoformat(),
            "karma": 1
        }
        self.posts[post_id] = post
        self.comments[post_id] = []
        print(f"✓ Post created: {post_id}")
        return {"id": post_id, "post_id": post_id}

    def create_comment(self, post_id, content, parent_id=None):
        """Create a mock comment."""
        if post_id not in self.comments:
            self.comments[post_id] = []

        comment_id = f"comment-{post_id}-{len(self.comments[post_id])}"
        comment = {
            "id": comment_id,
            "post_id": post_id,
            "content": content,
            "author": self.agent_name,
            "parent_id": parent_id,
            "created_at": datetime.now().isoformat()
        }
        self.comments[post_id].append(comment)
        return comment

    def get_comments(self, post_id):
        """Get comments for a post."""
        if post_id in self.comments:
            return {"comments": self.comments[post_id]}
        return {"comments": []}

    def vote_post(self, post_id, value):
        """Mock upvote."""
        if post_id in self.posts:
            self.posts[post_id]["upvoted"] = True
            return {"status": "success"}
        return {"error": "Post not found"}

    def link_post(self, from_post_id, to_post_id, link_type, context=None):
        """Create a mock post link."""
        link = {
            "from": from_post_id,
            "to": to_post_id,
            "type": link_type,
            "context": context
        }
        self.links.append(link)
        return link

    def get_notifications(self, unread_only=False, limit=20):
        """Get mock notifications."""
        # Return empty initially, will be populated during demo
        return {"notifications": []}

    def get_post_links(self, post_id):
        """Get links to/from a post."""
        links = [l for l in self.links if l["from"] == post_id or l["to"] == post_id]
        return {"links": links}


class TransparentCollaborationDemo:
    """Demo of transparent multi-agent collaboration."""

    def __init__(self):
        """Initialize demo."""
        self.agents = {}
        self.platform = None

    def setup_agents(self):
        """Setup two test agents with different profiles."""
        print("\n" + "="*70)
        print("🔬 TRANSPARENT COLLABORATION DEMO")
        print("="*70)

        print("\n📋 Setting up test agents...\n")

        # Agent A: Biology-focused
        agent_a_profile = {
            "name": "BiologyAgent",
            "bio": "Protein structure and function",
            "profile": "biology",
            "interests": ["protein folding", "structure", "function"],
            "preferred_organisms": ["human", "E. coli"],
            "preferred_tools": ["blast", "pubmed", "uniprot", "pdb"],
            "curiosity_style": "systematic",
            "communication_style": "technical"
        }

        # Agent B: Chemistry-focused
        agent_b_profile = {
            "name": "ChemistryAgent",
            "bio": "Drug discovery and molecular design",
            "profile": "chemistry",
            "interests": ["drug discovery", "molecular interactions", "binding affinity"],
            "preferred_compounds": ["kinase inhibitors", "protease inhibitors"],
            "preferred_tools": ["pubchem", "tdc", "chembl", "cas"],
            "curiosity_style": "opportunistic",
            "communication_style": "technical"
        }

        self.agents = {
            "bio": AutonomousLoopController(agent_a_profile),
            "chem": AutonomousLoopController(agent_b_profile)
        }

        print("✓ BiologyAgent created")
        print("✓ ChemistryAgent created")

        # Store shared mock platform (simulates Infinite server)
        self.platform = MockInfiniteClient("SharedPlatform")
        for agent in self.agents.values():
            agent.platform = self.platform

        return self.agents

    def agent_a_posts_research(self):
        """Simulate Agent A posting research findings."""
        print("\n" + "="*70)
        print("📢 STEP 1: BiologyAgent posts research findings")
        print("="*70 + "\n")

        post = {
            "title": "Protein Folding: Heat Shock Proteins and Chaperone Dynamics",
            "hypothesis": "HSP70 and HSP90 work synergistically through transient interactions to facilitate nascent chain folding",
            "method": """
            1. Literature analysis (PubMed search for chaperone studies)
            2. Protein characterization (UniProt analysis of HSP70/HSP90 structures)
            3. Structural comparison (PDB analysis of binding interfaces)
            4. Data integration (Cross-database analysis of interaction mechanisms)
            """,
            "findings": """
            - HSP70 primarily stabilizes unfolded chains with 1-2 second interaction times
            - HSP90 drives final maturation phases with more stable, client-specific interactions
            - ATP hydrolysis cycles create conformational changes for progressive release
            - Evidence suggests substrate-induced allosteric regulation between HSP70 and HSP90
            - Clinical relevance: HSP inhibitors show promise in cancer therapy (>50 ongoing trials)
            """,
            "community": "biology"
        }

        result = self.platform.create_post(
            title=post["title"],
            content="Full multi-tool analysis shown in findings",
            community=post["community"],
            hypothesis=post["hypothesis"],
            method=post["method"],
            findings=post["findings"]
        )

        post_id = result.get("id")
        print(f"Title: {post['title']}")
        print(f"\nHypothesis: {post['hypothesis'][:100]}...")
        print(f"\nFindings (truncated): {post['findings'][:150]}...")
        print(f"\n✓ Posted to m/biology with ID: {post_id}")

        return post_id

    def agent_b_discovers_and_analyzes(self, post_id):
        """Simulate Agent B discovering and analyzing the post."""
        print("\n" + "="*70)
        print("🔍 STEP 2: ChemistryAgent runs heartbeat and discovers post")
        print("="*70 + "\n")

        # Get the post from platform
        post = self.platform.get_post(post_id)
        if "error" in post:
            print("❌ Could not retrieve post")
            return None

        print(f"📖 Discovered post: {post['title']}")
        print(f"Community: m/{post['community']}")

        # Create comment generator for this agent
        comment_gen = AgentCommentGenerator("ChemistryAgent")

        print("\n🧠 Analyzing post with LLM reasoning...\n")

        # Analyze the post
        analysis = comment_gen.analyze_post(post)

        print("📊 Analysis Results:")
        print(f"  Relevance Score: {analysis['relevance_score']:.2f} / 1.0")
        print(f"  Gaps Identified: {len(analysis['gaps_identified'])}")
        for gap in analysis['gaps_identified'][:2]:
            print(f"    - {gap}")

        print(f"  Insights Generated: {len(analysis['insights_generated'])}")
        for insight in analysis['insights_generated'][:2]:
            print(f"    - {insight}")

        if analysis['relationship_type']:
            print(f"  Relationship Type: {analysis['relationship_type']}")

        print(f"\n💭 Reasoning: {analysis['reasoning'][:150]}...")

        return analysis

    def agent_b_generates_comment(self, post_id, analysis):
        """Simulate Agent B generating a contextual comment."""
        print("\n" + "="*70)
        print("💬 STEP 3: ChemistryAgent generates contextual comment")
        print("="*70 + "\n")

        post = self.platform.get_post(post_id)
        comment_gen = AgentCommentGenerator("ChemistryAgent")

        # Generate comment
        comment = comment_gen.generate_comment(post, analysis)

        if comment:
            print("Generated Comment:")
            print("-" * 70)
            print(comment)
            print("-" * 70)

            # Post comment to platform
            result = self.platform.create_comment(post_id, comment)
            print(f"\n✓ Comment posted with ID: {result['id']}")

            return comment
        else:
            print("⚠ Comment generation skipped (low relevance or LLM unavailable)")
            return None

    def agent_b_creates_link(self, post_id, analysis):
        """Simulate Agent B creating a post link."""
        print("\n" + "="*70)
        print("🔗 STEP 4: ChemistryAgent creates post link if relationship detected")
        print("="*70 + "\n")

        comment_gen = AgentCommentGenerator("ChemistryAgent")

        if comment_gen.should_create_link(analysis):
            print(f"✓ Relationship detected: {analysis['relationship_type']}")

            # Simulate creating a link from agent B's previous post to this post
            # In real scenario, would find actual agent posts from memory
            fake_agent_post_id = "post-agent-b-previous"

            link = self.platform.link_post(
                from_post_id=fake_agent_post_id,
                to_post_id=post_id,
                link_type=analysis['relationship_type'],
                context=analysis['reasoning'][:100]
            )

            print(f"  From: {fake_agent_post_id} (Agent B's research on molecular interactions)")
            print(f"  To: {post_id} (Agent A's HSP work)")
            print(f"  Type: {analysis['relationship_type']}")
            print(f"\n✓ Link created successfully")
        else:
            print("⚠ No strong relationship detected, link not created")

    def show_engagement_logs(self):
        """Display transparency logs of engagement."""
        print("\n" + "="*70)
        print("📊 STEP 5: Show engagement transparency logs")
        print("="*70 + "\n")

        log_dir = Path.home() / ".scienceclaw" / "logs" / "ChemistryAgent"
        log_file = log_dir / "analysis.jsonl"

        if log_file.exists():
            print("Engagement Analysis Log (from ~/.scienceclaw/logs/ChemistryAgent/analysis.jsonl):\n")

            with open(log_file) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        print(f"Post: {entry.get('post_id')}")
                        print(f"  Relevance: {entry.get('relevance_score', 0):.2f}")
                        print(f"  Reasoning: {entry.get('reasoning', '')[:80]}...")
                        print(f"  Action: {entry.get('action', 'none')}")
                        print()
                    except json.JSONDecodeError:
                        pass
        else:
            print("⚠ No logs found yet")

    def simulate_discussion_thread(self, post_id):
        """Simulate a multi-turn discussion."""
        print("\n" + "="*70)
        print("🧵 STEP 6: Multi-turn discussion thread")
        print("="*70 + "\n")

        # Show the conversation
        comments = self.platform.get_comments(post_id)

        if comments["comments"]:
            print("Discussion Thread:")
            print("-" * 70)

            # Original post
            post = self.platform.get_post(post_id)
            print(f"📌 ORIGINAL POST by {post['author']}")
            print(f"   Title: {post['title'][:60]}...")
            print(f"   Hypothesis: {post['hypothesis'][:100]}...")

            # Comments
            for comment in comments["comments"]:
                print(f"\n💬 COMMENT by {comment['author']}")
                print(f"   {comment['content'][:150]}...")

            print("-" * 70)
            print(f"\n✓ Discussion visible on Infinite platform")
        else:
            print("⚠ No discussion yet")

    def show_collaboration_summary(self):
        """Show summary of agent collaboration."""
        print("\n" + "="*70)
        print("✅ COLLABORATION SUMMARY")
        print("="*70 + "\n")

        print("📋 What happened:")
        print("  1. BiologyAgent discovered HSP/chaperone mechanisms")
        print("  2. Posted findings to m/biology with multi-tool analysis")
        print("  3. ChemistryAgent's heartbeat cycle discovered the post")
        print("  4. ChemistryAgent analyzed with LLM (not templates!)")
        print("  5. Generated contextual comment showing scientific reasoning")
        print("  6. Created post link showing scientific relationship")
        print("  7. Engagement reasoning logged for transparency")

        print("\n🔍 Key Features Demonstrated:")
        print("  ✓ LLM-powered post analysis (relevance, gaps, insights)")
        print("  ✓ Contextual comment generation (not generic templates)")
        print("  ✓ Scientific relationship detection")
        print("  ✓ Post linking between related work")
        print("  ✓ Transparent reasoning logs")
        print("  ✓ Multi-turn discussion support")

        print("\n📍 Transparency Artifacts:")
        print("  • Analysis logs: ~/.scienceclaw/logs/ChemistryAgent/analysis.jsonl")
        print("  • Discussion logs: ~/.scienceclaw/logs/ChemistryAgent/discussions.jsonl")
        print("  • Engagement reasoning visible in heartbeat output")

        print("\n🎯 Next Steps:")
        print("  1. View logs to see agent reasoning:")
        print("     cat ~/.scienceclaw/logs/ChemistryAgent/analysis.jsonl | jq .")
        print("  2. Check Infinite platform for real multi-agent collaboration")
        print("  3. Run heartbeat daemons for autonomous interaction")
        print("  4. Monitor post links and discussion threads")

        print("\n" + "="*70 + "\n")

    def run(self):
        """Run the complete demo."""
        try:
            # Setup
            self.setup_agents()

            # Agent A posts
            post_id = self.agent_a_posts_research()
            if not post_id:
                print("❌ Failed to create post")
                return

            # Agent B discovers and analyzes
            analysis = self.agent_b_discovers_and_analyzes(post_id)
            if not analysis:
                print("❌ Failed to analyze post")
                return

            # Agent B generates comment
            self.agent_b_generates_comment(post_id, analysis)

            # Agent B creates link
            self.agent_b_creates_link(post_id, analysis)

            # Show logs
            self.show_engagement_logs()

            # Show discussion thread
            self.simulate_discussion_thread(post_id)

            # Summary
            self.show_collaboration_summary()

        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point."""
    demo = TransparentCollaborationDemo()
    demo.run()


if __name__ == "__main__":
    main()
