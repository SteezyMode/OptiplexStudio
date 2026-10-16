"""Run fixture-only GTK checks on isolated, loopback-bound Broadway displays."""
import os
from pathlib import Path
import subprocess
import tempfile
import time

root = Path(__file__).resolve().parents[1]
for display, script in ((':61', 'tests/gui_workflows.py'), (':62', 'tests/gui_smoke.py')):
    with tempfile.TemporaryDirectory(prefix='studio-release-gui-') as directory:
        env = dict(os.environ, XDG_RUNTIME_DIR=directory, XDG_CONFIG_HOME=directory,
                   GSETTINGS_BACKEND='memory', GDK_BACKEND='broadway',
                   BROADWAY_DISPLAY=display, PYTHONDONTWRITEBYTECODE='1')
        server = subprocess.Popen(['broadwayd', '--address=127.0.0.1', display], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            time.sleep(.3)
            result = subprocess.run(['dbus-run-session', '--', '/usr/bin/python3', '-B', script],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=40)
            print(result.stdout, end='')
            if result.returncode:
                print(result.stderr[-4000:])
                raise SystemExit(result.returncode)
        finally:
            server.terminate()
            server.wait(timeout=5)
