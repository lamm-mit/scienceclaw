#!/usr/bin/env python3
"""
Open Notebook - Notebook Management Script

Create, list, update, and delete notebooks via the Open Notebook REST API.

Usage:
    python3 notebook_management.py --url http://localhost:5055 --action list
    python3 notebook_management.py --url http://localhost:5055 --action create --name "My Notebook"
    python3 notebook_management.py --url http://localhost:5055 --action get --notebook-id abc123
    python3 notebook_management.py --url http://localhost:5055 --action update --notebook-id abc123 --name "New Name"
    python3 notebook_management.py --url http://localhost:5055 --action delete --notebook-id abc123
"""

import argparse
import json
import sys
import requests


def create_notebook(base_url: str, name: str, description: str = "") -> dict:
    """Create a new notebook."""
    r = requests.post(
        f"{base_url}/api/notebooks",
        json={"name": name, "description": description},
        timeout=30
    )
    r.raise_for_status()
    return r.json()


def list_notebooks(base_url: str) -> list:
    """List all notebooks."""
    r = requests.get(f"{base_url}/api/notebooks", timeout=30)
    r.raise_for_status()
    return r.json()


def get_notebook(base_url: str, notebook_id: str) -> dict:
    """Get a single notebook by ID, including its sources."""
    r = requests.get(f"{base_url}/api/notebooks/{notebook_id}", timeout=30)
    r.raise_for_status()
    return r.json()


def update_notebook(base_url: str, notebook_id: str, name: str = None,
                    description: str = None) -> dict:
    """Update notebook name or description."""
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if not payload:
        raise ValueError("Nothing to update: provide --name or --description")
    r = requests.put(
        f"{base_url}/api/notebooks/{notebook_id}",
        json=payload,
        timeout=30
    )
    r.raise_for_status()
    return r.json()


def delete_notebook(base_url: str, notebook_id: str) -> dict:
    """Delete a notebook and all its sources."""
    r = requests.delete(f"{base_url}/api/notebooks/{notebook_id}", timeout=30)
    r.raise_for_status()
    return {"status": "deleted", "notebook_id": notebook_id}


def link_source(base_url: str, notebook_id: str, source_url: str) -> dict:
    """Add a URL source to a notebook."""
    r = requests.post(
        f"{base_url}/api/notebooks/{notebook_id}/sources",
        json={"url": source_url},
        timeout=60
    )
    r.raise_for_status()
    return r.json()


def unlink_source(base_url: str, notebook_id: str, source_id: str) -> dict:
    """Remove a source from a notebook."""
    r = requests.delete(
        f"{base_url}/api/notebooks/{notebook_id}/sources/{source_id}",
        timeout=30
    )
    r.raise_for_status()
    return {"status": "unlinked", "source_id": source_id}


def main():
    parser = argparse.ArgumentParser(
        description="Manage Open Notebook notebooks via REST API"
    )
    parser.add_argument("--url", default="http://localhost:5055",
                        help="Open Notebook base URL (default: http://localhost:5055)")
    parser.add_argument("--action", required=True,
                        choices=["create", "list", "get", "update", "delete",
                                 "link-source", "unlink-source"],
                        help="Action to perform")
    parser.add_argument("--name", help="Notebook name (for create/update)")
    parser.add_argument("--description", help="Notebook description (for create/update)")
    parser.add_argument("--notebook-id", help="Notebook ID (for get/update/delete)")
    parser.add_argument("--source-url", help="Source URL to link to notebook")
    parser.add_argument("--source-id", help="Source ID to unlink")

    args = parser.parse_args()
    base_url = args.url.rstrip("/")

    try:
        if args.action == "list":
            result = list_notebooks(base_url)

        elif args.action == "create":
            if not args.name:
                parser.error("--name is required for create")
            result = create_notebook(base_url, args.name, args.description or "")

        elif args.action == "get":
            if not args.notebook_id:
                parser.error("--notebook-id is required for get")
            result = get_notebook(base_url, args.notebook_id)

        elif args.action == "update":
            if not args.notebook_id:
                parser.error("--notebook-id is required for update")
            result = update_notebook(base_url, args.notebook_id, args.name, args.description)

        elif args.action == "delete":
            if not args.notebook_id:
                parser.error("--notebook-id is required for delete")
            result = delete_notebook(base_url, args.notebook_id)

        elif args.action == "link-source":
            if not args.notebook_id or not args.source_url:
                parser.error("--notebook-id and --source-url are required for link-source")
            result = link_source(base_url, args.notebook_id, args.source_url)

        elif args.action == "unlink-source":
            if not args.notebook_id or not args.source_id:
                parser.error("--notebook-id and --source-id are required for unlink-source")
            result = unlink_source(base_url, args.notebook_id, args.source_id)

        print(json.dumps(result, indent=2))

    except requests.HTTPError as e:
        print(json.dumps({
            "error": str(e),
            "status_code": e.response.status_code,
            "detail": e.response.text[:500]
        }), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
