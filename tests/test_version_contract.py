"""One version controls both the builder and Debian artifact validator."""
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VersionContractTests(unittest.TestCase):
    def test_single_version_source(self):
        version = runpy.run_path(str(ROOT / "studio/version.py"))["PACKAGE_VERSION"]
        self.assertRegex(version, r"^[0-9]+[.][0-9]+[.][0-9]+$")
        builder = (ROOT / "studio/package.py").read_text()
        validator = (ROOT / "studio/validate_package.py").read_text()
        self.assertIn("from version import PACKAGE_VERSION", builder)
        self.assertIn("from version import PACKAGE_VERSION", validator)
        self.assertIn("name = f'optiplex-studio_{PACKAGE_VERSION}_{arch}'", builder)
        self.assertIn("'Version': PACKAGE_VERSION", validator)
        self.assertIn("Version: {PACKAGE_VERSION}", builder)

    def test_ci_uses_its_actual_artifact(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("mapfile -t packages", ci)
        self.assertIn('studio/validate_package.py "$package"', ci)
        self.assertIn('tests/run_gtk.py --package "$package"', ci)
        self.assertNotIn("dist/optiplex-studio_0.3.0_amd64.deb", ci)


if __name__ == "__main__":
    unittest.main()
