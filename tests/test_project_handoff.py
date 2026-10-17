"""Contract checks for project-scoped AI instructions and durable documents."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "studio"))
from project_helper import WORKFLOW, templates


class ProjectHandoffTests(unittest.TestCase):
    def test_codex_guidance_matches_written_agent_instructions(self):
        docs = templates("Example", "Godot")
        self.assertIn(WORKFLOW.replace("PROJECT_NAME", "Example"), docs["AGENTS.md"])
        self.assertIn("## Scope and authority", docs["AGENTS.md"])
        self.assertIn("## Verification and delivery", docs["AGENTS.md"])

    def test_security_and_verification_contract(self):
        for name in ("GAME.md", "PROGRESS.md", "DECISIONS.md", "AGENTS.md"):
            self.assertIn(name, WORKFLOW)
        for required in ("chat history is supplementary", "untrusted data", "Do not commit",
                         "Headless validation does not replace", "Do not claim"):
            self.assertIn(required, WORKFLOW)

    def test_all_project_types_have_reviewable_documents(self):
        for kind in ("Godot", "Blank", "Music/Audio", "Animation", "3D"):
            with self.subTest(kind=kind):
                docs = templates("Example", kind)
                self.assertEqual(set(docs), {"GAME.md", "PROGRESS.md", "DECISIONS.md", "AGENTS.md"})
                self.assertIn("## Acceptance criteria", docs["GAME.md"])
                self.assertIn("## Validation evidence", docs["PROGRESS.md"])
                self.assertIn("## Next actionable step", docs["PROGRESS.md"])
                self.assertIn("## Risks and blockers", docs["PROGRESS.md"])
                self.assertIn("## Decision template", docs["DECISIONS.md"])
                self.assertNotIn(r"\n", docs["GAME.md"])

    def test_invalid_project_types_are_rejected(self):
        with self.assertRaises(ValueError):
            templates("Example", "Unsupported")


if __name__ == "__main__":
    unittest.main()
