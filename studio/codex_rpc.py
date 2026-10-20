"""Local newline JSON RPC transport. No history access and no automatic approvals."""
import json
import subprocess
import threading

APPROVALS = {'item/commandExecution/requestApproval', 'item/fileChange/requestApproval'}
MAX_LINE = 8 * 1024 * 1024


class AppServer:
    def __init__(self, executable, cwd, event):
        self.event = event
        self.lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.pending = {}
        self.approvals = set()
        self.seen_approvals = set()
        self.serial = 0
        self.closed = False
        self.process = subprocess.Popen([executable, 'app-server', '--listen', 'stdio://'],
                                        cwd=str(cwd), stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        threading.Thread(target=self._read, daemon=True).start()

    def write(self, message):
        with self.lock:
            if self.closed:
                raise RuntimeError('Codex disconnected; reconnect to resume.')
        with self.write_lock:
            self.process.stdin.write((json.dumps(message) + '\n').encode())
            self.process.stdin.flush()

    def request(self, method, params):
        with self.lock:
            self.serial += 1
            identifier = self.serial
            ready, box = threading.Event(), []
            self.pending[identifier] = (ready, box)
        try:
            self.write({'id': identifier, 'method': method, 'params': params})
            if not ready.wait(35):
                self.close()
                raise TimeoutError('Codex request timed out; reconnect before retrying.')
            response = box[0]
            if 'error' in response:
                raise RuntimeError(str(response['error']))
            return response['result']
        finally:
            with self.lock:
                self.pending.pop(identifier, None)

    def _message(self, message):
        if not isinstance(message, dict):
            raise ValueError('Invalid RPC envelope')
        if 'method' in message:
            if not isinstance(message['method'], str) or not isinstance(message.get('params', {}), dict):
                raise ValueError('Invalid RPC notification')
            if 'id' in message:
                if message['method'] in APPROVALS:
                    with self.lock:
                        if message['id'] in self.seen_approvals:
                            return
                        self.seen_approvals.add(message['id'])
                        self.approvals.add(message['id'])
                    self.event('approval', message)
                else:
                    self.write({'id': message['id'], 'error': {'code': -32601, 'message': 'Unsupported request; action not approved'}})
                    self.event('unsupported', message)
            else:
                self.event(message['method'], message.get('params', {}))
        elif 'id' in message and ('result' in message or 'error' in message):
            with self.lock:
                waiter = self.pending.get(message['id'])
                if waiter:
                    waiter[1].append(message)
                    waiter[0].set()
        else:
            raise ValueError('Invalid RPC response')

    def decide(self, identifier, approved):
        with self.lock:
            if identifier not in self.approvals or self.closed:
                raise ValueError('Approval expired')
            self.approvals.remove(identifier)
        self.write({'id': identifier, 'result': {'decision': 'accept' if approved else 'decline'}})

    def _read(self):
        detail = 'Codex disconnected; use Reconnect to resume verified history.'
        try:
            while not self.closed:
                line = self.process.stdout.readline(MAX_LINE + 1)
                if not line:
                    break
                if len(line) > MAX_LINE or not line.endswith(b'\n'):
                    raise ValueError('RPC frame exceeds limit or is truncated')
                self._message(json.loads(line))
        except Exception as exc:
            detail = 'Codex protocol error: ' + str(exc)
        finally:
            self.close()
            self.event('disconnected', {'message': detail})

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.approvals.clear()
            for ready, box in self.pending.values():
                if not ready.is_set():
                    box.append({'error': 'Codex disconnected'})
                    ready.set()
        self.process.terminate()
        def reap():
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process.stdin.close()
            self.process.stdout.close()
        threading.Thread(target=reap, daemon=True).start()
