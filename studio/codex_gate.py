#!/usr/bin/env python3
"""Restricted, project-scoped SSH entry point for Wolf's Codex UI.

Install as the normal OptiPlex user and use in authorized_keys as a forced
command. Never configure this as unrestricted shell access.
"""
import json
import os
from pathlib import Path
import re
import sys
import uuid

BASE = Path.home() / 'StudioProjects/Godot'
CODEX = Path.home() / '.local/bin/codex'
NAME = re.compile(r'[A-Za-z0-9_-]{1,128}\\Z')


def project_path(name):
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError('Invalid project')
    root = BASE.resolve(strict=True)
    target = root / name
    if target.is_symlink() or not target.is_dir() or target.resolve(strict=True).parent != root:
        raise ValueError('Project not found')
    return target


def main():
    import shlex
    original = os.environ.get('SSH_ORIGINAL_COMMAND', '')
    args = shlex.split(original)
    if len(args) < 3 or args[0] != 'studio-codex' or args[1] not in ('list', 'new', 'resume'):
        raise ValueError('Only Studio Codex operations are permitted')
    action, project = args[1:3]
    target = project_path(project)
    if not CODEX.is_file():
        raise RuntimeError('Codex not found')
    if action == 'list':
        if len(args) != 3:
            raise ValueError('Invalid session list')
        # Run the bundled read-only app-server listing against host Codex history.
        from session_helper import list_codex_sessions
        page = list_codex_sessions(BASE, project, {'all_projects': False, 'cursor': None})
        print(json.dumps(page), flush=True)
        return
    if action == 'new' and len(args) != 3:
        raise ValueError('Invalid new-session request')
    if action == 'resume':
        if len(args) != 4:
            raise ValueError('Invalid resume request')
        session = str(uuid.UUID(args[3]))
        # Only allow IDs associated with this exact Studio project.
        from session_helper import list_codex_sessions
        cursor = None
        found = False
        for _ in range(30):
            page = list_codex_sessions(BASE, project, {'all_projects': False, 'cursor': cursor})
            if any(row['id'] == session for row in page['sessions']):
                found = True
                break
            cursor = page.get('nextCursor')
            if not cursor:
                break
        if not found:
            raise ValueError('Session does not belong to this project')
    command = [str(CODEX), '--cd', str(target), '--sandbox', 'workspace-write',
               '--ask-for-approval', 'on-request']
    if action == 'resume':
        command += ['resume', session]
    os.execv(str(CODEX), command)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error': str(exc)[:500]}), file=sys.stderr)
        raise SystemExit(1)
