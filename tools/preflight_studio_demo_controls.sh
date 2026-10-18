#!/usr/bin/env bash
# Compile and exercise the shared pause menu in a disposable Godot 4 project.
# No existing Studio scenes, editors, services or configs are changed.
set -euo pipefail

source_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
root=/home/optiplex/StudioProjects
source_gd="$source_dir/../studio/demo_controls/StudioDemoControls.gd"
test -f "$source_gd"
test -d "$root/.studio"

container=$(docker ps --format '{{.Names}}' | grep '^WolfStudioDesktop_' | head -1 || true)
if [[ -z "$container" ]]; then
  echo "Open Wolf Studio Desktop first; the installed Godot engine is required for preflight." >&2
  exit 1
fi

project=$(mktemp -d "$root/.studio/demo-controls-preflight-XXXXXXXX")
trap 'rm -rf -- "$project"' EXIT
mkdir -p "$project/addons/optiplex_studio"
chmod 755 "$project" "$project/addons" "$project/addons/optiplex_studio"
install -m644 "$source_gd" "$project/addons/optiplex_studio/demo_controls.gd"

cat > "$project/project.godot" <<'EOF'
config_version=5

[application]
config/name="Studio Demo Controls Preflight"

[autoload]
StudioDemoControls="*res://addons/optiplex_studio/demo_controls.gd"
EOF

cat > "$project/test.tscn" <<'EOF'
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://test.gd" id="1"]

[node name="SafetyPreflight" type="Node"]
script = ExtResource("1")
EOF

cat > "$project/test.gd" <<'EOF'
extends Node

func _ready() -> void:
    call_deferred("_check")

func _check() -> void:
    var controls: Node = get_node_or_null("/root/StudioDemoControls")
    if controls == null:
        push_error("StudioDemoControls autoload missing")
        get_tree().quit(1)
        return
    controls.call("_pause")
    if not get_tree().paused:
        push_error("Escape menu failed to pause")
        get_tree().quit(1)
        return
    controls.call("_resume")
    if get_tree().paused:
        push_error("Resume left game paused")
        get_tree().quit(1)
        return
    print("STUDIO_DEMO_CONTROLS_PREFLIGHT_OK")
    get_tree().quit()
EOF
chmod 644 "$project/project.godot" "$project/test.gd" "$project/test.tscn"
container_project="/projects/.studio/$(basename "$project")"
echo "Testing demo safety autoload with Wolf's installed Godot..."
output=$(timeout 35s docker exec -u retro "$container" timeout 30s \
  flatpak run org.godotengine.Godot --headless \
  --path "$container_project" res://test.tscn 2>&1) || {
    echo "$output"
    echo "Godot preflight failed; no installed demo modified." >&2
    exit 1
}
printf '%s\n' "$output"
if ! grep -q "STUDIO_DEMO_CONTROLS_PREFLIGHT_OK" <<< "$output"; then
    echo "Godot preflight marker missing; no installed demo modified." >&2
    exit 1
fi
if grep -Eq 'SCRIPT ERROR|Parse Error|Failed to load script|ERROR:' <<< "$output"; then
    echo "Godot reported errors; no installed demo modified." >&2
    exit 1
fi
echo "PASS: shared pause, resume and autoload."
