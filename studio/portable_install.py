"""Rootless optional publisher packages. Never execute an installer or AppImage."""
import dataclasses
import fcntl
import functools
import html
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
import uuid
import native_tools as n

REPOS = {'blockbench': 'JannisX11/blockbench', 'lmms': 'LMMS/lmms',
         'vscodium': 'VSCodium/vscodium'}
RECEIPT = 'studio-portable.json'
MAX_UNPACKED = 4 * 1024 ** 3


@dataclasses.dataclass(frozen=True)
class Plan(n.InstallPlan):
    kind: str
    repair_executable: str = ''


def safe(path):
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise n.InstallError('Managed paths must be absolute and contain no symbolic links.')


def receipt(base):
    safe(base)
    path = base / RECEIPT
    if path.is_symlink() or path.stat().st_size > 1024 * 1024:
        raise n.InstallError('Invalid portable installation receipt.')
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get('entrypoint'), str):
        raise n.InstallError('Invalid portable installation receipt.')
    if data.get('application') not in n.OPTIONAL or base.parent != n.managed_root() / data['application']:
        raise n.InstallError('Invalid portable installation owner.')
    member = PurePosixPath(data['entrypoint'])
    if member.is_absolute() or '..' in member.parts:
        raise n.InstallError('Invalid managed executable.')
    return data


@functools.lru_cache(maxsize=100000)
def _cached_hash(path, identity):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def complete(base, data):
    files = data.get('files', {})
    if not isinstance(files, dict) or data['entrypoint'] not in files:
        return False
    total = 0
    for name, digest in files.items():
        if not isinstance(name, str) or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            return False
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts:
            return False
        path = base / name
        safe(path)
        if not path.is_file() or path.stat().st_size > MAX_UNPACKED:
            return False
        stat = path.stat()
        total += stat.st_size
        if total > MAX_UNPACKED:
            return False
        identity = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        if _cached_hash(str(path), identity) != digest:
            return False
    return n.executable(base / data['entrypoint'])


def detected_path(app):
    root = n.managed_root() / app
    for base in sorted(root.glob('*'), reverse=True):
        try:
            data = receipt(base)
            path = base / data['entrypoint']
            if complete(base, data):
                return str(path)
        except (OSError, ValueError, KeyError, n.InstallError):
            pass
    return None


def repairable(config, app):
    explicit = config.get(app + '_path')
    for base in (n.managed_root() / app).glob('*'):
        try:
            data = receipt(base)
            path = base / data['entrypoint']
            if (not explicit or explicit == str(path)) and not complete(base, data):
                return True
        except (OSError, ValueError, KeyError, n.InstallError):
            pass
    return False


def repaired_path(config, app):
    explicit = config.get(app + '_path')
    if not explicit or not repairable(config, app):
        return None
    for base in sorted((n.managed_root() / app).glob('*'), reverse=True):
        try:
            data = receipt(base)
            path = base / data['entrypoint']
            if data.get('repair_executable') == explicit and complete(base, data):
                return str(path)
        except (OSError, ValueError, KeyError, n.InstallError):
            pass
    return None


def checksum(manifest, asset, algorithm='sha256'):
    hashes = []
    for line in manifest.decode('utf-8').splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].lstrip('*') == asset:
            hashes.append(fields[0].lower())
    if len(hashes) != 1 or not re.fullmatch('[0-9a-f]{' + str(hashlib.new(algorithm).digest_size * 2) + '}', hashes[0]):
        raise n.InstallError('No unambiguous publisher checksum. Use Official guidance.')
    return hashes[0]


def prepare(config, app, cancel=None):
    if n.platform.system() != 'Linux':
        raise n.InstallError('Optional automatic installers support Linux only. Use Official guidance.')
    arch = {'x86_64': 'x64', 'amd64': 'x64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(n.platform.machine().lower())
    if not arch:
        raise n.InstallError('Unsupported CPU architecture. Use Official guidance.')
    status = n.inspect(config, app)
    if status['status'] != 'Missing' and not status.get('repairable'):
        raise n.InstallError('Existing executable or override preserved. Review it before installing.')
    repair = config.get(app + '_path', '') if status.get('repairable') else ''
    if app in ('blockbench', 'lmms', 'krita') and arch != 'x64':
        raise n.InstallError('No reviewed ARM64 AppImage layout. Use Official guidance.')
    if app in REPOS:
        repo = REPOS[app]
        source = 'https://api.github.com/repos/' + repo + '/releases/latest'
        release = json.loads(n._metadata(source, cancel=cancel))
        version = release.get('tag_name', '')
        if release.get('draft') or release.get('prerelease'):
            raise n.InstallError('Only stable publisher releases are supported.')
        if app == 'vscodium':
            pattern = r'VSCodium-linux-' + arch + r'-[0-9.]+\.tar\.gz'
            kind, member = 'tar', 'bin/codium'
        else:
            if arch != 'x64':
                raise n.InstallError('No reviewed ARM64 AppImage layout. Use Official guidance.')
            pattern = (r'Blockbench_[0-9.]+\.AppImage' if app == 'blockbench'
                       else r'lmms-[0-9.]+-linux-x86_64(?:\.AppImage)?')
            kind, member = 'appimage', app + '.AppImage'
        assets = [a for a in release.get('assets', []) if re.fullmatch(pattern, a.get('name', ''))]
        if len(assets) != 1:
            raise n.InstallError('No unique supported publisher asset. Use Official guidance.')
        asset = assets[0]['name']
        url = 'https://github.com/' + repo + '/releases/download/' + version + '/' + asset
        if assets[0].get('browser_download_url') != url:
            raise n.InstallError('Unexpected publisher download URL.')
        digest = assets[0].get('digest') or ''
        if re.fullmatch('sha256:[0-9a-fA-F]{64}', digest):
            value = digest.split(':')[1].lower()
        else:
            # Older official releases may predate API digest support. Fail closed.
            raise n.InstallError('Publisher SHA-256 release metadata unavailable. Use Official guidance; no unverified install.')
    elif app == 'blender':
        page = n._metadata(n.PUBLISHERS[app], cancel=cancel).decode('utf-8')
        versions = set(re.findall(r'blender-([0-9]+\.[0-9]+\.[0-9]+)-linux-x64\.tar\.xz', page))
        if not versions:
            raise n.InstallError('Publisher stable Blender layout changed. Use Official guidance.')
        version = max(versions, key=lambda v: tuple(map(int, v.split('.'))))
        asset = 'blender-' + version + '-linux-' + arch + '.tar.xz'
        prefix = 'https://download.blender.org/release/Blender' + '.'.join(version.split('.')[:2]) + '/'
        url = prefix + asset
        source = prefix + 'blender-' + version + '.sha256'
        value = checksum(n._metadata(source, cancel=cancel), asset)
        kind, member = 'tar', asset.removesuffix('.tar.xz') + '/blender'
    elif app == 'krita':
        if arch != 'x64':
            raise n.InstallError('No reviewed ARM64 Krita AppImage. Use Official guidance.')
        page = n._metadata(n.PUBLISHERS[app], cancel=cancel).decode('utf-8')
        versions = set(re.findall(r'https://download.kde.org/stable/krita/([0-9.]+)/krita-\1-x86_64\.appimage', page))
        if len(versions) != 1:
            raise n.InstallError('Publisher stable Krita layout changed. Use Official guidance.')
        version = versions.pop()
        asset = 'krita-' + version + '-x86_64.appimage'
        # Stay on KDE infrastructure; never follow arbitrary mirror redirects.
        url = 'https://download.kde.org/stable/krita/' + version + '/' + asset
        source = url + '.mirrorlist'
        details = n._metadata(source, cancel=cancel).decode('utf-8')
        text = html.unescape(re.sub('<[^>]*>', ' ', details))
        hashes = re.findall(r'SHA-?256(?:\s*(?:Hash|Sum|hash|sum))?\s*:?\s*([0-9a-fA-F]{64})\b', text)
        if len(hashes) != 1:
            raise n.InstallError('KDE SHA-256 details unavailable. Use Official guidance.')
        value = hashes[0].lower()
        kind, member = 'appimage', 'krita.AppImage'
    else:
        raise n.InstallError('Unsupported portable tool.')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', version):
        raise n.InstallError('Invalid publisher release version.')
    # Additive repair: even an incomplete existing directory is never replaced.
    destination = n.managed_root() / app / version
    if destination.exists() or destination.is_symlink():
        destination = destination.with_name(version + '-repair-' + uuid.uuid4().hex[:12])
    return Plan(app, version, asset, url, 'sha256', value, source, member, destination, kind, repair)


def extract(archive, payload, cancel):
    """Copy regular tar files only; permit bounded internal links in a second pass."""
    with tarfile.open(archive, 'r:*') as container:
        entries, seen, size, links = [], set(), 0, []
        for index, item in enumerate(container):
            n._check_cancel(cancel)
            name = PurePosixPath(item.name)
            if item.isdir() and str(name) == '.':
                continue
            if (index >= 100000 or name.is_absolute() or '..' in name.parts
                    or '\\' in item.name or str(name) in seen or not name.parts):
                raise n.InstallError('Unsafe publisher archive path or entry count.')
            seen.add(str(name))
            size += item.size
            if size > MAX_UNPACKED or item.size < 0:
                raise n.InstallError('Unpacked publisher package exceeds size limits.')
            if not (item.isfile() or item.isdir() or item.issym() or item.islnk()):
                raise n.InstallError('Publisher archive contains a special file.')
            entries.append(item)
        for item in entries:
            n._check_cancel(cancel)
            target = payload / item.name
            if item.issym() or item.islnk():
                links.append(item)
                continue
            # Links have not been created, so ancestors cannot redirect writes.
            target.parent.mkdir(parents=True, exist_ok=True)
            if item.isdir():
                target.mkdir(exist_ok=True)
            else:
                with container.extractfile(item) as src, target.open('xb') as dst:
                    copied = 0
                    while chunk := src.read(256 * 1024):
                        n._check_cancel(cancel)
                        copied += len(chunk)
                        if copied > item.size:
                            raise n.InstallError('Archive member size mismatch.')
                        dst.write(chunk)
                    if copied != item.size:
                        raise n.InstallError('Truncated archive member.')
                target.chmod(0o700 if item.mode & 0o111 else 0o600)
        pending = {str(PurePosixPath(item.name)): item for item in links}
        active = set()
        def copy_link(name):
            nonlocal size
            n._check_cancel(cancel)
            if name in active or len(active) >= 64:
                raise n.InstallError('Cyclic or excessive publisher archive links.')
            item = pending[name]
            active.add(name)
            target = payload / name
            relative = PurePosixPath(item.linkname)
            if relative.is_absolute() or '\\' in item.linkname:
                raise n.InstallError('Unsafe publisher archive link.')
            source = (target.parent if item.issym() else payload) / item.linkname
            resolved = source.resolve()
            if not resolved.is_relative_to(payload.resolve()):
                raise n.InstallError('Publisher link escapes package.')
            source_name = str(resolved.relative_to(payload.resolve()))
            if source_name in pending:
                copy_link(source_name)
            if not resolved.is_file():
                raise n.InstallError('Publisher link has no regular target.')
            size += resolved.stat().st_size
            if size > MAX_UNPACKED:
                raise n.InstallError('Expanded publisher links exceed size limits.')
            target.parent.mkdir(parents=True, exist_ok=True)
            if any(p.is_symlink() for p in (target.parent, *target.parent.parents)):
                raise n.InstallError('Archive link ancestor is unsafe.')
            # Copy targets instead of publishing symlinks or hardlinks.
            with resolved.open('rb') as src, target.open('xb') as dst:
                while chunk := src.read(256 * 1024):
                    n._check_cancel(cancel)
                    dst.write(chunk)
            target.chmod(resolved.stat().st_mode & 0o700)
            active.remove(name)
            del pending[name]
        while pending:
            copy_link(next(iter(pending)))


def install(config, plan, progress=None, cancel=None):
    progress = progress or (lambda *args: None)
    # Re-resolve metadata before download: do not trust caller-supplied URLs/hash.
    reviewed = prepare(config, plan.application, cancel)
    for field in ('application', 'version', 'asset', 'url', 'algorithm', 'checksum', 'integrity_source', 'member', 'kind', 'repair_executable'):
        if getattr(plan, field) != getattr(reviewed, field):
            raise n.InstallError('Publisher release or configuration changed. Review a new plan.')
    parent = n.managed_root() / plan.application
    if plan.destination.parent != parent or not re.fullmatch(re.escape(plan.version) + r'(?:-repair-[0-9a-f]{12})?', plan.destination.name):
        raise n.InstallError('Invalid managed destination.')
    safe(plan.destination)
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(n.managed_root() / ('.' + plan.application + '.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise n.InstallError('Another installation is active.') from exc
        if plan.destination.exists() or plan.destination.is_symlink():
            raise n.InstallError('Destination exists; existing files preserved.')
        with tempfile.TemporaryDirectory(prefix='.install-', dir=n.managed_root()) as temp:
            stage = Path(temp)
            archive = stage / 'download'
            with archive.open('xb') as output:
                n._download(plan.url, output, 1024 ** 3, progress, cancel)
            progress('Verifying publisher SHA-256', 0, None)
            digest = hashlib.sha256()
            with archive.open('rb') as stream:
                while chunk := stream.read(256 * 1024):
                    n._check_cancel(cancel)
                    digest.update(chunk)
            if digest.hexdigest() != plan.checksum:
                raise n.InstallError('Checksum mismatch. Nothing installed.')
            payload = stage / 'payload'
            payload.mkdir(mode=0o700)
            progress('Preparing verified portable package', 0, None)
            if plan.kind == 'appimage':
                # No --appimage-extract invocation: that would execute downloaded code.
                with archive.open('rb') as stream:
                    header = stream.read(12)
                if header[:4] != b'\x7fELF' or header[8:11] != b'AI\x02':
                    raise n.InstallError('Unsupported AppImage format. Use Official guidance.')
                with archive.open('rb') as src, (payload / plan.member).open('xb') as dst:
                    while chunk := src.read(256 * 1024):
                        n._check_cancel(cancel)
                        dst.write(chunk)
                (payload / plan.member).chmod(0o700)
            else:
                extract(archive, payload, cancel)
            entry = payload / plan.member
            if not n.executable(entry):
                raise n.InstallError('Publisher package lacks the expected executable.')
            data = dataclasses.asdict(plan)
            data['entrypoint'] = plan.member
            data['files'] = {}
            for path in payload.rglob('*'):
                if path.is_file():
                    n._check_cancel(cancel)
                    with path.open('rb') as stream:
                        digest = hashlib.sha256()
                        while chunk := stream.read(256 * 1024):
                            n._check_cancel(cancel)
                            digest.update(chunk)
                        data['files'][str(path.relative_to(payload))] = digest.hexdigest()
            (payload / RECEIPT).write_text(json.dumps(data, default=str, indent=2))
            n._check_cancel(cancel)
            # Recheck settings/discovery after long downloads, under the process lock.
            status = n.inspect(config, plan.application)
            if status['status'] != 'Missing' and not status.get('repairable'):
                raise n.InstallError('Tool discovery changed; existing installation preserved.')
            safe(plan.destination)
            payload.rename(plan.destination)
    progress('Installed; launch compatibility is not tested', 1, 1)
    return str(plan.destination / plan.member)
