import importlib.util
import json
import os
import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "skills", "keenable-search", "scripts", "keenable_search.py"
)
spec = importlib.util.spec_from_file_location("keenable_search", SCRIPT)
keenable_search = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keenable_search)


def response(status, body, headers=None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    resp.headers = headers or {}
    return resp


def run_main(argv, env=None):
    out = StringIO()
    with patch.object(sys, "argv", ["keenable_search.py", *argv]), \
            patch.dict(os.environ, env or {}, clear=True), \
            patch("sys.stdout", out), patch("sys.stderr", StringIO()):
        try:
            keenable_search.main()
            code = 0
        except SystemExit as e:
            code = e.code
    return code, out.getvalue()


class TestKeenableSearchSkill(unittest.TestCase):
    def test_payload_clamps_and_maps_filters(self):
        payload = keenable_search.build_search_payload(
            "q", 500, site="nature.com", exclude_domains=["a.com"], published_after="2025-01-01"
        )
        self.assertEqual(payload["max_results"], 50)
        self.assertEqual(payload["site"], "nature.com")
        self.assertEqual(payload["exclude_domains"], ["a.com"])
        self.assertEqual(payload["published_after"], "2025-01-01")
        self.assertNotIn("published_before", payload)

    @patch.object(keenable_search.requests, "post")
    def test_keyed_search_uses_api_key_and_returns_results(self, post):
        post.return_value = response(200, {"results": [
            {"title": "T", "url": "https://x.org/a", "snippet": "S", "published_at": "2025-02-01T00:00:00Z"},
            {"title": "no url"},
        ]})
        code, out = run_main(["--query", "q"], {"KEENABLE_API_KEY": "kn-test"})
        self.assertEqual(code, 0)
        url = post.call_args.args[0]
        headers = post.call_args.kwargs["headers"]
        self.assertEqual(url, "https://api.keenable.ai/v1/search")
        self.assertEqual(headers["X-API-Key"], "kn-test")
        self.assertEqual(headers["X-Keenable-Title"], "scienceclaw")
        data = json.loads(out)
        self.assertEqual(data["source"], "keenable")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["description"], "S")
        self.assertEqual(data["results"][0]["published_at"], "2025-02-01T00:00:00Z")

    @patch.object(keenable_search.requests, "post")
    def test_no_key_and_no_opt_in_does_not_call_the_api(self, post):
        code, out = run_main(["--query", "q"])
        self.assertEqual(code, 1)
        post.assert_not_called()
        self.assertIn("KEENABLE_API_KEY", json.loads(out)["error"])

    @patch.object(keenable_search.requests, "post")
    def test_keyless_opt_in_uses_public_endpoint_without_key_header(self, post):
        post.return_value = response(200, {"results": []})
        code, _ = run_main(["--query", "q"], {"KEENABLE_KEYLESS": "1"})
        self.assertEqual(code, 0)
        self.assertEqual(post.call_args.args[0], "https://api.keenable.ai/v1/search/public")
        self.assertNotIn("X-API-Key", post.call_args.kwargs["headers"])

    @patch.object(keenable_search.requests, "post")
    def test_rate_limit_returns_json_error(self, post):
        post.return_value = response(429, {"message": "Rate limit exceeded", "retry_after_seconds": 5})
        code, out = run_main(["--query", "q"], {"KEENABLE_API_KEY": "kn-test"})
        self.assertEqual(code, 1)
        self.assertIn("rate limit", json.loads(out)["error"])

    @patch.object(keenable_search.requests, "post")
    def test_fetch_attaches_markdown_and_keeps_per_url_errors(self, post):
        post.side_effect = [
            response(200, {"results": [
                {"title": "A", "url": "https://x.org/a", "snippet": "a"},
                {"title": "B", "url": "https://x.org/b", "snippet": "b"},
            ]}),
            response(200, {"results": [
                {"url": "https://x.org/a", "content": "# A page"},
                {"url": "https://x.org/b", "error": {"status": 502, "message": "unreachable"}},
            ]}),
        ]
        code, out = run_main(["--query", "q", "--fetch", "--max-content", "3"], {"KEENABLE_API_KEY": "kn-test"})
        self.assertEqual(code, 0)
        fetch_call = post.call_args_list[1]
        self.assertEqual(fetch_call.args[0], "https://api.keenable.ai/v1/fetch")
        self.assertEqual(fetch_call.kwargs["json"], {"urls": ["https://x.org/a", "https://x.org/b"]})
        results = json.loads(out)["results"]
        self.assertEqual(results[0]["markdown"], "# A")
        self.assertTrue(results[0]["markdown_truncated"])
        self.assertEqual(results[1]["fetch_error"], "unreachable")


if __name__ == "__main__":
    unittest.main()
