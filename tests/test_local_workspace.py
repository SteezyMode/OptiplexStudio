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
        with (patch('local_workspace.command', return_value=['/bin/true']),
              patch('core.ssh_args', side_effect=AssertionError('SSH invoked')),
              patch('core.terminal_args', side_effect=lambda argv: argv)):
            self.assertEqual(core.run_action(LOCAL, 'code', 'game'), 'Codex conversation closed.')
            self.assertEqual(core.run_action(LOCAL, 'resume', 'game',
                              session_id='12345678-1234-1234-1234-123456789012'), 'Codex conversation closed.')
            with self.assertRaises(ValueError):
                core.run_action(LOCAL, 'resume', 'game', session_id='not-a-uuid')
            with self.assertRaises(ValueError):
                core.run_action(LOCAL, 'code', 'game', prompt='untrusted arbitrary prompt')


if __name__ == '__main__':
    unittest.main()
