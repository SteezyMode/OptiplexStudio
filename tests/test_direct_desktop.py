import ctypes as C
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import core
import desktop_helper
import godot_focus

CONFIG = {'host': '100.100.100.102', 'user': 'optiplex'}

class DirectDesktop(unittest.TestCase):
    def test_default_and_legacy_settings_use_verified_title(self):
        with patch('core.moonlight_prefix', return_value=['/Applications/Moonlight.AppImage']):
            for settings in (CONFIG, dict(CONFIG, moonlight_app=''), dict(CONFIG, moonlight_app='Studio Desktop')):
                self.assertEqual(core.moonlight_args(settings), ['/Applications/Moonlight.AppImage', 'stream', CONFIG['host'], 'OptiPlex Studio Desktop'])
            self.assertEqual(core.moonlight_args(dict(CONFIG, moonlight_app='Other Desktop'))[-1], 'Other Desktop')

    def test_appimage_runtime_environment_is_local_and_preserves_preferences(self):
        with patch.dict(os.environ, {'STUDIO_TEST_KEEP': 'retained'}, clear=True):
            environment = core.moonlight_environment(CONFIG, ['/home/user/Applications/Moonlight-6.2.0-x86_64.AppImage'])
            self.assertEqual(environment['APPIMAGE_EXTRACT_AND_RUN'], '1')
            self.assertEqual(environment['STUDIO_TEST_KEEP'], 'retained')
            self.assertNotIn('APPIMAGE_EXTRACT_AND_RUN', os.environ)
            self.assertIsNone(core.moonlight_environment(CONFIG, ['/usr/bin/moonlight']))
            self.assertIsNone(core.moonlight_environment(CONFIG, ['flatpak', 'run', core.MOONLIGHT_ID]))
        custom = dict(CONFIG, moonlight_appimage='/home/user/custom-client')
        self.assertEqual(core.moonlight_environment(custom, ['/home/user/custom-client'])['APPIMAGE_EXTRACT_AND_RUN'], '1')

    def test_stream_spawn_receives_appimage_runtime_setting(self):
        process = MagicMock()
        process.wait.return_value = 0
        with patch('core.studio_stream_pid', return_value=None), patch('core.moonlight_prefix', return_value=['/home/user/Moonlight.AppImage']), patch('subprocess.Popen', return_value=process) as spawn:
            core.launch_studio_desktop(CONFIG)
        self.assertEqual(spawn.call_args.args[0], ['/home/user/Moonlight.AppImage', 'stream', CONFIG['host'], 'OptiPlex Studio Desktop'])
        self.assertEqual(spawn.call_args.kwargs['env']['APPIMAGE_EXTRACT_AND_RUN'], '1')
        self.assertFalse(any(flag in spawn.call_args.args[0] for flag in ('--resolution', '--bitrate', '--decoder')))

    def test_standalone_action_needs_no_project_or_remote_command(self):
        from test_projects import GUIActions
        fake = GUIActions().fake()
        fake.config = dict(CONFIG)
        fake.rows = []
        fake.combo.get_active_id.return_value = None
        with patch('project_ui.core.launch_studio_desktop', return_value='Desktop connected') as stream, patch('project_ui.client.request') as remote, patch('project_ui.GLib.idle_add'):
            fake.open_studio_desktop()
        self.assertEqual(stream.call_args.args, (CONFIG,))
        remote.assert_not_called()
        self.assertEqual(fake.status.text, 'Desktop connected')
        self.assertFalse(fake.busy)

    def test_standalone_connection_failure_is_visible(self):
        from test_projects import GUIActions
        fake = GUIActions().fake()
        with patch('project_ui.core.launch_studio_desktop', side_effect=RuntimeError('Moonlight is not paired')), patch('project_ui.GLib.idle_add'):
            fake.open_studio_desktop()
        self.assertIn('not paired', fake.status.text)
        self.assertEqual(fake.last_notice[0], 'Project operation failed')

    def test_focus_exec_is_fixed_and_project_scoped(self):
        with patch('desktop_helper.run', return_value='') as run:
            self.assertTrue(desktop_helper.focus_godot('WolfStudioDesktop_123', 'game'))
        args = run.call_args.args[0]
        self.assertEqual(args[:4], ['docker', 'exec', '-u', 'retro'])
        self.assertEqual(args[-4:-2], ['python3', '-c'])
        self.assertEqual(args[-1], 'game')
        self.assertIn('_NET_ACTIVE_WINDOW', args[-2])
        with patch('desktop_helper.run', side_effect=RuntimeError('No focusable window')):
            self.assertFalse(desktop_helper.focus_godot('WolfStudioDesktop_123', 'game'))

    def test_inside_desktop_pid_matching_is_exact(self):
        real_path = Path
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for pid, args in [(101, ['/app/bin/godot', '-e', '--path', '/projects/Godot/game/']),
                              (102, ['/app/bin/godot', '--editor', '--path=/projects/Godot/other']),
                              (103, ['/bin/sh', '-c', 'godot --editor --path /projects/Godot/game'])]:
                child = root / str(pid)
                child.mkdir()
                (child / 'cmdline').write_bytes(b'\0'.join(arg.encode() for arg in args))
            with patch('godot_focus.Path', side_effect=lambda value: root if value == '/proc' else real_path(value)):
                self.assertEqual(godot_focus.editor_pids('game'), {101})
            self.assertTrue(desktop_helper.matching_process('PID COMMAND\n101 /app/bin/godot -e --path /projects/Godot/game/\n', 'godot', 'game'))
        with self.assertRaises(ValueError):
            godot_focus.focus('../other')

    def test_x11_activation_targets_only_matching_editor_pid(self):
        library = MagicMock()
        library.XOpenDisplay.return_value = 1
        library.XDefaultRootWindow.return_value = 10
        library.XSendEvent.return_value = 1
        atoms, buffers = {}, []
        def atom(display, name, only_existing):
            return atoms.setdefault(name.decode(), len(atoms) + 1)
        library.XInternAtom.side_effect = atom
        def property_(display, window, requested, offset, length, delete, type_, actual, format_, count, after, data):
            name = next(name for name, value in atoms.items() if value == requested)
            values = [20, 21] if name == '_NET_CLIENT_LIST_STACKING' else [100] if name == '_NET_WM_PID' and window == 21 else [999]
            array = (C.c_ulong * len(values))(*values)
            buffers.append(array)
            C.cast(format_, C.POINTER(C.c_int))[0] = 32
            C.cast(count, C.POINTER(C.c_ulong))[0] = len(values)
            C.cast(data, C.POINTER(C.POINTER(C.c_ubyte)))[0] = C.cast(array, C.POINTER(C.c_ubyte))
            return 0
        library.XGetWindowProperty.side_effect = property_
        with patch('godot_focus.editor_pids', return_value={100}), patch('godot_focus.C.CDLL', return_value=library):
            self.assertTrue(godot_focus.focus('game'))
        library.XMapRaised.assert_called_once_with(1, 21)
        event = library.XSendEvent.call_args.args[-1]._obj
        self.assertEqual(event.message.window, 21)
        self.assertEqual(event.message.message_type, atoms['_NET_ACTIVE_WINDOW'])
        library.XCloseDisplay.assert_called_once_with(1)

    def test_pending_launch_is_not_repeated(self):
        import project_helper
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            base = home / 'StudioProjects/Godot'
            base.mkdir(parents=True)
            project_helper.create_project(base, 'game')
            calls = []
            def run(args, **kwargs):
                calls.append(args)
                return 'WolfStudioDesktop_123\n' if args[1] == 'ps' else 'COMMAND\n' if args[1] == 'top' else 'Opened Godot'
            request = {'version': 1, 'operation': 'desktop', 'project': 'game', 'application': 'godot'}
            with patch('desktop_helper.Path.home', return_value=home), patch('desktop_helper.desktop_environment', return_value={'DISPLAY': ':0', 'XDG_RUNTIME_DIR': '/run/user/wolf', 'WAYLAND_DISPLAY': 'wayland-1'}), patch('desktop_helper.run', side_effect=run), patch('desktop_helper.time.sleep'):
                with self.assertRaisesRegex(RuntimeError, 'no application process'):
                    desktop_helper.handle(request)
                with self.assertRaisesRegex(RuntimeError, 'already pending'):
                    desktop_helper.handle(request)
            self.assertEqual(sum('exec' in args and '-d' in args for args in calls), 1)
