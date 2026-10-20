"""Run under GDK_BACKEND=broadway and a private session D-Bus."""
import sys
import os
from pathlib import Path
sys.path.insert(0, os.environ.get('STUDIO_TEST_LIB', str(Path(__file__).resolve().parents[1] / 'studio')))
from gi.repository import GLib
import app
app.core.projects = lambda config: [{'name': 'smoke-project', 'branch': 'main', 'dirty': False, 'commit': 'fixture'}]
app.project_client.request = lambda *args, **kwargs: [{'name': 'smoke-project', 'type': 'Godot'}]
s = app.Studio()
s.config = {'projects_dir': '/tmp/studio-smoke-unused'}
errors = []
def check():
    try:
        assert s.window.get_visible()
        assert s.combo.get_active_id() == 'smoke-project'
        assert all(b.get_sensitive() for b in s.project_buttons if b is not s.ai_run)
        assert not s.ai_run.get_sensitive()
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
