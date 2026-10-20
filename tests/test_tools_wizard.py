"""Exercise wizard consent/retry callbacks without a display or external actions."""
import dataclasses
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
try:
    import gi
    gi.require_version('Gtk', '3.0')
    import tools_ui
except (ImportError, ValueError):
    tools_ui = None
import native_tools as n


class Widget:
    def __init__(self, text='', callback=None, **kwargs):
        self.text, self.callback, self.sensitive = text, callback, True
    def __getattr__(self, name): return lambda *args, **kwargs: None
    def get_content_area(self): return Widget()
    def set_text(self, text): self.text = text
    def set_label(self, text): self.text = text
    def set_sensitive(self, value): self.sensitive = value
    def click(self):
        if self.sensitive: self.callback(self)


@unittest.skipIf(tools_ui is None, 'GTK introspection not available')
class Wizard(unittest.TestCase):
    def run_wizard(self, decisions, fail_first=False, existing=False, repair=False):
        controls, notices, saved, confirmations, calls = [], [], [], [], []
        status = {'ready': existing}
        root = Path('/fixture/tools')
        plan = n.InstallPlan('godot', '4.7.2-stable', 'fixture.zip',
            'https://github.com/godotengine/godot-builds/releases/download/4.7.2-stable/fixture.zip',
            'sha512', 'a' * 128, 'https://github.com/official/checksum', 'Godot', root)
        def button(text, callback):
            widget = Widget(text, callback)
            controls.append(widget)
            return widget
        def inspect(config, app):
            ready = status['ready'] and app == 'godot'
            if repair and app == 'godot' and not ready:
                return dict(status='Repair needed', path='/fixture/Godot', repairable=True, detail='Missing companion')
            return dict(status='Ready' if ready else 'Missing', path='/fixture/Godot' if ready else '', detail='fixture')
        def install(config, reviewed, **kwargs):
            calls.append(kwargs)
            self.assertIs(reviewed, plan)
            self.assertTrue(kwargs['consent'])
            if fail_first and len(calls) == 1: raise n.InstallError('checksum mismatch')
            kwargs['progress']('Downloading', 4, 4)
            status['ready'] = True
            return '/fixture/Godot'
        class Dialog(Widget):
            def run(dialog):
                for decision in decisions:
                    target = next(c for c in controls if c.text in ('Install…', 'Retry install…', 'Repair…'))
                    # Installed or detected executables disable automatic downloads.
                    if existing:
                        self.assertFalse(target.sensitive)
                    else:
                        target.click()
                        if decision == 'accept':
                            self.assertTrue(status['ready'] or fail_first)
                if status['ready']:
                    self.assertFalse(next(c for c in controls if c.text in ('Install…', 'Retry install…', 'Repair…')).sensitive)
                return 0
        class Confirmation(Widget):
            def format_secondary_text(dialog, text): confirmations.append(text)
            def run(dialog):
                answer = decisions[len(confirmations) - 1]
                return 1 if answer == 'accept' else 0
        class Thread:
            def __init__(self, target, **kwargs): self.target = target
            def start(self): self.target()
        gtk = types.SimpleNamespace(Dialog=Dialog, MessageDialog=Confirmation,
            Box=Widget, ScrolledWindow=Widget, ProgressBar=Widget,
            ResponseType=types.SimpleNamespace(CLOSE=2, CANCEL=0, OK=1),
            PolicyType=types.SimpleNamespace(NEVER=0, AUTOMATIC=1),
            Orientation=types.SimpleNamespace(VERTICAL=1),
            MessageType=types.SimpleNamespace(QUESTION=1), ButtonsType=types.SimpleNamespace(NONE=0))
        host = types.SimpleNamespace(window=None, config={'existing_setting': 'keep'}, status=Widget(),
            label=lambda *a: Widget(*a[:1]), button=button,
            notice=lambda *a: notices.append(a), save_config=lambda c: saved.append(c))
        with patch.object(tools_ui, 'Gtk', gtk), patch.object(tools_ui.GLib, 'idle_add', side_effect=lambda f: f()), patch.object(tools_ui.threading, 'Thread', Thread), patch.object(n, 'inspect', side_effect=inspect), patch.object(n, 'prepare_install', return_value=plan) as prepare, patch.object(n, 'install', side_effect=install):
            tools_ui.ToolsUI.tools_setup(host)
        self.assertEqual(saved[-1], {'existing_setting': 'keep', 'native_setup_seen': True})
        self.assertEqual(sum(c.text == 'Official guidance' for c in controls), 7)
        self.assertTrue(any(c.text == 'Choose Executable…' for c in controls))
        self.assertEqual(sum(c.text in ('Install…', 'Retry install…', 'Repair…') for c in controls), 7)
        return calls, notices, confirmations, prepare.call_count

    def test_declining_never_installs(self):
        calls, _, confirmations, _ = self.run_wizard(['decline'])
        self.assertFalse(calls)
        self.assertIn('Version: 4.7.2-stable', confirmations[0])
        self.assertIn('Destination:', confirmations[0])

    def test_accepting_and_retrying(self):
        calls, notices, _, _ = self.run_wizard(['accept', 'accept'], fail_first=True)
        self.assertEqual(len(calls), 2)
        self.assertIn('checksum mismatch', notices[0][1])

    def test_detected_disables_download_offer(self):
        calls, _, confirmations, prepared = self.run_wizard(['accept'], existing=True)
        self.assertFalse(calls)
        self.assertFalse(confirmations)
        self.assertEqual(prepared, 0)

    def test_incomplete_runtime_exposes_repair(self):
        calls, notices, confirmations, prepared = self.run_wizard(['accept'], repair=True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(prepared, 1)
        self.assertFalse(notices)
