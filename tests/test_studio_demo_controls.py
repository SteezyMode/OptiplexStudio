"""Resource-light tests: safe, repeatable Studio demo-escape provisioning."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

FILE = Path(__file__).resolve().parents[1] / "tools" / "ensure_studio_demo_controls.py"
SPEC = importlib.util.spec_from_file_location("studio_demo_controls", FILE)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class DemoControlsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "StudioProjects"
        self.root.mkdir()
        self.source = Path(self.tmp.name) / "StudioDemoControls.gd"
        self.source.write_text("extends CanvasLayer\n# OptiPlex Studio: managed demo exit controls\n")
        self.experiment = self.root / ".studio/art-director/comparisons/patient-v3/animation-audition-01/project"
        self.make_project(self.experiment)
        self.production = self.root / "Godot/threshold"
        self.make_project(self.production)

    @staticmethod
    def make_project(folder, config="config_version=5\n\n[application]\nrun/main_scene=\"res://scenes/test.tscn\"\n"):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "project.godot").write_text(config)

    def test_only_experiments_and_opt_in_games(self):
        self.assertEqual(mod.discover(self.root), [self.experiment])
        optin = self.root / "Godot/another-game"
        self.make_project(optin)
        (optin / ".studio-demo").touch()
        self.assertEqual(set(mod.discover(self.root)), {self.experiment, optin})

    def test_existing_autoloads_preserved(self):
        cfg = ("[application]\nrun/main_scene=\"res://scenes/test.tscn\"\n"
               "\n[autoload]\n\nExisting=\"*res://keep.gd\"\n"
               "\n[display]\nwindow/size/viewport_width=1280\n")
        self.make_project(self.experiment, cfg)
        self.assertEqual(mod.apply(self.root, self.source, stable_seconds=0), 0)
        out = (self.experiment / "project.godot").read_text()
        self.assertIn('Existing="*res://keep.gd"', out)
        self.assertIn(mod.ENTRY, out)
        self.assertIn("[display]", out)
        self.assertEqual(out.count(mod.ENTRY), 1)

    def test_is_idempotent_and_production_unmodified(self):
        original_prod = (self.production / "project.godot").read_bytes()
        self.assertEqual(mod.apply(self.root, self.source, stable_seconds=0), 0)
        first = (self.experiment / "project.godot").read_bytes()
        self.assertEqual(mod.apply(self.root, self.source, stable_seconds=0), 0)
        self.assertEqual(first, (self.experiment / "project.godot").read_bytes())
        self.assertEqual(original_prod, (self.production / "project.godot").read_bytes())
        self.assertFalse((self.production / mod.SCRIPT_REL).exists())

    def test_written_script_and_backup(self):
        self.assertEqual(mod.apply(self.root, self.source, stable_seconds=0), 0)
        self.assertEqual((self.experiment / mod.SCRIPT_REL).read_bytes(),
                         self.source.read_bytes())
        self.assertTrue((self.experiment / "project.godot.studio-demo-backup").exists())

    def test_unmanaged_script_never_overwritten(self):
        dest = self.experiment / mod.SCRIPT_REL
        dest.parent.mkdir(parents=True)
        dest.write_text("extends CanvasLayer\n# user authored\n")
        self.assertEqual(mod.apply(self.root, self.source, stable_seconds=0), 1)
        self.assertEqual(dest.read_text(), "extends CanvasLayer\n# user authored\n")

    def test_recent_project_deferred(self):
        self.assertEqual(mod.apply(self.root, self.source, stable_seconds=3600), 0)
        self.assertNotIn(mod.ENTRY, (self.experiment / "project.godot").read_text())

    def test_conflicting_autoload_not_overwritten(self):
        self.make_project(self.experiment, "[autoload]\nStudioDemoControls=\"*res://another.gd\"\n")
        self.assertEqual(mod.apply(self.root, self.source, stable_seconds=0), 1)
        self.assertFalse((self.experiment / mod.SCRIPT_REL).exists())

    def test_symlinked_experiment_ignored(self):
        outside = Path(self.tmp.name) / "external"
        self.make_project(outside / "project")
        (self.root / ".studio/art-director/comparisons/foreign").symlink_to(outside, target_is_directory=True)
        self.assertEqual(mod.discover(self.root), [self.experiment])

    def test_autoload_added_as_new_section(self):
        cfg = "[application]\nconfig/name=\"audition\"\n"
        self.assertIn("[autoload]\n\n" + mod.ENTRY, mod.amend_cfg(cfg))


if __name__ == "__main__":
    unittest.main()
