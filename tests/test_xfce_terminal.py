from pathlib import Path
import shlex
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import core
import native_tools


class XfceTerminalTests(unittest.TestCase):
    def test_literal_argv_and_alternative(self):
        args = ['/a path/codex', '--no-daemon', '', "a'b", '"quoted"',
                'line\nbreak', '$(touch /tmp/injected); `id`', '\\', '-option']
        for alternative in (False, True):
            with self.subTest(alternative=alternative), patch('core.shutil.which',
                    side_effect=lambda name: '/usr/bin/x-terminal-emulator' if alternative and name == 'x-terminal-emulator'
                    else 'xfce4-terminal' if not alternative and name == 'xfce4-terminal' else None), patch(
                        'core.Path.resolve', return_value=Path('/usr/bin/xfce4-terminal')):
                terminal = core.terminal_args(args)
                self.assertEqual(terminal[1], '--window')
                self.assertEqual(shlex.split(terminal[2].split('=', 1)[1]), args)
                self.assertNotIn('--disable-server', terminal)

    def test_glib_command_parser_preserves_arbitrary_arguments(self):
        try:
            from gi.repository import GLib
        except ImportError:
            self.skipTest('GLib unavailable')
        args = ['/a path/codex', '', "a'b", '"', '\\', 'a\nb',
                '$(id); `id`', '--no-daemon', '雪']
        with patch('core.shutil.which', side_effect=lambda name: name if name == 'xfce4-terminal' else None):
            terminal = core.terminal_args(args)
        success, parsed = GLib.shell_parse_argv(terminal[-1].split('=', 1)[1])
        self.assertTrue(success)
        self.assertEqual(parsed, args)

    def launch(self, code=0, error=None):
        process = Mock(returncode=code)
        process.communicate.return_value = ('', 'launcher diagnostic')
        process.__enter__ = Mock(return_value=process)
        process.__exit__ = Mock(return_value=False)
        return patch('native_tools.subprocess.Popen', side_effect=error, return_value=process)

    def test_handoff_is_not_a_codex_exit(self):
        cwd = Path('/projects/path with spaces; $(id)')
        args = ['/home/a path/codex', '--no-daemon', '-C', str(cwd), '--', 'task']
        started = Mock()
        with patch('native_tools.codex_command', return_value=(args, cwd)), patch(
                'core.shutil.which', side_effect=lambda name: name if name == 'xfce4-terminal' else None), self.launch() as spawn:
            result = native_tools.run_action({}, 'code', 'game', on_started=started)
        self.assertIn('termination is not tracked', result)
        self.assertNotIn('closed', result)
        started.assert_called_once_with()
        actual = spawn.call_args.args[0]
        self.assertIn('--working-directory=' + str(cwd), actual)
        self.assertEqual(shlex.split(actual[-1].split('=', 1)[1]), args)
        self.assertEqual(spawn.call_args.kwargs['cwd'], str(cwd))
        self.assertNotIn('shell', spawn.call_args.kwargs)

    def test_launch_failure_is_not_codex_failure(self):
        for code, error in ((2, None), (0, FileNotFoundError('terminal missing'))):
            started = Mock()
            with self.subTest(code=code), patch('native_tools.codex_command', return_value=(['codex'], Path('/tmp'))), patch(
                    'core.terminal_args', return_value=['xfce4-terminal', '--window', '--command=codex']), self.launch(code, error):
                with self.assertRaisesRegex(RuntimeError, 'terminal launch failed'):
                    native_tools.run_action({}, 'code', 'game', on_started=started)
            started.assert_not_called()
