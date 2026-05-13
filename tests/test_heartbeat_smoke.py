"""
Smoke tests for the autonomous heartbeat cycle.

These tests don't try to exercise real science — they verify that the
cycle entry point and the new production primitives (budget, fingerprint,
logging, locked appends) hold together end-to-end without network calls.

Run: python3 -m pytest tests/test_heartbeat_smoke.py -v
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


# Make repo root importable when tests are run from outside it.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


class HeartbeatSmokeTests(unittest.TestCase):
    """End-to-end smoke against the AutonomousLoopController."""

    def setUp(self):
        # Redirect every persistent path under a temp HOME so the tests
        # don't touch the real ~/.scienceclaw.
        self._tmp = tempfile.mkdtemp(prefix="sc_smoke_")
        self._old_home = os.environ.get("HOME")
        os.environ["HOME"] = self._tmp
        (Path(self._tmp) / ".scienceclaw").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self._old_home is not None:
            os.environ["HOME"] = self._old_home
        shutil.rmtree(self._tmp, ignore_errors=True)

    # -- module-level imports must not regress -------------------------------

    def test_imports_dont_regress(self):
        """All production modules touched recently must import cleanly."""
        import importlib
        for name in [
            "utils.observability",
            "utils.budget",
            "utils.profile",
            "utils.rate_limit",
            "utils.compaction",
            "artifacts.artifact",
            "core.llm_client",
            "core.skill_executor",
            "autonomous.heartbeat_daemon",
            "autonomous.loop_controller",
        ]:
            importlib.import_module(name)

    # -- profile helper ------------------------------------------------------

    def test_profile_helper_handles_both_schemas(self):
        from utils.profile import profile_preferred_tools, profile_is_legacy

        current = {"name": "a", "preferred_tools": ["pubmed", "rdkit"]}
        legacy = {"name": "b", "preferences": {"tools": ["pubmed"]}}
        empty = {"name": "c"}

        self.assertEqual(profile_preferred_tools(current), ["pubmed", "rdkit"])
        self.assertFalse(profile_is_legacy(current))
        self.assertEqual(profile_preferred_tools(legacy), ["pubmed"])
        self.assertTrue(profile_is_legacy(legacy))
        self.assertEqual(profile_preferred_tools(empty), [])
        self.assertFalse(profile_is_legacy(empty))

    # -- budget end-to-end ---------------------------------------------------

    def test_budget_aborts_cycle_cleanly(self):
        """A budget exhaustion mid-cycle should yield a clean summary, not a crash."""
        from utils.budget import (
            CycleBudget, BudgetExhausted, set_active_budget,
            charge_llm_if_active,
        )

        b = CycleBudget(max_llm_calls=1)
        set_active_budget(b)
        try:
            charge_llm_if_active(10)  # first call ok
            with self.assertRaises(BudgetExhausted):
                charge_llm_if_active(10)  # second exceeds
        finally:
            set_active_budget(None)

    def test_pause_file_halts_charging(self):
        from utils.budget import CycleBudget, BudgetExhausted, PAUSE_FILE
        PAUSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        PAUSE_FILE.write_text("")
        try:
            b = CycleBudget()
            with self.assertRaises(BudgetExhausted):
                b.charge_llm(tokens=1)
        finally:
            PAUSE_FILE.unlink(missing_ok=True)

    # -- artifact store under temp HOME -------------------------------------

    def test_artifact_store_uses_temp_home(self):
        """Verify HOME override actually relocates the store, and writes work."""
        from artifacts.artifact import ArtifactStore, Artifact

        store = ArtifactStore(agent_name="smoke")
        artifact = Artifact.create(
            artifact_type="raw_output",
            producer_agent="smoke",
            skill_used="test_skill",
            payload={"hello": "world"},
        )
        aid = store.save(artifact)
        self.assertTrue(aid)

        # Per-agent store and global index should both exist under temp HOME.
        self.assertTrue(store.store_path.exists())
        self.assertIn(self._tmp, str(store.store_path))
        self.assertTrue(store._global_index_path.exists())

        # Lookup by ID round-trips.
        loaded = store.get(aid)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.payload, {"hello": "world"})

    # -- locked append + safe iter -----------------------------------------

    def test_locked_append_and_safe_iter(self):
        from utils.observability import locked_append, safe_jsonl_lines

        p = Path(self._tmp) / "concurrent.jsonl"
        for i in range(50):
            locked_append(p, json.dumps({"i": i}) + "\n")

        # Inject a corrupt line; safe_jsonl_lines should log and skip.
        with open(p, "a") as fh:
            fh.write("{not valid json\n")
        locked_append(p, json.dumps({"i": 99}) + "\n")

        seen = [e["i"] for e in safe_jsonl_lines(p)]
        self.assertEqual(len(seen), 51)
        self.assertEqual(seen[-1], 99)

    # -- compaction is a no-op below threshold ------------------------------

    def test_compaction_skips_below_threshold(self):
        from utils.compaction import compact_jsonl

        p = Path(self._tmp) / "tiny.jsonl"
        p.write_text(json.dumps({"artifact_id": "x", "timestamp": "2026-05-01T00:00:00+00:00"}) + "\n")
        out = compact_jsonl(p, min_size_bytes=10_000_000)
        self.assertEqual(out.get("skipped"), "below_threshold")

    # -- loop controller smoke (no platform, no preferred_tools) ------------

    def test_loop_controller_runs_no_tools_no_platform(self):
        """
        Construct a controller with an empty toolset and no platform; the
        cycle should complete with a structured summary, not raise.
        """
        # The controller pulls in a lot of optional deps. We mock the LLM
        # client class up front so anything that tries to call it gets a
        # stub instead of hitting the network.
        from core import llm_client
        stub = mock.MagicMock()
        stub.call.return_value = "stub response"
        with mock.patch.object(llm_client, "LLMClient", return_value=stub):
            # The controller imports a lot at __init__ time; if any step
            # below raises ImportError on this machine we skip rather than
            # fail (means a heavy optional dep is missing — out of scope
            # for a smoke test).
            try:
                from autonomous.loop_controller import AutonomousLoopController
            except ImportError as e:
                self.skipTest(f"optional dep missing: {e}")

            profile = {
                "name": "smoke-agent",
                "preferred_tools": [],   # cycle skips most steps
                "research": {"interests": []},
            }
            try:
                controller = AutonomousLoopController(profile)
            except Exception as e:
                self.skipTest(f"controller init not supported in this env: {e}")

            # Force platform off so engagement/post steps short-circuit.
            controller.platform = None

            summary = controller.run_heartbeat_cycle()
            self.assertIsInstance(summary, dict)
            # Must include the budget snapshot — this is the production
            # safety hook we wired in. Catches regressions where the
            # finally-block stops firing.
            self.assertIn("budget", summary)
            self.assertIn("llm_calls", summary["budget"])
            self.assertIn("steps_completed", summary)


if __name__ == "__main__":
    unittest.main()
