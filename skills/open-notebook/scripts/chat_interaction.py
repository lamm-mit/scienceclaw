#!/usr/bin/env python3
"""
Open Notebook - Chat Interaction Script

Chat with notebooks, search the knowledge base, and get source-grounded answers.

Usage:
    python3 chat_interaction.py --url http://localhost:5055 --notebook-id abc123 \
        --question "What are the key findings about amyloid beta mechanisms?"

    python3 chat_interaction.py --url http://localhost:5055 --notebook-id abc123 \
        --action search --query "tau protein phosphorylation"

    python3 chat_interaction.py --url http://localhost:5055 --notebook-id abc123 \
        --action create-session

    python3 chat_interaction.py --url http://localhost:5055 --notebook-id abc123 \
        --action chat --session-id sess123 \
        --message "How does this relate to the GWAS findings?"
"""

import argparse
import json
import sys
import requests


def create_chat_session(base_url: str, notebook_id: str,
                        system_prompt: str = None) -> dict:
    """
    Create a new chat session for multi-turn conversation with a notebook.

    Returns session object with session_id for subsequent messages.
    """
    payload = {"notebook_id": notebook_id}
    if system_prompt:
        payload["system_prompt"] = system_prompt
    r = requests.post(
        f"{base_url}/api/notebooks/{notebook_id}/chat/sessions",
        json=payload,
        timeout=30
    )
    r.raise_for_status()
    return r.json()


def send_chat_message(base_url: str, notebook_id: str, message: str,
                      session_id: str = None) -> dict:
    """
    Send a message to a notebook's AI and get a source-grounded response.

    If session_id is provided, continues an existing conversation.
    Otherwise starts a fresh single-turn query.

    Returns:
        {
            "response": "AI response text...",
            "sources": [{"source_id": "...", "title": "...", "excerpt": "..."}],
            "confidence": 0.87,
            "session_id": "sess_xyz"
        }
    """
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    r = requests.post(
        f"{base_url}/api/notebooks/{notebook_id}/chat",
        json=payload,
        timeout=120
    )
    r.raise_for_status()
    return r.json()


def search_knowledge_base(base_url: str, notebook_id: str, query: str,
                          search_type: str = "hybrid",
                          max_results: int = 10) -> dict:
    """
    Search the notebook's knowledge base.

    search_type options:
        "semantic"  - vector similarity search
        "keyword"   - full-text search
        "hybrid"    - combined (default, recommended)

    Returns ranked list of source excerpts with relevance scores.
    """
    r = requests.post(
        f"{base_url}/api/notebooks/{notebook_id}/search",
        json={
            "query": query,
            "search_type": search_type,
            "max_results": max_results
        },
        timeout=60
    )
    r.raise_for_status()
    return r.json()


def ask_question(base_url: str, notebook_id: str, question: str) -> dict:
    """
    Ask a single question and get a grounded answer. Convenience wrapper.

    Returns structured response with answer, supporting sources, and confidence.
    """
    result = send_chat_message(base_url, notebook_id, question)
    return {
        "question": question,
        "answer": result.get("response", ""),
        "sources_used": result.get("sources", []),
        "confidence": result.get("confidence", None),
        "session_id": result.get("session_id", None)
    }


def get_chat_history(base_url: str, notebook_id: str, session_id: str) -> list:
    """Retrieve the message history for a chat session."""
    r = requests.get(
        f"{base_url}/api/notebooks/{notebook_id}/chat/sessions/{session_id}",
        timeout=30
    )
    r.raise_for_status()
    return r.json().get("messages", [])


def main():
    parser = argparse.ArgumentParser(
        description="Chat with Open Notebook via REST API"
    )
    parser.add_argument("--url", default="http://localhost:5055",
                        help="Open Notebook base URL")
    parser.add_argument("--notebook-id", required=True, help="Notebook ID to chat with")
    parser.add_argument("--action", default="ask",
                        choices=["ask", "chat", "search", "create-session", "history"],
                        help="Action (default: ask)")
    parser.add_argument("--question", help="Question to ask (for ask action)")
    parser.add_argument("--message", help="Chat message (for chat action)")
    parser.add_argument("--query", help="Search query (for search action)")
    parser.add_argument("--session-id", help="Session ID for multi-turn chat")
    parser.add_argument("--search-type", default="hybrid",
                        choices=["semantic", "keyword", "hybrid"],
                        help="Search strategy (default: hybrid)")
    parser.add_argument("--max-results", type=int, default=10,
                        help="Max search results (default: 10)")
    parser.add_argument("--system-prompt",
                        help="System prompt for new chat session")

    args = parser.parse_args()
    base_url = args.url.rstrip("/")

    try:
        if args.action == "ask":
            q = args.question or args.message
            if not q:
                parser.error("--question is required for ask action")
            result = ask_question(base_url, args.notebook_id, q)

        elif args.action == "chat":
            msg = args.message or args.question
            if not msg:
                parser.error("--message is required for chat action")
            result = send_chat_message(base_url, args.notebook_id, msg, args.session_id)

        elif args.action == "search":
            if not args.query:
                parser.error("--query is required for search action")
            result = search_knowledge_base(
                base_url, args.notebook_id, args.query,
                args.search_type, args.max_results
            )

        elif args.action == "create-session":
            result = create_chat_session(base_url, args.notebook_id, args.system_prompt)

        elif args.action == "history":
            if not args.session_id:
                parser.error("--session-id is required for history action")
            result = get_chat_history(base_url, args.notebook_id, args.session_id)

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
