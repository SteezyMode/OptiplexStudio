"""Exercise local project-folder launch callbacks in a real GTK session."""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.environ.get('STUDIO_TEST_LIB', str(Path(__file__).resolve().parents[1] / 'studio')))
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gio
import app
import project_helper

fixture = tempfile.TemporaryDirectory(prefix='studio-local-browser-fixture-')
base = Path(fixture.name)
project_helper.create_project(base, 'game')
opened = []
errors = []
started = time.monotonic()
original = Gio.AppInfo.launch_default_for_uri
Gio.AppInfo.launch_default_for_uri = staticmethod(lambda uri, context: opened.append(uri) or True)
studio = app.Studio()
studio.config = {'projects_dir': str(base)}

def children(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            yield from children(child)

def click(caption):
    buttons = [item for item in children(studio.window)
               if isinstance(item, Gtk.Button) and item.get_label() == caption]
    assert len(buttons) == 1, f'Expected one {caption!r} button, found {len(buttons)}'
    assert buttons[0].get_sensitive(), caption
    buttons[0].clicked()

def check():
    try:
        assert time.monotonic() - started < 15, 'Timed out waiting for local project listing'
        if not studio.rows or studio.refreshing:
            return True
        if not opened:
            click('Project Files')
            return True
        if len(opened) == 1:
            click('Browse Assets')
            return True
        assert opened == [(base / 'game').as_uri(), (base / 'game' / 'assets').as_uri()], opened
        print('GTK local browser checks passed: Project Files and Browse Assets opened only local project URIs.')
        studio.quit()
        return False
    except Exception as exc:
        errors.append(exc)
        studio.quit()
        return False

GLib.timeout_add(100, check)
studio.run(None)
Gio.AppInfo.launch_default_for_uri = original
fixture.cleanup()
if errors:
    raise errors[0]
assert opened == [(base / 'game').as_uri(), (base / 'game' / 'assets').as_uri()], opened
