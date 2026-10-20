"""Verified canonical Codex packages; additive repair of Studio-owned installs.

Layout follows openai/codex rust-v0.163.0 scripts/codex_package/layout.py.
No credentials, settings, project directories, or downloaded code are accessed
by installation or passive inspection.
"""
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

import native_tools as n

API = 'https://api.github.com/repos/openai/codex/releases/'
RECEIPT = 'studio-runtime.json'
TARGETS = {a + b for a in ('x86_64', 'aarch64')
           for b in ('-unknown-linux-musl', '-apple-darwin')}


@dataclasses.dataclass(frozen=True)
class PackagePlan(n.InstallPlan):
    target: str
    repair_executable: str = ''
    existing_sha256: str = ''


def _json(path):
    if path.is_symlink() or path.stat().st_size > 1024 * 1024:
        raise n.InstallError('Invalid managed installation metadata.')
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise n.InstallError('Invalid managed installation metadata.')
    return value


def _hash(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > n.MAX_BINARY:
        raise n.InstallError('Expected a regular managed runtime file.')
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _safe(path):
    # Check every ancestor, including ancestors above the managed root.
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise n.InstallError('Managed installation paths must not contain symbolic links.')


def _owned(exe):
    """Only exact versioned Studio paths can be repaired; never PATH/npm/brew."""
    _safe(exe)
    relative = exe.relative_to(n.managed_root() / 'codex')
    parts = relative.parts
    if len(parts) not in (2, 3, 4) or not re.fullmatch(r'rust-v\d+\.\d+\.\d+', parts[0]):
        raise n.InstallError('Only versioned Studio-managed Codex installations can be repaired.')
    base = n.managed_root() / 'codex' / parts[0]
    if exe not in (base / 'codex', base / 'bin/codex', base / 'runtime/bin/codex'):
        raise n.InstallError('Unsupported managed executable layout.')
    if not n.executable(exe):
        raise n.InstallError('Existing Codex executable is unavailable; it will not be replaced.')
    return base, parts[0]


def _host_target():
    arch = {'amd64': 'x86_64', 'x86_64': 'x86_64', 'arm64': 'aarch64', 'aarch64': 'aarch64'}.get(n.platform.machine().lower())
    system = n.platform.system()
    if not arch or system not in ('Linux', 'Darwin'):
        raise n.InstallError('Automatic Codex installation supports Linux and macOS x86_64 and ARM64 only.')
    return arch + ('-apple-darwin' if system == 'Darwin' else '-unknown-linux-musl')


def _required(target):
    files = ['bin/codex', 'bin/codex-code-mode-host', 'codex-path/rg', 'codex-package.json']
    if '-linux-' in target:
        files.append('codex-resources/bwrap')
    return files


def _manifest(root, version, target):
    expected = dict(layoutVersion=1, version=version.removeprefix('rust-v'),
                    target=target, variant='codex', entrypoint='bin/codex',
                    resourcesDir='codex-resources', pathDir='codex-path')
    actual = _json(root / 'codex-package.json')
    if any(actual.get(k) != v for k, v in expected.items()):
        raise n.InstallError('Publisher package version, target, or layout mismatch.')
    for name in _required(target):
        path = root / name
        _safe(path)
        if not path.is_file() or (name != 'codex-package.json' and not n.executable(path)):
            raise n.InstallError('Missing runtime component: ' + name)


def _verified(root):
    receipt = _json(root / RECEIPT)
    version, target = receipt['version'], receipt['target']
    if target not in TARGETS or not re.fullmatch(r'rust-v\d+\.\d+\.\d+', version):
        raise n.InstallError('Invalid runtime receipt version or target.')
    _manifest(root, version, target)
    files = receipt['files']
    if not isinstance(files, dict) or set(files) != set(_required(target)):
        raise n.InstallError('Runtime receipt does not cover required components.')
    for name, digest in files.items():
        if _hash(root / name) != digest:
            raise n.InstallError('Runtime integrity failure: ' + name)
    return receipt


def repaired_path(path):
    try:
        base, _ = _owned(path)
        if path == base / 'codex':
            receipt = _verified(base / 'runtime')
            if receipt.get('legacy_sha256') == _hash(path):
                return base / 'runtime/bin/codex'
    except (OSError, ValueError, KeyError, TypeError, n.InstallError):
        pass
    return path


def inspect_runtime(path):
    result = dict(status='Executable detected', path=str(path), repairable=False,
                  runtime_ready=False, detail='Runtime companions/version are unverified. Use Check runtime; authentication and tool execution require a live test.')
    try:
        base, _ = _owned(path)
        result['repairable'] = True
        root = path.parent.parent if path.parent.name == 'bin' else base
        receipt = _verified(root)
        result.update(status='Components verified', repairable=False,
                      detail='Matching publisher package components verified (' + receipt['version'] + '). Runtime and authenticated tool execution are not tested.')
    except (OSError, ValueError, KeyError, TypeError, n.InstallError) as exc:
        if result['repairable']:
            result.update(status='Repair needed', detail='Executable detected; incomplete or unverified runtime: ' + str(exc))
    return result


def prepare(config, cancel=None):
    status = n.inspect(config, 'codex')
    repair, existing = '', ''
    if status['status'] != 'Missing':
        if not status.get('repairable'):
            raise n.InstallError('Existing Codex is not an incomplete Studio-managed installation. Use official guidance.')
        repair = status['path']
        base, version = _owned(Path(repair))
        existing = _hash(Path(repair))
        destination = base / 'runtime' if Path(repair) == base / 'codex' else Path(repair).parent.parent
        metadata_url = API + 'tags/' + version
    else:
        metadata_url = API + 'latest'
        destination = None
    target = _host_target()
    release = json.loads(n._metadata(metadata_url, cancel=cancel))
    tag = release.get('tag_name', '')
    if (release.get('draft') or release.get('prerelease') or not re.fullmatch(r'rust-v\d+\.\d+\.\d+', tag)
            or (repair and tag != version)):
        raise n.InstallError('Publisher release version mismatch or unsupported stable release.')
    asset_name = 'codex-package-' + target + '.tar.gz'
    matches = [a for a in release.get('assets', []) if a.get('name') == asset_name]
    url = 'https://github.com/openai/codex/releases/download/' + tag + '/' + asset_name
    if len(matches) != 1 or matches[0].get('browser_download_url') != url:
        raise n.InstallError('Publisher canonical runtime package is unavailable or ambiguous. No single-binary fallback.')
    digest = matches[0].get('digest', '') or ''
    if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
        raise n.InstallError('Trusted publisher release SHA-256 metadata is unavailable.')
    return PackagePlan('codex', tag, asset_name, url, 'sha256', digest.split(':')[1].lower(),
                       API + 'tags/' + tag, 'bin/codex', destination or n.managed_root() / 'codex' / tag,
                       target, repair, existing)


def _extract(archive, root, plan, cancel):
    required = set(_required(plan.target))
    seen = set()
    total = 0
    with tarfile.open(archive, 'r:gz') as container:
        for index, member in enumerate(container):
            n._check_cancel(cancel)
            name = member.name
            # Strict canonical layout. No links, paths outside layout, or duplicate entries.
            if (index >= 256 or name in seen or name.startswith('/') or '..' in Path(name).parts
                    or not (member.isdir() or member.isfile())):
                raise n.InstallError('Unsafe or duplicate publisher package entry.')
            seen.add(name)
            total += member.size
            if member.size < 0 or total > n.MAX_BINARY:
                raise n.InstallError('Publisher runtime package exceeds size limits.')
            if name not in required:
                continue
            if not member.isfile() or not 0 < member.size <= n.MAX_BINARY:
                raise n.InstallError('Publisher package lacks a regular executable or metadata.')
            output = root / name
            output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with container.extractfile(member) as source, output.open('xb') as dest:
                copied = 0
                while chunk := source.read(256 * 1024):
                    n._check_cancel(cancel)
                    copied += len(chunk)
                    dest.write(chunk)
                if copied != member.size:
                    raise n.InstallError('Incomplete runtime component.')
            output.chmod(0o600 if name.endswith('.json') else 0o700)
    if not required <= seen:
        raise n.InstallError('Publisher package lacks required runtime components: ' + ', '.join(sorted(required - seen)))
    (root / 'codex-resources').mkdir(exist_ok=True, mode=0o700)
    _manifest(root, plan.version, plan.target)


def install_package(config, plan, progress=None, cancel=None):
    if not isinstance(plan, PackagePlan) or plan.target != _host_target():
        raise n.InstallError('Invalid Codex runtime installation plan; prepare again.')
    # Re-fetch exact-tag publisher metadata to bind all reviewed fields, including
    # digests, at execution time. Repair never follows latest.
    status = n.inspect(config, 'codex')
    if plan.repair_executable:
        if status['path'] != plan.repair_executable or not status.get('repairable'):
            raise n.InstallError('Tool configuration or runtime changed; recheck before repair.')
        base, version = _owned(Path(plan.repair_executable))
        expected = base / 'runtime' if Path(plan.repair_executable) == base / 'codex' else Path(plan.repair_executable).parent.parent
        if version != plan.version or _hash(Path(plan.repair_executable)) != plan.existing_sha256:
            raise n.InstallError('Existing Codex changed; nothing replaced.')
    else:
        expected = n.managed_root() / 'codex' / plan.version
        if status['status'] != 'Missing':
            raise n.InstallError('Tool configuration or discovery changed. Recheck before installing.')
    if (not re.fullmatch(r'rust-v\d+\.\d+\.\d+', plan.version) or plan.destination != expected
            or plan.integrity_source != API + 'tags/' + plan.version or plan.member != 'bin/codex'
            or plan.algorithm != 'sha256' or not re.fullmatch('[0-9a-f]{64}', plan.checksum)
            or plan.asset != 'codex-package-' + plan.target + '.tar.gz'
            or plan.url != 'https://github.com/openai/codex/releases/download/' + plan.version + '/' + plan.asset):
        raise n.InstallError('Installation plan is invalid; prepare again.')
    _safe(plan.destination)
    progress = progress or (lambda *args: None)
    root = n.managed_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(root / '.codex.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        try:
            n.fcntl.flock(lock, n.fcntl.LOCK_EX | n.fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise n.InstallError('Another installation is active. Retry after it finishes.') from exc
        metadata = json.loads(n._metadata(plan.integrity_source, cancel=cancel))
        assets = [a for a in metadata.get('assets', []) if a.get('name') == plan.asset]
        if (metadata.get('tag_name') != plan.version or metadata.get('draft') or metadata.get('prerelease')
                or len(assets) != 1 or assets[0].get('browser_download_url') != plan.url
                or (assets[0].get('digest') or '').lower() != 'sha256:' + plan.checksum):
            raise n.InstallError('Publisher metadata changed or version mismatch; prepare again.')
        if not plan.repair_executable and plan.destination.exists():
            raise n.InstallError('Destination already exists; nothing overwritten.')
        with tempfile.TemporaryDirectory(prefix='.install-codex-', dir=root) as temp:
            stage = Path(temp)
            archive = stage / 'download'
            with archive.open('xb') as output:
                n._download(plan.url, output, n.MAX_DOWNLOAD, progress, cancel)
            progress('Verifying publisher package SHA-256', 0, None)
            if _hash(archive) != plan.checksum:
                raise n.InstallError('Checksum mismatch. Nothing installed.')
            payload = stage / 'payload'
            payload.mkdir(mode=0o700)
            progress('Extracting matching runtime components', 0, None)
            _extract(archive, payload, plan, cancel)
            files = {name: _hash(payload / name) for name in _required(plan.target)}
            receipt = dict(version=plan.version, target=plan.target, asset=plan.asset,
                           checksum=plan.checksum, integrity_source=plan.integrity_source, files=files)
            if plan.repair_executable:
                # Verify the retained executable against the publisher package,
                # rather than trusting a directory name or a version string.
                if _hash(Path(plan.repair_executable)) != files['bin/codex']:
                    # Some publisher distributions sign/strip the standalone and
                    # package entrypoints differently. Verify the original against
                    # the same release's standalone artifact before accepting it.
                    _verify_standalone(plan, metadata, stage, progress, cancel)
                    receipt['retained_executable_source'] = 'codex-' + plan.target + '.tar.gz'
                    if Path(plan.repair_executable) != base / 'codex':
                        # Keep the already verified entrypoint in a canonical repair.
                        # Staging is private; publication still never replaces files.
                        import shutil
                        shutil.copyfile(plan.repair_executable, payload / 'bin/codex')
                        receipt['files']['bin/codex'] = plan.existing_sha256
                if Path(plan.repair_executable) == base / 'codex':
                    receipt['legacy_sha256'] = plan.existing_sha256
            (payload / RECEIPT).write_text(json.dumps(receipt, indent=2))
            n._check_cancel(cancel)
            _safe(plan.destination)
            if plan.destination.exists():
                _add_missing(payload, plan.destination, cancel)
            else:
                plan.destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                payload.rename(plan.destination)
    progress('Components verified; use Check runtime, then test authenticated tool execution', 1, 1)
    return str(plan.destination / 'bin/codex')



def _verify_standalone(plan, release, stage, progress, cancel):
    member = 'codex-' + plan.target
    name = member + '.tar.gz'
    matches = [a for a in release.get('assets', []) if a.get('name') == name]
    url = 'https://github.com/openai/codex/releases/download/' + plan.version + '/' + name
    if (len(matches) != 1 or matches[0].get('browser_download_url') != url
            or not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', matches[0].get('digest') or '')):
        raise n.InstallError('Existing executable differs from matching publisher package; standalone verification unavailable. Nothing replaced.')
    archive = stage / 'standalone-download'
    with archive.open('xb') as output:
        n._download(url, output, n.MAX_DOWNLOAD, progress, cancel)
    checksum = matches[0]['digest'].split(':')[1].lower()
    if _hash(archive) != checksum:
        raise n.InstallError('Standalone checksum mismatch. Nothing replaced.')
    standalone = dataclasses.replace(plan, member=member)
    original = stage / 'original-codex'
    n._extract_binary(archive, standalone, original, cancel)
    if _hash(original) != plan.existing_sha256:
        raise n.InstallError('Existing executable differs from matching publisher release. Nothing replaced.')

def _add_missing(payload, destination, cancel):
    # Preflight every conflict before publishing anything. Never replace existing
    # files, even broken/non-executable companions or old receipt files.
    paths = sorted(p for p in payload.rglob('*') if p.is_file())
    for path in paths:
        target = destination / path.relative_to(payload)
        _safe(target)
        if target.exists() and (_hash(target) != _hash(path) or (os.access(path, os.X_OK) and not n.executable(target))):
            raise n.InstallError('Existing runtime component conflicts; nothing overwritten: ' + str(target))
    added = []
    try:
        for path in sorted(paths, key=lambda p: p.name == RECEIPT):
            n._check_cancel(cancel)
            target = destination / path.relative_to(payload)
            _safe(target)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if not target.exists():
                # Hard-link publication is atomic and refuses overwrites.
                os.link(path, target)
                added.append(target)
        (destination / 'codex-resources').mkdir(exist_ok=True, mode=0o700)
    except BaseException:
        for path in reversed(added):
            path.unlink()
        raise


def check_runtime(config):
    """User-requested smoke check in isolated scratch space; no model/auth calls."""
    path = Path(n.discover(config, 'codex'))
    status = inspect_runtime(path)
    if status['status'] != 'Components verified':
        raise n.InstallError('Verify or repair runtime components before executing the runtime check.')
    root = path.parent.parent
    receipt = _verified(root)
    commands = [(path, '--version'), (root / 'bin/codex-code-mode-host', '--help'),
                (root / 'codex-path/rg', '--version')]
    if '-linux-' in receipt['target']:
        commands.append((root / 'codex-resources/bwrap', '--version'))
    with tempfile.TemporaryDirectory(prefix='studio-codex-check-') as tmp:
        # Do not inherit credential, proxy, telemetry, or CODEX_* overrides.
        env = {'HOME': tmp, 'CODEX_HOME': tmp, 'PATH': '/usr/bin:/bin', 'TMPDIR': tmp}
        for executable, flag in commands:
            try:
                result = subprocess.run([str(executable), flag], cwd=tmp, env=env,
                                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, timeout=15, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise n.InstallError('Runtime check failed for ' + executable.name + ': ' + str(exc)) from exc
            if result.returncode != 0:
                raise n.InstallError('Runtime check failed for ' + executable.name + ' (exit ' + str(result.returncode) + ').')
            if executable == path and not re.search(rb'(?<![0-9.])' + re.escape(receipt['version'].removeprefix('rust-v').encode()) + rb'(?![0-9.])', result.stdout):
                raise n.InstallError('Runtime executable version mismatch.')
    status.update(status='Runtime checked', runtime_ready=True,
                  detail='Codex version and companion startup checks passed. Authentication, app-server tool execution, and sandbox behavior still need a live test.')
    return status
