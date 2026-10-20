"""Read-only session listing through Codex's documented app-server protocol.

Uses additive Studio associations; never reads or edits rollout JSONL/SQLite files.
"""
def list_codex_sessions(base, project, request):
    import json
    import os
    import selectors
    import subprocess
    import tempfile
    import time
    import uuid

    cursor = request.get('cursor')
    if cursor is not None and (not isinstance(cursor, str) or len(cursor) > 4096):
        raise ValueError('Invalid session page cursor.')
    all_projects = request.get('all_projects', False)
    if not isinstance(all_projects, bool):
        raise ValueError('Invalid session scope.')
    deadline = time.monotonic() + 35
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen([__import__('native_tools').discover(request.get('_config', {}), 'codex'), 'app-server', '--listen', 'stdio://'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        buffer = bytearray()
        def send(value):
            process.stdin.write((json.dumps(value) + '\n').encode())
            process.stdin.flush()
        def response(identifier):
            while time.monotonic() < deadline:
                while b'\n' in buffer:
                    line, _, rest = buffer.partition(b'\n')
                    buffer[:] = rest
                    if not line:
                        continue
                    message = json.loads(line)
                    if message.get('id') != identifier:
                        # Never approve tool calls or run turns in the listing process.
                        if 'id' in message and 'method' in message:
                            send({'id': message['id'], 'error': {'code': -32601, 'message': 'Listing only'}})
                        continue
                    if 'error' in message:
                        raise RuntimeError('Codex session listing unavailable: ' + str(message['error'].get('message', 'protocol error')))
                    return message['result']
                if len(buffer) > 4 * 1024 * 1024:
                    raise ValueError('Codex metadata response exceeds 4 MiB.')
                if selector.select(min(1, max(0, deadline - time.monotonic()))):
                    data = os.read(process.stdout.fileno(), 65536)
                    if not data:
                        raise RuntimeError('Codex session listing stopped. Check the local Codex version; use its conversation picker as a fallback.')
                    buffer.extend(data)
            raise TimeoutError('Codex session listing timed out. You can still use the Codex conversation picker.')
        try:
            send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'optiplex_studio', 'title': 'OptiPlex Studio', 'version': '0.3.0'}}})
            response(1)
            send({'method': 'initialized', 'params': {}})
            params = {'limit': 100, 'cursor': cursor, 'sortKey': 'updated_at', 'useStateDbOnly': True,
                      'sourceKinds': ['cli', 'vscode', 'appServer', 'exec', 'unknown']}
            send({'id': 2, 'method': 'thread/list', 'params': params})
            page = response(2)
            rows = []
            for item in page['data']:
                try:
                    identifier = str(uuid.UUID(item['id']))
                except (ValueError, KeyError, TypeError, AttributeError):
                    continue
                cwd = item.get('cwd')
                rows.append({'id': identifier, 'title': ' '.join(str(item.get('name') or item.get('preview') or 'Untitled conversation').split())[:160] or 'Untitled conversation',
                             'cwd': cwd or '', 'project': None,
                             'createdAt': item.get('createdAt', 0), 'updatedAt': item.get('updatedAt', 0)})
            from conversation_store import associate
            rows = associate(base, rows)
            if not all_projects:
                rows = [row for row in rows if row['project'] == project]
            return {'sessions': rows, 'nextCursor': page.get('nextCursor')}
        finally:
            selector.close()
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdin.close()
            process.stdout.close()
