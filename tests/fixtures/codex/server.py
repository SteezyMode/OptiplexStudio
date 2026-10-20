#!/usr/bin/python3
"""Deterministic stdio peer; never invokes Codex or executes agent actions."""
import json
import sys
for line in sys.stdin:
    m = json.loads(line)
    method = m.get('method')
    if method == 'fixture/disconnect':
        break
    if method == 'fixture/malformed':
        print('not json', flush=True)
        continue
    if method == 'fixture/approval':
        print(json.dumps({'id': 'approval-1', 'method': 'item/commandExecution/requestApproval',
                          'params': {'threadId': 'thread', 'command': 'echo fixture'}}), flush=True)
    if 'id' in m and method:
        result = {'echo': m.get('params')}
        print(json.dumps({'id': m['id'], 'result': result}), flush=True)
