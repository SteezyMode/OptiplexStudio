"""Keep the release process distinct from normal development checks."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class ReleaseSafetyTests(unittest.TestCase):
    def test_only_version_tags_can_publish(self):
        release = (WORKFLOWS / "release.yml").read_text()
        self.assertIn("tags:", release)
        self.assertIn("- 'v*'", release)
        self.assertNotIn("workflow_dispatch:", release)
        self.assertNotIn("--clobber", release)
        self.assertIn("GITHUB_REF_NAME", release)
        self.assertIn('dpkg-deb -f "$package" Version', release)
        self.assertIn('gh release view "$GITHUB_REF_NAME"', release)

    def test_other_workflows_cannot_publish(self):
        for path in list(WORKFLOWS.glob("*.yml")) + list(WORKFLOWS.glob("*.yaml")):
            if path.name == "release.yml":
                continue
            with self.subTest(workflow=path.name):
                content = path.read_text()
                self.assertNotIn("contents: write", content)
                self.assertNotIn("gh release create", content)
                self.assertNotIn("gh release upload", content)
                self.assertNotIn("--clobber", content)

    def test_validation_runs_on_pull_requests(self):
        ci = (WORKFLOWS / "ci.yml").read_text()
        self.assertIn("pull_request:", ci)
        self.assertIn("contents: read", ci)
        self.assertIn("make -f Makefile.studio package", ci)
        self.assertIn("tests/run_gtk.py", ci)


if __name__ == "__main__":
    unittest.main()
