"""Local project/agent adapter; no SSH, Wolf, Docker, or tool installation.

Existing project_helper remains the sole project policy/metadata implementation.
Only a validated Studio project may be passed to an editor or Codex.
"""
from pathlib import Path
import subprocess
import os


def is_local(config):
    return config.get("mode") == "local"


def root():
    return Path.home() / "StudioProjects" / "Godot"


def validate_root(create=False):
    base = root()
    if (base.parent.is_symlink() or base.is_symlink()):
        raise ValueError("Studio project storage cannot be a symbolic link.")
    if create:
        base.mkdir(parents=True, exist_ok=True)
    if base.exists() and not base.is_dir():
        raise ValueError("Studio project storage is not a directory.")
    return base


def project_path(name):
    from project_helper import Project, project_name
    project_name(name)
    base = validate_root()
    try:
        project = Project(base, name)  # FD-based path checks refuse symlinks.
    except FileNotFoundError:
        raise ValueError("Selected Studio project does not exist.") from None
    try:
        return base / name
    finally:
        project.close()


def request(project, operation, **fields):
    import project_helper
    project_helper.project_name(project)
    base = validate_root(create=(operation == "create"))
    if not base.exists() and operation == "list_projects":
        return []
    if operation == "sessions":
        from session_helper import list_codex_sessions
        return list_codex_sessions(base, project, fields, codex_binary=binary("codex"))
    return project_helper.handle(dict(fields, version=project_helper.VERSION,
                                      project=project, operation=operation), base)


def binary(name):
    from native_tools import resolve
    return resolve(name)


def command(action, name):
    from project_helper import WORKFLOW
    from project_helper import project_name
    project_name(name)
    path = project_path(name)
    if action in ("code", "resume"):
        args = [binary("codex"), "--cd", str(path),
                "--sandbox", "workspace-write", "--ask-for-approval", "on-request",
                "--config", "developer_instructions=" + WORKFLOW.replace("PROJECT_NAME", name)]
        return args + (["resume"] if action == "resume" else [])
    if action == "edit":
        if not (path / "project.godot").is_file():
            raise ValueError("Select a Godot project before opening its editor.")
        return [binary("godot"), "--editor", "--path", str(path)]
    if action in ("blender", "lmms"):
        # These programs don't accept a generic Godot project argument. Start
        # from the selected project directory without inventing a source file.
        return [binary(action)]
    raise ValueError("Unsupported local Studio action.")


def start_application(action, name):
    """Start a native program from an existing project with private diagnostics.

    Launch success is not proof of a graphical window or of asset roundtrips.
    """
    labels = {"edit": "Godot editor", "blender": "Blender", "lmms": "LMMS"}
    filenames = {"edit": "godot", "blender": "blender", "lmms": "lmms"}
    if action not in labels:
        raise ValueError("Unsupported native application launch.")
    args = command(action, name)
    state = Path(os.environ.get("XDG_STATE_HOME", "")) if os.environ.get("XDG_STATE_HOME") else Path.home() / ".local/state"
    if not state.is_absolute():
        state = Path.home() / ".local/state"
    directory = state / "optiplex-studio"
    if directory.is_symlink():
        raise RuntimeError("Studio diagnostics directory cannot be a symlink.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    logfile = directory / (filenames[action] + "-launch.log")
    flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW
    try:
        fd = os.open(logfile, flags, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as output:
            process = subprocess.Popen(args, cwd=str(project_path(name)), stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=True)
        try:
            status = process.wait(timeout=0.35)
        except subprocess.TimeoutExpired:
            return labels[action] + " started for " + name + "."
        raise RuntimeError(f"{labels[action]} exited immediately (code {status}). See {logfile} for details.")
    except OSError as exc:
        raise RuntimeError(f"{labels[action]} could not be launched: {exc}. See {logfile} for details.") from exc


def start_godot(name):
    return start_application("edit", name)
