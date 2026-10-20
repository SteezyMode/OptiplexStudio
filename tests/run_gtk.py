"""Run fixture-only GTK checks on isolated, loopback-bound Broadway displays."""
import os
os.environ["STUDIO_SKIP_ONBOARDING"] = "1"
import sys
from pathlib import Path
import subprocess
import tempfile
import time

root = Path(__file__).resolve().parents[1]
package_dir = None
if '--package' in sys.argv:
    package_dir = tempfile.TemporaryDirectory(prefix='studio-unpacked-')
    package = sys.argv[sys.argv.index('--package') + 1]
    subprocess.run(['dpkg-deb', '--extract', package, package_dir.name], check=True)
for display, script in ((':61', 'tests/gui_workflows.py'), (':62', 'tests/gui_smoke.py'), (':63', 'tests/gui_browse.py'), (':64', 'tests/gui_embedded.py')):
    with tempfile.TemporaryDirectory(prefix='studio-release-gui-') as directory:
        env = dict(os.environ, XDG_RUNTIME_DIR=directory, XDG_CONFIG_HOME=directory,
                   GSETTINGS_BACKEND='memory', GDK_BACKEND='broadway',
                   BROADWAY_DISPLAY=display, PYTHONDONTWRITEBYTECODE='1')
        if package_dir:
            env['STUDIO_TEST_LIB'] = str(Path(package_dir.name) / 'usr/lib/optiplex-studio')
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

if package_dir:
    package_dir.cleanup()
