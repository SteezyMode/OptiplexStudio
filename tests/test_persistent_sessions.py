"""Test the local-first Studio tmux backend without opening real sessions."""
import importlib.util
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "persistent_sessions", ROOT / "studio" / "persistent_sessions.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class FakeTmux:
    def __init__(self):
        self.sessions = {}
        self.calls = []
        self.race_once = False

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        assert kwargs["capture_output"] and kwargs["text"]
        assert kwargs["check"] is False and kwargs["timeout"] == 10
        op = argv[1]
        if op == "list-sessions":
            if not self.sessions:
                return subprocess.CompletedProcess(argv, 1, "", "no server running on /tmp/tmux-test/default")
            text = "\n".join(f"{name}\t{clients}\t1" for name, clients in self.sessions.items())
            return subprocess.CompletedProcess(argv, 0, text + "\n", "")
        if op == "new-session":
            name = argv[argv.index("-s") + 1]
            if name in self.sessions or self.race_once:
                self.sessions[name] = 0
                self.race_once = False
                return subprocess.CompletedProcess(argv, 1, "", "duplicate session")
            self.sessions[name] = 0
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(f"Unexpected tmux call: {argv}")


class PersistentSessionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        (self.home / "StudioProjects/Godot/threshold").mkdir(parents=True)
        (self.home / "StudioProjects/Godot/other").mkdir(parents=True)
        (self.home / "StudioProjects/.studio/art-director").mkdir(parents=True)
        launcher_dir = self.home / ".local/bin"
        launcher_dir.mkdir(parents=True)
        for name in ("studio-codex-art", "studio-codex-project"):
            p = launcher_dir / name
            p.write_text("#!/bin/sh\nexit 0\n")
            p.chmod(0o700)
        self.runner = FakeTmux()
        self.backend = module.TmuxSessionBackend(
            home=self.home, tmux="/usr/bin/tmux", runner=self.runner)

    def test_create_and_reconnect_without_duplicate_start(self):
        info, created = self.backend.ensure_running("project", "threshold")
        self.assertTrue(created)
        self.assertTrue(info.name.startswith("studio-project-threshold-"))
        self.assertEqual(len([a for a in self.runner.calls if a[1] == "new-session"]), 1)
        same, created = self.backend.ensure_running("project", "threshold")
        self.assertFalse(created)
        self.assertEqual(same, info)
        self.assertEqual(len([a for a in self.runner.calls if a[1] == "new-session"]), 1)
        self.assertEqual(self.backend.attach_command("project", "threshold"),
                         ["/usr/bin/tmux", "attach-session", "-t", "=" + info.name])
        # Neither client disconnect nor GUI close executes any stop/kill.
        self.assertFalse(any("kill" in a or "send-keys" in a for a in self.runner.calls))

    def test_artist_scope_reuses_existing_session(self):
        self.runner.sessions["studio-art"] = 1
        session, created = self.backend.ensure_running("art")
        self.assertEqual((session.name, session.attached_clients, created),
                         ("studio-art", 1, False))
        self.assertFalse(any(a[1] == "new-session" for a in self.runner.calls))

    def test_art_and_each_project_use_distinct_names(self):
        art, _ = self.backend.ensure_running("art")
        project, _ = self.backend.ensure_running("project", "threshold")
        other, _ = self.backend.ensure_running("project", "other")
        self.assertEqual(len({art.name, project.name, other.name}), 3)
        self.assertEqual(self.backend.list_sessions()[art.name].windows, 1)

    def test_tmux_create_race_reuses_winning_process(self):
        self.runner.race_once = True
        session, created = self.backend.ensure_running("project", "threshold")
        self.assertFalse(created)
        self.assertIn(session.name, self.runner.sessions)

    def test_missing_launcher_fails_before_creating_session(self):
        (self.home / ".local/bin/studio-codex-project").unlink()
        with self.assertRaisesRegex(module.SessionError, "not installed"):
            self.backend.ensure_running("project", "threshold")
        self.assertFalse(any(a[1] == "new-session" for a in self.runner.calls))

    def test_rejects_invalid_names_and_roles(self):
        for name in ("../x", "", "foo bar", "-x;rm", "/tmp/foo", "a" * 129, "🌲"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.backend.ensure_running("project", name)
        with self.assertRaises(ValueError):
            self.backend.ensure_running("art", "threshold")
        with self.assertRaises(ValueError):
            self.backend.ensure_running("unknown", "threshold")
        self.assertFalse(any(a[1] == "new-session" for a in self.runner.calls))

    def test_rejects_symlink_project_path(self):
        outside = self.home / "outside"
        outside.mkdir()
        (self.home / "StudioProjects/Godot/redirect").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(module.SessionError):
            self.backend.ensure_running("project", "redirect")

    def test_existing_session_does_not_require_launcher_file(self):
        # A running process remains reachable after the local app is upgraded.
        name, _, _, _ = self.backend._profile("project", "threshold")
        self.runner.sessions[name] = 0
        (self.home / ".local/bin/studio-codex-project").unlink()
        s, created = self.backend.ensure_running("project", "threshold")
        self.assertFalse(created)
        self.assertEqual(s.name, name)

    def test_no_session_attach_is_explicit_error(self):
        with self.assertRaisesRegex(module.SessionError, "No running"):
            self.backend.attach_command("project", "threshold")

    def test_fails_on_other_tmux_errors(self):
        class Broken:
            def __call__(self, args, **kwargs):
                return subprocess.CompletedProcess(args, 1, "", "permission denied")
        b = module.TmuxSessionBackend(home=self.home, tmux="/usr/bin/tmux", runner=Broken())
        with self.assertRaisesRegex(module.SessionError, "permission denied"):
            b.list_sessions()


if __name__ == "__main__":
    unittest.main()
