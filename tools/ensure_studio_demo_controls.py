#!/usr/bin/env python3
"""Install safe in-game quit controls in *experiment* Godot projects.

One-shot, host-side, stdlib only. Run periodically using the existing Wolf Godot
project-sync timer. Does NOT touch Threshold or other production Godot projects.
Projects in .studio/art-director/comparisons are auto-managed; regular projects
under Godot/ can opt in by creating a .studio-demo file.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time

MAX_DIRS = 2500
MAX_PROJECTS = 200
MIN_STABLE_SECONDS = 60
SCRIPT_REL = Path("addons/optiplex_studio/demo_controls.gd")
SOURCE = Path("/usr/local/share/optiplex-studio/StudioDemoControls.gd")
ENTRY = 'StudioDemoControls="*res://addons/optiplex_studio/demo_controls.gd"'
TAG = "# OptiPlex Studio: managed demo exit controls"
NAME = re.compile(r"[A-Za-z0-9_. -]{1,128}\Z")
SKIP = {".git", ".godot", "node_modules", "build", "dist", "assets", ".cache"}


def discover(root):
    """Only designated experiments or explicitly opted-in Studio projects."""
    found = []
    experiments = root / ".studio/art-director/comparisons"
    if experiments.is_dir() and not experiments.is_symlink():
        visited = 0
        for base, dirs, files in os.walk(experiments, topdown=True, followlinks=False):
            visited += 1
            if visited > MAX_DIRS:
                raise RuntimeError("Experiment directory limit reached")
            here = Path(base)
            depth = len(here.relative_to(experiments).parts)
            dirs[:] = ([d for d in dirs if d not in SKIP and NAME.fullmatch(d)
                        and not (here / d).is_symlink()] if depth < 7 else [])
            if "project.godot" in files and not (here / "project.godot").is_symlink():
                found.append(here)
                dirs[:] = []  # Never descend inside Godot project files.
            if len(found) > MAX_PROJECTS:
                raise RuntimeError("Too many experiment projects")

    godot = root / "Godot"
    if godot.is_dir() and not godot.is_symlink():
        for child in sorted(godot.iterdir()):
            if (not child.is_dir() or child.is_symlink()
                    or not NAME.fullmatch(child.name)):
                continue
            if ((child / ".studio-demo").is_file()
                    and not (child / ".studio-demo").is_symlink()
                    and (child / "project.godot").is_file()
                    and not (child / "project.godot").is_symlink()):
                found.append(child)
    if len(found) > MAX_PROJECTS:
        raise RuntimeError("Too many demo projects")
    return sorted(set(found))


def amend_cfg(original):
    """Append or insert exactly one autoload, keeping all other settings."""
    if re.search(r'(?m)^\s*StudioDemoControls\s*=', original):
        if ENTRY in original:
            return original
        raise ValueError("Conflicting StudioDemoControls autoload; manual review required")
    # Preserve unrelated autoloads; insert before the following section.
    heading = re.search(r"(?m)^\[autoload\]\s*$", original)
    if heading:
        next_heading = re.search(r"(?m)^\[[^]\r\n]+\]\s*$", original[heading.end():])
        at = heading.end() + next_heading.start() if next_heading else len(original)
        return original[:at].rstrip() + "\n" + ENTRY + "\n\n" + original[at:].lstrip("\n")
    return original.rstrip() + "\n\n[autoload]\n\n" + ENTRY + "\n"


def atomic_write(path, content, *, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".studio-demo-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def apply(root, source, stable_seconds=MIN_STABLE_SECONDS):
    source_bytes = source.read_bytes()
    if not source_bytes.startswith(b"extends CanvasLayer\n"):
        raise ValueError("Invalid demo controls source")
    seen = 0
    changed = 0
    skipped = 0
    problems = []

    for project in discover(root):
        cfg = project / "project.godot"
        try:
            if not cfg.is_file() or cfg.is_symlink():
                skipped += 1
                continue
            before = cfg.stat()
            if time.time() - before.st_mtime < stable_seconds:
                skipped += 1
                continue
            original = cfg.read_text(encoding="utf-8")
            updated = amend_cfg(original)
            dest = project / SCRIPT_REL
            if dest.is_symlink():
                raise RuntimeError("Refusing symlinked demo controls file")
            if dest.exists() and dest.read_bytes() != source_bytes and TAG.encode() not in dest.read_bytes():
                raise RuntimeError("Existing unmanaged demo controls file; refusing overwrite")
            # If an agent/editor wrote a new config during our inspection,
            # defer the change instead of clobbering the newer file.
            if cfg.stat().st_mtime_ns != before.st_mtime_ns or cfg.stat().st_size != before.st_size:
                skipped += 1
                continue
            needs_script = not dest.exists() or dest.read_bytes() != source_bytes
            needs_config = updated != original
            if needs_config or needs_script:
                if needs_config:
                    backup = cfg.with_name("project.godot.studio-demo-backup")
                    if not backup.exists():
                        shutil.copy2(cfg, backup)
                if needs_script:
                    atomic_write(dest, source_bytes)
                if needs_config:
                    atomic_write(cfg, updated.encode("utf-8"),
                                 mode=before.st_mode & 0o777)
                changed += 1
            seen += 1
        except (OSError, ValueError, RuntimeError) as exc:
            problems.append(str(project) + ": " + str(exc))

    print(f"Studio demo controls: checked={seen}, modified={changed}, "
          f"deferred={skipped}, errors={len(problems)}")
    for problem in problems:
        print("ERROR: " + problem, file=sys.stderr)
    return 1 if problems else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.home() / "StudioProjects")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--force", action="store_true",
                        help="Bypass 60-second project stability check (manual use only)")
    opts = parser.parse_args()
    if not opts.root.is_dir() or not opts.source.is_file():
        parser.error("Studio project root or installed demo controls missing")
    return apply(opts.root, opts.source, stable_seconds=0 if opts.force else MIN_STABLE_SECONDS)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print("Studio demo controls setup error: " + str(error), file=sys.stderr)
        sys.exit(1)
