#!/usr/bin/python3
"""Narrow project protocol over SSH stdio. No daemon, Docker or arbitrary commands.

The client sends this bundled module to python3 -c; no remote installation.
All filesystem access is anchored to directory FDs opened with O_NOFOLLOW.
"""
import base64
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import subprocess
import sys
import tempfile

VERSION = 1
MAX_ASSET = 32 * 1024 * 1024
MAX_TEXT = 512 * 1024
MAX_VISUAL = 2 * 1024 * 1024
MAX_SNAPSHOT = 24 * 1024 * 1024
MAX_REQUEST = 46 * 1024 * 1024
MAX_FILES = 1500
CATEGORIES = {'Sprites': 'assets/sprites', 'Textures': 'assets/textures',
              '3D Models': 'assets/3d', 'Music': 'assets/audio/music',
              'Sound Effects': 'assets/audio/sfx', 'Other Assets': 'assets/other'}
PROJECT_TYPES = ('Blank', 'Godot', 'Music/Audio', 'Animation', '3D')
DOCS = ('GAME.md', 'PROGRESS.md', 'DECISIONS.md', 'AGENTS.md')
WORKFLOW = ('Before significant implementation, read GAME.md, PROGRESS.md, DECISIONS.md and AGENTS.md '
            'in the project root. Keep PROGRESS.md and DECISIONS.md concise and accurate after meaningful changes. '
            'Work only in this project; never change Wolf, server services or unrelated projects. '
            'Do not commit unless explicitly requested. For Godot projects only, validate Godot changes with the existing '
            '~/.local/bin/studio-validate PROJECT_NAME when available, replacing PROJECT_NAME with the project name. '
            'Report missing validation tools or permissions; never bypass them through unrestricted Docker access. '
            'Headless validation does not replace playtesting.')
TEXT_TYPES = {'.gd', '.tscn', '.tres', '.godot', '.gdshader', '.gdshaderinc', '.uid',
              '.json', '.csv', '.txt', '.gltf', '.obj', '.mtl', '.md'}
VISUAL_TYPES = {'.png', '.jpg', '.jpeg', '.webp'}
ASSET_TYPES = VISUAL_TYPES | {'.svg', '.bmp', '.tga', '.ase', '.aseprite', '.wav', '.ogg',
    '.mp3', '.flac', '.m4a', '.mid', '.midi', '.glb', '.gltf', '.obj', '.fbx', '.blend',
    '.mtl', '.tres', '.res', '.ttf', '.otf', '.txt', '.csv', '.json', '.atlas', '.kra', '.ora', '.bbmodel', '.piskel', '.psd', '.xcf', '.gif', '.exr', '.hdr'}
EXCLUDED_DIRS = {'.git', '.godot', 'build', 'dist', 'exports', 'node_modules', '__pycache__', '.venv', 'vendor'}
PRIVATE = re.compile(r'(^|[._ -])(secret|secrets|credential|credentials|password|passwords|private|token|tokens|apikey|api_key)([._ -]|$)', re.I)
SECRET = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b|(?:api[_-]?key|access[_-]?token|password|client[_-]?secret)\s*["\']?\s*[:=]\s*["\']?[^\s"\'\n]{8,}', re.I)


def project_name(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', name):
        raise ValueError('Invalid project name.')
    return name


def relative(path):
    if (not isinstance(path, str) or not path or len(path) > 500 or '\\' in path
            or any(ord(c) < 32 for c in path)):
        raise ValueError('Invalid project path.')
    parts = path.split('/')
    if path.startswith('/') or any(p in ('', '.', '..') for p in parts):
        raise ValueError('Path traversal is not allowed.')
    return parts


def filename(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _().-]{0,159}', name):
        raise ValueError('Use a filename with letters, numbers, spaces, periods, parentheses, hyphens or underscores.')
    if PRIVATE.search(name) or PurePosixPath(name).suffix.lower() not in ASSET_TYPES:
        raise ValueError('Unsupported asset type or private filename: ' + name)
    return name


def exportable_path(path):
    parts = relative(path)
    if any(p.startswith('.') or p.lower() in EXCLUDED_DIRS or PRIVATE.search(p) for p in parts):
        return False
    if path == 'studio-project.json':
        return True
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == '.md':
        return path in DOCS or path == 'README.md' or parts[0] == 'docs'
    if suffix in {'.json', '.csv', '.txt', '.gltf', '.obj', '.mtl'}:
        return len(parts) > 1 and parts[0] in {'assets', 'docs', 'data', 'resources'}
    return suffix in TEXT_TYPES | VISUAL_TYPES


def digest(data):
    return hashlib.sha256(data).hexdigest()


def text_safe(data):
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return False
    return '\0' not in text and not SECRET.search(text)


def templates(name, kind='Godot'):
    documents = {'GAME.md': f'# {name}\n\n## Concept and genre\nTo be defined.\n\n## Mechanics\nTo be defined.\n\n## Aesthetic direction\nTo be defined.\n\n## Goals\nTo be defined.\n',
            'PROGRESS.md': '# Progress\n\n## Implemented\n- Godot project scaffold.\n\n## Current work\n- Define the game concept.\n\n## Next steps\n- Build and playtest a small prototype.\n',
            'DECISIONS.md': '# Decisions\n\nRecord meaningful technical and design decisions with their reasons.\n',
            'AGENTS.md': '# Project instructions\n\n' + WORKFLOW.replace('PROJECT_NAME', name) + '\n'}

    if kind != 'Godot':
        documents['GAME.md'] = f'# {name}\n\n## Project type\n{kind}\n\n## Goals and creative direction\nTo be defined.\n'
        documents['PROGRESS.md'] = '# Progress\n\n## Implemented\n- Shared project scaffold.\n\n## Current work\n- Define goals.\n\n## Next steps\n- Create an initial draft.\n'
    return documents


class Project:
    def __init__(self, base, name):
        self.name = project_name(name)
        # Walk from / without following even an intermediate symlink.
        directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in Path(base).absolute().parts[1:] + (self.name,):
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                os.close(directory)
                directory = child
            self.fd = directory
            directory = None
            self.kind = self.project_type()
        except BaseException:
            if hasattr(self, 'fd'):
                os.close(self.fd)
            raise
        finally:
            if directory is not None:
                os.close(directory)

    def project_type(self):
        try:
            self.read('project.godot', MAX_TEXT)
            return 'Godot'
        except FileNotFoundError:
            metadata = json.loads(self.read('studio-project.json', MAX_TEXT))
            if metadata.get('type') not in PROJECT_TYPES:
                raise ValueError('Invalid Studio project type.')
            return metadata['type']

    def close(self):
        os.close(self.fd)

    @contextlib.contextmanager
    def parent(self, path, create=False):
        parts = relative(path)
        fd = os.dup(self.fd)
        try:
            for part in parts[:-1]:
                if create:
                    try:
                        os.mkdir(part, 0o755, dir_fd=fd)
                    except FileExistsError:
                        pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            yield fd, parts[-1]
        finally:
            os.close(fd)

    def read(self, path, limit):
        with self.parent(path) as (parent, name):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(fd, 'rb') as stream:
                st = os.fstat(stream.fileno())
                if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                    raise ValueError('Only ordinary files without hard links are allowed: ' + path)
                if st.st_size > limit:
                    raise ValueError('File exceeds size limit: ' + path)
                data = stream.read(limit + 1)
                if len(data) > limit:
                    raise ValueError('File grew beyond the size limit: ' + path)
                return data

    def current_hash(self, path, limit):
        try:
            return digest(self.read(path, limit))
        except FileNotFoundError:
            return None

    @contextlib.contextmanager
    def lock(self):
        fd = os.open('.studio-project.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self.fd)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                raise ValueError('Invalid project lock.')
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def write(self, path, data, expected, limit):
        if len(data) > limit:
            raise ValueError('File exceeds size limit.')
        with self.lock():
            with self.parent(path, create=True) as (parent, name):
                if self.current_hash(path, limit) != expected:
                    raise ValueError('File conflict: ' + path + '. Reload and confirm the current version before overwriting.')
                temporary = '.studio-' + secrets.token_hex(12)
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=parent)
                try:
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(data)
                        stream.flush()
                        os.fsync(stream.fileno())
                    if expected is None:
                        # Atomic no-clobber create, even if another writer races.
                        os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                    else:
                        if self.current_hash(path, limit) != expected:
                            raise ValueError('File changed during transfer; reload and retry: ' + path)
                        os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                    return digest(data)
                finally:
                    try:
                        os.unlink(temporary, dir_fd=parent)
                    except FileNotFoundError:
                        pass

    def ensure_docs(self):
        created = []
        for name, text in templates(self.name, self.kind).items():
            if self.current_hash(name, MAX_TEXT) is None:
                try:
                    self.write(name, text.encode(), None, MAX_TEXT)
                    created.append(name)
                except FileExistsError:
                    pass
        return created

    def git(self, args, limit=MAX_TEXT):
        if not args or args[0] != 'init':
            try:
                git_fd = os.open('.git', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
                os.close(git_fd)
            except OSError:
                return '[Git metadata unavailable: no ordinary project-local .git directory]', False
        # No shell, hooks, external diff drivers, textconv, pager or fsmonitor.
        command = ['git', '--no-pager', '--literal-pathspecs', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
                   '-c', 'diff.external=', '-C', '/proc/self/fd/' + str(self.fd)] + args
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'})
        with tempfile.TemporaryFile() as output:
            try:
                result = subprocess.run(command, stdout=output, stderr=subprocess.DEVNULL,
                                        pass_fds=(self.fd,), env=env, timeout=15)
                output.seek(0)
                data = output.read(limit + 1)
                if len(data) > limit:
                    return '[Git output omitted: size limit]', False
                text = data.decode('utf-8', errors='replace')
                if SECRET.search(text):
                    return '[Git output omitted: potential credential]', False
                return text.strip(), result.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                return '[Git unavailable]', False

    def metadata(self):
        branch, _ = self.git(['branch', '--show-current'])
        commit, _ = self.git(['log', '-1', '--format=%h %s'])
        status, okay = self.git(['status', '--porcelain', '--untracked-files=normal'])
        return {'project': self.name, 'type': self.kind, 'branch': branch or '(unborn/detached)',
                'commit': commit or '(no commits)', 'dirty': bool(status) if okay else None}

    def inventory(self):
        entries, visited = [], [0]
        def walk(fd, prefix, depth):
            if depth > 12:
                raise ValueError('Snapshot inventory exceeds 12 directory levels; narrow the project before sharing.')
            with os.scandir(fd) as scan:
                for entry in scan:
                    visited[0] += 1
                    if visited[0] > 10000:
                        raise ValueError('Project inventory exceeds 10,000 entries; reduce project size first.')
                    path = prefix + entry.name
                    if (entry.name.startswith('.') or entry.name.lower() in EXCLUDED_DIRS or PRIVATE.search(entry.name)):
                        continue
                    st = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(st.st_mode):
                        child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                        try:
                            walk(child, path + '/', depth + 1)
                        finally:
                            os.close(child)
                    elif stat.S_ISREG(st.st_mode) and st.st_nlink == 1:
                        if len(entries) >= MAX_FILES:
                            raise ValueError('Project has too many eligible files; narrow it before sharing.')
                        suffix = PurePosixPath(path).suffix.lower()
                        is_asset = suffix in ASSET_TYPES and (prefix.startswith('assets/') or suffix not in {'.txt', '.csv', '.json'})
                        if not exportable_path(path) and not is_asset:
                            continue
                        item = {'path': path, 'size': st.st_size, 'type': suffix, 'asset': is_asset,
                                'sha256': None, 'reason': 'Inventory only: unsupported snapshot type.'}
                        limit = MAX_VISUAL if suffix in VISUAL_TYPES else MAX_TEXT
                        if exportable_path(path) and st.st_size <= limit:
                            data = self.read(path, limit)
                            if suffix in VISUAL_TYPES or text_safe(data):
                                item.update(sha256=digest(data), reason='')
                            else:
                                item['reason'] = 'Excluded: non-UTF8 text or potential credential.'
                        elif st.st_size > limit:
                            item['reason'] = 'Inventory only: snapshot file size limit.'
                        entries.append(item)
        walk(self.fd, '', 0)
        deleted, okay = self.git(['diff', '--no-ext-diff', '--no-textconv', '--name-only', '--diff-filter=D', '-z', 'HEAD', '--'])
        if okay:
            for path in deleted.split('\0'):
                if not path or not exportable_path(path) or PurePosixPath(path).suffix.lower() not in TEXT_TYPES:
                    continue
                size, size_okay = self.git(['cat-file', '-s', 'HEAD:' + path])
                if not size_okay or not size.isdigit() or int(size) > MAX_TEXT:
                    continue
                original, original_okay = self.git(['show', 'HEAD:' + path])
                if original_okay and text_safe(original.encode()):
                    entries.append({'path': path, 'size': 0, 'type': PurePosixPath(path).suffix.lower(),
                                    'asset': False, 'sha256': 'deleted:' + digest(original.encode()),
                                    'reason': 'Deleted file: include its reviewed deletion diff.', 'deleted': True})
        if len(entries) > MAX_FILES:
            raise ValueError('Project inventory exceeds its file limit.')
        return sorted(entries, key=lambda p: p['path'])

    def snapshot(self, selections):
        if not isinstance(selections, dict) or len(selections) > MAX_FILES:
            raise ValueError('Invalid snapshot selection.')
        inventory = self.inventory()
        allowed = {p['path']: p for p in inventory if p['sha256']}
        files, diffs, deleted_files, total = [], [], [], 0
        for path, expected in selections.items():
            if not exportable_path(path) or path not in allowed or allowed[path]['sha256'] != expected:
                raise ValueError('Selection changed or is excluded; review again: ' + path)
            if allowed[path].get('deleted'):
                deleted_files.append({'path': path, 'sha256': expected})
            else:
                limit = MAX_VISUAL if PurePosixPath(path).suffix.lower() in VISUAL_TYPES else MAX_TEXT
                data = self.read(path, limit)
                if digest(data) != expected:
                    raise ValueError('File changed since review: ' + path)
                total += len(data)
                if total > MAX_SNAPSHOT:
                    raise ValueError('Selected files exceed the 24 MiB snapshot limit.')
                files.append({'path': path, 'sha256': expected, 'data': base64.b64encode(data).decode()})
            if PurePosixPath(path).suffix.lower() in TEXT_TYPES:
                old_size, old_okay = self.git(['cat-file', '-s', 'HEAD:' + path])
                if old_okay and old_size.isdigit() and int(old_size) > MAX_TEXT:
                    diffs.append(f'Diff omitted for {path}: original committed file exceeds the size limit.')
                    continue
                diff, okay = self.git(['diff', '--no-ext-diff', '--no-textconv', '--no-renames', 'HEAD', '--', path], 1024 * 1024)
                if diff:
                    diffs.append(diff if okay else f'Diff omitted for {path}: unavailable, too large or potentially sensitive.')
        # Recheck after diff collection so concurrent edits do not silently mix
        # reviewed contents with a newer diff or a recreated deleted file.
        for path, expected in selections.items():
            current = self.current_hash(path, MAX_VISUAL if PurePosixPath(path).suffix.lower() in VISUAL_TYPES else MAX_TEXT)
            if (allowed[path].get('deleted') and current is not None) or (not allowed[path].get('deleted') and current != expected):
                raise ValueError('File changed while collecting context; review again: ' + path)
        changes = '\n\n'.join(diffs)
        if len(changes.encode()) > 2 * 1024 * 1024:
            changes = '[Diff omitted: combined diff exceeds 2 MiB; selected files contain current working contents.]'
        return {'version': VERSION, 'metadata': self.metadata(), 'inventory': inventory, 'files': files, 'deleted': deleted_files, 'diff': changes}


def create_project(base, name, kind='Godot'):
    project_name(name)
    if kind not in PROJECT_TYPES:
        raise ValueError('Unsupported project template.')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(base).absolute().parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        os.mkdir(name, 0o755, dir_fd=fd)
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
    finally:
        os.close(fd)
    project = Project.__new__(Project)
    project.fd, project.name, project.kind = child, name, kind
    try:
        folders = {'Blank': ('docs',), 'Godot': ('docs', 'scenes', 'scripts'),
                   'Music/Audio': ('docs', 'sessions', 'mixes'),
                   'Animation': ('docs', 'storyboards', 'sequences'),
                   '3D': ('docs', 'models', 'renders')}
        for folder in folders[kind] + tuple(CATEGORIES.values()):
            with project.parent(folder + '/placeholder', create=True):
                pass
        files = templates(name, kind)
        files.update({'project.godot': f'config_version=5\n\n[application]\nconfig/name="{name}"\nrun/main_scene="res://scenes/main.tscn"\n\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',
                      'scenes/main.tscn': '[gd_scene format=3]\n\n[node name="Main" type="Node2D"]\n',
                      '.gitignore': '.godot/\n.studio*\n*.tmp\n'})
        if kind != 'Godot':
            files.pop('project.godot')
            files.pop('scenes/main.tscn')
        files['studio-project.json'] = json.dumps({'version': 1, 'type': kind}) + '\n'
        for filename_, content in files.items():
            project.write(filename_, content.encode(), None, MAX_TEXT)
        _, okay = project.git(['init', '-b', 'main'])
        return {'created': name, 'warning': '' if okay else 'Project created but Git initialization failed. No commit was made.'}
    finally:
        project.close()


def handle(request, base=None):
    if not isinstance(request, dict) or request.get('version') != VERSION:
        raise ValueError('Unsupported project protocol.')
    base = Path(base) if base is not None else Path.home() / 'StudioProjects/Godot'
    name = project_name(request.get('project'))
    operation = request.get('operation')
    if operation == 'list_projects':
        rows = []
        # Open base without following intermediate symlinks, as Project does.
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in base.absolute().parts[1:]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            names = os.listdir(fd)
        finally:
            os.close(fd)
        if len(names) > 10000:
            raise ValueError('Too many project directories.')
        for candidate in names:
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', candidate):
                continue
            try:
                project = Project(base, candidate)
            except (OSError, ValueError):
                continue
            try:
                rows.append(dict(project.metadata(), name=candidate))
            finally:
                project.close()
        return sorted(rows, key=lambda row: row['name'].lower())
    if operation == 'sessions':
        return list_codex_sessions(base, name, request)
    if operation == 'create':
        return create_project(base, name, request.get('template', 'Godot'))
    project = Project(base, name)
    try:
        if operation == 'inspect_assets':
            category = request['category']
            if category not in CATEGORIES or len(request['names']) > 100:
                raise ValueError('Invalid asset category or file count.')
            return {filename(n): project.current_hash(CATEGORIES[category] + '/' + filename(n), MAX_ASSET) for n in request['names']}
        if operation == 'put_asset':
            category = request['category']
            if category not in CATEGORIES:
                raise ValueError('Invalid asset category.')
            name_ = filename(request['name'])
            data = base64.b64decode(request['data'], validate=True)
            return {'sha256': project.write(CATEGORIES[category] + '/' + name_, data, request.get('expected'), MAX_ASSET)}
        if operation == 'docs':
            result = {}
            for name_ in DOCS:
                try:
                    data = project.read(name_, MAX_TEXT)
                    result[name_] = {'text': data.decode('utf-8'), 'sha256': digest(data)}
                except FileNotFoundError:
                    result[name_] = {'text': '', 'sha256': None}
            return result
        if operation == 'ensure_docs':
            return {'created': project.ensure_docs()}
        if operation == 'save_doc':
            if request['name'] not in DOCS:
                raise ValueError('Unsupported documentation file.')
            return {'sha256': project.write(request['name'], request['text'].encode('utf-8'), request.get('expected'), MAX_TEXT)}
        if operation == 'inventory':
            return {'metadata': project.metadata(), 'inventory': project.inventory()}
        if operation == 'snapshot':
            return project.snapshot(request['selections'])
        if operation in ('browse', 'browse_project'):
            with project.parent('assets/placeholder', create=True):
                pass
            return {'path': str(base / name / 'assets') if operation == 'browse' else str(base / name)}
        raise ValueError('Unsupported project operation.')
    finally:
        project.close()


def main():
    try:
        payload = sys.stdin.buffer.read(MAX_REQUEST + 1)
        if len(payload) > MAX_REQUEST:
            raise ValueError('Project request exceeds size limit.')
        result = handle(json.loads(payload))
        print(json.dumps({'ok': True, 'result': result}))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
