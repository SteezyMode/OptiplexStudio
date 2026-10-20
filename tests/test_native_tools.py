"""Canonical resolver contract; no launching and no host mutations."""
import importlib.util
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "studio"))
import native_tools
import local_workspace
import project_client
import session_helper

spec = importlib.util.spec_from_file_location("studio_preflight", ROOT / "tools/native_preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def write_executable(self, relative):
        p = self.home / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("#!/bin/sh\nexit 0\n")
        p.chmod(0o755)
        return p

    def test_preflight_agrees_with_runtime_for_all_four(self):
        paths = {
            "godot": self.write_executable("StudioProjects/.tools/godot-native/4.7.2/Godot_v4.7.2-stable_linux.x86_64"),
            "blender": self.write_executable("StudioProjects/.tools/blender-native/blender-5.2.0-linux-x64/blender"),
            "lmms": self.write_executable("StudioProjects/.tools/lmms-native/lmms.AppImage"),
            "codex": self.write_executable(".local/bin/codex"),
        }
        before = {name: p.read_bytes() for name, p in paths.items()}
        with patch("native_tools.Path.home", return_value=self.home):
            found = preflight.report(self.home, which=lambda name: None)
            for name, path in paths.items():
                self.assertEqual(native_tools.resolve(name, path_finder=lambda _: None), str(path))
                self.assertEqual(found[name]["paths"][0], str(path))
        self.assertTrue(all(found[name]["found"] for name in paths))
        self.assertEqual(before, {name: p.read_bytes() for name, p in paths.items()})

    def test_path_override_and_missing_binary(self):
        staged = self.write_executable(".local/bin/codex")
        preferred = self.write_executable("external/codex")
        self.assertEqual(native_tools.resolve("codex", self.home, lambda _: str(preferred)), str(preferred))
        self.assertEqual(native_tools.available("codex", self.home, lambda _: str(preferred)),
                         [str(preferred), str(staged)])
        with self.assertRaises(ValueError):
            native_tools.resolve("dangerous_app", self.home, lambda _: None)

    def test_non_executable_staging_rejected(self):
        path = self.home / "StudioProjects/.tools/lmms-native/lmms.AppImage"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not runnable")
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        self.assertFalse(native_tools.inventory(self.home, path_finder=lambda _: None)["lmms"]["found"])

    def test_local_session_picker_uses_same_codex_path_as_launcher(self):
        # No actual Codex process is invoked; verify the exact path handed off.
        with patch("local_workspace.binary", return_value="/custom/install/codex") as binary, patch(
                "session_helper.list_codex_sessions", return_value={"sessions": [], "nextCursor": None}) as listing:
            local_workspace.request("Studio", "sessions", all_projects=False)
            self.assertEqual(listing.call_args.kwargs["codex_binary"], "/custom/install/codex")
            binary.assert_called_once_with("codex")


if __name__ == "__main__":
    unittest.main()
