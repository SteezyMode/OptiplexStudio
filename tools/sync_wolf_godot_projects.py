#!/usr/bin/env python3
"""Reconcile Wolf's Godot Project Manager with approved OptiPlex Studio projects.

Host-side, stdlib-only, one-shot. A systemd *timer* may run this periodically.
Does not create/restart Wolf containers, start Godot, or inspect unrelated files.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

MAX_PROJECTS = 200
MAX_WALK_DIRS = 2500
NAME = re.compile(r"[A-Za-z0-9_. -]{1,128}\Z")
SKIP_DIRS = {".git", ".godot", "node_modules", "assets", "build", "dist", ".cache"}

# Written by the already-existing 'retro' user *inside* each Wolf Studio
# container, so Flatpak Godot sees its normal per-user projects.cfg.
REMOTE = r'''
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

projects = json.loads(sys.stdin.read())
if not isinstance(projects, list) or len(projects) > 200:
    raise ValueError("Invalid project manifest")

allowed = ("/projects/Godot/", "/projects/.studio/art-director/comparisons/")
entries = []
for raw in projects:
    if not isinstance(raw, str) or not raw.startswith(allowed) or any(c in raw for c in "\r\n[]"):
        raise ValueError("Project path outside approved Studio roots")
    p = Path(raw)
    if p.is_symlink() or not p.is_dir() or not (p / "project.godot").is_file():
        continue
    entries.append(raw)

cfg = Path.home() / ".var/app/org.godotengine.Godot/data/godot/projects.cfg"
cfg.parent.mkdir(parents=True, exist_ok=True)
original = cfg.read_text(encoding="utf-8") if cfg.is_file() else ""
registered = set(re.findall(r"(?m)^\[([^\]\r\n]+)\]\s*$", original))
missing = sorted(set(entries) - registered)
if not missing:
    print(f"unchanged: {len(entries)} Studio project(s) checked")
    sys.exit(0)

if cfg.exists():
    backup = cfg.with_name("projects.cfg.studio-backup")
    if not backup.exists():
        shutil.copy2(cfg, backup)

addition = "\n\n".join("[" + path + "]\n\nfavorite=false" for path in missing)
updated = original.rstrip() + ("\n\n" if original.strip() else "") + addition + "\n"
fd, tmp = tempfile.mkstemp(prefix=".projects-studio-", dir=str(cfg.parent))
try:
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        out.write(updated)
        out.flush()
        os.fsync(out.fileno())
    os.chmod(tmp, (cfg.stat().st_mode & 0o777) if cfg.exists() else 0o600)
    os.replace(tmp, cfg)
finally:
    if os.path.exists(tmp):
        os.unlink(tmp)
print("registered: " + ", ".join(missing))
'''


def project_names(root):
    """Approved project roots only. Never follow directory symlinks."""
    found = []
    godot = root / "Godot"
    if godot.is_dir() and not godot.is_symlink():
        for child in sorted(godot.iterdir()):
            if (child.is_symlink() or not child.is_dir() or not NAME.fullmatch(child.name)
                    or not (child / "project.godot").is_file()
                    or (child / "project.godot").is_symlink()):
                continue
            found.append("/projects/Godot/" + child.name)

    comparisons = root / ".studio/art-director/comparisons"
    if comparisons.is_dir() and not comparisons.is_symlink():
        visited = 0
        for base, dirs, files in os.walk(comparisons, topdown=True, followlinks=False):
            visited += 1
            if visited > MAX_WALK_DIRS:
                raise RuntimeError("Comparison index too large; refusing unbounded scan.")
            here = Path(base)
            depth = len(here.relative_to(comparisons).parts)
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and NAME.fullmatch(d)
                       and not (here / d).is_symlink()] if depth < 7 else []
            if ("project.godot" in files and not (here / "project.godot").is_symlink()
                    and depth > 0):
                relative = here.relative_to(root).as_posix()
                found.append("/projects/" + relative)
            if len(found) > MAX_PROJECTS:
                raise RuntimeError("Too many Godot projects; refine approved roots.")

    if len(found) > MAX_PROJECTS:
        raise RuntimeError("Too many Godot projects; refine approved roots.")
    return sorted(set(found))


def active_desktops(run=subprocess.run):
    response = run(["docker", "ps", "--format", "{{.Names}}"],
                   capture_output=True, text=True, timeout=12, check=False)
    if response.returncode:
        raise RuntimeError("Cannot enumerate Wolf desktops: " + response.stderr.strip()[:300])
    return sorted(name for name in response.stdout.splitlines()
                  if re.fullmatch(r"WolfStudioDesktop_[A-Za-z0-9_-]+", name))


def matches_workspace(container, root, run=subprocess.run):
    response = run(["docker", "inspect", "--format", "{{json .Mounts}}", container],
                   capture_output=True, text=True, timeout=12, check=False)
    if response.returncode:
        raise RuntimeError("Cannot inspect Wolf desktop: " + response.stderr.strip()[:300])
    mounts = json.loads(response.stdout)
    return any(m.get("Destination") == "/projects"
               and m.get("Type") == "bind"
               and Path(m.get("Source", "/unmapped")).resolve() == root.resolve()
               for m in mounts)


def synchronize(root=None, run=subprocess.run):
    root = Path(root) if root is not None else Path.home() / "StudioProjects"
    if not root.is_dir():
        raise RuntimeError("StudioProjects directory not found: " + str(root))
    projects = project_names(root)
    containers = active_desktops(run=run)
    if not containers:
        print("No Wolf Studio desktop running; next check will retry.")
        return 0
    failures = []
    for container in containers:
        try:
            if not matches_workspace(container, root, run=run):
                print(f"SKIP {container}: /projects is not this host's StudioProjects")
                continue
            response = run(["docker", "exec", "-i", "-u", "retro",
                            container, "python3", "-c", REMOTE],
                           input=json.dumps(projects), capture_output=True,
                           text=True, timeout=20, check=False)
            if response.returncode:
                raise RuntimeError((response.stderr or "Godot registry update failed")[-500:])
            print(container + ": " + response.stdout.strip())
        except (OSError, subprocess.TimeoutExpired, ValueError, RuntimeError) as exc:
            failures.append(f"{container}: {exc}")
    if failures:
        for error in failures:
            print("ERROR: " + error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(synchronize())
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("Studio Godot registration error: " + str(exc), file=sys.stderr)
        sys.exit(1)
