import base64
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import project_helper as helper
import project_client as client

CONFIG = {}

class Projects(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name) / 'Godot'
        self.base.mkdir()
        helper.create_project(self.base, 'game')
        self.root = self.base / 'game'

    def call(self, operation, **fields):
        return helper.handle(dict(fields, project='game', version=1, operation=operation), self.base)

    def transport(self, config, project, operation, progress=None, **fields):
        self.assertEqual(project, 'game')
        if progress:
            progress(1)
        return self.call(operation, **fields)

    def put(self, name, data, expected=None, category='Sprites'):
        return self.call('put_asset', category=category, name=name, expected=expected, data=base64.b64encode(data).decode())

    def git(self, *args):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@localhost', '-C', str(self.root), *args], capture_output=True, text=True, check=True).stdout

    def test_create_documents_and_no_automatic_commit(self):
        for name in helper.DOCS:
            self.assertTrue((self.root / name).is_file())
        self.assertIn('Do not commit', (self.root / 'AGENTS.md').read_text())
        guidance = (self.root / 'AGENTS.md').read_text()
        self.assertIn('do not request broader system access', guidance)
        self.assertNotIn('Docker', guidance)
        if not shutil.which('git'):
            self.assertIn('Git initialization failed', helper.create_project(self.base, 'no_git')['warning'])
            return
        self.assertTrue((self.root / '.git').is_dir())
        self.assertEqual(self.git('status', '--porcelain')[:2], '??')
        with self.assertRaises(FileExistsError):
            helper.create_project(self.base, 'game')

    def test_missing_documents_do_not_replace_existing(self):
        (self.root / 'GAME.md').write_text('My actual concept')
        (self.root / 'PROGRESS.md').unlink()
        result = self.call('ensure_docs')
        self.assertEqual(result['created'], ['PROGRESS.md'])
        self.assertEqual((self.root / 'GAME.md').read_text(), 'My actual concept')
        self.assertEqual(self.call('ensure_docs')['created'], [])

    def test_document_save_checks_hash_and_name(self):
        docs = self.call('docs')
        self.call('save_doc', name='GAME.md', text='Updated game concept', expected=docs['GAME.md']['sha256'])
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.call('save_doc', name='GAME.md', text='Stale contents', expected=docs['GAME.md']['sha256'])
        with self.assertRaises(ValueError):
            self.call('save_doc', name='../other.md', text='bad')

    def test_import_conflicts_and_atomic_replacement(self):
        first = self.put('hero.png', b'first')['sha256']
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.put('hero.png', b'overwrite')
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.put('hero.png', b'overwrite', expected='0' * 64)
        self.put('hero.png', b'updated', expected=first)
        self.assertEqual((self.root / 'assets/sprites/hero.png').read_bytes(), b'updated')
        self.assertEqual(list((self.root / 'assets/sprites').glob('.studio-*')), [])

    def test_paths_categories_and_symlinks_are_rejected(self):
        for name in ('../escape.png', '/tmp/escape.png', 'foo/bar.png', 'foo\\bar.png', '.env', 'secret.png', 'run.sh'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.put(name, b'bad')
        with self.assertRaises(ValueError):
            self.put('okay.png', b'bad', category='../escape')
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (self.root / 'assets/sprites').rmdir()
        (self.root / 'assets/sprites').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            self.put('escape.png', b'bad')
        self.assertEqual(list(outside.iterdir()), [])
        (self.base / 'alias').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError):
            helper.Project(self.base, 'alias')

    def test_hard_links_and_file_symlinks_are_not_read_or_overwritten(self):
        target = Path(self.temp.name) / 'external.gd'
        target.write_text('private external contents')
        (self.root / 'linked.gd').symlink_to(target)
        os.link(target, self.root / 'hard.gd')
        inventory = self.call('inventory')['inventory']
        self.assertNotIn('linked.gd', {p['path'] for p in inventory})
        self.assertNotIn('hard.gd', {p['path'] for p in inventory})
        with self.assertRaises(ValueError):
            project = helper.Project(self.base, 'game')
            try: project.read('hard.gd', 1024)
            finally: project.close()

    def test_inventory_exclusions_and_size_limits(self):
        for path, content in {'.env': 'API_KEY=private', '.godot/cache.gd': 'cache', 'build/binary.gd': 'compiled',
                              'credentials/auth.json': '{"token":"private"}', 'data/service.json': '{"api_key":"private-key-value"}',
                              'personal.txt': 'unrelated', 'assets/audio/music/theme.ogg': 'audio', 'scripts/player.gd': 'extends Node'}.items():
            file = self.root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content)
        (self.root / 'scripts/huge.gd').write_bytes(b'x' * (helper.MAX_TEXT + 1))
        items = {p['path']: p for p in self.call('inventory')['inventory']}
        for path in ('.env', '.godot/cache.gd', 'build/binary.gd', 'credentials/auth.json', 'personal.txt'):
            self.assertNotIn(path, items)
        self.assertIsNone(items['data/service.json']['sha256'])
        self.assertIsNone(items['scripts/huge.gd']['sha256'])
        self.assertIsNone(items['assets/audio/music/theme.ogg']['sha256'])
        self.assertTrue(items['scripts/player.gd']['sha256'])

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_snapshot_has_working_tree_staged_untracked_and_git_diff(self):
        script = self.root / 'scripts/player.gd'
        script.write_text('extends Node\nvar speed = 1\n')
        self.git('add', '.')
        self.git('commit', '--no-gpg-sign', '-m', 'Fixture baseline')
        script.write_text('extends Node\nvar speed = 2\n')
        self.git('add', 'scripts/player.gd')
        script.write_text('extends Node\nvar speed = 3\n')
        (self.root / 'scripts/new.gd').write_text('extends Node\n# Untracked work\n')
        manifest = self.call('inventory')
        selection = {p['path']: p['sha256'] for p in manifest['inventory'] if p['sha256']}
        snapshot = self.call('snapshot', selections=selection)
        self.assertTrue(snapshot['metadata']['dirty'])
        self.assertEqual(snapshot['metadata']['branch'], 'main')
        self.assertIn('Fixture baseline', snapshot['metadata']['commit'])
        files = {p['path']: base64.b64decode(p['data']) for p in snapshot['files']}
        self.assertIn(b'speed = 3', files['scripts/player.gd'])
        self.assertIn('scripts/new.gd', files)
        self.assertIn('-var speed = 1', snapshot['diff'])
        self.assertIn('+var speed = 3', snapshot['diff'])

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_sensitive_deleted_lines_not_leaked_in_diff(self):
        path = self.root / 'scripts/legacy.gd'
        path.write_text('extends Node\n# api_key = "very-private-key-value"\n')
        self.git('add', '.')
        self.git('commit', '--no-gpg-sign', '-m', 'Fixture baseline')
        path.write_text('extends Node\n')
        snapshot = self.call('snapshot', selections={'scripts/legacy.gd': helper.digest(path.read_bytes())})
        self.assertNotIn('very-private-key-value', snapshot['diff'])
        self.assertIn('omitted', snapshot['diff'])

    def test_snapshot_stale_selection_and_total_limit(self):
        manifest = self.call('inventory')
        old = next(p for p in manifest['inventory'] if p['path'] == 'GAME.md')['sha256']
        (self.root / 'GAME.md').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.call('snapshot', selections={'GAME.md': old})
        with patch.object(helper, 'MAX_SNAPSHOT', 1):
            with self.assertRaisesRegex(ValueError, 'snapshot limit'):
                self.call('snapshot', selections={'GAME.md': helper.digest(b'changed')})

    def test_client_import_transfer_progress_and_confirmation(self):
        local = Path(self.temp.name) / 'hero.png'
        local.write_bytes(b'exported sprite')
        updates = []
        with patch('project_client.request', side_effect=self.transport):
            plan = client.plan_import(CONFIG, 'game', [str(local)], 'Sprites')
            self.assertIn('Imported 1', client.import_assets(CONFIG, 'game', plan, 'Sprites', progress=lambda *args: updates.append(args)))
            plan = client.plan_import(CONFIG, 'game', [str(local)], 'Sprites')
            with self.assertRaisesRegex(ValueError, 'confirmation'):
                client.import_assets(CONFIG, 'game', plan, 'Sprites')
            local.write_bytes(b'changed sprite!')
            # Same size is fine; the target conflict remains bound to the checked hash.
            client.import_assets(CONFIG, 'game', plan, 'Sprites', overwrite=True)
        self.assertEqual(updates[-1][0], 1)

    def test_client_duplicate_names_and_oversized_imports(self):
        file = Path(self.temp.name) / 'asset.png'
        file.touch()
        with self.assertRaisesRegex(ValueError, 'same filename'):
            client.plan_import(CONFIG, 'game', [str(file), str(file)], 'Sprites')
        with file.open('wb') as out:
            out.truncate(helper.MAX_ASSET + 1)
        with self.assertRaisesRegex(ValueError, 'Import limit'):
            client.plan_import(CONFIG, 'game', [str(file)], 'Sprites')

    def test_client_zip_contains_only_reviewed_current_files(self):
        (self.root / 'scripts/player.gd').write_text('extends Node\n')
        manifest = self.call('inventory')
        destination = Path(self.temp.name) / 'context.zip'
        with patch('project_client.request', side_effect=self.transport):
            result = client.export_snapshot(CONFIG, 'game', manifest, ['GAME.md', 'scripts/player.gd'], destination)
        with zipfile.ZipFile(destination) as archive:
            self.assertEqual(set(archive.namelist()), {'OVERVIEW.md', 'CHATGPT-BRIEF.md', 'CHANGES.diff', 'game/GAME.md', 'game/scripts/player.gd'})
            self.assertEqual(archive.read('game/scripts/player.gd'), b'extends Node\n')
            self.assertIn(b'CURRENT', archive.read('OVERVIEW.md'))
        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
        self.assertIn('game', client.brief(result))
        self.assertIn('not assume', client.brief(result))

    def test_client_zip_rejects_unreviewed_and_tampered_paths(self):
        manifest = self.call('inventory')
        destination = Path(self.temp.name) / 'bad.zip'
        with self.assertRaises(ValueError):
            client.export_snapshot(CONFIG, 'game', manifest, ['../secret'], destination)
        snapshot = self.call('snapshot', selections={'GAME.md': helper.digest((self.root / 'GAME.md').read_bytes())})
        snapshot['files'][0]['path'] = '../escape.md'
        with patch('project_client.request', return_value=snapshot):
            with self.assertRaises(ValueError):
                client.export_snapshot(CONFIG, 'game', manifest, ['GAME.md'], destination)
        self.assertFalse(destination.exists())

    def test_local_protocol_and_file_uri(self):
        config = dict(CONFIG, projects_dir=str(self.base))
        result = client.request(config, 'game', 'docs')
        self.assertIn('GAME.md', result)
        self.assertEqual(client.asset_uri(config, 'game'), (self.root / 'assets').as_uri())
        with self.assertRaises(ValueError):
            client.asset_uri(config, '../other')

class GUIActions(unittest.TestCase):
    def fake(self):
        from project_ui import ProjectUI
        from ui_fakes import Widget
        class Fake(ProjectUI):
            config = dict(CONFIG)
            busy = False
            rows = [{'name': 'game'}]
            status, create_button = Widget(), Widget()
            combo = MagicMock()
            window = None
            def selection_changed(self, _): pass
            def notice(self, *args): self.last_notice = args
            def worker(self, task, done):
                try: result = task()
                except Exception as exc: done(None, str(exc))
                else: done(result, None)
        result = Fake()
        result.combo.get_active_id.return_value = 'game'
        return result

    def test_share_opens_review_and_never_auto_exports(self):
        fake = self.fake()
        fake.review_snapshot = MagicMock()
        manifest = {'metadata': {'project': 'game'}, 'inventory': []}
        with patch('project_ui.client.request', return_value=manifest) as request, patch('project_ui.GLib.idle_add'), patch('project_ui.client.export_snapshot') as export:
            fake.share_context()
            request.assert_called_once_with(CONFIG, 'game', 'inventory')
            fake.review_snapshot.assert_called_once_with(CONFIG, 'game', manifest)
            export.assert_not_called()
        self.assertFalse(fake.busy)
        self.assertTrue(fake.create_button.sensitive)

    def test_no_project_blocks_file_operations(self):
        fake = self.fake()
        fake.combo.get_active_id.return_value = None
        with patch('project_ui.client.request') as request:
            for method in (fake.share_context, fake.import_assets, fake.browse_assets, fake.documents):
                method()
            request.assert_not_called()
        self.assertIn('Select a project', fake.status.text)

    def test_project_errors_are_visible_and_controls_restored(self):
        fake = self.fake()
        with patch('project_ui.client.request', side_effect=RuntimeError('Local workspace failure')), patch('project_ui.GLib.idle_add'):
            fake.share_context()
        self.assertIn('Local workspace failure', fake.status.text)
        self.assertEqual(fake.last_notice[0], 'Project operation failed')
        self.assertFalse(fake.busy)

    def test_persist_selection_separately_from_settings(self):
        import project_ui
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, XDG_CONFIG_HOME=folder):
            project_ui.remember_project('game')
            self.assertEqual(project_ui.remembered_project(), 'game')
            self.assertFalse((Path(folder) / 'optiplex-studio/config.json').exists())
            with self.assertRaises(ValueError):
                project_ui.remember_project('../other')

class MoreGUIActions(unittest.TestCase):
    def test_native_import_picker_conflict_requires_gui_confirmation(self):
        from project_ui import ProjectUI
        from gi.repository import Gtk
        fake = GUIActions().fake()
        fake.label = MagicMock()
        fake.confirm = MagicMock(return_value=False)
        picker, dialog, choice = MagicMock(), MagicMock(), MagicMock()
        picker.run.return_value = Gtk.ResponseType.OK
        picker.get_filenames.return_value = ['/tmp/sprite.png']
        dialog.run.return_value = Gtk.ResponseType.OK
        choice.get_active_id.return_value = 'Sprites'
        plan = [{'name': 'sprite.png', 'expected': 'previous-hash'}]
        with patch('project_ui.Gtk.FileChooserDialog', return_value=picker), patch('project_ui.Gtk.Dialog', return_value=dialog), patch('project_ui.Gtk.ComboBoxText', return_value=choice), patch('project_ui.client.plan_import', return_value=plan), patch('project_ui.client.import_assets') as transfer, patch('project_ui.GLib.idle_add'):
            fake.import_assets()
            picker.set_select_multiple.assert_called_once_with(True)
            fake.confirm.assert_called_once()
            transfer.assert_not_called()
            self.assertIn('cancelled', fake.status.text)

    def test_document_editor_load_is_scoped_to_active_project(self):
        from gi.repository import Gtk
        fake = GUIActions().fake()
        fake.label = MagicMock()
        fake.edit_document = MagicMock()
        dialog, choice = MagicMock(), MagicMock()
        dialog.run.return_value = 2
        choice.get_active_text.return_value = 'GAME.md'
        current = {'text': '# Actual game', 'sha256': 'hash'}
        with patch('project_ui.Gtk.Dialog', return_value=dialog), patch('project_ui.Gtk.ComboBoxText', return_value=choice), patch('project_ui.client.request', return_value={'GAME.md': current}) as request, patch('project_ui.GLib.idle_add'):
            fake.documents()
            request.assert_called_once_with(CONFIG, 'game', 'docs')
            fake.edit_document.assert_called_once_with(CONFIG, 'game', 'GAME.md', current)

class SnapshotDeletions(unittest.TestCase):
    setUp = Projects.setUp
    call = Projects.call
    git = Projects.git
    transport = Projects.transport

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_reviewed_deleted_file_is_in_diff_but_not_attached(self):
        path = self.root / 'scripts/removed.gd'
        path.write_text('extends Node\n# old game logic\n')
        self.git('add', '.')
        self.git('commit', '--no-gpg-sign', '-m', 'Fixture baseline')
        path.unlink()
        manifest = self.call('inventory')
        entry = next(row for row in manifest['inventory'] if row['path'] == 'scripts/removed.gd')
        self.assertTrue(entry['deleted'])
        destination = Path(self.temp.name) / 'deleted.zip'
        with patch('project_client.request', side_effect=self.transport):
            client.export_snapshot(CONFIG, 'game', manifest, ['scripts/removed.gd'], destination)
        with zipfile.ZipFile(destination) as archive:
            self.assertNotIn('game/scripts/removed.gd', archive.namelist())
            self.assertIn(b'deleted file', archive.read('CHANGES.diff'))
            self.assertIn(b'old game logic', archive.read('CHANGES.diff'))

class CodexConcurrency(unittest.TestCase):
    def test_terminal_exit_does_not_clear_another_project_operation(self):
        import app
        fake = GUIActions().fake()
        from ui_fakes import Widget
        fake.codex_status = Widget()
        def conversation(config, action, name, **callbacks):
            callbacks['on_started']()
            self.assertFalse(fake.busy)
            # Another project operation starts while the conversation remains open.
            fake.busy = True
            fake.create_button.set_sensitive(False)
            fake.status.set_text('Import in progress')
            return 'Codex conversation closed.'
        with patch('app.project_client.request', return_value={}), patch('native_tools.run_action', side_effect=conversation), patch('app.GLib.idle_add', side_effect=lambda function, *args: function(*args)):
            app.Studio.action(fake, 'code', 'game')
        self.assertTrue(fake.busy)
        self.assertFalse(fake.create_button.sensitive)
        self.assertEqual(fake.status.text, 'Import in progress')
        self.assertIn('closed', fake.codex_status.text)
