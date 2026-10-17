"""Opt-in, project-local Godot MCP configuration; no server installation or startup.

The bridge and Godot addon are explicitly provisioned separately on the XFCE host.
"""
from pathlib import Path
import json
import shutil


def inspect(project_dir, executable=None):
    root = Path(project_dir).expanduser().resolve(strict=True)
    if not root.is_dir() or not (root / "project.godot").is_file():
        raise ValueError("Choose an existing Godot project containing project.godot.")
    if (root / "project.godot").is_symlink():
        raise ValueError("Godot project marker must not be a symlink.")
    executable = executable or shutil.which("godot-editor-mcp")
    if not executable:
        raise RuntimeError("Install the reviewed godot-editor-mcp package on the remote XFCE host first.")
    tool = Path(executable).expanduser().resolve(strict=True)
    if not tool.is_file():
        raise ValueError("Godot MCP executable is not an ordinary file.")
    target_dir = root / ".codex"
    target = target_dir / "config.toml"
    if target_dir.is_symlink() or target.is_symlink():
        raise ValueError("Refusing symbolic-link Codex configuration.")
    if target.exists():
        raise FileExistsError("Project Codex config already exists; merge reviewed MCP settings manually.")
    return root, tool, target


def project_configuration(project_dir, executable=None):
    _root, tool, target = inspect(project_dir, executable)
    # Codex supports trusted project-local .codex/config.toml. MCP stdio runs
    # on the same XFCE host as Godot; no network-exposed HTTP server is needed.
    content = ("# Opt-in Godot editor MCP; review before trusting this project.\n"
               "[mcp_servers.godot]\n"
               "command = " + json.dumps(str(tool)) + "\n"
               "args = []\n"
               "enabled = true\n")
    return target, content


def enable(project_dir, executable=None):
    target, content = project_configuration(project_dir, executable)
    target.parent.mkdir(mode=0o700, exist_ok=True)
    # Create-only prevents overwriting existing user config.
    with target.open("x", encoding="utf-8") as stream:
        stream.write(content)
    return target
