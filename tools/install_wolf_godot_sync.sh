#!/usr/bin/env bash
# Install a tiny, host-side timer that re-registers approved Studio projects.
# Explicit operator action: does not run merely by git pull.
set -euo pipefail

if [[ "$USER" != "optiplex" ]]; then
  echo "Install as the regular OptiPlex 'optiplex' user, not as root." >&2
  exit 1
fi

source_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
script="$source_dir/sync_wolf_godot_projects.py"
test -f "$script"
test -d /home/optiplex/StudioProjects

sudo install -Dm755 "$script" /usr/local/libexec/optiplex-studio/sync_wolf_godot_projects.py

sudo tee /etc/systemd/system/optiplex-studio-godot-sync.service >/dev/null <<'UNIT'
[Unit]
Description=Register approved Studio Godot projects in active Wolf desktops
After=docker.service
Wants=docker.service
ConditionPathIsDirectory=/home/optiplex/StudioProjects

[Service]
Type=oneshot
User=optiplex
Group=optiplex
Environment=HOME=/home/optiplex
ExecStart=/usr/bin/python3 /usr/local/libexec/optiplex-studio/sync_wolf_godot_projects.py
Nice=10
IOSchedulingClass=idle
TimeoutStartSec=60
NoNewPrivileges=true
UNIT

sudo tee /etc/systemd/system/optiplex-studio-godot-sync.timer >/dev/null <<'UNIT'
[Unit]
Description=Refresh Godot Project Manager when Studio/Wolf projects change

[Timer]
OnBootSec=90s
OnUnitInactiveSec=3min
AccuracySec=15s
Unit=optiplex-studio-godot-sync.service

[Install]
WantedBy=timers.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now optiplex-studio-godot-sync.timer
sudo systemctl start optiplex-studio-godot-sync.service
echo
systemctl is-enabled optiplex-studio-godot-sync.timer
systemctl is-active optiplex-studio-godot-sync.timer
sudo journalctl -u optiplex-studio-godot-sync.service -n 12 --no-pager
