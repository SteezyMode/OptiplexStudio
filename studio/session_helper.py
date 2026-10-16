"""Read-only session listing through Codex's documented app-server protocol.

Bundled into the SSH helper; never reads or edits rollout JSONL/SQLite files.
"""
def list_codex_sessions(base, project, request):
    import json
    import os
    from pathlib import Path, PurePosixPath
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
        process = subprocess.Popen([str(Path.home() / '.local/bin/codex'), 'app-server', '--listen', 'stdio://'],
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
                        raise RuntimeError('Codex session listing stopped. Check the remote Codex version; use its conversation picker as a fallback.')
                    buffer.extend(data)
            raise TimeoutError('Codex session listing timed out. You can still use the Codex conversation picker.')
        try:
            send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'optiplex_studio', 'title': 'OptiPlex Studio', 'version': '0.3.0'}}})
            response(1)
            send({'method': 'initialized', 'params': {}})
            params = {'limit': 100, 'cursor': cursor, 'sortKey': 'updated_at', 'useStateDbOnly': True,
                      'sourceKinds': ['cli', 'vscode', 'appServer', 'exec', 'unknown']}
            if not all_projects:
                params['cwd'] = str(base / project)
            send({'id': 2, 'method': 'thread/list', 'params': params})
            page = response(2)
            rows = []
            for item in page['data']:
                try:
                    identifier = str(uuid.UUID(item['id']))
                except (ValueError, KeyError, TypeError, AttributeError):
                    continue
                cwd = item.get('cwd')
                # Only associate by a real exact cwd or a directory below this project.
                association = None
                if isinstance(cwd, str):
                    path = PurePosixPath(cwd)
                    try:
                        parts = path.relative_to(PurePosixPath(base)).parts
                        if parts and all(p not in ('.', '..') for p in parts):
                            association = parts[0]
                    except ValueError:
                        pass
                if not all_projects and association != project:
                    continue
                rows.append({'id': identifier, 'title': str(item.get('name') or item.get('preview') or identifier)[:500],
                             'cwd': cwd or '', 'project': association,
                             'createdAt': item.get('createdAt', 0), 'updatedAt': item.get('updatedAt', 0)})
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
