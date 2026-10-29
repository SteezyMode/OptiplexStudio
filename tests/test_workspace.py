import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import core
import project_helper as helper
import project_client
from session_helper import list_codex_sessions
from session_ui import session_rows

CONFIG = {}
A = '12345678-1234-1234-1234-123456789012'
B = '12345678-1234-1234-1234-123456789013'
C = '12345678-1234-1234-1234-123456789014'

class Templates(unittest.TestCase):
    def test_unified_project_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for index, kind in enumerate(helper.PROJECT_TYPES):
                name = 'project-' + str(index)
                helper.create_project(base, name, kind)
                project = helper.Project(base, name)
                try:
                    self.assertEqual(project.kind, kind)
                    self.assertEqual((base / name / 'project.godot').exists(), kind == 'Studio')
                    self.assertEqual(project.metadata()['type'], kind)
                    self.assertTrue(all((base / name / doc).is_file() for doc in helper.DOCS))
                    original = project.read('GAME.md', helper.MAX_TEXT)
                    self.assertEqual(project.ensure_docs(), [])
                    self.assertEqual(project.read('GAME.md', helper.MAX_TEXT), original)
                    project.write('docs/notes.md', b'# Uncommitted notes\n', None, helper.MAX_TEXT)
                    inventory = project.inventory()
                    eligible = {i['path']: i['sha256'] for i in inventory if i['sha256']}
                    snapshot = project.snapshot(eligible)
                    self.assertIn('docs/notes.md', [i['path'] for i in snapshot['files']])
                finally:
                    project.close()
            (base / 'project-0/project.godot').unlink()  # Missing engine files do not erase the Studio workspace.
            (base / 'unrelated').mkdir()
            (base / 'linked').symlink_to(base / 'project-0', target_is_directory=True)
            result = helper.handle({'version': 1, 'operation': 'list_projects', 'project': 'Studio'}, base)
            self.assertEqual(len(result), 1)
            self.assertEqual(next(p['type'] for p in result if p['name'] == 'project-0'), 'Studio')
            with self.assertRaisesRegex(ValueError, 'Unsupported project template'):
                helper.create_project(base, 'bad', '../escape')
            self.assertFalse((base / 'bad').exists())

class Sessions(unittest.TestCase):
    def fixture(self, root, rows, error=False):
        cli = root / '.local/bin/codex'
        cli.parent.mkdir(parents=True)
        cli.write_text('#!/usr/bin/python3\n' + '''import json,sys
for line in sys.stdin:
    request = json.loads(line)
    if request['method'] == 'initialize':
        print(json.dumps({'id':1,'result':{}}),flush=True)
    elif request['method'] == 'thread/list':
        with open(sys.argv[0] + '.request','w') as out: json.dump(request['params'],out)
        print(json.dumps(RESPONSE),flush=True)
'''.replace('RESPONSE', repr({'id': 2, 'error': {'message': 'Unsupported method'}} if error else {'id':2,'result':{'data':rows,'nextCursor':'page-two'}})))
        cli.chmod(0o755)
        return cli

    def test_real_stdio_protocol_scope_association_pagination_and_external_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            base = home / 'StudioProjects/Godot'
            base.mkdir(parents=True)
            helper.create_project(base, 'one', 'Studio')
            helper.create_project(base, 'two', 'Studio')
            rows = [dict(id=A, name='Alpha', cwd=str(base/'one'), updatedAt=20, createdAt=1),
                    dict(id=B, preview='Beta', cwd=str(base/'one'), updatedAt=30, createdAt=2),
                    dict(id=C, name='Other project', cwd=str(base/'two'), updatedAt=10, createdAt=3),
                    dict(id='invalid; shell', cwd=str(base/'one'))]
            cli = self.fixture(home, rows)
            with patch('pathlib.Path.home', return_value=home):
                result = list_codex_sessions(base, 'one', {'_config': {'codex_path': str(cli)}})
                self.assertEqual([r['id'] for r in result['sessions']], [A,B])
                params = json.loads(Path(str(cli)+'.request').read_text())
                self.assertNotIn('cwd', params)
                self.assertTrue(params['useStateDbOnly'])
                self.assertEqual(result['nextCursor'], 'page-two')
                all_rows = list_codex_sessions(base, 'one', {'all_projects':True,'cursor':'page-two', '_config': {'codex_path': str(cli)}})['sessions']
                self.assertEqual({r['project'] for r in all_rows}, {'one','two'})
                self.assertNotIn('cwd', json.loads(Path(str(cli)+'.request').read_text()))
                self.assertEqual([r['id'] for r in session_rows(all_rows,sort='Recent')], [B,A,C])
                self.assertEqual([r['id'] for r in session_rows(all_rows,sort='Oldest')], [A,B,C])
                self.assertEqual([r['id'] for r in session_rows(all_rows,'Beta', 'Name')], [B])
                self.assertEqual([r['id'] for r in session_rows(all_rows,'two')], [C])

    def test_unsupported_cli_metadata_is_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            cli = self.fixture(home, [], error=True)
            with patch('pathlib.Path.home', return_value=home):
                with self.assertRaisesRegex(RuntimeError, 'Unsupported method'):
                    list_codex_sessions(home, 'one', {'_config': {'codex_path': str(cli)}})

class Routing(unittest.TestCase):
    def test_contextual_action_and_real_session_id_keep_project_working_directory(self):
        from test_projects import GUIActions
        import app
        for action, kwargs in [('code', {'prompt': core.CODEX_TASKS['Review Changes']}),
                               ('code', {'prompt': 'Review this project\nPreserve existing work.'}),
                               ('resume', {'session_id': A})]:
            fake = GUIActions().fake()
            with patch('app.project_client.request', return_value={}) as request, patch('native_tools.run_action', return_value='done') as run:
                app.Studio.action(fake, action, 'game', **kwargs)
            request.assert_called_once_with(fake.config, 'game', 'ensure_docs')
            self.assertEqual(run.call_args.args[:3], (fake.config, action, 'game'))
            for key, value in kwargs.items():
                self.assertEqual(run.call_args.kwargs[key], value)

    def test_godot_disabled_for_other_media_and_no_project_actions(self):
        from test_projects import GUIActions
        from ui_fakes import Widget
        import app
        fake = GUIActions().fake()
        fake.rows = [{'name':'game','type':'Studio'}]
        fake.project_buttons, fake.godot_buttons = [Widget()], [Widget()]
        fake.detail, fake.active_label = Widget(), Widget()
        app.Studio.selection_changed(fake,None)
        self.assertTrue(fake.project_buttons[0].sensitive)
        self.assertTrue(fake.godot_buttons[0].sensitive)
        with patch('native_tools.run_action') as run:
            app.Studio.action(fake,'edit','game')
            run.assert_called_once()
        fake.combo.get_active_id.return_value = None
        app.Studio.selection_changed(fake,None)
        self.assertFalse(fake.project_buttons[0].sensitive)
        self.assertFalse(fake.godot_buttons[0].sensitive)
        fake.config = {'host': '', 'user': 'artist'}
        app.Studio.selection_changed(fake, None)
        self.assertTrue(fake.create_button.sensitive)

    def test_independent_creative_tool_launches_locally(self):
        from test_projects import GUIActions
        from project_ui import ProjectUI
        fake = GUIActions().fake()
        fake.combo.get_active_id.return_value = None
        fake.project_task = lambda task, done, message: done(task(lambda *args: None))
        with patch('native_tools.launch', return_value='Opened') as launch:
            ProjectUI.open_desktop_application(fake, 'krita')
        launch.assert_called_once_with(fake.config, 'krita', None)

class AIComposer(unittest.TestCase):
    def fake(self, text='Review the scene\nKeep existing assets.'):
        from types import SimpleNamespace
        import app
        buffer = MagicMock()
        buffer.get_bounds.return_value = (0, len(text))
        buffer.get_text.return_value = text
        fake = SimpleNamespace(ai_run=MagicMock(), ai_prompt=MagicMock(),
                               combo=MagicMock(), rows=[{'name': 'game'}], busy=False,
                               action=MagicMock(), open_embedded=MagicMock(), status=MagicMock())
        fake.ai_prompt.get_buffer.return_value = buffer
        fake.combo.get_active_id.return_value = 'game'
        return app, fake

    def test_run_sensitivity_tracks_prompt_project_and_busy_state(self):
        app, fake = self.fake()
        for text, project, busy, expected in [
            ('Review', 'game', False, True), ('Review', 'game', True, False),
            ('Review', None, False, False), ('Review', 'unknown', False, False),
            ('  \n', 'game', False, False), ('x' * 32001, 'game', False, False),
            ('bad\0text', 'game', False, False)]:
            fake.ai_prompt.get_buffer().get_text.return_value = text
            fake.combo.get_active_id.return_value = project
            fake.busy = busy
            app.Studio.update_ai_run(fake)
            fake.ai_run.set_sensitive.assert_called_with(expected)

    def test_run_preserves_multiline_text_and_rejects_invalid_input(self):
        app, fake = self.fake()
        app.Studio.run_ai_prompt(fake)
        fake.open_embedded.assert_called_once_with(prompt='Review the scene\nKeep existing assets.')
        for invalid in ('', '  ', 'x' * 32001, 'bad\0text'):
            fake.open_embedded.reset_mock()
            fake.ai_prompt.get_buffer().get_text.return_value = invalid
            app.Studio.run_ai_prompt(fake)
            fake.open_embedded.assert_not_called()
            fake.status.set_text.assert_called()

    def test_layout_keeps_presets_and_advanced_actions_separate(self):
        app, fake = self.fake()
        fake.project_buttons = []
        fake.label = MagicMock()
        fake.button = MagicMock()
        fake.session_browser = MagicMock()
        fake.copy_brief = MagicMock()
        fake.run_ai_prompt = MagicMock()
        fake.update_ai_run = MagicMock()
        grid = MagicMock()
        # Build without a display; live widget checks are in gui_workflows.py.
        with patch('app.Gtk.Box'), patch('app.Gtk.TextView'), patch('app.Gtk.ScrolledWindow'), patch('app.Gtk.Expander'), patch('app.Gtk.Menu'), patch('app.Gtk.MenuItem'), patch('app.Gtk.Button'):
            app.Studio.build_ai_workspace(fake, MagicMock(), grid)
        groups = [call.args[1] for call in grid.call_args_list]
        self.assertEqual([entry[0] for entry in groups[0]], ['New Conversation', 'Resume Conversation'])
        self.assertEqual([entry[0] for entry in groups[1]], ['Review Changes', 'Fix Godot Errors', 'Validate Project'])
        self.assertEqual([entry[2] for entry in groups[1]], ['project', 'godot', 'godot'])
        self.assertEqual(len(groups), 3)
        self.assertEqual([entry[0] for entry in groups[2]], ['Find Conversations', 'External Codex Terminal', 'Explain Project', 'Copy ChatGPT Brief'])
        for name, callback, _ in groups[1]:
            callback(None)
            fake.open_embedded.assert_called_with(prompt=core.CODEX_TASKS[name])
        groups[0][0][1](None)
        fake.open_embedded.assert_called_with()
        groups[0][1][1](None)
        fake.session_browser.assert_called_once_with(None)


class Packaging(unittest.TestCase):
    def test_missing_approved_icons_fail_before_build(self):
        import shutil
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            fixture=Path(directory)
            (fixture/'studio').mkdir()
            (fixture/'assets').mkdir()
            shutil.copy2(root/'studio/package.py', fixture/'studio/package.py')
            shutil.copy2(root/'studio/version.py', fixture/'studio/version.py')
            icon=root/'assets/optiplex-studio.png'
            if icon.exists():
                shutil.copy2(icon,fixture/'assets/optiplex-studio.png')
            result=subprocess.run(['/usr/bin/python3','-B',str(fixture/'studio/package.py')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Approved PNG required',result.stderr)
            self.assertNotIn('.svg',result.stderr)
            self.assertFalse((fixture/'build').exists())

    def test_truncated_png_is_rejected_before_staging(self):
        import shutil
        root=Path(__file__).resolve().parents[1]
        icon=root/'assets/optiplex-studio.png'
        if not icon.exists():
            self.skipTest('No approved application PNG supplied yet.')
        with tempfile.TemporaryDirectory() as directory:
            fixture=Path(directory)
            (fixture/'studio').mkdir()
            (fixture/'assets').mkdir()
            shutil.copy2(root/'studio/package.py',fixture/'studio/package.py')
            shutil.copy2(root/'studio/version.py',fixture/'studio/version.py')
            (fixture/'assets/optiplex-studio.png').write_bytes(icon.read_bytes()[:24])
            result=subprocess.run(['/usr/bin/python3','-B',str(fixture/'studio/package.py')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('could not be decoded',result.stderr)
            self.assertFalse((fixture/'build').exists())
