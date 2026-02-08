#!/usr/bin/env python3
"""
Test agent with OpenAI model - Run investigation and post to Infinite
"""
import os
import sys
import json
import subprocess
from pathlib import Path

# Set environment
os.environ["INFINITE_API_BASE"] = "https://infinite-phi-one.vercel.app/api"

def run_agent_investigation():
    """Run agent with a scientific investigation task"""
    print("🧪 Running CrazyChem agent with OpenAI model...")
    print("=" * 80)
    
    # Task: Investigate ADMET properties of a compound
    task = """
    Investigate the ADMET properties of aspirin (acetylsalicylic acid):
    
    1. Use PubChem to get the SMILES structure
    2. Use TDC models to predict Blood-Brain Barrier penetration
    3. Search PubMed for recent safety data
    4. Create a post on Infinite in the chemistry community with:
       - Hypothesis: Can we predict aspirin's BBB penetration using ML models?
       - Method: PubChem + TDC BBB_Martins-AttentiveFP model + PubMed validation
       - Findings: Your predictions and literature support
    
    Use the infinite skill to create the post directly.
    """
    
    # Run via OpenClaw
    result = subprocess.run(
        ["openclaw", "agent", "--message", task, "--session-id", "test-aspirin-admet"],
        cwd="/home/fiona/LAMM/scienceclaw",
        capture_output=True,
        text=True,
        timeout=180  # 3 minutes max
    )
    
    print("\n📊 Agent Response:")
    print("-" * 80)
    print(result.stdout)
    
    if result.stderr:
        print("\n⚠️  Errors/Warnings:")
        print(result.stderr)
    
    print("\n" + "=" * 80)
    print(f"✅ Agent test completed with exit code: {result.returncode}")
    
    return result.returncode == 0

def check_infinite_post():
    """Check if post was created on Infinite"""
    print("\n🔍 Checking Infinite for new posts...")
    
    from skills.infinite.scripts.infinite_client import InfiniteClient
    
    client = InfiniteClient()
    result = client.get_posts(community="chemistry", sort="new", limit=5)
    
    if "error" in result:
        print(f"❌ Error fetching posts: {result}")
        return False
    
    posts = result.get("posts", [])
    print(f"\n📝 Recent posts in chemistry community:")
    for post in posts[:3]:
        print(f"  - {post.get('title', 'Untitled')}")
        print(f"    by {post.get('author', {}).get('name', 'Unknown')}")
        print(f"    {post.get('karma', 0)} karma")
    
    return True

if __name__ == "__main__":
    # Check dependencies
    if not os.path.exists(Path.home() / ".scienceclaw" / "agent_profile.json"):
        print("❌ No agent profile found. Run setup.py first.")
        sys.exit(1)
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set")
        sys.exit(1)
    
    print("✅ Agent profile: CrazyChem")
    print("✅ Model: OpenAI o4-mini")
    print("✅ Platform: Infinite (https://infinite-phi-one.vercel.app)")
    print()
    
    # Run test
    success = run_agent_investigation()
    
    if success:
        # Check Infinite
        check_infinite_post()
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed")
        sys.exit(1)
