"""One workstation-owned Codex PTY session per Studio project.

No network listener, Docker socket, daemon, or second AI agent. This backend
runs on the computer owning the project and relies on tmux for detach/attach.
A Wolf frontend would require separate, scoped access to *this same* backend;
running an independent instance in a Wolf container is not supported.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import shlex
import shutil
import subprocess
import uuid


class SessionError(RuntimeError):
    """A persistent Codex workspace could not be opened safely."""


@dataclass(frozen=True)
class SessionInfo:
    name: str
    attached_clients: int


class TmuxSessions:
    def __init__(self, home=None, tmux=None, runner=None):
        self.home = Path(home) if home is not None else Path.home()
        self.tmux = tmux or shutil.which("tmux")
        self.runner = runner or subprocess.run
        if not self.tmux:
            raise SessionError("tmux is required to keep Codex working when Studio closes.")

    def _project(self, name):
        from project_helper import Project, project_name
        project_name(name)
        base = self.home / "StudioProjects" / "Godot"
        try:
            project = Project(base, name)
        except (OSError, ValueError) as exc:
            raise SessionError("Selected Studio project is unavailable or unsafe.") from exc
        try:
            path = base / name
            return path, "studio-codex-" + hashlib.sha256(
                str(path.absolute()).encode("utf-8")).hexdigest()[:20]
        finally:
            project.close()

    def _run(self, args):
        try:
            return self.runner([self.tmux, *args], capture_output=True,
                               text=True, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SessionError("Cannot inspect Studio's Codex workspace: " + str(exc)[:200]) from exc

    def list_sessions(self):
        result = self._run(["list-sessions", "-F", "#{session_name}\t#{session_attached}"])
        if result.returncode:
            error = (result.stderr or "").lower()
            if "no server running" in error or "error connecting to" in error:
                return {}
            raise SessionError("Cannot read Codex workspaces: " +
                               (result.stderr or f"tmux exit {result.returncode}")[:200])
        rows = {}
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) != 2:
                raise SessionError("Unexpected Codex workspace listing.")
            try:
                rows[parts[0]] = SessionInfo(parts[0], int(parts[1]))
            except ValueError as exc:
                raise SessionError("Invalid Codex workspace status.") from exc
        return rows

    def ensure(self, project, session_id=None, prompt=None, all_sessions=False):
        """Reuse an existing project workspace or create exactly one.

        We do not inject keystrokes into an active Codex process. Requested
        historical conversations/contextual tasks cannot replace live work.
        """
        path, name = self._project(project)
        existing = self.list_sessions().get(name)
        if existing:
            if session_id is not None or prompt is not None or all_sessions:
                raise SessionError(
                    "A Codex workspace already exists for this project. Open it instead "
                    "of starting another conversation.")
            return existing, False

        import local_workspace
        import core
        if session_id is not None:
            try:
                session_id = str(uuid.UUID(session_id))
            except (ValueError, TypeError, AttributeError) as exc:
                raise ValueError("Invalid Codex session ID.") from exc
            args = local_workspace.command("resume", project) + [session_id]
        elif all_sessions:
            args = local_workspace.command("resume", project) + ["--all"]
        else:
            if prompt is not None and prompt not in core.CODEX_TASKS.values():
                raise ValueError("Unsupported Codex task.")
            args = local_workspace.command("code", project)
            if prompt is not None:
                args.append(prompt)

        # tmux executes one *quoted* shell-command argument. exec replaces
        # the tmux shell with Codex, so ending Codex ends the session too.
        command = shlex.join(["exec", *args])
        result = self._run(["new-session", "-d", "-s", name, "-c", str(path), command])
        if result.returncode:
            # Another window can win the creation race; never spawn a duplicate.
            winner = self.list_sessions().get(name)
            if winner:
                if session_id is not None or prompt is not None or all_sessions:
                    raise SessionError("Another Codex workspace started first. Open it instead.")
                return winner, False
            raise SessionError("Cannot start Codex workspace: " +
                               (result.stderr or f"tmux exit {result.returncode}")[:250])
        created = self.list_sessions().get(name)
        if not created:
            raise SessionError("Codex workspace exited immediately. Check Codex login and CLI settings.")
        return created, True

    def attach_argv(self, project):
        _, name = self._project(project)
        if name not in self.list_sessions():
            raise SessionError("No running Codex workspace for this project.")
        # Detach an earlier terminal client rather than concurrently typing into
        # the same agent. The Codex process continues on the workstation.
        return [self.tmux, "attach-session", "-d", "-t", "=" + name]
