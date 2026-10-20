#!/usr/bin/env python3
"""Read-only CLI report using Studio's exact native tool resolver."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "studio"))
from native_tools import inventory


def report(home, which=None):
    # An explicit finder lets isolated tests prove no machine PATH leaks.
    if which is None:
        return inventory(home)
    return inventory(home, path_finder=which)


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
        print("Projects:", data["project_root"]["path"],
              "FOUND" if data["project_root"]["exists"] else "MISSING")
        print(data["note"])
    return 0 if all(data[t]["found"] for t in ("godot", "blender", "lmms", "codex")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
