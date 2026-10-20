"""Safe mocked tmux lifecycle; never starts Codex or a real terminal."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "studio"))
import persistent_sessions
import local_workspace


class FakeTmux:
    def __init__(self):
        self.sessions = {}
        self.calls = []
        self.race_once = False

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        assert kwargs == dict(capture_output=True, text=True, timeout=10, check=False)
        if argv[1] == "list-sessions":
            if not self.sessions:
                return subprocess.CompletedProcess(argv, 1, "", "no server running")
            lines = "\n".join(f"{name}\t{attached}" for name, attached in self.sessions.items())
            return subprocess.CompletedProcess(argv, 0, lines + "\n", "")
        if argv[1] == "new-session":
            name = argv[argv.index("-s") + 1]
            if self.race_once or name in self.sessions:
                self.race_once = False
                self.sessions[name] = 0
                return subprocess.CompletedProcess(argv, 1, "", "duplicate session")
            self.sessions[name] = 0
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(f"Unexpected tmux invocation: {argv}")


class PersistentSessionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        import project_helper
        base = self.home / "StudioProjects/Godot"
        base.mkdir(parents=True)
        project_helper.create_project(base, "game")
        project_helper.create_project(base, "other")
        self.runner = FakeTmux()
        self.backend = persistent_sessions.TmuxSessions(
            home=self.home, tmux="/usr/bin/tmux", runner=self.runner)

    def start(self, name="game", **kwargs):
        with patch("local_workspace.Path.home", return_value=self.home), patch(
                "local_workspace.binary", return_value="/usr/bin/codex"):
            return self.backend.ensure(name, **kwargs)

    def test_one_session_and_reattach_no_duplicate_agent(self):
        first, created = self.start()
        self.assertTrue(created)
        self.assertTrue(first.name.startswith("studio-codex-"))
        self.assertEqual(sum(x[1] == "new-session" for x in self.runner.calls), 1)
        again, created = self.start()
        self.assertFalse(created)
        self.assertEqual(first, again)
        self.assertEqual(sum(x[1] == "new-session" for x in self.runner.calls), 1)
        self.assertEqual(self.backend.attach_argv("game"),
                         ["/usr/bin/tmux", "attach-session", "-d", "-t", "=" + first.name])
        self.assertFalse(any("kill" in part or "send-keys" in part
                             for call in self.runner.calls for part in call))

    def test_command_is_project_scoped_and_shell_quoted(self):
        self.start()
        invocation = next(x for x in self.runner.calls if x[1] == "new-session")
        self.assertEqual(invocation[invocation.index("-c") + 1],
                         str(self.home / "StudioProjects/Godot/game"))
        from shlex import split
        actual = split(invocation[-1])
        self.assertEqual(actual[:4], ["exec", "/usr/bin/codex", "--cd",
                                      str(self.home / "StudioProjects/Godot/game")])
        self.assertIn("on-request", actual)
        self.assertIn("workspace-write", actual)
        self.assertIn("AGENTS.md", " ".join(actual))

    def test_saved_session_requires_no_other_live_agent(self):
        uuid = "12345678-1234-1234-1234-123456789012"
        self.start(session_id=uuid)
        invocation = next(x for x in self.runner.calls if x[1] == "new-session")
        self.assertEqual(__import__("shlex").split(invocation[-1])[-2:], ["resume", uuid])
        with self.assertRaisesRegex(persistent_sessions.SessionError, "already exists"):
            self.start(session_id=uuid)
        self.assertEqual(sum(x[1] == "new-session" for x in self.runner.calls), 1)

    def test_new_project_distinct_and_creation_race(self):
        self.runner.race_once = True
        result, created = self.start()
        self.assertFalse(created)
        second, created = self.start("other")
        self.assertTrue(created)
        self.assertNotEqual(result.name, second.name)
        self.assertEqual(len(self.runner.sessions), 2)

    def test_invalid_inputs_cannot_launch_anything(self):
        for name in ("../escape", "/tmp/x", "", "wrong project", "extra;evil", "unknown"):
            with self.subTest(name=name), self.assertRaises((ValueError, persistent_sessions.SessionError)):
                self.start(name)
        with self.assertRaises(ValueError):
            self.start(session_id="unsafe id")
        with self.assertRaises(ValueError):
            self.start(prompt="run arbitrary shell")
        self.assertFalse(any(x[1] == "new-session" for x in self.runner.calls))

    def test_symlink_project_rejected(self):
        (self.home / "StudioProjects/Godot/sneaky").symlink_to(self.home / "StudioProjects/Godot/game", target_is_directory=True)
        with self.assertRaises(persistent_sessions.SessionError):
            self.start("sneaky")

    def test_second_task_never_injected_into_live_codex(self):
        self.start()
        with self.assertRaisesRegex(persistent_sessions.SessionError, "already exists"):
            self.start(prompt=__import__("core").CODEX_TASKS["Review Changes"])
        self.assertEqual(sum(x[1] == "new-session" for x in self.runner.calls), 1)


if __name__ == "__main__":
    unittest.main()
