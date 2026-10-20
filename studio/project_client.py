"""Local project workflows using the validated project engine."""
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from urllib.parse import quote
import zipfile
import core
import project_helper as policy

OPERATIONS = {'create', 'inspect_assets', 'put_asset', 'docs', 'ensure_docs', 'save_doc', 'inventory', 'snapshot', 'list_projects', 'sessions'}


def project_path(config, project):
    policy.project_name(project)
    return str(workspace(config) / project)


def project_uri(config, project, assets=False):
    path = Path(project_path(config, project)) / 'assets' if assets else Path(project_path(config, project))
    return path.as_uri()


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
        raise ValueError('Snapshot project mismatch.')
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
        raise ValueError('Snapshot did not contain all selected files.')
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


def local_request(config, project, operation, progress=None, **fields):
    """Execute a project operation in the configured local workspace."""
    if operation not in OPERATIONS:
        raise ValueError("Unsupported local project operation.")
    policy.project_name(project)
    payload = dict(fields, version=policy.VERSION, project=project, operation=operation)
    if len(json.dumps(payload).encode()) > policy.MAX_REQUEST:
        raise ValueError('Transfer request exceeds size limit.')
    base = workspace(config)
    if operation == "list_projects" and not base.exists():
        return []
    if operation == "sessions":
        from session_helper import list_codex_sessions
        return list_codex_sessions(base, project, dict(fields, _config=config))
    if operation == 'create':
        # Create workspace components through directory descriptors; reject symlinks.
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in base.parts[1:]:
                try:
                    os.mkdir(part, 0o755, dir_fd=fd)
                except FileExistsError:
                    pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
        finally:
            os.close(fd)
    result = policy.handle(dict(fields, version=policy.VERSION, project=project, operation=operation), base=base)
    if progress:
        progress(1.0)
    return result


def workspace(config):
    """Normalize an explicitly configured local workspace without migrating data."""
    value = config.get('projects_dir') or str(Path.home() / 'StudioProjects')
    path = Path(value).expanduser()
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Choose an absolute workspace path without parent traversal.')
    return path


def request(config, project, operation, progress=None, **fields):
    return local_request(config, project, operation, progress, **fields)
