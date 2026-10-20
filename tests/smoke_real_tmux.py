"""Exercise real tmux process persistence in an isolated CI user workspace.

Uses a dummy agent, not Codex credentials/network. Its private tmux socket,
fake project and process are destroyed even on failure.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "studio"))
import project_helper
from persistent_sessions import TmuxSessions


def main():
    binary = shutil.which("tmux")
    if not binary:
        raise RuntimeError("CI runtime must install tmux before this test.")
    original_home = os.environ.get("HOME")
    original_tmux_dir = os.environ.get("TMUX_TMPDIR")
    with tempfile.TemporaryDirectory(prefix="studio-live-tmux-") as folder:
        root = Path(folder)
        home = root / "home"
        socket_root = root / "sockets"
        home.mkdir(mode=0o700)
        socket_root.mkdir(mode=0o700)
        project_root = home / "StudioProjects/Godot"
        project_root.mkdir(parents=True)
        project_helper.create_project(project_root, "fixture")
        codex = home / ".local/bin/codex"
        codex.parent.mkdir(parents=True)
        marker = home / "agent-starts"
        codex.write_text('#!/bin/sh\nprintf "start\\n" >> "$HOME/agent-starts"\nsleep 120\n')
        codex.chmod(0o700)
        os.environ["HOME"] = str(home)
        os.environ["TMUX_TMPDIR"] = str(socket_root)
        # Do not accidentally share a tmux server inherited from another job.
        os.environ.pop("TMUX", None)
        try:
            left = TmuxSessions(home=home, tmux=binary)
            right = TmuxSessions(home=home, tmux=binary)
            first, created = left.ensure("fixture")
            assert created, "Expected first frontend to start session"
            for _ in range(50):
                if marker.exists() and marker.read_text().strip():
                    break
                time.sleep(0.1)
            assert marker.exists() and marker.read_text().splitlines() == ["start"], (
                "A single background agent should have started."
            )
            again, created = right.ensure("fixture")
            assert not created and again.name == first.name, "Reopen spawned a duplicate"
            assert marker.read_text().splitlines() == ["start"], "A second Codex process was launched"
            assert right.attach_argv("fixture")[-1] == "=" + first.name
            print("Live isolated tmux smoke passed: two frontends reused one running process.")
        finally:
            subprocess.run([binary, "kill-server"], capture_output=True, text=True, timeout=10)
            if original_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = original_home
            if original_tmux_dir is None:
                os.environ.pop("TMUX_TMPDIR", None)
            else:
                os.environ["TMUX_TMPDIR"] = original_tmux_dir


if __name__ == "__main__":
    main()
