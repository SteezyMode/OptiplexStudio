"""Display-backed embedded panel smoke test; no native server or user history."""
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, os.environ.get('STUDIO_TEST_LIB', str(Path(__file__).resolve().parents[1] / 'studio')))
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from embedded_ui import EmbeddedView

errors = []
window = Gtk.Window()
window.set_default_size(1024, 768)
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
window.add(box)
app = SimpleNamespace(window=window, ai_output_area=box, ai_controls=Gtk.Box(), ai_advanced=Gtk.Expander())
box.pack_start(app.ai_controls, False, False, 0)
box.pack_start(app.ai_advanced, False, False, 0)
def worker(task, done):
    def run():
        try:
            result, error = task(), None
        except Exception as exc:
            result, error = None, str(exc)
        GLib.idle_add(done, result, error)
    threading.Thread(target=run, daemon=True).start()
app.worker = worker

class Fixture:
    def __init__(self, config, project, event):
        self.event = event
        self.server = SimpleNamespace(closed=False)
        self.thread = 'fixture'
    def connect(self, identifier):
        self.event('history', {'turns': []})
    def send(self, text):
        self.event('item/agentMessage/delta', {'delta': 'streamed fixture reply'})
    def close(self):
        self.server.closed = True
    def interrupt(self):
        pass

with patch('embedded_ui.Conversation', Fixture):
    view = EmbeddedView(app, {}, 'fixture-project')
    window.show_all()
    phase = [0]
    def check():
        try:
            if not view.ready:
                return True
            if phase[0] == 0:
                assert view.send_button.get_sensitive()
                view.prompt.get_buffer().set_text('fixture message')
                view.send()
                phase[0] = 1
                return True
            buffer = view.output.get_buffer()
            text = buffer.get_text(*buffer.get_bounds(), True)
            if 'streamed fixture reply' not in text:
                return True
            view.event('item/started', {'item': {'id': 'tool1', 'type': 'commandExecution', 'command': 'pwd'}})
            view.event('item/completed', {'item': {'id': 'tool1', 'type': 'commandExecution', 'command': 'pwd', 'status': 'completed'}})
            text = buffer.get_text(*buffer.get_bounds(), True)
            assert text.count('pwd') == 1
            view.search.set_text('fixture')
            view.update_search()
            assert len(view.search_hits) == 2
            view.navigate(-1)
            assert view.search_index == 1
            view.navigate(1)
            assert view.search_index == 0
            assert view.panel.get_preferred_width()[0] <= 1024
            assert view.panel.get_preferred_height()[0] <= 768
            assert view.output.get_allocated_height() >= 120
            assert view.prompt.get_allocated_height() >= 48
            _, send_y = view.send_button.translate_coordinates(view.panel, 0, 0)
            assert send_y + view.send_button.get_allocated_height() <= view.panel.get_allocated_height()
            view.close()
            assert not view.alive and view.conversation.server.closed
        except Exception as exc:
            errors.append(exc)
        Gtk.main_quit()
        return False
    def timeout():
        errors.append(RuntimeError('embedded GTK fixture timed out'))
        Gtk.main_quit()
        return False
    GLib.timeout_add(30, check)
    GLib.timeout_add_seconds(8, timeout)
    Gtk.main()
window.destroy()
if errors:
    raise errors[0]
print('Embedded GTK panel fixture passed')
