"""Project-bound Codex lifecycle; public operations run on Studio's workers."""
from pathlib import Path
import uuid
import sys
import conversation_store as store
import native_tools
import project_client
import project_helper as policy
from codex_rpc import AppServer


class Conversation:
    def __init__(self, config, project, event):
        self.config, self.project, self.event = dict(config), project, event
        self.cwd = native_tools.project_directory(config, project).resolve(strict=True)
        source = Path(__file__).resolve().parent.parent
        if source.is_relative_to(self.cwd) or self.cwd.is_relative_to(source):
            raise ValueError("Selected Project overlaps Studio source; isolation unavailable.")
        checked = policy.Project(project_client.workspace(config), project)
        try:
            self.identity = store.identity(checked)
        finally:
            checked.close()
        self.tools = None
        self.server = None
        self.thread = None
        self.turn = None
        self.stopped = False
        self.completed_turns = set()

    def verify(self):
        checked = policy.Project(project_client.workspace(self.config), self.project)
        try:
            if store.identity(checked) != self.identity:
                raise ValueError('Active Project identity changed; reopen the conversation.')
        finally:
            checked.close()

    def receive(self, method, params):
        thread_id = (params.get('params', {}) if method == 'approval' else params).get('threadId')
        if thread_id and self.thread and thread_id != self.thread:
            if method == 'approval':
                self.server.decide(params['id'], False)
            return
        if method == 'turn/started':
            self.turn = params['turn']['id']
        elif method in ('turn/completed', 'disconnected'):
            if method == 'turn/completed':
                self.completed_turns.add(params['turn']['id'])
            self.turn = None
        self.event(method, params)

    def connect(self, identifier=None):
        self.verify()
        if identifier:
            store.require_owner(self.config, self.project, identifier)
        from tool_environment import ToolEnvironment
        if self.tools:
            self.tools.close()
        self.tools = ToolEnvironment(self.config, self.cwd)
        try:
            server = AppServer(native_tools.discover(self.config, 'codex'), self.cwd, self.receive)
        except Exception:
            self.tools.close()
            raise
        self.server = server
        try:
            if self.stopped:
                raise RuntimeError('Conversation closed')
            server.request('initialize', {'clientInfo': {'name': 'optiplex_studio', 'version': '0.4.0'}})
            server.write({'method': 'initialized', 'params': {}})
            params = {'cwd': str(self.cwd), 'approvalPolicy': 'on-request', 'sandbox': 'workspace-write',
                      'approvalsReviewer': 'user',
                      'config': {**self.tools.config(), 'sandbox_workspace_write': {
                          'writable_roots': [str(self.cwd)], 'network_access': False,
                          'exclude_slash_tmp': True, 'exclude_tmpdir_env_var': True}}}
            if identifier:
                # Inspect before resume: never change a foreign thread's cwd.
                metadata = server.request('thread/read', {'threadId': identifier, 'includeTurns': False})['thread']
                if metadata['id'] != identifier or Path(metadata['cwd']) != self.cwd:
                    raise ValueError('Thread directory differs from the verified Project; use terminal recovery.')
                params['threadId'] = identifier
            else:
                import core
                args, _ = native_tools.codex_command(self.config, 'code', self.project)
                # One general creation workflow for all new project conversations.
                # Project AI_MEMORY remains additional context, never discarded.
                instructions = core.CREATIVE_WORKFLOW_GUIDANCE
                if '--' in args:
                    memory = args[args.index('--') + 1].removesuffix(
                        '\n\nAsk the user what to work on next.')
                    if memory.strip():
                        instructions += '\n\n' + memory
                params['developerInstructions'] = instructions
                params['ephemeral'] = False
            result = server.request('thread/resume' if identifier else 'thread/start', params)
            self.check_permissions(result)
            self.probe_isolation(server)
            thread = result['thread']
            returned = str(uuid.UUID(thread['id']))
            if identifier and returned != identifier:
                raise ValueError('Codex returned a different thread')
            if Path(thread['cwd']) != self.cwd:
                raise ValueError('Codex returned a different Project directory')
            self.verify()
            rows = store.associate(project_client.workspace(self.config), [{'id': returned, 'cwd': str(self.cwd)}])
            if rows[0]['project_id'] != self.identity:
                raise ValueError('Conversation ownership conflict')
            self.thread = returned
            self.event('history', thread)
        except Exception:
            server.close()
            self.tools.close()
            raise

    def sandbox_policy(self):
        # App Server 0.163.0: thread uses SandboxMode; turns use SandboxPolicy.
        return {'type': 'workspaceWrite', 'writableRoots': [str(self.cwd)],
                'networkAccess': False, 'excludeSlashTmp': True, 'excludeTmpdirEnvVar': True}

    def check_permissions(self, result):
        if (result.get('cwd') != str(self.cwd)
                or result.get('approvalPolicy') != 'on-request'
                or result.get('approvalsReviewer') != 'user'
                or result.get('sandbox') not in (self.sandbox_policy(), dict(self.sandbox_policy(), writableRoots=[]))):
            raise ValueError('Codex did not establish project-only workspace-write isolation.')

    def probe_isolation(self, server):
        # Test the actual execution sandbox without creating files in protected paths.
        # A read-only mount makes access(W_OK) false, even for otherwise writable dirs.
        protected = {self.cwd.parent, Path(__file__).resolve().parent.parent}
        protected.update(p.resolve() for p in self.cwd.parent.iterdir()
                         if p.is_dir() and p.resolve() != self.cwd)
        script = ("import os,sys,tempfile; "
                  "assert not any(os.access(p, os.W_OK) for p in sys.argv[1:]); "
                  "f=tempfile.TemporaryFile(dir='.'); f.write(b'isolation'); f.close(); "
                  "print('studio-isolated')")
        result = server.request('command/exec', {
            'command': [sys.executable, '-c', script, *map(str, sorted(protected))],
            'cwd': str(self.cwd), 'sandboxPolicy': self.sandbox_policy(), 'timeoutMs': 10000})
        if result.get('exitCode') != 0 or result.get('stdout', '').strip() != 'studio-isolated':
            raise ValueError('Project sandbox isolation probe failed; embedded session disabled.')

    def send(self, text):
        self.verify()
        if not isinstance(text, str) or not text.strip() or len(text) > 32000 or '\0' in text:
            raise ValueError('Enter 1–32,000 characters without NUL.')
        if self.turn:
            raise ValueError('Wait for the current turn or interrupt it.')
        result = self.server.request('turn/start', {'threadId': self.thread,
                                     'input': [{'type': 'text', 'text': text}],
                                     'cwd': str(self.cwd), 'sandboxPolicy': self.sandbox_policy(),
                                     'approvalPolicy': 'on-request', 'approvalsReviewer': 'user'})
        turn = result['turn']
        self.turn = turn['id'] if turn.get('status') == 'inProgress' and turn['id'] not in self.completed_turns else None

    def interrupt(self):
        if self.turn:
            self.server.request('turn/interrupt', {'threadId': self.thread, 'turnId': self.turn})

    def close(self):
        self.stopped = True
        if self.server:
            self.server.close()
        if self.tools:
            self.tools.close()
