"""Run under GDK_BACKEND=broadway and a private session D-Bus."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
from gi.repository import GLib
import app
app.core.projects = lambda config: [{'name': 'smoke-project', 'branch': 'main', 'dirty': False, 'commit': 'fixture'}]
app.project_client.request = lambda *args, **kwargs: []
s = app.Studio()
s.config = {'host': '100.100.100.100', 'user': 'optiplex'}
errors = []
def check():
    try:
        assert s.window.get_visible()
        assert s.combo.get_active_id() == 'smoke-project'
        assert all(b.get_sensitive() for b in s.project_buttons)
        assert not s.close_window()  # no tray host in Broadway
        s.window.hide()
        s.activate()
        assert s.window.get_visible()
        print('GUI smoke passed: window, project selection, action sensitivity, no-tray close, restore')
    except Exception as exc:
        errors.append(exc)
    s.quit()
    return False
GLib.timeout_add(600, check)
s.run(None)
if errors:
    raise errors[0]
