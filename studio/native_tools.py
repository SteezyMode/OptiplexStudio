"""Canonical native executable discovery for Studio's in-house core four.

This module makes no installations, launches, mutations or network requests.
Both the GTK runtime and CLI preflight use the exact same resolver.
"""
import os
from pathlib import Path
import shutil

TOOLS = ("godot", "blender", "lmms", "codex")
DISPLAY = {"godot": "Godot", "blender": "Blender", "lmms": "LMMS", "codex": "Codex"}


def candidates(name, home=None, path_finder=shutil.which):
    """Return candidates in a documented, stable priority order.

    Native PATH installations take precedence, followed by user-staged binaries,
    then common system locations (which may be absent from a restricted PATH).
    """
    if name not in TOOLS:
        raise ValueError("Unsupported Studio tool.")
    home = Path.home() if home is None else Path(home)
    stage = home / "StudioProjects" / ".tools"
    staged = {
        "godot": sorted((stage / "godot-native").glob("*/Godot*_linux.x86_64"), reverse=True),
        "blender": sorted((stage / "blender-native").glob("blender-*-linux-x64/blender"), reverse=True),
        "lmms": [stage / "lmms-native/lmms.AppImage"],
        "codex": [home / ".local/bin/codex"],
    }
    result = []
    installed = path_finder(name) if path_finder else None
    if installed:
        result.append(Path(installed))
    result.extend(staged[name])
    result.extend((Path("/usr/local/bin") / name, Path("/usr/bin") / name))
    return result


def available(name, home=None, path_finder=shutil.which):
    """List executable paths without starting or modifying any processes."""
    results = []
    for path in candidates(name, home, path_finder):
        try:
            if path.is_file() and os.access(path, os.X_OK):
                canonical = str(path.resolve(strict=True))
                if canonical not in results:
                    results.append(canonical)
        except (OSError, RuntimeError):
            continue
    return results


def resolve(name, home=None, path_finder=shutil.which):
    paths = available(name, home, path_finder)
    if paths:
        return paths[0]
    if name not in TOOLS:
        raise ValueError("Unsupported Studio tool.")
    raise RuntimeError(DISPLAY[name] + " is not installed or executable on this computer. See the Studio setup instructions.")


def inventory(home=None, path_finder=shutil.which):
    home = Path.home() if home is None else Path(home)
    data = {tool: {"found": bool(paths := available(tool, home, path_finder)), "paths": paths}
            for tool in TOOLS}
    project_root = home / "StudioProjects" / "Godot"
    data["project_root"] = {"exists": project_root.is_dir(), "path": str(project_root)}
    data["note"] = ("Executable presence only. Rendering, Codex authentication, MCP availability, "
                    "session persistence and clean-install reproducibility still require live tests.")
    return data
