#!/usr/bin/env python3
"""
Moltbook Client - Minimal version for ScienceClaw setup.

For full API usage, agents should read: https://moltbook.com/skill.md

This module provides:
- Agent registration (used by setup.py)
- API key storage/loading

Agents can use curl or requests directly for all other API calls.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

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
    Minimal client for Moltbook registration and config.

    For full API documentation: https://moltbook.com/skill.md
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Moltbook client.

        Args:
            api_key: Moltbook API key. If not provided, loads from config or environment.
        """
        self.api_base = MOLTBOOK_API_BASE
        self.api_key = api_key or self._load_api_key()

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

    def register(self, name: str = "ScienceClaw Agent", bio: str = None) -> Dict:
        """
        Register a new agent with Moltbook.

        Returns an API key and claim URL for human verification.

        Args:
            name: Agent display name
            bio: Optional agent description

        Returns:
            Dict with api_key and claim_url on success, or error info
        """
        payload = {"name": name}
        if bio:
            payload["description"] = bio

        try:
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

            # Handle both flat and nested response (API may return { agent: { api_key, claim_url } })
            api_key = result.get("api_key") or (result.get("agent") or {}).get("api_key")
            claim_url = result.get("claim_url") or (result.get("agent") or {}).get("claim_url")

            if api_key:
                self._save_config(api_key, claim_url)
                self.api_key = api_key
                # Return shape that setup.py expects
                return {"api_key": api_key, "claim_url": claim_url}

            return result

        except requests.exceptions.RequestException as e:
            return {"error": "connection_failed", "message": str(e)}

    def get_submolt(self, name: str) -> Dict:
        """Check if a submolt exists."""
        try:
            response = requests.get(
                f"{self.api_base}/submolts/{name}",
                timeout=30
            )
            if response.status_code >= 400:
                return {"error": "not_found"}
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def create_submolt(self, name: str, description: str, display_name: str = None, rules: list = None) -> Dict:
        """Create a new submolt (used by setup.py for first agent)."""
        if not self.api_key:
            return {"error": "not_authenticated"}

        payload = {
            "name": name,
            "display_name": display_name or name.replace("-", " ").title(),
            "description": description
        }
        if rules:
            payload["rules"] = rules

        try:
            response = requests.post(
                f"{self.api_base}/submolts",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                timeout=30
            )
            if response.status_code >= 400:
                try:
                    return response.json()
                except Exception:
                    return {"error": response.text}
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def subscribe_submolt(self, name: str) -> Dict:
        """Subscribe to a submolt."""
        if not self.api_key:
            return {"error": "not_authenticated"}

        try:
            response = requests.post(
                f"{self.api_base}/submolts/{name}/subscribe",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30
            )
            if response.status_code >= 400:
                try:
                    return response.json()
                except Exception:
                    return {"error": response.text}
            return response.json() if response.text else {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def create_post(self, title: str, content: str, submolt: str = None) -> Dict:
        """Create a post (used by manifesto.py)."""
        if not self.api_key:
            return {"error": "not_authenticated"}

        payload = {"title": title, "content": content}
        if submolt:
            payload["submolt"] = submolt

        try:
            response = requests.post(
                f"{self.api_base}/posts",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                timeout=30
            )
            if response.status_code >= 400:
                try:
                    return response.json()
                except Exception:
                    return {"error": response.text}
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def pin_post(self, post_id: str) -> Dict:
        """Pin a post (submolt owner/mod only). Max 3 pinned per submolt."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        try:
            response = requests.post(
                f"{self.api_base}/posts/{post_id}/pin",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30
            )
            if response.status_code >= 400:
                try:
                    return response.json()
                except Exception:
                    return {"error": response.text}
            return response.json() if response.text else {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def get_feed(self, submolt: str = None, sort: str = "new", limit: int = 5) -> Dict:
        """Get posts (e.g. to find a post id)."""
        if not self.api_key:
            return {"error": "not_authenticated"}
        try:
            url = f"{self.api_base}/posts?sort={sort}&limit={limit}"
            if submolt:
                url += f"&submolt={submolt}"
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30
            )
            if response.status_code >= 400:
                try:
                    return response.json()
                except Exception:
                    return {"error": response.text}
            return response.json()
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# CLI - Minimal commands for setup/testing
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Moltbook client (minimal). For full API: https://moltbook.com/skill.md"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Register
    reg = subparsers.add_parser("register", help="Register new agent")
    reg.add_argument("--name", "-n", default="ScienceClaw Agent")
    reg.add_argument("--bio", "-b", help="Agent description")

    # Status (check if registered)
    subparsers.add_parser("status", help="Check registration status")

    # Post
    post_parser = subparsers.add_parser("post", help="Create a post on m/scienceclaw")
    post_parser.add_argument("--title", "-t", required=True, help="Post title")
    post_parser.add_argument("--content", "-c", required=True, help="Post content (body)")
    post_parser.add_argument("--submolt", "-s", default="scienceclaw", help="Submolt (default: scienceclaw)")

    # Pin (submolt owner/mod only)
    pin_parser = subparsers.add_parser("pin", help="Pin a post (need post id; submolt owner/mod only)")
    pin_parser.add_argument("post_id", help="Post ID (from feed or from manifesto.py output)")

    # Feed (to get post ids)
    feed_parser = subparsers.add_parser("feed", help="Show latest posts (to get post IDs for pin)")
    feed_parser.add_argument("--submolt", "-s", default="scienceclaw")
    feed_parser.add_argument("--sort", default="new", choices=("new", "hot", "top", "rising"))
    feed_parser.add_argument("--limit", "-n", type=int, default=5)

    args = parser.parse_args()

    if args.command == "register":
        client = MoltbookClient()
        result = client.register(name=args.name, bio=args.bio)
        if "api_key" in result:
            print(f"Registered! API key saved to {CONFIG_FILE}")
            print(f"Claim URL: {result.get('claim_url', 'N/A')}")
        else:
            print(f"Error: {result}")

    elif args.command == "status":
        client = MoltbookClient()
        if client.api_key:
            print(f"Registered. API key: {client.api_key[:20]}...")
            print(f"Config: {CONFIG_FILE}")
        else:
            print("Not registered. Run: moltbook_client.py register --name 'Your Agent'")

    elif args.command == "post":
        client = MoltbookClient()
        if not client.api_key:
            print("Not registered. Run: moltbook_client.py register --name 'Your Agent'")
            sys.exit(1)
        result = client.create_post(title=args.title, content=args.content, submolt=args.submolt)
        if "error" in result:
            print(f"Error: {result}")
            sys.exit(1)
        print(f"Posted to m/{args.submolt}: {result.get('id', result)}")

    elif args.command == "pin":
        client = MoltbookClient()
        if not client.api_key:
            print("Not registered. Run: moltbook_client.py register --name 'Your Agent'")
            sys.exit(1)
        result = client.pin_post(args.post_id)
        if "error" in result:
            print(f"Error: {result}")
            sys.exit(1)
        print(f"Pinned post {args.post_id}")

    elif args.command == "feed":
        client = MoltbookClient()
        if not client.api_key:
            print("Not registered. Run: moltbook_client.py register --name 'Your Agent'")
            sys.exit(1)
        result = client.get_feed(submolt=args.submolt, sort=args.sort, limit=args.limit)
        if "error" in result:
            print(f"Error: {result}")
            sys.exit(1)
        posts = result.get("posts") or result.get("items") or []
        for p in posts:
            pid = p.get("id") or p.get("post_id")
            title = p.get("title") or p.get("content", "")[:50]
            print(f"{pid}\t{title}")

    else:
        parser.print_help()
        print("\nFor full Moltbook API, see: https://moltbook.com/skill.md")


if __name__ == "__main__":
    main()
