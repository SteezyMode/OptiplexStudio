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

CONFIG = {'host': '100.100.100.101', 'user': 'artist'}
A = '12345678-1234-1234-1234-123456789012'
B = '12345678-1234-1234-1234-123456789013'
C = '12345678-1234-1234-1234-123456789014'

class Templates(unittest.TestCase):
    def test_all_templates_and_legacy_projects_no_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for index, kind in enumerate(helper.PROJECT_TYPES):
                name = 'project-' + str(index)
                helper.create_project(base, name, kind)
                project = helper.Project(base, name)
                try:
                    self.assertEqual(project.kind, kind)
                    self.assertEqual((base / name / 'project.godot').exists(), kind == 'Godot')
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
            (base / 'project-1/studio-project.json').unlink()  # Existing Godot has no manifest.
            (base / 'unrelated').mkdir()
            (base / 'linked').symlink_to(base / 'project-1', target_is_directory=True)
            result = helper.handle({'version': 1, 'operation': 'list_projects', 'project': 'Studio'}, base)
            self.assertEqual(len(result), 5)
            self.assertEqual(next(p['type'] for p in result if p['name'] == 'project-1'), 'Godot')
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
            rows = [dict(id=A, name='Alpha', cwd=str(base/'one'), updatedAt=20, createdAt=1),
                    dict(id=B, preview='Beta', cwd=str(base/'one'), updatedAt=30, createdAt=2),
                    dict(id=C, name='Other project', cwd=str(base/'two'), updatedAt=10, createdAt=3),
                    dict(id='invalid; shell', cwd=str(base/'one'))]
            cli = self.fixture(home, rows)
            with patch('pathlib.Path.home', return_value=home):
                result = list_codex_sessions(base, 'one', {})
                self.assertEqual([r['id'] for r in result['sessions']], [A,B])
                params = json.loads(Path(str(cli)+'.request').read_text())
                self.assertEqual(params['cwd'], str(base/'one'))
                self.assertTrue(params['useStateDbOnly'])
                self.assertEqual(result['nextCursor'], 'page-two')
                all_rows = list_codex_sessions(base, 'one', {'all_projects':True,'cursor':'page-two'})['sessions']
                self.assertEqual({r['project'] for r in all_rows}, {'one','two'})
                self.assertNotIn('cwd', json.loads(Path(str(cli)+'.request').read_text()))
                self.assertEqual([r['id'] for r in session_rows(all_rows,sort='Recent')], [B,A,C])
                self.assertEqual([r['id'] for r in session_rows(all_rows,sort='Oldest')], [A,B,C])
                self.assertEqual([r['id'] for r in session_rows(all_rows,'Beta', 'Name')], [B])
                self.assertEqual([r['id'] for r in session_rows(all_rows,'two')], [C])

    def test_unsupported_cli_metadata_is_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.fixture(home, [], error=True)
            with patch('pathlib.Path.home', return_value=home):
                with self.assertRaisesRegex(RuntimeError, 'Unsupported method'):
                    list_codex_sessions(home, 'one', {})

    def test_resume_uuid_and_prompt_command_construction(self):
        def terminal(command):
            captured.extend(command)
            Path(command[4]).write_text('0')
            return ['terminal']
        for kwargs, expected in [({'session_id':A}, ['resume',A]), ({'all_sessions':True},['resume','--all'])]:
            captured=[]
            process=MagicMock()
            process.__enter__.return_value.communicate.return_value=('', '')
            with patch('core.terminal_args', side_effect=terminal), patch('core.subprocess.Popen', return_value=process):
                core.run_action(CONFIG,'resume','one',**kwargs)
            remote=shlex.split(captured[-1])
            self.assertEqual(remote[-2:],expected)
            self.assertEqual(remote[2],'/home/artist/StudioProjects/Godot/one')
        with patch('core.subprocess.Popen') as spawn:
            with self.assertRaises(ValueError): core.run_action(CONFIG,'resume','one',session_id='bad;command')
            with self.assertRaises(ValueError): core.run_action(CONFIG,'code','one',prompt='arbitrary')
            spawn.assert_not_called()
        captured=[]
        with patch('core.terminal_args', side_effect=terminal), patch('core.subprocess.Popen', return_value=process):
            core.run_action(CONFIG,'code','one',prompt=core.CODEX_TASKS['Explain Project'])
        self.assertEqual(shlex.split(captured[-1])[-1], core.CODEX_TASKS['Explain Project'])

    def test_helper_source_contains_supported_session_listing(self):
        original = Path.read_text
        def read(path, *args, **kwargs):
            if path.name == 'project_helper.py':
                return "import json,sys\njson.load(sys.stdin)\nprint(json.dumps({'ok': True, 'result': {'available': callable(list_codex_sessions)}}))"
            return original(path, *args, **kwargs)
        with patch('core.ssh_args', return_value=['/bin/sh','-c','replaced']), patch('project_client.Path.read_text', new=read):
            result = project_client.request(CONFIG,'one','sessions')
        self.assertTrue(result['available'])

class Routing(unittest.TestCase):
    def test_contextual_action_and_real_session_id_keep_project_working_directory(self):
        from test_projects import GUIActions
        import app
        for action, kwargs in [('code', {'prompt': core.CODEX_TASKS['Review Changes']}),
                               ('resume', {'session_id': A})]:
            fake = GUIActions().fake()
            with patch('app.project_client.request', return_value={}) as request, patch('app.core.run_action', return_value='done') as run:
                app.Studio.action(fake, action, 'game', **kwargs)
            request.assert_called_once_with(fake.config, 'game', 'ensure_docs')
            self.assertEqual(run.call_args.args[:3], (fake.config, action, 'game'))
            for key, value in kwargs.items():
                self.assertEqual(run.call_args.kwargs[key], value)

    def test_godot_disabled_for_other_media_and_no_project_actions(self):
        from test_projects import GUIActions
        from test_network import Widget
        import app
        fake = GUIActions().fake()
        fake.rows = [{'name':'game','type':'Music/Audio'}]
        fake.project_buttons, fake.godot_buttons, fake.connection_buttons = [Widget()], [Widget()], [Widget()]
        fake.detail, fake.active_label = Widget(), Widget()
        app.Studio.selection_changed(fake,None)
        self.assertTrue(fake.project_buttons[0].sensitive)
        self.assertFalse(fake.godot_buttons[0].sensitive)
        with patch('app.core.run_action') as run:
            app.Studio.action(fake,'edit','game')
            run.assert_not_called()
        self.assertIn('Godot project', fake.status.text)
        fake.combo.get_active_id.return_value = None
        app.Studio.selection_changed(fake,None)
        self.assertFalse(fake.project_buttons[0].sensitive)
        self.assertFalse(fake.godot_buttons[0].sensitive)
        self.assertTrue(fake.connection_buttons[0].sensitive)
        fake.config = {'host': '', 'user': 'artist'}
        app.Studio.selection_changed(fake, None)
        self.assertFalse(fake.connection_buttons[0].sensitive)
        self.assertFalse(fake.create_button.sensitive)

    def test_independent_creative_tool_streams_before_helper(self):
        from test_projects import GUIActions
        from project_ui import ProjectUI
        fake = GUIActions().fake()
        fake.combo.get_active_id.return_value = None
        calls=[]
        fake.project_task = lambda task, done, message: done(task(lambda *args: None))
        with patch('project_ui.core.launch_studio_desktop',side_effect=lambda *args,**kw: calls.append('stream') or 'Streaming'), patch('project_ui.core.wait_for_studio_desktop',side_effect=lambda *args,**kw: calls.append('ready')), patch('project_ui.client.request',side_effect=lambda *args,**kw: calls.append((args[1], kw['application'])) or {'message':'Opened'}):
            ProjectUI.open_desktop_application(fake,'krita')
        self.assertEqual(calls,['stream','ready',('__desktop__','krita')])

class Packaging(unittest.TestCase):
    def test_missing_approved_icons_fail_before_build(self):
        import shutil
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            fixture=Path(directory)
            (fixture/'studio').mkdir()
            (fixture/'assets').mkdir()
            shutil.copy2(root/'studio/package.py', fixture/'studio/package.py')
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
            (fixture/'assets/optiplex-studio.png').write_bytes(icon.read_bytes()[:24])
            result=subprocess.run(['/usr/bin/python3','-B',str(fixture/'studio/package.py')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('could not be decoded',result.stderr)
            self.assertFalse((fixture/'build').exists())
