"""Host-side persistent Codex PTY sessions for a local-first Studio runtime.

This module is deliberately not wired into the GTK application yet. It is a
narrow, local Linux backend. No SSH, Docker, daemon, socket listener, shell
input from clients, or privileged operations are introduced here.
"""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess


NAME_RE = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


class SessionError(RuntimeError):
    """A persistent terminal operation was unavailable or unsafe."""


@dataclass(frozen=True)
class SessionInfo:
    name: str
    attached_clients: int
    windows: int


class TmuxSessionBackend:
    """One owner per project/role; attach never launches a second agent.

    Use from the workstation hosting Studio's projects and Codex launchers.
    Multiple local/Wolf frontends must route through this *same* backend.
    """

    def __init__(self, home=None, tmux=None, runner=None):
        self.home = Path(home) if home is not None else Path.home()
        self.root = self.home / "StudioProjects"
        self.tmux = tmux or shutil.which("tmux")
        self.runner = runner or subprocess.run
        if not self.tmux:
            raise SessionError("tmux is not installed on the Studio workstation.")

    @staticmethod
    def _project_name(name):
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise ValueError("Invalid Studio project name.")
        return name

    def _directory(self, role, project):
        if role == "art":
            if project is not None:
                raise ValueError("Art Director does not take a project name.")
            path = self.root / ".studio" / "art-director"
            if path.is_symlink() or not path.is_dir():
                raise SessionError("Art Director workspace is missing or unsafe.")
            return path.resolve(strict=True)
        if role != "project":
            raise ValueError("Unknown Studio workspace role.")
        name = self._project_name(project)
        projects = (self.root / "Godot").resolve(strict=True)
        path = projects / name
        if path.is_symlink() or not path.is_dir():
            raise SessionError("Project is missing or is a symlink.")
        resolved = path.resolve(strict=True)
        if resolved.parent != projects:
            raise SessionError("Project resolves outside the Studio project root.")
        return resolved

    def _profile(self, role, project):
        directory = self._directory(role, project)
        if role == "art":
            # Preserve the already-used Art Director tmux name.
            name = "studio-art"
            launcher = self.home / ".local" / "bin" / "studio-codex-art"
            args = [str(launcher)]
        else:
            # Distinct names even for long, similarly prefixed projects.
            digest = hashlib.sha256(str(directory).encode("utf-8")).hexdigest()[:10]
            name = "studio-project-" + project[:36] + "-" + digest
            launcher = self.home / ".local" / "bin" / "studio-codex-project"
            args = [str(launcher), project]
        return name, directory, launcher, args

    def _run(self, args):
        try:
            return self.runner([self.tmux, *args], capture_output=True,
                               text=True, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SessionError("tmux command failed: " + str(exc)[:200]) from exc

    def list_sessions(self):
        """Read the host tmux state without creating or terminating sessions."""
        result = self._run(["list-sessions", "-F",
                            "#{session_name}\t#{session_attached}\t#{session_windows}"])
        if result.returncode:
            stderr = (result.stderr or "").lower()
            # Empty tmux server: normal when nothing has run yet.
            if ("no server running" in stderr
                    or "error connecting to" in stderr):
                return {}
            raise SessionError("Cannot inspect tmux sessions: " +
                               (result.stderr or f"exit {result.returncode}")[:300])
        sessions = {}
        for line in result.stdout.splitlines():
            pieces = line.split("\t")
            if len(pieces) != 3:
                raise SessionError("Unexpected tmux session listing.")
            name, attached, windows = pieces
            try:
                sessions[name] = SessionInfo(name, int(attached), int(windows))
            except ValueError as exc:
                raise SessionError("Invalid tmux status fields.") from exc
        return sessions

    def status(self, role, project=None):
        name, _, _, _ = self._profile(role, project)
        return self.list_sessions().get(name)

    def attach_command(self, role, project=None):
        """Return foreground argv for a real terminal/PTY; does not start it."""
        name, _, _, _ = self._profile(role, project)
        if name not in self.list_sessions():
            raise SessionError("No running Studio session; open it first.")
        return [self.tmux, "attach-session", "-t", "=" + name]

    def ensure_running(self, role, project=None):
        """Create once when absent; never replace/kill an existing tmux pane.

        Note that an existing *tmux session* does not prove Codex is still
        alive. The GUI must inspect process/task state separately before
        advertising 'Codex running' or offering a resumed task.
        """
        name, directory, launcher, command = self._profile(role, project)
        existing = self.list_sessions().get(name)
        if existing is not None:
            return existing, False
        if not launcher.is_file() or not os.access(launcher, os.X_OK):
            raise SessionError("Studio Codex launcher not installed: " + str(launcher))
        # Fixed launcher + validated project name; shell command is quoted as
        # one tmux argument, never interpolated from unchecked GUI text.
        invocation = shlex.join(command)
        result = self._run(["new-session", "-d", "-s", name, "-c",
                            str(directory), invocation])
        if result.returncode:
            # Competing frontend may have won the create race. Only then reuse.
            raced = self.list_sessions().get(name)
            if raced is not None:
                return raced, False
            raise SessionError("Could not create Studio session: " +
                               (result.stderr or f"exit {result.returncode}")[:300])
        created = self.list_sessions().get(name)
        if created is None:
            raise SessionError("Session exited immediately; inspect Codex launcher/logs.")
        return created, True
