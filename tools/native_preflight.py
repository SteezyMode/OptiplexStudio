#!/usr/bin/env python3
"""Read-only preflight for Studio's four native creative tools.

This is not an installer. It never launches applications, talks to Wolf, changes
project contents, or attempts to authorize an MCP integration.
"""
import argparse
import json
import os
from pathlib import Path
import shutil

def candidates(home):
    tools = home / "StudioProjects" / ".tools"
    godot = tools / "godot-native"
    blender = tools / "blender-native"
    return {
        "godot": [
            *(sorted(godot.glob("*/Godot*_linux.x86_64")) if godot.is_dir() else []),
            Path("/usr/bin/godot"), Path("/usr/local/bin/godot"),
        ],
        "blender": [
            *(sorted(blender.glob("blender-*-linux-x64/blender")) if blender.is_dir() else []),
            Path("/usr/bin/blender"), Path("/usr/local/bin/blender"),
        ],
        "lmms": [
            tools / "lmms-native" / "lmms.AppImage",
            Path("/usr/bin/lmms"), Path("/usr/local/bin/lmms"),
        ],
        "codex": [
            home / ".local/bin/codex",
            Path("/usr/local/bin/codex"), Path("/usr/bin/codex"),
        ],
    }

def report(home, which=shutil.which):
    discovered = candidates(home)
    result = {}
    for name, paths in discovered.items():
        additional = which(name)
        if additional:
            paths.append(Path(additional))
        matches = []
        for path in paths:
            # An executable file or executable symlink, but never merely an archive.
            try:
                if path.is_file() and os.access(path, os.X_OK):
                    resolved = str(path.resolve())
                    if resolved not in matches:
                        matches.append(resolved)
            except OSError:
                continue
        result[name] = {"found": bool(matches), "paths": matches}
    project_root = home / "StudioProjects" / "Godot"
    result["project_root"] = {"exists": project_root.is_dir(), "path": str(project_root)}
    result["note"] = ("Executable presence only. Godot/Blender/LMMS rendering, "
                      "Codex authentication, MCP availability, session persistence "
                      "and clean-install reproducibility require separate tests.")
    return result

def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only native core-four preflight")
    parser.add_argument("--home", type=Path, default=Path.home(),
                        help="Account home to inspect (defaults to current home)")
    parser.add_argument("--json", action="store_true", help="Print machine-readable report")
    args = parser.parse_args(argv)
    data = report(args.home.expanduser())
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        for tool in ("godot", "blender", "lmms", "codex"):
            found = data[tool]
            print(f"{tool:8} {'FOUND' if found['found'] else 'MISSING'}"
                  + (": " + ", ".join(found["paths"]) if found["found"] else ""))
        print("Projects:", data["project_root"]["path"], "FOUND" if data["project_root"]["exists"] else "MISSING")
        print(data["note"])
    return 0 if all(data[t]["found"] for t in ("godot", "blender", "lmms", "codex")) else 1

if __name__ == "__main__":
    raise SystemExit(main())
