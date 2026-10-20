"""Real local project-policy tests, without Codex, Godot, Wolf or SSH."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import core
import local_workspace as local
import project_client

LOCAL = {'mode': 'local', 'host': '', 'user': 'unused'}


class NativeLocalWorkspace(unittest.TestCase):
    def test_local_project_creation_and_existing_policy_reuse(self):
        with tempfile.TemporaryDirectory() as d, patch('local_workspace.Path.home', return_value=Path(d)):
            with patch('core.ssh_args', side_effect=AssertionError('No SSH permitted')):
                self.assertEqual(project_client.request(LOCAL, 'Studio', 'list_projects'), [])
                created = project_client.request(LOCAL, 'testgame', 'create', template='Godot')
                self.assertEqual(created['created'], 'testgame')
                projects = project_client.request(LOCAL, 'Studio', 'list_projects')
                self.assertEqual([p['name'] for p in projects], ['testgame'])
                self.assertTrue((Path(d)/'StudioProjects/Godot/testgame/project.godot').is_file())
                self.assertEqual(project_client.project_uri(LOCAL, 'testgame'),
                                 (Path(d)/'StudioProjects/Godot/testgame').as_uri())
                self.assertEqual(project_client.request(LOCAL, 'testgame', 'ensure_docs')['created'], [])
                with self.assertRaises(FileExistsError):
                    project_client.request(LOCAL, 'testgame', 'create', template='Godot')

    def test_local_codex_argv_uses_selected_project_and_approvals(self):
        with tempfile.TemporaryDirectory() as d, patch('local_workspace.Path.home', return_value=Path(d)):
            project_client.request(LOCAL, 'game', 'create')
            with patch('local_workspace.binary', side_effect=lambda name: '/fake/' + name):
                args = local.command('code', 'game')
                self.assertEqual(args[:3], ['/fake/codex', '--cd', str(Path(d)/'StudioProjects/Godot/game')])
                self.assertEqual(args[args.index('--sandbox')+1], 'workspace-write')
                self.assertEqual(args[args.index('--ask-for-approval')+1], 'on-request')
                self.assertIn('AGENTS.md', args[args.index('--config')+1])
                self.assertEqual(local.command('resume', 'game')[-1], 'resume')
                self.assertEqual(local.command('edit', 'game')[:3], ['/fake/godot', '--editor', '--path'])
                with self.assertRaises(ValueError):
                    local.command('code', '../outside')
                with self.assertRaises(ValueError):
                    local.command('edit', 'other')

    def test_symlinked_local_projects_denied(self):
        with tempfile.TemporaryDirectory() as d, patch('local_workspace.Path.home', return_value=Path(d)):
            base = Path(d)/'StudioProjects/Godot'
            base.mkdir(parents=True)
            other = Path(d)/'another'
            other.mkdir()
            (base/'linked').symlink_to(other, target_is_directory=True)
            with self.assertRaises((ValueError, OSError)):
                local.project_path('linked')
            with self.assertRaises((ValueError, OSError)):
                project_client.request(LOCAL, 'linked', 'docs')

    def test_local_codex_terminal_never_uses_ssh(self):
        with (patch('persistent_sessions.TmuxSessions') as backend,
              patch('core.ssh_args', side_effect=AssertionError('SSH invoked')),
              patch('core.terminal_args', side_effect=lambda argv: argv)):
            backend.return_value.attach_argv.return_value = ['/bin/true']
            self.assertEqual(core.run_action(LOCAL, 'code', 'game'),
                             'Codex terminal detached; reconnect to the same project workspace.')
            backend.return_value.ensure.assert_called_with(
                'game', session_id=None, prompt=None, all_sessions=False)
            backend.return_value.attach_argv.assert_called_with('game')
            self.assertEqual(core.run_action(
                LOCAL, 'resume', 'game',
                session_id='12345678-1234-1234-1234-123456789012'),
                'Codex terminal detached; reconnect to the same project workspace.')
            with self.assertRaises(ValueError):
                core.run_action(LOCAL, 'resume', 'game', session_id='not-a-uuid')
            with self.assertRaises(ValueError):
                core.run_action(LOCAL, 'code', 'game', prompt='untrusted arbitrary prompt')


    def test_godot_launch_creates_private_diagnostics_and_detects_exit(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d, patch('local_workspace.Path.home', return_value=Path(d)):
            project_client.request(LOCAL, 'game', 'create')
            state = Path(d) / '.state'
            with patch.dict(os.environ, {'XDG_STATE_HOME': str(state)}), patch(
                'local_workspace.binary', return_value='/fake/godot'), patch(
                'local_workspace.subprocess.Popen') as launched:
                launched.return_value.wait.side_effect = subprocess.TimeoutExpired('godot', 0.35)
                self.assertIn('started for game', local.start_godot('game'))
                self.assertEqual(launched.call_args.kwargs['stderr'], subprocess.STDOUT)
                self.assertEqual(launched.call_args.kwargs['cwd'],
                                 str(Path(d)/'StudioProjects/Godot/game'))
                log = state / 'optiplex-studio/godot-launch.log'
                self.assertTrue(log.is_file())
                self.assertEqual(log.stat().st_mode & 0o777, 0o600)
                launched.return_value.wait.side_effect = None
                launched.return_value.wait.return_value = 42
                with self.assertRaisesRegex(RuntimeError, 'exited immediately.*42'):
                    local.start_godot('game')

    def test_godot_diagnostics_refuse_symlink_log(self):
        with tempfile.TemporaryDirectory() as d, patch('local_workspace.Path.home', return_value=Path(d)):
            project_client.request(LOCAL, 'game', 'create')
            state = Path(d) / '.state'
            log = state / 'optiplex-studio/godot-launch.log'
            log.parent.mkdir(parents=True)
            victim = Path(d) / 'do-not-touch.txt'
            victim.write_text('keep')
            log.symlink_to(victim)
            with patch.dict(os.environ, {'XDG_STATE_HOME': str(state)}), patch(
                    'local_workspace.binary', return_value='/fake/godot'), patch(
                    'local_workspace.subprocess.Popen') as launched:
                with self.assertRaises(RuntimeError):
                    local.start_godot('game')
                launched.assert_not_called()
                self.assertEqual(victim.read_text(), 'keep')


    def test_blender_lmms_are_scoped_native_launches(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d, patch('local_workspace.Path.home', return_value=Path(d)):
            project_client.request(LOCAL, 'game', 'create')
            native = {'blender': '/native/blender', 'lmms': '/native/lmms'}
            state = Path(d) / 'state'
            with patch.dict(os.environ, {'XDG_STATE_HOME': str(state)}), patch(
                'local_workspace.binary', side_effect=lambda name: native[name]), patch(
                'local_workspace.subprocess.Popen') as launched, patch(
                'core.ssh_args', side_effect=AssertionError('No SSH permitted')):
                launched.return_value.wait.side_effect = subprocess.TimeoutExpired('program', 0.35)
                for kind in ('blender', 'lmms'):
                    self.assertEqual(local.command(kind, 'game'), [native[kind]])
                    self.assertIn(kind.title() if kind == 'blender' else 'LMMS',
                                  core.run_action(LOCAL, kind, 'game'))
                    self.assertEqual(launched.call_args.args[0], [native[kind]])
                    self.assertEqual(launched.call_args.kwargs['cwd'],
                                     str(Path(d) / 'StudioProjects/Godot/game'))
                    self.assertEqual((state / 'optiplex-studio' / (kind + '-launch.log')).stat().st_mode & 0o777, 0o600)
                with self.assertRaises(ValueError):
                    local.command('blender', '../bad-name')
                self.assertEqual(launched.call_count, 2)


if __name__ == '__main__':
    unittest.main()
