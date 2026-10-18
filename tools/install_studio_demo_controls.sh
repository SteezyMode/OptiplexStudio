#!/usr/bin/env bash
# One-time installation. Reuses the EXISTING Godot project-sync systemd timer.
# Does not start/restart Docker, Wolf, Godot, Codex or any graphical application.
set -euo pipefail
if [[ "$USER" != "optiplex" ]]; then
    echo "Run from optiplex's regular host account." >&2
    exit 1
fi
here="$(cd -- "$(dirname -- "$0")" && pwd)"
test -d /home/optiplex/StudioProjects
test -f "$here/../studio/demo_controls/StudioDemoControls.gd"
test -f "$here/ensure_studio_demo_controls.py"

if ! systemctl cat optiplex-studio-godot-sync.service >/dev/null 2>&1; then
    echo "Existing optiplex-studio-godot-sync.service not found; do not install an extra timer." >&2
    exit 1
fi

sudo install -Dm644 "$here/../studio/demo_controls/StudioDemoControls.gd" \
    /usr/local/share/optiplex-studio/StudioDemoControls.gd
sudo install -Dm755 "$here/ensure_studio_demo_controls.py" \
    /usr/local/libexec/optiplex-studio/ensure_studio_demo_controls.py

# Multiple sequential ExecStart= commands are permitted for Type=oneshot.
# Existing Wolf project registration remains the first action.
sudo install -d -m755 /etc/systemd/system/optiplex-studio-godot-sync.service.d
sudo tee /etc/systemd/system/optiplex-studio-godot-sync.service.d/20-demo-exit.conf >/dev/null <<'UNIT'
[Service]
ExecStart=/usr/bin/python3 /usr/local/libexec/optiplex-studio/ensure_studio_demo_controls.py
UNIT

sudo systemctl daemon-reload
sudo systemctl start optiplex-studio-godot-sync.service
echo "=== Demo controls status ==="
sudo journalctl -u optiplex-studio-godot-sync.service -n 16 --no-pager
echo "=== Existing timer ==="
systemctl is-enabled optiplex-studio-godot-sync.timer
systemctl is-active optiplex-studio-godot-sync.timer
