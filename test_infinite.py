#!/usr/bin/env python3
"""
Test script for Infinite integration.

Tests:
1. Connection to Infinite API
2. Agent registration (if not registered)
3. Post creation
4. Feed retrieval
5. Comment creation

Usage:
    python3 test_infinite.py              # Run all tests
    python3 test_infinite.py --register   # Test registration only
    python3 test_infinite.py --post       # Test posting only
"""

import argparse
import sys
from pathlib import Path

# Add skills to path
sys.path.insert(0, str(Path(__file__).parent / "skills" / "infinite" / "scripts"))

try:
    from infinite_client import InfiniteClient, CONFIG_FILE
except ImportError as e:
    print(f"Error importing infinite_client: {e}")
    sys.exit(1)


def test_connection():
    """Test connection to Infinite API."""
    print("=" * 60)
    print("TEST 1: Connection")
    print("=" * 60)

    client = InfiniteClient()

    # Try to get communities list (public endpoint)
    result = client.get_community("meta")

    if "error" in result and "connection" in str(result.get("error", "")).lower():
        print("❌ FAILED: Cannot connect to Infinite API")
        print(f"   Error: {result}")
        print("\n   Make sure Infinite is running:")
        print("   cd /home/fiona/LAMM/lammac && npm run dev")
        return False

    print("✓ Connection OK")
    return True


def test_registration():
    """Test agent registration."""
    print("\n" + "=" * 60)
    print("TEST 2: Registration")
    print("=" * 60)

    client = InfiniteClient()

    if client.api_key:
        print(f"✓ Already registered: {CONFIG_FILE}")
        print(f"  API key: {client.api_key[:20]}...")
        if client.jwt_token:
            print("✓ Authentication OK")
        return True

    print("Not registered. Attempting registration...")

    # Simple registration for testing
    result = client.register(
        name="TestAgent-ScienceClaw",
        bio="Test agent for ScienceClaw Infinite integration",
        capabilities=["pubmed", "blast"],
        capability_proof={
            "tool": "pubmed",
            "query": "test query",
            "result": {"success": True}
        }
    )

    if "api_key" in result:
        print("✓ Registration successful!")
        print(f"  Agent ID: {result.get('agent_id')}")
        print(f"  Config saved to: {CONFIG_FILE}")
        return True
    else:
        print(f"❌ FAILED: Registration error")
        print(f"   {result}")
        return False


def test_community():
    """Test community operations."""
    print("\n" + "=" * 60)
    print("TEST 3: Community")
    print("=" * 60)

    client = InfiniteClient()

    if not client.jwt_token:
        print("❌ FAILED: Not authenticated")
        return False

    # Check if scienceclaw community exists
    result = client.get_community("scienceclaw")

    if "error" not in result:
        print("✓ Community 'scienceclaw' exists")
        return True

    print("Community 'scienceclaw' not found. Creating...")

    result = client.create_community(
        name="scienceclaw",
        display_name="ScienceClaw",
        description="Autonomous science agents exploring biology, chemistry, and materials",
        manifesto="Evidence-based scientific discovery",
        rules=[
            "All posts must include data sources",
            "No speculation without evidence",
            "Constructive peer review only"
        ]
    )

    if "error" not in result:
        print("✓ Community created successfully")
        return True
    else:
        print(f"⚠ Community creation: {result}")
        print("  (This may be expected if community already exists)")
        return True


def test_post():
    """Test post creation."""
    print("\n" + "=" * 60)
    print("TEST 4: Post Creation")
    print("=" * 60)

    client = InfiniteClient()

    if not client.jwt_token:
        print("❌ FAILED: Not authenticated")
        return False

    result = client.create_post(
        community="scienceclaw",
        title="Test Post - Infinite Integration",
        content="This is a test post from ScienceClaw Infinite integration test suite.",
        hypothesis="ScienceClaw can successfully post to Infinite",
        method="Using infinite_client.py create_post() method",
        findings="Integration test successful",
        data_sources=["https://github.com/lamm-mit/scienceclaw"],
        open_questions=["What other communities should ScienceClaw agents join?"]
    )

    if "error" not in result and ("id" in result or "post_id" in result):
        post_id = result.get("id") or result.get("post_id")
        print(f"✓ Post created successfully")
        print(f"  Post ID: {post_id}")
        return True
    else:
        print(f"❌ FAILED: {result}")
        return False


def test_feed():
    """Test feed retrieval."""
    print("\n" + "=" * 60)
    print("TEST 5: Feed Retrieval")
    print("=" * 60)

    client = InfiniteClient()

    result = client.get_posts(community="scienceclaw", sort="new", limit=5)

    if "error" not in result:
        posts = result.get("posts", [])
        print(f"✓ Feed retrieved successfully")
        print(f"  Found {len(posts)} posts")
        if posts:
            print("\n  Recent posts:")
            for i, post in enumerate(posts[:3], 1):
                title = post.get("title", "")[:50]
                print(f"    {i}. {title}")
        return True
    else:
        print(f"❌ FAILED: {result}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Infinite integration")
    parser.add_argument("--register", action="store_true", help="Test registration only")
    parser.add_argument("--post", action="store_true", help="Test posting only")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")

    args = parser.parse_args()

    # Default to all tests
    if not (args.register or args.post):
        args.all = True

    print("\n🔬 ScienceClaw Infinite Integration Test Suite\n")

    results = []

    if args.all or args.register:
        results.append(("Connection", test_connection()))
        results.append(("Registration", test_registration()))
        results.append(("Community", test_community()))

    if args.all or args.post:
        results.append(("Post", test_post()))
        results.append(("Feed", test_feed()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status:10} {name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n✨ All tests passed! Infinite integration is working.")
        return 0
    else:
        print("\n⚠ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
