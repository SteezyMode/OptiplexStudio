"""Moonlight detection, direct launch, reuse and GUI failure regression tests."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import core

CONFIG = {'host': '100.100.100.101', 'user': 'optiplex', 'moonlight_app': 'Configured Desktop'}

class Moonlight(unittest.TestCase):
    def test_appimage_detection_precedes_native_and_flatpak(self):
        with tempfile.TemporaryDirectory() as home:
            appimage = Path(home) / 'Applications' / 'Moonlight Qt.AppImage'
            appimage.parent.mkdir()
            appimage.write_text('fixture')
            appimage.chmod(0o755)
            with patch('core.Path.home', return_value=Path(home)), patch('shutil.which') as which:
                self.assertEqual(core.moonlight_args(CONFIG), [str(appimage), 'stream', CONFIG['host'], 'Configured Desktop'])
                which.assert_not_called()

    def test_explicit_appimage_and_invalid_path(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / 'custom image'
            image.touch(mode=0o755)
            config = dict(CONFIG, moonlight_appimage=str(image))
            self.assertEqual(core.moonlight_args(config), [str(image), 'stream', CONFIG['host'], 'Configured Desktop'])
            image.chmod(0o644)
            with self.assertRaisesRegex(RuntimeError, 'not an executable file'):
                core.moonlight_args(config)

    def test_native_and_flatpak_commands_preserve_preferences(self):
        with tempfile.TemporaryDirectory() as folder, patch('core.Path.home', return_value=Path(folder)):
            with patch('shutil.which', side_effect=lambda name: '/usr/bin/moonlight' if name == 'moonlight' else None):
                self.assertEqual(core.moonlight_args(CONFIG), ['/usr/bin/moonlight', 'stream', CONFIG['host'], 'Configured Desktop'])
            with patch('shutil.which', side_effect=lambda name: '/usr/bin/flatpak' if name == 'flatpak' else None), patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'app/ref', '')) as run:
                self.assertEqual(core.moonlight_args(CONFIG), ['/usr/bin/flatpak', 'run', core.MOONLIGHT_ID, 'stream', CONFIG['host'], 'Configured Desktop'])
                run.assert_called_once_with(['/usr/bin/flatpak', 'info', '--show-ref', core.MOONLIGHT_ID], capture_output=True, text=True, timeout=5)

    def test_missing_installation_and_flatpak_failure(self):
        with tempfile.TemporaryDirectory() as folder, patch('core.Path.home', return_value=Path(folder)):
            for result in (subprocess.CompletedProcess([], 1, '', ''), subprocess.TimeoutExpired('flatpak', 5)):
                with patch('shutil.which', side_effect=lambda name: '/usr/bin/flatpak' if name == 'flatpak' else None), patch('subprocess.run', **({'side_effect': result} if isinstance(result, Exception) else {'return_value': result})):
                    with self.assertRaisesRegex(RuntimeError, 'Moonlight was not found'):
                        core.moonlight_args(CONFIG)
            with patch('shutil.which', return_value=None):
                with self.assertRaisesRegex(RuntimeError, 'Moonlight was not found'):
                    core.moonlight_args(CONFIG)

    def test_invalid_host_never_launches_moonlight(self):
        with patch('core.moonlight_prefix') as detect:
            with self.assertRaises(ValueError):
                core.moonlight_args(dict(CONFIG, host='public.example.com'))
            detect.assert_not_called()

    def test_moonlight_and_ready_desktop_precede_godot(self):
        order = []
        def remote(config, project, operation, **fields):
            order.append(operation)
            if operation == 'desktop_status':
                return {'ready': True}
            self.assertEqual((project, operation, fields), ('game', 'desktop', {'application': 'godot'}))
            return {'message': 'Godot opened.'}
        def stream(config, **kwargs):
            order.append('moonlight')
            return 'Configured Desktop opened'
        with patch('project_client.request', side_effect=remote), patch('core.launch_studio_desktop', side_effect=stream):
            self.assertIn('Configured Desktop opened', core.run_action(CONFIG, 'edit', 'game'))
        self.assertEqual(order, ['moonlight', 'desktop_status', 'desktop'])

    def test_readiness_failure_prevents_godot_launch(self):
        for error in (RuntimeError('Wolf is not running'), TimeoutError('SSH timeout')):
            with patch('project_client.request', side_effect=error) as remote, patch('core.launch_studio_desktop') as stream:
                with self.assertRaises((RuntimeError, TimeoutError)):
                    core.run_action(CONFIG, 'edit', 'game')
                stream.assert_called_once()
                self.assertEqual(remote.call_args.args[2], 'desktop_status')

    def test_successful_creation_never_launches_moonlight(self):
        with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'Created game', '')), patch('core.launch_studio_desktop') as stream:
            self.assertEqual(core.run_action(CONFIG, 'new', 'game'), 'Created game')
            stream.assert_not_called()

    def test_moonlight_error_is_distinct_from_godot_error(self):
        with patch('project_client.request', return_value={'message': 'Godot opened'}), patch('core.launch_studio_desktop', side_effect=OSError('AppImage runtime unavailable')):
            with self.assertRaisesRegex(OSError, 'AppImage runtime unavailable'):
                core.run_action(CONFIG, 'edit', 'game')

    def test_startup_failure_includes_moonlight_output(self):
        with patch('core.studio_stream_pid', return_value=None), patch('core.moonlight_args', return_value=['/bin/sh', '-c', 'echo "Not paired with Wolf" >&2; exit 9']):
            with self.assertRaisesRegex(RuntimeError, 'Not paired with Wolf'):
                core.launch_studio_desktop(CONFIG)
        with patch('core.studio_stream_pid', return_value=None), patch('core.moonlight_args', return_value=['/missing/moonlight']):
            with self.assertRaises(OSError):
                core.launch_studio_desktop(CONFIG)

    def test_late_stream_failure_reports_callback(self):
        event = threading.Event()
        errors = []
        process = MagicMock()
        process.wait.side_effect = [subprocess.TimeoutExpired('moonlight', 2), 7]
        process.poll.return_value = 7
        def spawn(*args, **kwargs):
            kwargs['stdout'].write(b'Decoder failed')
            kwargs['stdout'].flush()
            return process
        def failure(message):
            errors.append(message)
            event.set()
        with patch('core.studio_stream_pid', return_value=None), patch('core.moonlight_args', return_value=['moonlight']), patch('subprocess.Popen', side_effect=spawn):
            message = core.launch_studio_desktop(CONFIG, on_error=failure)
            self.assertIn('connecting', message)
            self.assertTrue(event.wait(2))
            self.assertIn('Decoder failed', errors[0])
            self.assertIn('exit 7', errors[0])

    def test_existing_stream_reused_even_without_window_activation(self):
        for focused in (True, False):
            with patch('core.studio_stream_pid', return_value=123), patch('core.focus_studio_stream', return_value=focused) as focus, patch('subprocess.Popen') as spawn:
                message = core.launch_studio_desktop(CONFIG)
                focus.assert_called_once_with(123, CONFIG['moonlight_app'])
                spawn.assert_not_called()
                self.assertIn('brought forward' if focused else 'already streaming', message)

    def test_process_match_requires_exact_host_app_and_current_user(self):
        real_path = Path
        with tempfile.TemporaryDirectory() as folder:
            proc = Path(folder)
            def put(pid, args):
                child = proc / str(pid)
                child.mkdir(exist_ok=True)
                (child / 'cmdline').write_bytes(b'\0'.join(arg.encode() for arg in args) + b'\0')
            def path(value): return proc if value == '/proc' else real_path(value)
            put(101, ['/usr/bin/moonlight', 'stream', CONFIG['host'], 'Steam'])
            put(102, ['/usr/bin/moonlight', 'stream', '100.100.100.102', 'Configured Desktop'])
            put(103, ['/usr/bin/other', 'stream', CONFIG['host'], 'Configured Desktop'])
            with patch('core.Path', side_effect=path):
                self.assertIsNone(core.studio_stream_pid(CONFIG['host'], CONFIG['moonlight_app']))
                put(104, ['/tmp/.mount_moonlight/usr/bin/moonlight', 'stream', CONFIG['host'], 'Configured Desktop'])
                self.assertEqual(core.studio_stream_pid(CONFIG['host'], CONFIG['moonlight_app']), 104)
                with patch('os.getuid', return_value=os.getuid() + 1):
                    self.assertIsNone(core.studio_stream_pid(CONFIG['host'], CONFIG['moonlight_app']))

    def test_window_activation_uses_matching_pid_and_title(self):
        listing = '0x001 0 122 client Steam - Moonlight\n0x002 0 123 client Configured Desktop - Moonlight\n'
        with patch('shutil.which', return_value='/usr/bin/wmctrl'), patch('subprocess.run', side_effect=[subprocess.CompletedProcess([], 0, listing, ''), subprocess.CompletedProcess([], 0, '', '')]) as run:
            self.assertTrue(core.focus_studio_stream(123, CONFIG['moonlight_app']))
            self.assertEqual(run.call_args.args[0], ['/usr/bin/wmctrl', '-ia', '0x002'])
        with patch('shutil.which', return_value=None):
            self.assertFalse(core.focus_studio_stream(123, CONFIG['moonlight_app']))

    def test_gui_displays_stream_failures_and_restores_controls(self):
        import app
        from test_network import Widget
        class Fake:
            config = dict(CONFIG)
            rows = [{'name': 'game'}]
            busy = False
            status, create_button = Widget(), Widget()
            def selection_changed(self, _): pass
            def worker(self, task, done):
                try: result = task()
                except Exception as exc: done(None, str(exc))
                else: done(result, None)
        for late in (False, True):
            fake = Fake()
            def launch(*args, **kwargs):
                if late:
                    kwargs['on_error']('Moonlight failed after startup')
                    return 'connecting'
                raise RuntimeError('Godot opened, but Moonlight not paired')
            with patch('app.core.run_action', side_effect=launch), patch('app.GLib.idle_add', side_effect=lambda callback, *args: callback(*args)):
                app.Studio.action(fake, 'edit', 'game')
            self.assertIn('Moonlight', fake.status.text)
            self.assertNotEqual(fake.status.text, 'connecting')
            self.assertFalse(fake.busy)
            self.assertTrue(fake.create_button.sensitive)
