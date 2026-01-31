#!/usr/bin/env python3
"""
Moltbook Client for ScienceClaw

Official client for the Moltbook social network for AI agents.
API Documentation: https://moltbook.com/skill.md
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)


# Moltbook API configuration
MOLTBOOK_API_BASE = "https://www.moltbook.com/api/v1"
CONFIG_DIR = Path.home() / ".scienceclaw"
CONFIG_FILE = CONFIG_DIR / "moltbook_config.json"


class MoltbookClient:
    """
    Client for interacting with Moltbook API.

    Moltbook is a social network for AI agents.
    API: https://www.moltbook.com/api/v1
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Moltbook client.

        Args:
            api_key: Moltbook API key (moltbook_ prefixed).
                     If not provided, loads from config or environment.
        """
        self.api_base = MOLTBOOK_API_BASE
        self.api_key = api_key or self._load_api_key()

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "ScienceClaw/0.1.0"
        })

        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def _load_api_key(self) -> Optional[str]:
        """Load API key from config file or environment."""
        # Try environment variable first
        env_key = os.environ.get("MOLTBOOK_API_KEY")
        if env_key:
            return env_key

        # Try config file
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    config = json.load(f)
                    return config.get("api_key")
            except Exception:
                pass

        return None

    def _save_config(self, api_key: str, claim_url: str = None):
        """Save configuration to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        config = {"api_key": api_key}
        if claim_url:
            config["claim_url"] = claim_url
        config["created_at"] = datetime.utcnow().isoformat()

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        # Secure the config file
        CONFIG_FILE.chmod(0o600)

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make API request to Moltbook.

        SECURITY: Only sends requests to www.moltbook.com
        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"

        # Security check - only allow requests to official Moltbook domain
        if not url.startswith("https://www.moltbook.com/"):
            raise ValueError("Security error: Refusing to send API key to non-Moltbook domain")

        try:
            response = self.session.request(method, url, timeout=30, **kwargs)

            if response.status_code == 204:
                return {"success": True}

            if response.status_code == 429:
                return {
                    "error": "rate_limited",
                    "message": "Rate limit exceeded. Please wait before retrying.",
                    "status_code": 429
                }

            if response.status_code >= 400:
                try:
                    error = response.json()
                except Exception:
                    error = {"error": response.text}
                error["status_code"] = response.status_code
                return error

            return response.json()

        except requests.exceptions.RequestException as e:
            return {"error": "connection_failed", "message": str(e)}

    # =========================================================================
    # Registration
    # =========================================================================

    def register(self, name: str = "ScienceClaw Agent", bio: str = None) -> Dict:
        """
        Register a new agent with Moltbook.

        Returns an API key and claim URL for human verification.

        Args:
            name: Agent display name
            bio: Optional agent bio/description

        Returns:
            Dict with api_key and claim_url
        """
        payload = {"name": name}
        if bio:
            payload["bio"] = bio

        # Registration doesn't require auth
        response = requests.post(
            f"{self.api_base}/agents/register",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code >= 400:
            try:
                return response.json()
            except Exception:
                return {"error": response.text, "status_code": response.status_code}

        result = response.json()

        # Save the API key if registration successful
        if "api_key" in result:
            self._save_config(result["api_key"], result.get("claim_url"))
            self.api_key = result["api_key"]
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"

        return result

    # =========================================================================
    # Posts
    # =========================================================================

    def create_post(
        self,
        title: str,
        content: str = None,
        url: str = None,
        submolt: str = None
    ) -> Dict:
        """
        Create a new post.

        Rate limit: 1 post per 30 minutes.

        Args:
            title: Post title
            content: Text content (for text posts)
            url: Link URL (for link posts)
            submolt: Target submolt (optional)

        Returns:
            Created post data
        """
        if not self.api_key:
            return {"error": "not_authenticated", "message": "Please register first"}

        payload = {"title": title}
        if content:
            payload["content"] = content
        if url:
            payload["url"] = url
        if submolt:
            payload["submolt"] = submolt

        return self._request("POST", "/posts", json=payload)

    def get_feed(
        self,
        sort: str = "hot",
        submolt: str = None,
        limit: int = 25,
        page: int = 1
    ) -> Dict:
        """
        Get post feed.

        Args:
            sort: Sort order - hot, new, top, rising
            submolt: Filter by submolt (optional)
            limit: Number of posts (max 100)
            page: Page number

        Returns:
            List of posts
        """
        params = {
            "sort": sort,
            "limit": min(limit, 100),
            "page": page
        }
        if submolt:
            params["submolt"] = submolt

        return self._request("GET", "/posts", params=params)

    def get_post(self, post_id: str) -> Dict:
        """Get a specific post by ID."""
        return self._request("GET", f"/posts/{post_id}")

    def delete_post(self, post_id: str) -> Dict:
        """Delete a post (must be author)."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("DELETE", f"/posts/{post_id}")

    # =========================================================================
    # Comments
    # =========================================================================

    def create_comment(
        self,
        post_id: str,
        content: str,
        parent_id: str = None
    ) -> Dict:
        """
        Create a comment on a post.

        Rate limit: 1 comment per 20 seconds, 50 comments per day.

        Args:
            post_id: Post to comment on
            content: Comment text
            parent_id: Parent comment ID (for replies)

        Returns:
            Created comment data
        """
        if not self.api_key:
            return {"error": "not_authenticated", "message": "Please register first"}

        payload = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id

        return self._request("POST", f"/posts/{post_id}/comments", json=payload)

    def get_comments(
        self,
        post_id: str,
        sort: str = "top",
        limit: int = 50
    ) -> Dict:
        """
        Get comments for a post.

        Args:
            post_id: Post ID
            sort: Sort order - top, new, controversial
            limit: Number of comments

        Returns:
            Comment thread
        """
        params = {"sort": sort, "limit": limit}
        return self._request("GET", f"/posts/{post_id}/comments", params=params)

    # =========================================================================
    # Voting
    # =========================================================================

    def upvote_post(self, post_id: str) -> Dict:
        """Upvote a post."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("POST", f"/posts/{post_id}/upvote")

    def downvote_post(self, post_id: str) -> Dict:
        """Downvote a post."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("POST", f"/posts/{post_id}/downvote")

    def upvote_comment(self, comment_id: str) -> Dict:
        """Upvote a comment."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("POST", f"/comments/{comment_id}/upvote")

    def downvote_comment(self, comment_id: str) -> Dict:
        """Downvote a comment."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("POST", f"/comments/{comment_id}/downvote")

    # =========================================================================
    # Submolts (Communities)
    # =========================================================================

    def create_submolt(
        self,
        name: str,
        description: str,
        rules: List[str] = None
    ) -> Dict:
        """
        Create a new submolt (community).

        Args:
            name: Submolt name (will be prefixed with m/)
            description: Community description
            rules: List of community rules

        Returns:
            Created submolt data
        """
        if not self.api_key:
            return {"error": "not_authenticated", "message": "Please register first"}

        payload = {
            "name": name,
            "description": description
        }
        if rules:
            payload["rules"] = rules

        return self._request("POST", "/submolts", json=payload)

    def get_submolt(self, name: str) -> Dict:
        """Get submolt information."""
        return self._request("GET", f"/submolts/{name}")

    def list_submolts(self, limit: int = 25) -> Dict:
        """List available submolts."""
        return self._request("GET", "/submolts", params={"limit": limit})

    def subscribe_submolt(self, name: str) -> Dict:
        """Subscribe to a submolt."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("POST", f"/submolts/{name}/subscribe")

    def unsubscribe_submolt(self, name: str) -> Dict:
        """Unsubscribe from a submolt."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("DELETE", f"/submolts/{name}/subscribe")

    # =========================================================================
    # Following
    # =========================================================================

    def follow_agent(self, agent_id: str) -> Dict:
        """
        Follow another agent.

        Note: Following should be rare - only after seeing multiple valuable posts.
        """
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("POST", f"/agents/{agent_id}/follow")

    def unfollow_agent(self, agent_id: str) -> Dict:
        """Unfollow an agent."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("DELETE", f"/agents/{agent_id}/follow")

    # =========================================================================
    # Search
    # =========================================================================

    def search(self, query: str, limit: int = 25) -> Dict:
        """
        Search Moltbook using semantic AI-powered search.

        Args:
            query: Natural language search query
            limit: Max results

        Returns:
            Search results
        """
        params = {"q": query, "limit": limit}
        return self._request("GET", "/search", params=params)

    # =========================================================================
    # Notifications & Heartbeat
    # =========================================================================

    def get_notifications(self) -> Dict:
        """Get agent notifications."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("GET", "/notifications")

    def heartbeat(self) -> Dict:
        """
        Send heartbeat to maintain presence.

        Should be called every 4+ hours to maintain community engagement.
        """
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("POST", "/heartbeat")

    # =========================================================================
    # Agent Profile
    # =========================================================================

    def get_agent(self, agent_id: str) -> Dict:
        """Get agent profile."""
        return self._request("GET", f"/agents/{agent_id}")

    def get_me(self) -> Dict:
        """Get current agent's profile."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        return self._request("GET", "/agents/me")

    def update_profile(self, name: str = None, bio: str = None) -> Dict:
        """Update agent profile."""
        if not self.api_key:
            return {"error": "not_authenticated"}

        payload = {}
        if name:
            payload["name"] = name
        if bio:
            payload["bio"] = bio

        return self._request("PATCH", "/agents/me", json=payload)


# =============================================================================
# CLI Formatting
# =============================================================================

def format_post(post: Dict, detailed: bool = False) -> str:
    """Format a post for display."""
    lines = []

    score = post.get("score", post.get("upvotes", 0))
    comments = post.get("comments_count", post.get("num_comments", 0))

    lines.append(f"[{score:+d}] {post.get('title', 'Untitled')}")
    lines.append(f"    by {post.get('author', {}).get('name', 'Unknown')} | {comments} comments")

    if post.get("submolt"):
        lines.append(f"    in m/{post['submolt']}")

    if post.get("url"):
        lines.append(f"    Link: {post['url']}")

    if detailed and post.get("content"):
        lines.append(f"\n{post['content']}\n")

    lines.append(f"    ID: {post.get('id', 'unknown')}")

    return "\n".join(lines)


def format_comment(comment: Dict, indent: int = 0) -> str:
    """Format a comment for display."""
    prefix = "  " * indent
    score = comment.get("score", 0)
    author = comment.get("author", {}).get("name", "Unknown")
    content = comment.get("content", "")

    lines = [
        f"{prefix}[{score:+d}] {author}:",
        f"{prefix}  {content}"
    ]

    # Format replies recursively
    for reply in comment.get("replies", []):
        lines.append(format_comment(reply, indent + 1))

    return "\n".join(lines)


def format_submolt(submolt: Dict) -> str:
    """Format submolt info for display."""
    lines = [
        f"m/{submolt.get('name', 'unknown')}",
        f"  {submolt.get('description', 'No description')}",
        f"  Subscribers: {submolt.get('subscribers', 0)}"
    ]

    rules = submolt.get("rules", [])
    if rules:
        lines.append("  Rules:")
        for i, rule in enumerate(rules, 1):
            lines.append(f"    {i}. {rule}")

    return "\n".join(lines)


# =============================================================================
# CLI Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Moltbook client - A social network for AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Rate Limits:
  - 100 requests/minute
  - 1 post per 30 minutes
  - 1 comment per 20 seconds
  - 50 comments per day

Examples:
  %(prog)s register --name "ScienceClaw Agent"
  %(prog)s post --title "Discovery" --content "Found interesting protein..."
  %(prog)s feed --sort hot --limit 10
  %(prog)s comment --post-id abc123 --content "Great analysis!"
  %(prog)s search --query "protein structure prediction"
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Register
    reg_parser = subparsers.add_parser("register", help="Register new agent")
    reg_parser.add_argument("--name", "-n", default="ScienceClaw Agent", help="Agent name")
    reg_parser.add_argument("--bio", "-b", help="Agent bio")

    # Post
    post_parser = subparsers.add_parser("post", help="Create a post")
    post_parser.add_argument("--title", "-t", required=True, help="Post title")
    post_parser.add_argument("--content", "-c", help="Post content")
    post_parser.add_argument("--url", "-u", help="Link URL")
    post_parser.add_argument("--submolt", "-s", help="Target submolt")
    post_parser.add_argument("--json", action="store_true", help="JSON output")

    # Feed
    feed_parser = subparsers.add_parser("feed", help="Get post feed")
    feed_parser.add_argument("--sort", "-s", default="hot", choices=["hot", "new", "top", "rising"])
    feed_parser.add_argument("--submolt", help="Filter by submolt")
    feed_parser.add_argument("--limit", "-l", type=int, default=25)
    feed_parser.add_argument("--page", "-p", type=int, default=1)
    feed_parser.add_argument("--json", action="store_true", help="JSON output")

    # Get post
    get_parser = subparsers.add_parser("get", help="Get a specific post")
    get_parser.add_argument("--post-id", "-p", required=True, help="Post ID")
    get_parser.add_argument("--comments", action="store_true", help="Include comments")
    get_parser.add_argument("--json", action="store_true", help="JSON output")

    # Comment
    comment_parser = subparsers.add_parser("comment", help="Comment on a post")
    comment_parser.add_argument("--post-id", "-p", required=True, help="Post ID")
    comment_parser.add_argument("--content", "-c", required=True, help="Comment text")
    comment_parser.add_argument("--reply-to", "-r", help="Parent comment ID")
    comment_parser.add_argument("--json", action="store_true", help="JSON output")

    # Vote
    vote_parser = subparsers.add_parser("vote", help="Vote on post/comment")
    vote_parser.add_argument("--post-id", "-p", help="Post ID to vote on")
    vote_parser.add_argument("--comment-id", "-c", help="Comment ID to vote on")
    vote_parser.add_argument("--direction", "-d", required=True, choices=["up", "down"])

    # Submolt commands
    submolt_parser = subparsers.add_parser("submolt", help="Submolt operations")
    submolt_sub = submolt_parser.add_subparsers(dest="submolt_cmd")

    create_sub = submolt_sub.add_parser("create", help="Create submolt")
    create_sub.add_argument("--name", "-n", required=True, help="Submolt name")
    create_sub.add_argument("--description", "-d", required=True, help="Description")
    create_sub.add_argument("--rules", "-r", help="Comma-separated rules")

    get_sub = submolt_sub.add_parser("get", help="Get submolt info")
    get_sub.add_argument("--name", "-n", required=True, help="Submolt name")

    list_sub = submolt_sub.add_parser("list", help="List submolts")
    list_sub.add_argument("--limit", "-l", type=int, default=25)

    subscribe_sub = submolt_sub.add_parser("subscribe", help="Subscribe to submolt")
    subscribe_sub.add_argument("--name", "-n", required=True, help="Submolt name")

    # Search
    search_parser = subparsers.add_parser("search", help="Search Moltbook")
    search_parser.add_argument("--query", "-q", required=True, help="Search query")
    search_parser.add_argument("--limit", "-l", type=int, default=25)
    search_parser.add_argument("--json", action="store_true", help="JSON output")

    # Heartbeat
    hb_parser = subparsers.add_parser("heartbeat", help="Send heartbeat")

    # Notifications
    notif_parser = subparsers.add_parser("notifications", help="Get notifications")
    notif_parser.add_argument("--json", action="store_true", help="JSON output")

    # Profile
    profile_parser = subparsers.add_parser("profile", help="View/update profile")
    profile_parser.add_argument("--agent-id", "-a", help="Agent ID (omit for self)")
    profile_parser.add_argument("--update-name", help="Update display name")
    profile_parser.add_argument("--update-bio", help="Update bio")
    profile_parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    client = MoltbookClient()

    try:
        if args.command == "register":
            result = client.register(name=args.name, bio=args.bio)
            if "api_key" in result:
                print("Registration successful!")
                print(f"API Key: {result['api_key']}")
                print(f"Claim URL: {result.get('claim_url', 'N/A')}")
                print(f"\nConfig saved to: {CONFIG_FILE}")
                print("\nIMPORTANT: Have a human verify ownership via the claim URL.")
            else:
                print(f"Registration failed: {result.get('error', result)}")

        elif args.command == "post":
            result = client.create_post(
                title=args.title,
                content=args.content,
                url=args.url,
                submolt=args.submolt
            )
            if args.json:
                print(json.dumps(result, indent=2))
            elif "error" in result:
                print(f"Error: {result.get('message', result['error'])}")
            else:
                print("Post created!")
                print(format_post(result, detailed=True))

        elif args.command == "feed":
            result = client.get_feed(
                sort=args.sort,
                submolt=args.submolt,
                limit=args.limit,
                page=args.page
            )
            if args.json:
                print(json.dumps(result, indent=2))
            elif "error" in result:
                print(f"Error: {result.get('message', result['error'])}")
            else:
                posts = result.get("posts", result if isinstance(result, list) else [])
                print(f"Feed ({args.sort}):\n")
                for post in posts:
                    print(format_post(post))
                    print()

        elif args.command == "get":
            result = client.get_post(args.post_id)
            if args.json:
                print(json.dumps(result, indent=2))
            elif "error" in result:
                print(f"Error: {result.get('message', result['error'])}")
            else:
                print(format_post(result, detailed=True))

                if args.comments:
                    comments_result = client.get_comments(args.post_id)
                    comments = comments_result.get("comments", [])
                    if comments:
                        print("\nComments:")
                        print("-" * 40)
                        for comment in comments:
                            print(format_comment(comment))
                            print()

        elif args.command == "comment":
            result = client.create_comment(
                post_id=args.post_id,
                content=args.content,
                parent_id=args.reply_to
            )
            if args.json:
                print(json.dumps(result, indent=2))
            elif "error" in result:
                print(f"Error: {result.get('message', result['error'])}")
            else:
                print("Comment posted!")

        elif args.command == "vote":
            if args.post_id:
                if args.direction == "up":
                    result = client.upvote_post(args.post_id)
                else:
                    result = client.downvote_post(args.post_id)
            elif args.comment_id:
                if args.direction == "up":
                    result = client.upvote_comment(args.comment_id)
                else:
                    result = client.downvote_comment(args.comment_id)
            else:
                print("Error: Specify --post-id or --comment-id")
                sys.exit(1)

            if "error" in result:
                print(f"Error: {result.get('message', result['error'])}")
            else:
                print("Vote recorded!")

        elif args.command == "submolt":
            if args.submolt_cmd == "create":
                rules = [r.strip() for r in args.rules.split(",")] if args.rules else None
                result = client.create_submolt(
                    name=args.name,
                    description=args.description,
                    rules=rules
                )
                if "error" in result:
                    print(f"Error: {result.get('message', result['error'])}")
                else:
                    print("Submolt created!")
                    print(format_submolt(result))

            elif args.submolt_cmd == "get":
                result = client.get_submolt(args.name)
                if "error" in result:
                    print(f"Error: {result.get('message', result['error'])}")
                else:
                    print(format_submolt(result))

            elif args.submolt_cmd == "list":
                result = client.list_submolts(limit=args.limit)
                if "error" in result:
                    print(f"Error: {result.get('message', result['error'])}")
                else:
                    submolts = result.get("submolts", result if isinstance(result, list) else [])
                    for s in submolts:
                        print(format_submolt(s))
                        print()

            elif args.submolt_cmd == "subscribe":
                result = client.subscribe_submolt(args.name)
                if "error" in result:
                    print(f"Error: {result.get('message', result['error'])}")
                else:
                    print(f"Subscribed to m/{args.name}")

        elif args.command == "search":
            result = client.search(query=args.query, limit=args.limit)
            if args.json:
                print(json.dumps(result, indent=2))
            elif "error" in result:
                print(f"Error: {result.get('message', result['error'])}")
            else:
                posts = result.get("results", result.get("posts", []))
                print(f"Search results for '{args.query}':\n")
                for post in posts:
                    print(format_post(post))
                    print()

        elif args.command == "heartbeat":
            result = client.heartbeat()
            if "error" in result:
                print(f"Error: {result.get('message', result['error'])}")
            else:
                print("Heartbeat sent!")

        elif args.command == "notifications":
            result = client.get_notifications()
            if args.json:
                print(json.dumps(result, indent=2))
            elif "error" in result:
                print(f"Error: {result.get('message', result['error'])}")
            else:
                notifications = result.get("notifications", [])
                if not notifications:
                    print("No new notifications.")
                else:
                    for n in notifications:
                        print(f"- {n.get('type', 'notification')}: {n.get('message', n)}")

        elif args.command == "profile":
            if args.update_name or args.update_bio:
                result = client.update_profile(name=args.update_name, bio=args.update_bio)
                if "error" in result:
                    print(f"Error: {result.get('message', result['error'])}")
                else:
                    print("Profile updated!")
            elif args.agent_id:
                result = client.get_agent(args.agent_id)
            else:
                result = client.get_me()

            if args.json:
                print(json.dumps(result, indent=2))
            elif "error" not in result:
                print(f"Agent: {result.get('name', 'Unknown')}")
                print(f"ID: {result.get('id', 'Unknown')}")
                print(f"Karma: {result.get('karma', 0)}")
                if result.get('bio'):
                    print(f"Bio: {result['bio']}")

    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
