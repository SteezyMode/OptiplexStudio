"""Ownership boundaries and additive metadata preserve existing history."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import conversation_store as store
import project_helper as policy
import native_tools as native
import project_client as client

A = '12345678-1234-1234-1234-123456789abc'


class Conversations(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.config = {'projects_dir': str(self.base)}
        for name in ('one', 'two'):
            policy.create_project(self.base, name, 'Studio')

    def row(self, cwd):
        return {'id': A, 'cwd': str(cwd)}

    def test_association_survives_rename_without_touching_history(self):
        history = self.base / 'original.jsonl'
        history.write_bytes(b'original codex history\n')
        rows = store.associate(self.base, [self.row(self.base / 'one')])
        identity = rows[0]['project_id']
        (self.base / 'one').rename(self.base / 'renamed')
        rows = store.associate(self.base, [self.row(self.base / 'one')])
        self.assertEqual(rows[0]['project'], 'renamed')
        self.assertEqual(rows[0]['project_id'], identity)
        self.assertEqual(history.read_bytes(), b'original codex history\n')

    def test_uncertain_external_traversal_symlink_and_source_stay_unassigned(self):
        (self.base / 'source').mkdir()
        (self.base / 'source/README.md').write_text('Studio source')
        (self.base / 'one/link').symlink_to(self.base / 'two', target_is_directory=True)
        for cwd in (self.base / 'unknown', self.base / 'one/../two',
                    self.base / 'one/link', self.base / 'source', '/external', 'one'):
            self.assertIsNone(store.associate(self.base, [self.row(cwd)])[0]['project'])
        self.assertFalse((self.base / 'source/project.godot').exists())

    def test_conflicting_evidence_and_duplicate_identity_fail_closed(self):
        store.associate(self.base, [self.row(self.base / 'one')])
        self.assertIsNone(store.associate(self.base, [self.row(self.base / 'two')])[0]['project'])
        (self.base / 'two' / store.IDENTITY).write_bytes((self.base / 'one' / store.IDENTITY).read_bytes())
        self.assertIsNone(store.associate(self.base, [self.row(self.base / 'one')])[0]['project'])

    def test_resume_checks_owner_pagination_and_forbids_picker_bypass(self):
        with patch('project_client.request', side_effect=[{'sessions': [], 'nextCursor': 'next'},
                   {'sessions': [{'id': A, 'project': 'two'}]}]), patch('native_tools.discover') as discover:
            with self.assertRaisesRegex(ValueError, 'active Project'):
                native.codex_command(self.config, 'resume', 'one', session_id=A)
            discover.assert_not_called()
        for fields in ({}, {'all_sessions': True}, {'session_id': A, 'all_sessions': True}):
            with self.assertRaises(ValueError):
                native.codex_command(self.config, 'resume', 'one', **fields)
        with patch('project_client.request', side_effect=RuntimeError('metadata unavailable')):
            with self.assertRaises(RuntimeError):
                native.codex_command(self.config, 'resume', 'one', session_id=A)

    def test_ui_rejects_explicit_cross_project_launch(self):
        import app
        fake = SimpleNamespace(busy=False, combo=MagicMock(), status=MagicMock(),
                               rows=[{'name': 'one'}, {'name': 'two'}], worker=MagicMock())
        fake.combo.get_active_id.return_value = 'one'
        for action in ('code', 'resume'):
            app.Studio.action(fake, action, name='two', session_id=A if action == 'resume' else None)
            fake.worker.assert_not_called()
            self.assertIn('owning Project', fake.status.set_text.call_args.args[0])

    def test_memory_edit_conflict_and_new_task_context(self):
        docs = client.request(self.config, 'one', 'docs')
        original = docs['AI_MEMORY.md']
        client.request(self.config, 'one', 'save_doc', name='AI_MEMORY.md', text='Use blue.', expected=original['sha256'])
        with self.assertRaisesRegex(ValueError, 'conflict'):
            client.request(self.config, 'one', 'save_doc', name='AI_MEMORY.md', text='stale', expected=original['sha256'])
        with patch('native_tools.discover', return_value='/codex'):
            args, _ = native.codex_command(self.config, 'code', 'one', prompt='Build')
        self.assertIn('--no-daemon', args)
        self.assertIn('Use blue.', args[-1])
        self.assertTrue(args[-1].endswith('Task:\nBuild'))
        self.assertNotIn('Use blue.', (self.base / 'two/AI_MEMORY.md').read_text())
