"""Project workflows over the existing validated Tailscale SSH connection."""
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import tempfile
import threading
from urllib.parse import quote
import zipfile
import core
import project_helper as policy

OPERATIONS = {'create', 'inspect_assets', 'put_asset', 'docs', 'ensure_docs', 'save_doc', 'inventory', 'snapshot', 'browse', 'desktop', 'desktop_status', 'list_projects', 'sessions', 'browse_project'}


def request(config, project, operation, progress=None, request_timeout=180, **fields):
    if operation not in OPERATIONS:
        raise ValueError('Unsupported project operation.')
    policy.project_name(project)
    command = core.ssh_args(config, 'edit', project)
    # Source is the bundled, fixed helper, never a user-provided script or command.
    source = Path(__file__).with_name('desktop_helper.py' if operation in ('desktop', 'desktop_status') else 'project_helper.py').read_text()
    if operation == 'sessions':
        source = Path(__file__).with_name('session_helper.py').read_text() + '\n' + source
    if operation == 'desktop':
        focus_source = Path(__file__).with_name('godot_focus.py').read_text()
        source = 'GODOT_FOCUS_SOURCE = ' + repr(focus_source) + '\n' + source
    # Assemble the final source BEFORE shell-quoting it into the SSH command.
    command[-1] = '/usr/bin/python3 -c ' + shlex.quote(source)
    body = dict(fields, version=policy.VERSION, project=project, operation=operation)
    payload = json.dumps(body).encode()
    if len(payload) > policy.MAX_REQUEST:
        raise ValueError('Transfer request exceeds size limit.')
    expired = threading.Event()
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=output, stderr=errors, bufsize=0)
        def timeout():
            expired.set()
            try:
                process.kill()
            except ProcessLookupError:
                pass
        timer = threading.Timer(request_timeout, timeout)
        timer.daemon = True
        timer.start()
        try:
            offset = 0
            try:
                while offset < len(payload):
                    count = process.stdin.write(payload[offset:offset + 65536])
                    if not count:
                        raise BrokenPipeError('SSH transfer stopped.')
                    offset += count
                    if progress:
                        progress(offset / len(payload))
            except BrokenPipeError:
                pass  # Read the actionable SSH/helper error below.
            finally:
                process.stdin.close()
            process.wait()
            if expired.is_set():
                raise TimeoutError('Project transfer timed out. Check Tailscale connectivity, then retry.')
            output.seek(0)
            data = output.read(48 * 1024 * 1024 + 1)
            if len(data) > 48 * 1024 * 1024:
                raise ValueError('Remote response exceeds the transfer limit.')
            try:
                response = json.loads(data)
            except (ValueError, UnicodeDecodeError):
                errors.seek(0, os.SEEK_END)
                size = errors.tell()
                errors.seek(max(0, size - 3000))
                detail = errors.read().decode(errors='replace').strip()
                raise RuntimeError('Project connection failed. Verify SSH keys, trusted host key and server Python 3. ' + detail) from None
            if not response.get('ok') or process.returncode:
                raise RuntimeError(response.get('error') or 'Remote project operation failed.')
            return response['result']
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
                process.wait()


def remote_project_path(config, project):
    policy.project_name(project)
    core.ssh_args(config, 'edit', project)  # validate configured user and numeric IP
    home = '/root' if config['user'] == 'root' else '/home/' + config['user']
    return f'{home}/StudioProjects/Godot/{project}'


def project_uri(config, project, assets=False):
    path = remote_project_path(config, project) + ('/assets' if assets else '')
    return f'sftp://{config["user"]}@{core.tailscale_ip(config)}' + quote(path, safe='/')


def asset_uri(config, project):
    return project_uri(config, project, assets=True)

def plan_import(config, project, files, category):
    if category not in policy.CATEGORIES or not files or len(files) > 100:
        raise ValueError('Choose 1–100 files and a supported asset category.')
    planned, names, total = [], set(), 0
    for filename in files:
        path = Path(filename)
        if path.is_symlink() or not path.is_file():
            raise ValueError('Select ordinary local files, not symlinks or directories.')
        name = policy.filename(path.name)
        if name in names:
            raise ValueError('Two selected files have the same filename: ' + name)
        names.add(name)
        size = path.stat().st_size
        total += size
        if size > policy.MAX_ASSET or total > 256 * 1024 * 1024:
            raise ValueError('Import limit: 32 MiB per file and 256 MiB per batch.')
        planned.append({'local': str(path), 'name': name, 'size': size})
    existing = request(config, project, 'inspect_assets', category=category, names=[p['name'] for p in planned])
    for item in planned:
        item['expected'] = existing[item['name']]
    return planned


def import_assets(config, project, plan, category, overwrite=False, progress=None):
    if any(p['expected'] is not None for p in plan) and not overwrite:
        raise ValueError('Filename conflicts require confirmation before overwriting.')
    total = max(1, sum(p['size'] for p in plan))
    transferred, completed = 0, []
    try:
        for item in plan:
            path = Path(item['local'])
            if path.is_symlink():
                raise ValueError('Local file became a symlink; select it again.')
            with path.open('rb') as source:
                data = source.read(policy.MAX_ASSET + 1)
            if len(data) > policy.MAX_ASSET or len(data) != item['size']:
                raise ValueError('Local file changed size; select it again: ' + item['name'])
            def update(fraction):
                if progress:
                    progress(min(1, (transferred + len(data) * fraction) / total), item['name'])
            result = request(config, project, 'put_asset', progress=update, category=category,
                             name=item['name'], expected=item['expected'], data=base64.b64encode(data).decode())
            if result['sha256'] != policy.digest(data):
                raise RuntimeError('Transferred file verification failed: ' + item['name'])
            completed.append(item['name'])
            transferred += len(data)
        if progress:
            progress(1, 'Complete')
        return f'Imported {len(completed)} file(s) into {project}/{policy.CATEGORIES[category]}.'
    except Exception as exc:
        raise RuntimeError(f'Import stopped after {len(completed)} completed file(s) ({", ".join(completed) or "none"}). {exc}') from exc


def overview(manifest, selected=None):
    metadata = manifest['metadata']
    name = policy.project_name(metadata['project'])
    rows = manifest['inventory']
    lines = [f'# Project snapshot: {name}', '', f'Generated: {datetime.now(timezone.utc).isoformat()}',
             f'Branch: {metadata.get("branch", "unknown")}', f'Latest commit: {metadata.get("commit", "unknown")}',
             f'Uncommitted work: {metadata.get("dirty", "unknown")}', '',
             'This snapshot contains selected CURRENT working-tree files, including uncommitted and untracked work.',
             'CHANGES.diff covers only selected text files against HEAD. Untracked files appear as current files, not as a Git diff.',
             'Excluded files, caches, credentials, symlinks and oversized files are not attached. Review for private information before sharing.',
             'Git metadata may be unavailable for new projects or when Git is missing.', '', '## Project structure and asset inventory', '']
    for item in rows:
        path = item['path']
        policy.relative(path)
        included = 'attached' if selected is not None and path in selected else 'not attached'
        lines.append(f'- {path} — {item["size"]} bytes; {item["type"] or "unknown type"}; {included}' + (f'; {item["reason"]}' if item.get('reason') else ''))
    return '\n'.join(lines) + '\n'


def brief(manifest):
    meta = manifest['metadata']
    return (f'Please review the attached OptiPlex Studio snapshot for {policy.project_name(meta["project"])}.\n'
            f'Current branch: {meta.get("branch")}; latest commit: {meta.get("commit")}; '
            f'uncommitted work: {meta.get("dirty")}.\n'
            'Read OVERVIEW.md, the selected GAME.md, PROGRESS.md, DECISIONS.md and AGENTS.md, '
            'then the current project sources, documents, assets and CHANGES.diff. The working tree, including uncommitted work, '
            'is authoritative. Some files are intentionally excluded; ask for missing context. '
            'Explain findings and a concrete implementation plan; use Codex for code changes. '
            'Do not assume anything was uploaded automatically or that this snapshot stays synchronized.\n')


def export_snapshot(config, project, manifest, selections, destination, overwrite=False, progress=None):
    if manifest['metadata']['project'] != project or not selections:
        raise ValueError('Select at least one file from this project before exporting.')
    allowed = {p['path']: p for p in manifest['inventory'] if p.get('sha256')}
    expected = {}
    for path in selections:
        if path not in allowed or not policy.exportable_path(path):
            raise ValueError('File was not eligible in the reviewed inventory: ' + path)
        expected[path] = allowed[path]['sha256']
    if sum(allowed[path]['size'] for path in expected) > policy.MAX_SNAPSHOT:
        raise ValueError('Selected files exceed 24 MiB; deselect large previews.')
    snapshot = request(config, project, 'snapshot', progress=progress, selections=expected)
    if snapshot['metadata']['project'] != project:
        raise ValueError('Remote snapshot project mismatch.')
    files, total = {}, 0
    for item in snapshot['files']:
        path = item['path']
        if path not in expected or path in files or not policy.exportable_path(path):
            raise ValueError('Unexpected snapshot path.')
        data = base64.b64decode(item['data'], validate=True)
        limit = policy.MAX_VISUAL if PurePosixPath(path).suffix.lower() in policy.VISUAL_TYPES else policy.MAX_TEXT
        total += len(data)
        if len(data) > limit or total > policy.MAX_SNAPSHOT or policy.digest(data) != expected[path]:
            raise ValueError('Snapshot file changed or exceeds its limit: ' + path)
        if PurePosixPath(path).suffix.lower() not in policy.VISUAL_TYPES and not policy.text_safe(data):
            raise ValueError('Potential credential detected in selected text: ' + path)
        files[path] = data
    deleted = {}
    for item in snapshot.get('deleted', []):
        path = item['path']
        if path not in expected or not allowed[path].get('deleted') or item['sha256'] != expected[path] or path in deleted:
            raise ValueError('Unexpected deletion in snapshot.')
        deleted[path] = item['sha256']
    if set(files) & set(deleted):
        raise ValueError('Snapshot cannot attach and delete the same file.')
    if set(files) | set(deleted) != set(expected):
        raise ValueError('Remote snapshot did not contain all selected files.')
    changes = snapshot.get('diff', '')
    if len(changes.encode()) > 2 * 1024 * 1024 or policy.SECRET.search(changes):
        raise ValueError('Snapshot diff exceeds its limit or contains potential credentials.')
    output = Path(destination)
    if output.exists() and not overwrite:
        raise FileExistsError('Choose a new filename or confirm replacing the existing export.')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.studio-snapshot-', dir=output.parent, delete=False) as file:
            temporary = Path(file.name)
            with zipfile.ZipFile(file, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('OVERVIEW.md', overview(snapshot, set(files) | set(deleted)))
                archive.writestr('CHATGPT-BRIEF.md', brief(snapshot))
                archive.writestr('CHANGES.diff', changes)
                for path, data in files.items():
                    archive.writestr(project + '/' + path, data)
        if overwrite:
            os.replace(temporary, output)
        else:
            os.link(temporary, output)  # refuses a filename created after the picker
            temporary.unlink()
        return snapshot
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
