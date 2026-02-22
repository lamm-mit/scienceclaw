import os
import stat
import tempfile
import unittest
from pathlib import Path

from coordination.session_manager import SessionManager
from core.skill_executor import SkillExecutor


class SessionManagerRobustnessTests(unittest.TestCase):
    def test_duplicate_validation_is_rejected(self):
        old_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as temp_home:
            os.environ["HOME"] = temp_home
            try:
                creator = SessionManager("agent-creator")
                session_id = creator.create_collaborative_session(
                    topic="robustness test",
                    description="validation dedupe check",
                )

                validator = SessionManager("agent-validator")
                joined = validator.join_session(session_id)
                self.assertEqual(joined.get("status"), "joined")

                posted = creator.post_finding(
                    session_id=session_id,
                    result="finding",
                    confidence=0.9,
                )
                finding_id = posted["finding_id"]

                first = validator.validate_finding(
                    session_id=session_id,
                    finding_id=finding_id,
                    validation_status="confirmed",
                    reasoning="first pass",
                    confidence=0.8,
                )
                self.assertEqual(first.get("status"), "validated")

                second = validator.validate_finding(
                    session_id=session_id,
                    finding_id=finding_id,
                    validation_status="challenged",
                    reasoning="duplicate",
                    confidence=0.7,
                )
                self.assertIn("already validated", second.get("error", ""))

                state = creator.get_session_state(session_id)
                finding = state["session"]["findings"][0]
                self.assertEqual(len(finding["validations"]), 1)
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home


class SkillExecutorPathSafetyTests(unittest.TestCase):
    def test_rejects_executable_outside_skills_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "scienceclaw"
            skills_dir = root / "skills"
            scripts_dir = skills_dir / "demo" / "scripts"
            scripts_dir.mkdir(parents=True)

            outside = root / "outside.py"
            outside.write_text("print('outside')\n", encoding="utf-8")

            executor = SkillExecutor(scienceclaw_dir=root)
            result = executor.execute_skill(
                skill_name="demo",
                skill_metadata={"type": "tool", "executables": [str(outside)]},
                parameters={},
            )
            self.assertEqual(result.get("status"), "error")
            self.assertIn("outside allowed skills tree", result.get("error", ""))

    def test_executes_valid_script_under_skills_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "scienceclaw"
            scripts_dir = root / "skills" / "demo" / "scripts"
            scripts_dir.mkdir(parents=True)
            script = scripts_dir / "run.py"
            script.write_text("import json\nprint(json.dumps({'ok': True}))\n", encoding="utf-8")
            script.chmod(script.stat().st_mode | stat.S_IXUSR)

            executor = SkillExecutor(scienceclaw_dir=root)
            result = executor.execute_skill(
                skill_name="demo",
                skill_metadata={"type": "tool", "executables": [str(script)]},
                parameters={},
            )
            self.assertEqual(result.get("status"), "success")
            self.assertEqual(result.get("result"), {"ok": True})


if __name__ == "__main__":
    unittest.main()
