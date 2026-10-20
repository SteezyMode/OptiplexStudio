"""Local project/agent adapter; no SSH, Wolf, Docker, or tool installation.

Existing project_helper remains the sole project policy/metadata implementation.
Only a validated Studio project may be passed to an editor or Codex.
"""
from pathlib import Path
import subprocess


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
    raise ValueError("Unsupported local Studio action.")


def start_godot(name):
    args = command("edit", name)
    process = subprocess.Popen(args, cwd=str(project_path(name)), stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               start_new_session=True)
    # Start confirmation only: render, window appearance, and project import
    # require an actual graphical acceptance test.
    if process.poll() is not None and process.returncode:
        raise RuntimeError(f"Godot exited immediately (code {process.returncode}).")
    return "Godot editor launch requested for " + name + "."
