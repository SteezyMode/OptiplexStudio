#!/usr/bin/env bash
# Lightweight X11 Godot demo runner INSIDE the optional Wolf XFCE desktop.
# No new services, container processes, or changes to native Studio Godot.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo 'Usage: bash run_wolf_studio_demo.sh /projects/.../project res://scenes/demo.tscn' >&2
  exit 2
fi
project=$(realpath -e -- "$1") || exit 2
case "$project" in
  /projects/.studio/art-director/comparisons/*|/projects/Godot/*) ;;
  *) echo "Refusing path outside Studio project directories: $project" >&2; exit 2 ;;
esac
if [[ ! -f "$project/project.godot" ]]; then
  echo "Not a Godot project: $project" >&2
  exit 2
fi
scene=$2
case "$scene" in
  res://*.tscn) ;;
  *) echo "Expected project-local res:// scene (.tscn)" >&2; exit 2 ;;
esac
case "$scene" in
  *"/../"*|*"/./"*|*"//"*)
    # The scheme's res:// is allowed; scrutinize only the suffix.
    relative=$(printf '%s' "$scene" | cut -c 7-)
    case "$relative" in
      *"/../"*|*"/./"*|*"//"*) echo "Invalid relative scene path" >&2; exit 2 ;;
    esac
    ;;
esac
relative=$(printf '%s' "$scene" | cut -c 7-)
scene_path=$(realpath -e -- "$project/$relative") || exit 2
case "$scene_path" in
  "$project"/*) ;;
  *) echo "Scene path escapes Godot project" >&2; exit 2 ;;
esac

export DISPLAY=:0
export XDG_SESSION_TYPE=x11
export XDG_RUNTIME_DIR=/run/user/wolf
# --display-driver wayland lacked titlebar/minimize/close under Wolf XFCE.
exec flatpak run --socket=x11 org.godotengine.Godot \
  --display-driver x11 --windowed --resolution 960x540 \
  --path "$project" "$scene"
