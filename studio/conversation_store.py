"""Additive Studio metadata; never writes Codex history."""
import json
from pathlib import Path
import uuid
import project_helper as policy

IDENTITY = '.studio-project-id'
ASSOCIATIONS = '.studio-conversations.json'


def identity(project):
    try:
        return str(uuid.UUID(project.read(IDENTITY, 100).decode().strip()))
    except FileNotFoundError:
        value = str(uuid.uuid4())
        try:
            project.write(IDENTITY, (value + '\n').encode(), None, 100)
        except (ValueError, FileExistsError):
            return str(uuid.UUID(project.read(IDENTITY, 100).decode().strip()))
        return value


def associate(base, rows):
    """Resolve only verified projects and save proven mappings across renames."""
    projects = {}
    for item in policy.handle({'version': policy.VERSION, 'project': 'Studio',
                               'operation': 'list_projects'}, base):
        project = policy.Project(base, item['name'])
        try:
            project_id = identity(project)
            try:
                raw = project.read(ASSOCIATIONS, policy.MAX_TEXT)
                saved = json.loads(raw)
                if saved['project_id'] != project_id:
                    raise ValueError('Conversation identity mismatch.')
                ids = {str(uuid.UUID(value)) for value in saved['sessions']}
            except FileNotFoundError:
                raw, ids = None, set()
            projects[item['name']] = (project_id, ids, raw)
        finally:
            project.close()
    counts = {}
    for project_id, _, _ in projects.values():
        counts[project_id] = counts.get(project_id, 0) + 1
    base = Path(base)
    changed = set()
    for row in rows:
        owners = {name for name, (_, ids, _) in projects.items() if row['id'] in ids}
        cwd = row.get('cwd')
        if isinstance(cwd, str) and Path(cwd).is_absolute() and '..' not in Path(cwd).parts:
            path = Path(cwd)
            try:
                parts = path.relative_to(base).parts
                # A symlinked directory or a nonexistent cwd is not ownership evidence.
                if parts and parts[0] in projects and path.exists() and path.resolve() == path:
                    owners.add(parts[0])
            except (ValueError, OSError):
                pass
        owner = next(iter(owners)) if len(owners) == 1 else None
        if owner and counts[projects[owner][0]] != 1:
            owner = None
        row['project'] = owner
        row['project_id'] = projects[owner][0] if owner else None
        if owner and row['id'] not in projects[owner][1]:
            projects[owner][1].add(row['id'])
            changed.add(owner)
    for name in changed:
        project_id, ids, raw = projects[name]
        project = policy.Project(base, name)
        try:
            data = json.dumps({'project_id': project_id, 'sessions': sorted(ids)}).encode()
            project.write(ASSOCIATIONS, data, policy.digest(raw) if raw is not None else None, policy.MAX_TEXT)
        finally:
            project.close()
    return rows


def require_owner(config, project, identifier):
    """Fresh metadata validation also covers callers outside the GTK browser."""
    import project_client
    identifier = str(uuid.UUID(identifier))
    cursor, seen = None, set()
    while True:
        page = project_client.request(config, project, 'sessions', all_projects=True, cursor=cursor)
        row = next((row for row in page['sessions'] if row['id'] == identifier), None)
        if row:
            if row.get('project') != project:
                raise ValueError('Conversation does not belong to the active Project.')
            return identifier
        cursor = page.get('nextCursor')
        if not cursor or cursor in seen:
            raise ValueError('Conversation ownership could not be verified.')
        seen.add(cursor)
