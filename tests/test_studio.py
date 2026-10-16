import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import core

class Safety(unittest.TestCase):
    def test_injection_rejected(self):
        for name in ['../other', 'x;id', '$(id)', '-x\nwhoami', '', 'a b']:
            with self.assertRaises(ValueError):
                core.remote_command('edit', name, 'optiplex')
        for host in ['-oProxyCommand=id', 'host;id', 'x\ny']:
            with self.assertRaises(ValueError):
                core.ssh_args({'host': host, 'user': 'optiplex'}, 'edit', 'game')

    def test_fixed_actions(self):
        config = {'host': '100.100.100.100', 'user': 'optiplex'}
        self.assertEqual(core.ssh_args(config, 'edit', 'game')[-1], '/home/optiplex/.local/bin/studio edit game')
        self.assertIn('resume', core.ssh_args(config, 'resume', 'game', True)[-1])
        self.assertIn('-tt', core.ssh_args(config, 'code', 'game', True))
        with self.assertRaises(ValueError):
            core.remote_command('docker', 'game', 'optiplex')

    def test_error_visible(self):
        import subprocess
        with patch('project_client.request', side_effect=RuntimeError('Host key verification failed')), patch('core.launch_studio_desktop'):
            with self.assertRaisesRegex(RuntimeError, 'Host key'):
                core.run_action({'host': '100.100.100.100', 'user': 'optiplex'}, 'edit', 'game')

    def test_terminal_argv(self):
        with patch('shutil.which', side_effect=lambda p: p if p == 'gnome-terminal' else None):
            self.assertEqual(core.terminal_args(['ssh', 'host']), ['gnome-terminal', '--wait', '--', 'ssh', 'host'])

    def test_remote_paths_for_configured_user(self):
        for user, home in [('alice', '/home/alice'), ('root', '/root')]:
            config = {'host': '100.100.100.100', 'user': user}
            for action in ('new', 'edit'):
                self.assertEqual(core.ssh_args(config, action, 'game')[-1], f'{home}/.local/bin/studio {action} game')
            import shlex
            for action in ('code', 'resume'):
                command = shlex.split(core.ssh_args(config, action, 'game', True)[-1])
                self.assertEqual(command[:3], [f'{home}/.local/bin/codex', '--cd', f'{home}/StudioProjects/Godot/game'])
                self.assertIn('--sandbox', command)
                self.assertIn('--config', command)
                self.assertIn('GAME.md', command[command.index('--config') + 1])
                self.assertEqual(command[-1] == 'resume', action == 'resume')
        for user in ['x;id', '../root', '-root', 'a b']:
            with self.assertRaises(ValueError):
                core.remote_command('code', 'game', user)

    def test_terminal_adapters(self):
        for terminal, flags in [('gnome-terminal', ['--wait', '--']), ('konsole', ['--nofork', '-e']),
                                ('xfce4-terminal', ['--disable-server', '-x']), ('xterm', ['-e'])]:
            with self.subTest(terminal=terminal), patch('shutil.which', side_effect=lambda p: p if p == terminal else None):
                self.assertEqual(core.terminal_args(['ssh', 'host']), [terminal] + flags + ['ssh', 'host'])
        with patch('shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'supported terminal'):
                core.terminal_args(['ssh'])

    def test_debian_terminal_alternative(self):
        with patch('shutil.which', side_effect=lambda p: '/usr/bin/x-terminal-emulator' if p == 'x-terminal-emulator' else None), patch('pathlib.Path.resolve', return_value=Path('/usr/bin/konsole')):
            self.assertEqual(core.terminal_args(['ssh']), ['/usr/bin/x-terminal-emulator', '--nofork', '-e', 'ssh'])
        with patch('shutil.which', side_effect=lambda p: '/usr/bin/x-terminal-emulator' if p == 'x-terminal-emulator' else None), patch('pathlib.Path.resolve', return_value=Path('/usr/bin/cosmic-term')):
            with self.assertRaisesRegex(RuntimeError, 'supported terminal'):
                core.terminal_args(['ssh'])

    def test_codex_exit_status_handoff(self):
        # Execute the actual wrapper without a terminal or remote connection.
        for action in ('code', 'resume'):
            for status in (0, 255):
                with self.subTest(action=action, status=status), patch('core.ssh_args', return_value=['/bin/sh', '-c', f'exit {status}']), patch('core.terminal_args', side_effect=lambda command: command):
                    if status:
                        with self.assertRaisesRegex(RuntimeError, 'exit 255'):
                            core.run_action({}, action, 'game')
                    else:
                        self.assertEqual(core.run_action({}, action, 'game'), 'Codex conversation closed.')

    def test_terminal_spawn_failure(self):
        with patch('core.terminal_args', return_value=['/no/such/studio-terminal']):
            with self.assertRaises(OSError):
                core.run_action({'host': '100.100.100.100', 'user': 'optiplex'}, 'code', 'game')

    def test_terminal_missing_status(self):
        with patch('core.terminal_args', return_value=['/bin/true']):
            with self.assertRaisesRegex(RuntimeError, 'No remote exit status'):
                core.run_action({'host': '100.100.100.100', 'user': 'optiplex'}, 'resume', 'game')
