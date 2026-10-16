import json
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import core
import desktop_helper
import project_client

CONFIG = {'host': '100.100.100.102', 'user': 'optiplex'}

class ColdStart(unittest.TestCase):
    def test_stopped_session_starts_stream_waits_then_opens_once(self):
        calls, messages = [], []
        ready = iter([False, False, True])
        clock = [0]
        def stream(config, **kwargs):
            calls.append('Moonlight')
            return 'Connecting to OptiPlex Studio Desktop'
        def remote(config, project, operation, **fields):
            self.assertEqual(project, 'game')
            calls.append(operation)
            if operation == 'desktop_status':
                self.assertEqual(fields['request_timeout'], 25)
                return {'ready': next(ready), 'message': 'Session still warming up'}
            self.assertEqual(fields, {'application': 'godot'})
            return {'message': 'Godot opened for game.'}
        with patch('core.launch_studio_desktop', side_effect=stream), patch('project_client.request', side_effect=remote), patch('core.time.monotonic', side_effect=lambda: clock[0]), patch('core.time.sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            result = core.run_action(CONFIG, 'edit', 'game', on_progress=messages.append)
        self.assertEqual(calls, ['Moonlight', 'desktop_status', 'desktop_status', 'desktop_status', 'desktop'])
        self.assertIn('Godot opened', result)
        self.assertTrue(any('warming up' in message for message in messages))

    def test_moonlight_failure_never_runs_remote_operations(self):
        with patch('core.launch_studio_desktop', side_effect=RuntimeError('Pairing failed')), patch('project_client.request') as remote:
            with self.assertRaisesRegex(RuntimeError, 'Pairing failed'):
                core.run_action(CONFIG, 'edit', 'game')
            remote.assert_not_called()

    def test_readiness_timeout_never_launches_godot(self):
        clock = [0]
        with patch('project_client.request', return_value={'ready': False, 'message': 'No display yet'}) as remote, patch('core.time.monotonic', side_effect=lambda: clock[0]), patch('core.time.sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            with self.assertRaisesRegex(RuntimeError, 'Godot was not launched.*No display yet'):
                core.wait_for_studio_desktop(CONFIG, 'game', timeout=4, interval=2)
        self.assertTrue(all(call.args[2] == 'desktop_status' for call in remote.call_args_list))

    def test_stream_failure_while_waiting_aborts_before_editor(self):
        errors = []
        def remote(*args, **kwargs):
            errors.append('Video connection failed')
            return {'ready': True}
        with patch('project_client.request', side_effect=remote):
            with self.assertRaisesRegex(RuntimeError, 'Video connection failed'):
                core.wait_for_studio_desktop(CONFIG, 'game', stream_errors=errors)

    def test_stopped_container_status_is_normal_pending_state(self):
        with patch('desktop_helper.run', return_value='Steam_123\nWolfUI_456\n') as run, patch('subprocess.run') as execute:
            status = desktop_helper.handle({'version': 1, 'operation': 'desktop_status', 'project': 'game'})
        self.assertFalse(status['ready'])
        self.assertIn('Waiting for Moonlight', status['message'])
        execute.assert_not_called()
        self.assertEqual(run.call_args.args[0][:2], ['docker', 'ps'])

    def test_container_is_not_ready_until_display_probe_succeeds(self):
        for code in (1, 0):
            with self.subTest(code=code), patch('desktop_helper.desktop_environment', return_value={'DISPLAY': ':0', 'XDG_RUNTIME_DIR': '/run/user/wolf', 'WAYLAND_DISPLAY': 'wayland-1'}), patch('desktop_helper.run', return_value='WolfStudioDesktop_123\n'), patch('subprocess.run', return_value=subprocess.CompletedProcess([], code, 'Desktop probe result', '')) as execute:
                status = desktop_helper.desktop_status('game')
                self.assertEqual(status['ready'], code == 0)
                args = execute.call_args.args[0]
                self.assertEqual(args[:4], ['docker', 'exec', '-u', 'retro'])
                self.assertEqual(args[-1], 'game')
                self.assertIn('_NET_SUPPORTING_WM_CHECK', args[-2])
                self.assertNotIn('restart', args)

    def test_ambiguous_session_is_not_selected(self):
        with patch('desktop_helper.run', return_value='WolfStudioDesktop_1\nWolfStudioDesktop_2\n'):
            with self.assertRaisesRegex(RuntimeError, 'Multiple'):
                desktop_helper.desktop_status('game')

class HelperSource(unittest.TestCase):
    def test_injected_focus_source_is_executed_from_actual_constructed_command(self):
        focus = "print(\"literal 'quotes' `backticks` $(not_a_command)\")\n"
        helper = "import json, sys\njson.load(sys.stdin)\nprint(json.dumps({'ok':True,'result':{'focus':GODOT_FOCUS_SOURCE}}))\n"
        def read(path, *args, **kwargs):
            return focus if path.name == 'godot_focus.py' else helper
        # A real local process exercises quoting and stdio without SSH or Docker.
        with patch('core.ssh_args', return_value=['/bin/sh', '-c', 'replaced']), patch('pathlib.Path.read_text', new=read):
            result = project_client.request(CONFIG, 'game', 'desktop', application='godot')
        self.assertEqual(result['focus'], focus)

    def test_readiness_command_uses_desktop_helper_not_asset_helper(self):
        def read(path, *args, **kwargs):
            self.assertEqual(path.name, 'desktop_helper.py')
            return "import json,sys\nrequest=json.load(sys.stdin)\nprint(json.dumps({'ok':True,'result':{'operation':request['operation']}}))"
        with patch('core.ssh_args', return_value=['/bin/sh', '-c', 'replaced']), patch('pathlib.Path.read_text', new=read):
            result = project_client.request(CONFIG, 'game', 'desktop_status', request_timeout=5)
        self.assertEqual(result['operation'], 'desktop_status')

class Identity(unittest.TestCase):
    def test_explicit_glib_and_gdk_identity(self):
        import app
        with patch('app.GLib.set_prgname') as prgname, patch('app.GLib.get_application_name', return_value='app.py'), patch('app.GLib.set_application_name') as name, patch('app.Gdk.set_program_class') as program:
            app.configure_identity()
        prgname.assert_called_once_with('optiplex-studio')
        name.assert_called_once_with('OptiPlex Studio')
        program.assert_called_once_with('optiplex-studio')

    def tray_fake(self):
        return SimpleNamespace(restore=MagicMock(), open_studio_desktop=MagicMock(), action=MagicMock(),
                               open_url=MagicMock(), settings=MagicMock(), quit=MagicMock())

    def test_appindicator_has_human_readable_title(self):
        import app, builtins
        fake = self.tray_fake()
        api = MagicMock()
        indicator = api.Indicator.new.return_value
        real_import = builtins.__import__
        def import_(name, *args, **kwargs):
            return SimpleNamespace(AyatanaAppIndicator3=api) if name == 'gi.repository' else real_import(name, *args, **kwargs)
        bus = MagicMock()
        bus.call_sync.return_value.unpack.return_value = (True,)
        with patch('app.Gtk.Menu'), patch('app.Gtk.MenuItem'), patch('app.Gio.bus_get_sync', return_value=bus), patch('app.gi.require_version'), patch('builtins.__import__', side_effect=import_):
            app.Studio.initialize_tray(fake)
        indicator.set_title.assert_called_once_with('OptiPlex Studio')
        indicator.set_desktop_entry.assert_called_once_with('com.monumentrisk.OptiPlexStudio')
        indicator.set_icon_full.assert_called_once_with('optiplex-studio-tray', 'OptiPlex Studio')

    def test_xembed_title_is_not_python_script_name(self):
        import app
        fake = self.tray_fake()
        bus = MagicMock()
        bus.call_sync.return_value.unpack.return_value = (False,)
        with patch('app.Gtk.Menu'), patch('app.Gtk.MenuItem'), patch('app.Gio.bus_get_sync', return_value=bus), patch('app.Gtk.StatusIcon.new_from_icon_name') as factory:
            app.Studio.initialize_tray(fake)
        factory.return_value.set_title.assert_called_once_with('OptiPlex Studio')
        factory.return_value.set_name.assert_called_once_with('optiplex-studio')
