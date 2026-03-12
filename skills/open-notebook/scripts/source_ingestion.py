#!/usr/bin/env python3
"""
Open Notebook - Source Ingestion Script

Ingest content into an Open Notebook: URLs, raw text, or file uploads.
Polls for processing completion with configurable timeout.

Usage:
    python3 source_ingestion.py --url http://localhost:5055 --notebook-id abc123 \
        --action add-url --source "https://pubmed.ncbi.nlm.nih.gov/12345678/"

    python3 source_ingestion.py --url http://localhost:5055 --notebook-id abc123 \
        --action add-text --content "Raw text content to ingest..." \
        --title "Manually entered notes"

    python3 source_ingestion.py --url http://localhost:5055 --notebook-id abc123 \
        --action upload-file --file /path/to/paper.pdf

    python3 source_ingestion.py --url http://localhost:5055 --notebook-id abc123 \
        --action list-sources

    python3 source_ingestion.py --url http://localhost:5055 --notebook-id abc123 \
        --action retry-failed
"""

import argparse
import json
import sys
import time
import requests


def add_url_source(base_url: str, notebook_id: str, url: str) -> dict:
    """Add a URL source (web page, PubMed, YouTube, etc.) to a notebook."""
    r = requests.post(
        f"{base_url}/api/notebooks/{notebook_id}/sources",
        json={"type": "url", "url": url},
        timeout=60
    )
    r.raise_for_status()
    return r.json()


def add_text_source(base_url: str, notebook_id: str, content: str,
                    title: str = "Text Source") -> dict:
    """Add raw text content to a notebook."""
    r = requests.post(
        f"{base_url}/api/notebooks/{notebook_id}/sources",
        json={"type": "text", "content": content, "title": title},
        timeout=60
    )
    r.raise_for_status()
    return r.json()


def upload_file_source(base_url: str, notebook_id: str, file_path: str) -> dict:
    """Upload a file (PDF, audio, etc.) to a notebook."""
    with open(file_path, "rb") as f:
        import os
        filename = os.path.basename(file_path)
        r = requests.post(
            f"{base_url}/api/notebooks/{notebook_id}/sources/upload",
            files={"file": (filename, f)},
            timeout=120
        )
    r.raise_for_status()
    return r.json()


def list_sources(base_url: str, notebook_id: str) -> list:
    """List all sources in a notebook with their processing status."""
    r = requests.get(
        f"{base_url}/api/notebooks/{notebook_id}/sources",
        timeout=30
    )
    r.raise_for_status()
    return r.json()


def get_source_status(base_url: str, notebook_id: str, source_id: str) -> dict:
    """Get the processing status of a specific source."""
    r = requests.get(
        f"{base_url}/api/notebooks/{notebook_id}/sources/{source_id}",
        timeout=30
    )
    r.raise_for_status()
    return r.json()


def wait_for_processing(base_url: str, notebook_id: str, source_id: str,
                        timeout_seconds: int = 300, poll_interval: int = 5) -> dict:
    """
    Poll until source processing is complete or timeout is reached.

    Status transitions: pending -> processing -> completed | failed
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        source = get_source_status(base_url, notebook_id, source_id)
        status = source.get("status", "unknown")

        if status == "completed":
            return {"success": True, "source": source}
        elif status == "failed":
            return {
                "success": False,
                "source": source,
                "error": source.get("error_message", "Processing failed")
            }

        # Still processing
        print(f"  Source {source_id}: status={status}, waiting {poll_interval}s...",
              file=sys.stderr)
        time.sleep(poll_interval)

    return {
        "success": False,
        "error": f"Timeout after {timeout_seconds}s waiting for source {source_id}",
        "source_id": source_id
    }


def retry_failed_sources(base_url: str, notebook_id: str) -> list:
    """Find and retry all failed sources in a notebook."""
    sources = list_sources(base_url, notebook_id)
    failed = [s for s in sources if s.get("status") == "failed"]

    results = []
    for source in failed:
        source_id = source["id"]
        r = requests.post(
            f"{base_url}/api/notebooks/{notebook_id}/sources/{source_id}/retry",
            timeout=60
        )
        if r.status_code == 200:
            results.append({"source_id": source_id, "status": "retry_queued"})
        else:
            results.append({"source_id": source_id, "status": "retry_failed",
                            "error": r.text[:200]})

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Ingest sources into Open Notebook"
    )
    parser.add_argument("--url", default="http://localhost:5055",
                        help="Open Notebook base URL")
    parser.add_argument("--notebook-id", required=True, help="Target notebook ID")
    parser.add_argument("--action", required=True,
                        choices=["add-url", "add-text", "upload-file",
                                 "list-sources", "retry-failed"],
                        help="Ingestion action")
    parser.add_argument("--source", help="URL to ingest (for add-url)")
    parser.add_argument("--content", help="Text content (for add-text)")
    parser.add_argument("--title", default="Text Source",
                        help="Title for text source (for add-text)")
    parser.add_argument("--file", help="File path to upload (for upload-file)")
    parser.add_argument("--wait", action="store_true",
                        help="Wait for processing to complete after ingestion")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Timeout in seconds when --wait is used (default: 300)")

    args = parser.parse_args()
    base_url = args.url.rstrip("/")

    try:
        if args.action == "add-url":
            if not args.source:
                parser.error("--source (URL) is required for add-url")
            result = add_url_source(base_url, args.notebook_id, args.source)
            if args.wait and "id" in result:
                print(json.dumps({"ingestion": result}), file=sys.stderr)
                result = wait_for_processing(base_url, args.notebook_id, result["id"],
                                             args.timeout)

        elif args.action == "add-text":
            if not args.content:
                parser.error("--content is required for add-text")
            result = add_text_source(base_url, args.notebook_id, args.content, args.title)
            if args.wait and "id" in result:
                print(json.dumps({"ingestion": result}), file=sys.stderr)
                result = wait_for_processing(base_url, args.notebook_id, result["id"],
                                             args.timeout)

        elif args.action == "upload-file":
            if not args.file:
                parser.error("--file is required for upload-file")
            result = upload_file_source(base_url, args.notebook_id, args.file)
            if args.wait and "id" in result:
                print(json.dumps({"ingestion": result}), file=sys.stderr)
                result = wait_for_processing(base_url, args.notebook_id, result["id"],
                                             args.timeout)

        elif args.action == "list-sources":
            result = list_sources(base_url, args.notebook_id)

        elif args.action == "retry-failed":
            result = retry_failed_sources(base_url, args.notebook_id)

        print(json.dumps(result, indent=2))

    except requests.HTTPError as e:
        print(json.dumps({
            "error": str(e),
            "status_code": e.response.status_code,
            "detail": e.response.text[:500]
        }), file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(json.dumps({"error": f"File not found: {e}"}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
