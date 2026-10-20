"""Local workflows run without network services or optional creative tools."""
import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import project_client as client
import native_tools as native
import project_helper as policy


class LocalFirst(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name) / 'Workspace with spaces'
        self.config = {'projects_dir': str(self.base), 'host': 'obsolete-server', 'user': 'old-user'}

    def create(self, kind='Studio'):
        return client.request(self.config, 'game', 'create', template=kind)

    def test_fresh_workspace_discovery_and_creation_are_local(self):
            self.assertEqual(client.request(self.config, 'Studio', 'list_projects'), [])
            self.create()
            self.assertEqual(client.request(self.config, 'Studio', 'list_projects')[0]['name'], 'game')
            self.assertIn('GAME.md', client.request(self.config, 'game', 'docs'))
            self.assertEqual(client.project_uri(self.config, 'game'), (self.base / 'game').as_uri())

    def test_legacy_transport_and_hosted_catalog_are_absent(self):
        import core
        self.assertFalse(hasattr(core, 'ssh_args'))
        self.assertFalse(hasattr(core, 'remote_projects'))
        self.assertFalse(hasattr(core, 'open_application'))
        self.assertFalse(hasattr(client, 'remote_request'))
        self.assertFalse(hasattr(client, 'remote_project_path'))

    def test_templates_and_existing_data_preserved(self):
        for index, kind in enumerate(policy.PROJECT_TYPES):
            name = 'project_' + str(index)
            client.request(self.config, name, 'create', template=kind)
            with self.assertRaises(FileExistsError):
                client.request(self.config, name, 'create', template=kind)
        target = self.base / 'project_0/GAME.md'
        target.write_text('My existing document')
        client.request(self.config, 'project_0', 'ensure_docs')
        self.assertEqual(target.read_text(), 'My existing document')

    def test_symlink_workspace_and_project_rejected(self):
        self.base.symlink_to(Path(self.temp.name), target_is_directory=True)
        with self.assertRaises(OSError):
            self.create()
        self.assertFalse((Path(self.temp.name) / 'game').exists())

    def test_traversal_and_unsupported_operations_rejected(self):
        for name in ('../escape', '/escape', 'a/b'):
            with self.assertRaises(ValueError):
                client.request(self.config, name, 'create')
        with self.assertRaises(ValueError):
            client.request(self.config, 'game', 'desktop')

    def test_asset_conflicts_still_require_review(self):
        self.create()
        args = dict(category='Sprites', name='sprite.png', data=base64.b64encode(b'image').decode(), expected=None)
        client.request(self.config, 'game', 'put_asset', **args)
        with self.assertRaises((ValueError, FileExistsError)):
            client.request(self.config, 'game', 'put_asset', **args)

    def test_native_discovery_and_godot_argv(self):
        self.create()
        with patch('native_tools.shutil.which', return_value='/usr/bin/godot'):
            args, cwd = native.command(self.config, 'godot', 'game')
        self.assertEqual(args, ['/usr/bin/godot', '--editor', '--path', str(self.base / 'game')])
        self.assertEqual(cwd, self.base / 'game')
        with patch('native_tools.shutil.which', return_value=None), patch('native_tools.Path.home', return_value=Path(self.temp.name)), patch('native_tools.tool_roots', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'Install Blender locally'):
                native.discover(self.config, 'blender')
        with self.assertRaises(ValueError):
            native.discover(dict(self.config, blender_path='blender --python dangerous'), 'blender')

    def test_adapter_launches_have_no_shell_or_remote_dependency(self):
        self.create()
        for tool in ('blender', 'blockbench', 'lmms', 'krita'):
            with patch('native_tools.discover', return_value='/native/' + tool), patch('native_tools.subprocess.Popen') as spawn:
                native.launch(self.config, tool, 'game')
                self.assertEqual(spawn.call_args.args[0], ['/native/' + tool])
                self.assertEqual(spawn.call_args.kwargs['cwd'], str(self.base / 'game'))
                self.assertNotIn('shell', spawn.call_args.kwargs)
        with patch('native_tools.discover', return_value='/native/godot'):
            self.assertEqual(native.command(self.config, 'godot', 'game')[0][1:], ['--editor', '--path', str(self.base / 'game')])

    def test_codex_is_local_project_aware_and_validates_resume(self):
        self.create()
        identifier = '12345678-1234-1234-1234-123456789abc'
        with patch('native_tools.discover', return_value='/local/codex'), patch('project_client.request', return_value={'sessions': [{'id': identifier, 'project': 'game'}]}):
            args, cwd = native.codex_command(self.config, 'resume', 'game', session_id=identifier)
            self.assertEqual(args, ['/local/codex', '--no-daemon', '-C', str(self.base / 'game'), 'resume', identifier])
            with self.assertRaises(ValueError):
                native.codex_command(self.config, 'resume', 'game', session_id='$(bad)')
            prompt = '--help\nReview $(touch /tmp/never) and `literal` text'
            args, cwd = native.codex_command(self.config, 'code', 'game', prompt=prompt)
            self.assertEqual(args[:4], ['/local/codex', '--no-daemon', '-C', str(self.base / 'game')])
            self.assertTrue(args[-1].endswith(prompt))
            self.assertIn('Project context from AI_MEMORY.md', args[-1])
            self.assertEqual(cwd, self.base / 'game')
            for invalid in ('', '   ', 'bad\0text', 'x' * 32001, 42):
                with self.assertRaises(ValueError):
                    native.codex_command(self.config, 'code', 'game', prompt=invalid)
            with self.assertRaises(ValueError):
                native.codex_command(self.config, 'resume', 'game', prompt='Review')

    def test_session_listing_passes_local_workspace_and_configuration(self):
        with patch('session_helper.list_codex_sessions', return_value={'sessions': []}) as listing:
            self.assertEqual(client.request(self.config, 'game', 'sessions'), {'sessions': []})
            self.assertEqual(listing.call_args.args, (self.base, 'game', {'_config': self.config}))

    def test_workspace_expands_home_and_rejects_relative_paths(self):
        with patch('pathlib.Path.home', return_value=Path(self.temp.name)):
            self.assertEqual(client.workspace({}), Path(self.temp.name) / 'StudioProjects')
        with self.assertRaises(ValueError):
            client.workspace({'projects_dir': 'relative'})


class LocalTerminal(unittest.TestCase):
    def test_custom_prompt_survives_terminal_wrapper_as_literal_argument(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {'projects_dir': directory}
            client.request(config, 'game', 'create')
            executable = Path(directory) / 'fake-codex'
            executable.write_text('#!/usr/bin/python3\n'
                                  'import json, os, pathlib, sys\n'
                                  'pathlib.Path(sys.argv[0] + ".args").write_text(json.dumps([sys.argv[1:], os.getcwd()]))\n')
            executable.chmod(0o755)
            config['codex_path'] = str(executable)
            sentinel = Path(directory) / 'must-not-exist'
            prompt = '--help\n$(touch ' + str(sentinel) + ') `exit 9` "quoted"'
            with patch('core.terminal_args', side_effect=lambda args: args):
                self.assertEqual(native.run_action(config, 'code', 'game', prompt=prompt), 'Codex conversation closed.')
            args, cwd = json.loads(Path(str(executable) + '.args').read_text())
            self.assertEqual(args[:4], ['--no-daemon', '-C', str(Path(directory) / 'game'), '--'])
            self.assertTrue(args[-1].endswith(prompt))
            self.assertIn('Project context from AI_MEMORY.md', args[-1])
            self.assertEqual(cwd, str(Path(directory) / 'game'))
            self.assertFalse(sentinel.exists())

    def test_cli_exit_status_survives_terminal_emulator(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {'projects_dir': directory}
            client.request(config, 'game', 'create')
            executable = Path(directory) / 'fake-codex'
            executable.write_text('#!/bin/sh\nexit 7\n')
            executable.chmod(0o755)
            config['codex_path'] = str(executable)
            with patch('core.terminal_args', side_effect=lambda args: args):
                with self.assertRaisesRegex(RuntimeError, 'exit 7'):
                    native.run_action(config, 'code', 'game')
            executable.write_text('#!/bin/sh\nexit 0\n')
            with patch('core.terminal_args', side_effect=lambda args: args):
                self.assertEqual(native.run_action(config, 'code', 'game'), 'Codex conversation closed.')
