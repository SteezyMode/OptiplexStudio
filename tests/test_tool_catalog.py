"""Only verified native/streaming operations belong on Studio's Tools screen."""
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]
CATALOG = runpy.run_path(str(ROOT / "studio/tool_catalog.py"))


class NativeToolsContract(unittest.TestCase):
    def test_every_visible_action_has_real_adapter_and_unique_label(self):
        groups = CATALOG["TOOL_GROUPS"]
        rows = [tool for group in groups for tool in group["tools"]]
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(rows), 5)
        self.assertEqual({r[1] for r in rows}, CATALOG["READY_ACTIONS"])
        self.assertEqual(len(set(r[0] for r in rows)), len(rows))
        self.assertEqual(len(set(g["title"] for g in groups)), len(groups))
        for group in groups:
            self.assertTrue(group["title"] and group["description"] and group["tools"])
            for name, action, description in group["tools"]:
                self.assertTrue(name and action and description)
                self.assertFalse(name.lower().startswith("http"))

    def test_browser_services_have_no_shortcuts(self):
        names = " ".join(r[0].lower() for g in CATALOG["TOOL_GROUPS"] for r in g["tools"])
        for legacy in ("ultrabox", "audiomass", "opendaw", "piskel", "onionskyn", "cozyclay", "blockbench"):
            self.assertNotIn(legacy, names)
        self.assertNotIn("core.APPS", (ROOT / "studio/app.py").read_text())
        self.assertNotIn("APPS = [('UltraBox'", (ROOT / "studio/core.py").read_text())


if __name__ == "__main__":
    unittest.main()
