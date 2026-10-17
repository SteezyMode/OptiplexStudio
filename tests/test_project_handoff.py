"""Contract tests for project-based AI context handoff."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "studio"))
from project_helper import WORKFLOW, templates


class ProjectHandoffTests(unittest.TestCase):
    def test_agent_instructions_identical_to_codex_guidance(self):
        docs = templates("Example", "Godot")
        self.assertIn(WORKFLOW.replace("PROJECT_NAME", "Example"), docs["AGENTS.md"])

    def test_handoff_is_durable_and_project_scoped(self):
        for name in ("GAME.md", "PROGRESS.md", "DECISIONS.md", "AGENTS.md"):
            self.assertIn(name, WORKFLOW)
        self.assertIn("conversation is not the source of truth", WORKFLOW)
        self.assertIn("what is still uncertain", WORKFLOW)
        self.assertIn("do not change Wolf", WORKFLOW)
        self.assertIn("Do not commit unless explicitly requested", WORKFLOW)

    def test_templates_cover_non_godot_project_types(self):
        for kind in ("Blank", "Music/Audio", "Animation", "3D"):
            docs = templates("Example", kind)
            self.assertEqual(set(docs), {"GAME.md", "PROGRESS.md", "DECISIONS.md", "AGENTS.md"})
            self.assertIn(kind, docs["GAME.md"])


if __name__ == "__main__":
    unittest.main()
