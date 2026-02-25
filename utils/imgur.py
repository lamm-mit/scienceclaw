"""Shared Imgur upload utility for scienceclaw agents."""
import base64
import json
import urllib.request
import urllib.parse
from pathlib import Path

_IMGUR_CLIENT_ID = "546c25a59c58ad7"  # public anonymous client


def upload_figure(path) -> str:
    """Upload a PNG to Imgur anonymously; return public URL or empty string."""
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        body = urllib.parse.urlencode({"image": data, "type": "base64"}).encode()
        req = urllib.request.Request(
            "https://api.imgur.com/3/image",
            data=body,
            headers={"Authorization": f"Client-ID {_IMGUR_CLIENT_ID}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        return result.get("data", {}).get("link", "")
    except Exception as e:
        print(f"  ⚠  Imgur upload failed for {Path(path).name}: {e}")
        return ""
