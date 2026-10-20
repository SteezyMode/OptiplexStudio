"""App Server protocol fixtures and fail-closed Project lifecycle tests."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
from codex_rpc import AppServer
from embedded_codex import Conversation
import project_helper as policy
import conversation_store as store

FIXTURE = Path(__file__).parent / 'fixtures/codex/server.py'
A = '12345678-1234-1234-1234-123456789abc'


class Protocol(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.signal = threading.Event()
        def event(method, params):
            self.events.append((method, params))
            self.signal.set()
        self.server = AppServer(str(FIXTURE), '/tmp', event)
        self.addCleanup(self.server.close)

    def test_handshake_and_multiple_requests(self):
        for method in ('initialize', 'thread/start', 'turn/start', 'turn/interrupt'):
            self.assertEqual(self.server.request(method, {'test': method}), {'echo': {'test': method}})

    def test_approval_requires_explicit_decision(self):
        self.server.request('fixture/approval', {})
        self.assertTrue(self.signal.wait(2))
        self.assertIn('approval-1', self.server.approvals)
        with patch.object(self.server, 'write') as write:
            self.server.decide('approval-1', False)
            self.assertEqual(write.call_args.args[0]['result'], {'decision': 'decline'})
            with self.assertRaises(ValueError):
                self.server.decide('approval-1', True)

    def test_duplicate_approval_before_and_after_decision(self):
        message = {'id': 42, 'method': 'item/commandExecution/requestApproval', 'params': {}}
        self.server._message(message)
        self.server._message(message)
        self.server.decide(42, False)
        self.server._message(message)
        self.assertEqual([e for e in self.events if e[0] == 'approval'], [('approval', message)])
        self.assertNotIn(42, self.server.approvals)

    def test_unknown_request_is_rejected(self):
        with patch.object(self.server, 'write') as write:
            self.server._message({'id': 'x', 'method': 'item/tool/call', 'params': {}})
            self.assertEqual(write.call_args.args[0]['error']['code'], -32601)

    def test_protocol_error_releases_waiter(self):
        with self.assertRaises(RuntimeError):
            self.server.request('fixture/malformed', {})
        self.assertTrue(self.server.closed)

    def test_disconnect_releases_waiter_and_invalidates_approval(self):
        self.server.approvals.add('old')
        with self.assertRaises(RuntimeError):
            self.server.request('fixture/disconnect', {})
        self.assertFalse(self.server.approvals)

    def test_startup_failure(self):
        with self.assertRaises(OSError):
            AppServer('/missing/studio-codex', '/tmp', lambda *_: None)


class Isolation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.config = {'projects_dir': str(self.base)}
        for name in ('one', 'two'):
            policy.create_project(self.base, name, 'Studio')
        self.events = []
        self.conversation = Conversation(self.config, 'one', lambda *event: self.events.append(event))
        self.server = MagicMock()
        self.server.request.side_effect = lambda method, params: ({'cwd': str(self.base / 'one'),
                                        'approvalPolicy': 'on-request', 'approvalsReviewer': 'user',
                                        'sandbox': self.conversation.sandbox_policy(), 'thread': {'id': A, 'cwd': str(self.base / 'one'), 'turns': []}}
                                        if method.startswith('thread/') else
                                        {'exitCode': 0, 'stdout': 'studio-isolated\n'} if method == 'command/exec' else {})

    def test_new_thread_is_persistent_safe_and_associated(self):
        memory = 'Use project one memory.'
        (self.base / 'one/AI_MEMORY.md').write_text(memory)
        with patch('embedded_codex.AppServer', return_value=self.server), patch('native_tools.discover', return_value='/codex'):
            self.conversation.connect()
        calls = self.server.request.call_args_list
        params = next(c.args[1] for c in calls if c.args[0] == 'thread/start')
        self.assertFalse(params['ephemeral'])
        self.assertFalse(params['config']['allow_login_shell'])
        self.assertIn('studio-tool-path-', params['config']['shell_environment_policy']['set']['PATH'])
        self.assertEqual(params['config']['sandbox_workspace_write']['writable_roots'], [str(self.base / 'one')])
        self.assertEqual(params['approvalPolicy'], 'on-request')
        self.assertEqual(params['sandbox'], 'workspace-write')
        self.assertEqual(params['approvalsReviewer'], 'user')
        self.assertIn(memory, params['developerInstructions'])
        self.assertIn(A, json.loads((self.base / 'one' / store.ASSOCIATIONS).read_text())['sessions'])
        self.assertFalse((self.base / 'two' / store.ASSOCIATIONS).exists())

    def test_fail_closed_for_missing_or_broadened_permissions(self):
        for change in ({'sandbox': {}}, {'approvalPolicy': 'never'},
                       {'approvalsReviewer': 'auto_review'}, {'cwd': str(self.base)},
                       {'sandbox': dict(self.conversation.sandbox_policy(), writableRoots=[str(self.base)])},
                       {'sandbox': dict(self.conversation.sandbox_policy(), excludeSlashTmp=False)}):
            result = {'cwd': str(self.conversation.cwd), 'approvalPolicy': 'on-request',
                      'approvalsReviewer': 'user', 'sandbox': self.conversation.sandbox_policy()}
            result.update(change)
            with self.assertRaisesRegex(ValueError, 'isolation'):
                self.conversation.check_permissions(result)

    def test_probe_failure_closes_without_association(self):
        original = self.server.request.side_effect
        self.server.request.side_effect = lambda method, params: ({'exitCode': 1, 'stdout': ''}
                                           if method == 'command/exec' else original(method, params))
        with patch('embedded_codex.AppServer', return_value=self.server), patch('native_tools.discover', return_value='/codex'):
            with self.assertRaisesRegex(ValueError, 'probe failed'):
                self.conversation.connect()
        self.server.close.assert_called_once()
        self.assertIsNone(self.conversation.thread)
        self.assertFalse((self.base / 'one' / store.ASSOCIATIONS).exists())

    def test_probe_and_turn_scope(self):
        self.conversation.probe_isolation(self.server)
        params = self.server.request.call_args.args[1]
        self.assertIn(str(self.base / 'two'), params['command'])
        self.assertIn(str(Path(__file__).resolve().parents[1]), params['command'])
        self.assertEqual(params['sandboxPolicy']['writableRoots'], [str(self.base / 'one')])
        self.server.request.return_value = {'turn': {'id': 't', 'status': 'completed'}}
        self.server.request.side_effect = None
        self.conversation.server = self.server
        self.conversation.thread = A
        self.conversation.send('hello')
        params = self.server.request.call_args.args[1]
        self.assertEqual(params['sandboxPolicy'], self.conversation.sandbox_policy())
        self.assertEqual(params['approvalPolicy'], 'on-request')

    def test_resume_reapplies_and_checks_project_policy(self):
        with patch('conversation_store.require_owner'), patch('embedded_codex.AppServer', return_value=self.server), patch('native_tools.discover', return_value='/codex'):
            self.conversation.connect(A)
        params = next(c.args[1] for c in self.server.request.call_args_list if c.args[0] == 'thread/resume')
        self.assertEqual(params['sandbox'], 'workspace-write')
        self.assertEqual(params['approvalPolicy'], 'on-request')
        self.assertEqual(params['config']['sandbox_workspace_write'], {
            'writable_roots': [str(self.base / 'one')], 'network_access': False,
            'exclude_slash_tmp': True, 'exclude_tmpdir_env_var': True})

    def test_bad_policy_response_closes_before_probe_or_association(self):
        original = self.server.request.side_effect
        def response(method, params):
            result = original(method, params)
            if method == 'thread/start':
                result.pop('sandbox')
            return result
        self.server.request.side_effect = response
        with patch('embedded_codex.AppServer', return_value=self.server), patch('native_tools.discover', return_value='/codex'):
            with self.assertRaisesRegex(ValueError, 'isolation'):
                self.conversation.connect()
        self.server.close.assert_called_once()
        self.assertNotIn('command/exec', [c.args[0] for c in self.server.request.call_args_list])
        self.assertIsNone(self.conversation.thread)

    def test_foreign_approval_is_denied_without_ui_event(self):
        self.conversation.thread = A
        self.conversation.server = self.server
        self.conversation.receive('approval', {'id': 'foreign', 'params': {'threadId': 'other'}})
        self.server.decide.assert_called_once_with('foreign', False)
        self.assertFalse(self.events)

    def test_resume_owner_failure_never_starts_server(self):
        with patch('conversation_store.require_owner', side_effect=ValueError('foreign')), patch('embedded_codex.AppServer') as start:
            with self.assertRaises(ValueError):
                self.conversation.connect(A)
            start.assert_not_called()

    def test_resume_cwd_mismatch_never_resumes(self):
        self.server.request.side_effect = lambda method, params: {'thread': {'id': A, 'cwd': str(self.base / 'two')}}
        with patch('conversation_store.require_owner'), patch('embedded_codex.AppServer', return_value=self.server), patch('native_tools.discover', return_value='/codex'):
            with self.assertRaisesRegex(ValueError, 'directory differs'):
                self.conversation.connect(A)
        self.assertNotIn('thread/resume', [c.args[0] for c in self.server.request.call_args_list])
        self.server.close.assert_called_once()

    def test_changed_project_identity_blocks_send(self):
        (self.base / 'one' / store.IDENTITY).write_text('87654321-1234-1234-1234-123456789abc')
        self.conversation.server = self.server
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            self.conversation.send('hello')
        self.server.request.assert_not_called()

    def test_close_does_not_write_history(self):
        history = self.base / 'untouched.jsonl'
        history.write_text('original')
        self.conversation.server = self.server
        self.conversation.close()
        self.assertEqual(history.read_text(), 'original')
        self.server.close.assert_called_once()

    def test_fast_completed_turn_does_not_leave_interrupt_stale(self):
        self.conversation.server = self.server
        self.conversation.thread = A
        def response(method, params):
            self.conversation.receive('turn/completed', {'threadId': A, 'turn': {'id': 'turn1', 'status': 'completed'}})
            return {'turn': {'id': 'turn1', 'status': 'inProgress'}}
        self.server.request.side_effect = response
        self.conversation.send('hello')
        self.assertIsNone(self.conversation.turn)


class GTKDispatch(unittest.TestCase):
    """Widget-independent GTK handlers can be exercised without a display."""
    def test_stream_and_disconnect_invalidate_controls_and_approvals(self):
        from embedded_ui import EmbeddedView
        view = EmbeddedView.__new__(EmbeddedView)
        view.ready = True
        view.status = MagicMock()
        from transcript import Transcript
        view.transcript = Transcript()
        view.render = MagicMock()
        view.controls = MagicMock()
        dialog = MagicMock()
        view.approval_dialogs = [dialog]
        view.event('item/agentMessage/delta', {'delta': 'fixture streamed text'})
        self.assertIn('fixture streamed text', view.transcript.render()[0])
        view.render.assert_called_once()
        view.event('disconnected', {'message': 'fixture disconnect'})
        self.assertFalse(view.ready)
        dialog.destroy.assert_called_once()
        self.assertFalse(view.approval_dialogs)
        view.controls.assert_called_once()

    def test_close_is_idempotent_and_closes_transport(self):
        from embedded_ui import EmbeddedView
        view = EmbeddedView.__new__(EmbeddedView)
        view.alive = True
        view.approval_dialogs = [MagicMock()]
        view.conversation = MagicMock()
        view.panel = MagicMock()
        view.app = MagicMock()
        view.close()
        view.close()
        view.conversation.close.assert_called_once()
        view.panel.destroy.assert_called_once()

    def test_approval_defaults_to_deny_and_only_explicit_ok_accepts(self):
        from embedded_ui import EmbeddedView
        from gi.repository import Gtk
        for response, approved in ((Gtk.ResponseType.DELETE_EVENT, False),
                                   (Gtk.ResponseType.CANCEL, False), (Gtk.ResponseType.OK, True)):
            view = EmbeddedView.__new__(EmbeddedView)
            view.alive = True
            view.project = 'one'
            view.items = {'file': {'changes': [{'path': 'fixture.txt', 'diff': '+fixture'}]}}
            view.dialog = MagicMock()
            view.app = MagicMock()
            view.status = MagicMock()
            view.conversation = MagicMock()
            view.conversation.thread = A
            view.approval_dialogs = []
            view.approval_ids = set()
            view.app.worker.side_effect = lambda task, done: task()
            with patch('embedded_ui.Gtk.Dialog') as dialog, patch('embedded_ui.Gtk.TextView'), patch('embedded_ui.Gtk.ScrolledWindow'):
                view.approve({'id': 'approval', 'method': 'item/fileChange/requestApproval', 'params': {'threadId': A, 'itemId': 'file'}})
                instance = dialog.return_value
                instance.set_default_response.assert_called_once_with(Gtk.ResponseType.CANCEL)
                callback = instance.connect.call_args.args[1]
                view.approve({'id': 'approval', 'method': 'item/fileChange/requestApproval', 'params': {'threadId': A, 'itemId': 'file'}})
                dialog.assert_called_once()
                callback(instance, response)
                callback(instance, response)
                view.conversation.server.decide.assert_called_once_with('approval', approved)
