#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# ONLY run on disposable CI runner: installs the actual built package globally.
mapfile -t packages < <(find dist -maxdepth 1 -type f -name 'optiplex-studio_*_amd64.deb')
[[ "${#packages[@]}" -eq 1 ]] || { echo "Expected one Studio package" >&2; exit 1; }
package="$(realpath "${packages[0]}")"
version="$(dpkg-deb -f "$package" Version)"
[[ "$(dpkg-deb -f "$package" Package)" = "optiplex-studio" ]]
export DEBIAN_FRONTEND=noninteractive
sudo apt-get install -y --no-install-recommends "$package"
[[ "$(dpkg-query -W -f='${Version}' optiplex-studio)" = "$version" ]]
test -x /usr/bin/optiplex-studio
test -r /usr/lib/optiplex-studio/app.py
test -r /usr/lib/optiplex-studio/core.py
desktop-file-validate /usr/share/applications/com.monumentrisk.OptiPlexStudio.desktop
tmp="$(mktemp -d -t studio-installed.XXXXXX)"
cleanup() {
  # GVfs can leave an asynchronous FUSE mount after the GTK window exits.
  # A mountpoint must be detached before removing its temporary parent.
  if mountpoint -q "$tmp/runtime/gvfs"; then
    fusermount3 -uz "$tmp/runtime/gvfs" 2>/dev/null || \
      fusermount -uz "$tmp/runtime/gvfs" 2>/dev/null || true
  fi
  rm -rf -- "$tmp" || echo "Warning: temporary GTK smoke files not fully removed" >&2
}
trap cleanup EXIT
mkdir -p "$tmp/home" "$tmp/config" "$tmp/runtime"
chmod 700 "$tmp/runtime"
HOME="$tmp/home" XDG_CONFIG_HOME="$tmp/config" XDG_RUNTIME_DIR="$tmp/runtime" GIO_USE_VFS=local \
xvfb-run -a dbus-run-session -- bash -c '
  set -euo pipefail
  /usr/bin/optiplex-studio > "$1/console.log" 2>&1 &
  pid=$!
  trap "kill $pid 2>/dev/null || true; wait $pid 2>/dev/null || true" EXIT
  seen=0
  for ((i=0;i<70;i++)); do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "Installed Studio exited before rendering UI" >&2
      tail -40 "$1/console.log" >&2 || true
      exit 1
    fi
    if xwininfo -root -tree 2>/dev/null | grep -F "OptiPlex Studio" >/dev/null; then
      seen=1; break
    fi
    sleep .1
  done
  if [[ "$seen" != 1 ]]; then
    echo "Installed Studio did not show its GTK window" >&2
    tail -40 "$1/console.log" >&2 || true
    exit 1
  fi
  echo "Installed Studio GTK window opened under isolated Xvfb."
' bash "$tmp"
echo "Studio installed-package acceptance passed: apt, installed launcher and GTK window."
