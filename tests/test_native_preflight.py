"""Fixture-only checks for the portable native preflight."""
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_preflight", ROOT / "tools/native_preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)

class NativePreflightTests(unittest.TestCase):
    def test_staged_four_without_launch_or_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            paths = {
                "godot": home / "StudioProjects/.tools/godot-native/4.7.2/Godot_v4.7.2-stable_linux.x86_64",
                "blender": home / "StudioProjects/.tools/blender-native/blender-5.2.0-linux-x64/blender",
                "lmms": home / "StudioProjects/.tools/lmms-native/lmms.AppImage",
                "codex": home / ".local/bin/codex",
            }
            for path in paths.values():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("#!/bin/sh\nexit 0\n")
                path.chmod(0o755)
            (home / "StudioProjects/Godot").mkdir()
            before = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in paths.values()}
            result = preflight.report(home, which=lambda name: None)
            self.assertTrue(all(result[k]["found"] for k in paths))
            self.assertTrue(result["project_root"]["exists"])
            self.assertEqual(before, {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in paths.values()})

    def test_archives_are_not_executables(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            source = home / "StudioProjects/.tools/godot-native/4.7.2/godot.zip"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"not an executable")
            source.chmod(0o755)
            result = preflight.report(home, which=lambda name: None)
            self.assertFalse(result["godot"]["found"])
            self.assertFalse(result["lmms"]["found"])
            self.assertFalse(result["codex"]["found"])

    def test_non_executable_file_not_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            source = home / ".local/bin/codex"
            source.parent.mkdir(parents=True)
            source.write_text("not executable")
            source.chmod(stat.S_IRUSR | stat.S_IWUSR)
            self.assertFalse(preflight.report(home, which=lambda name: None)["codex"]["found"])

if __name__ == "__main__":
    unittest.main()
