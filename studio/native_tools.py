"""Native application adapters. Commands are argv lists, never shell strings."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
import project_client
import project_helper

ADAPTERS = {
    'godot': ('godot', 'godot4', 'godot-mono'),
    'blender': ('blender',),
    'blockbench': ('blockbench',),
    'lmms': ('lmms',),
    'krita': ('krita',),
    'codex': ('codex',),
    'vscodium': ('codium', 'vscodium'),
}


LABELS = dict(godot='Godot', blender='Blender', blockbench='Blockbench',
              lmms='LMMS', krita='Krita', codex='Codex', vscodium='VSCodium')
# Bounded patterns: never crawl projects or execute candidates during discovery.
PATTERNS = {
    'godot': ('Godot*', '*/Godot*'),
    'blender': ('blender', '*/blender'),
    'blockbench': ('blockbench', '*/blockbench', 'squashfs-root/AppRun', '*/squashfs-root/AppRun', 'Blockbench*.AppImage', '*/Blockbench*.AppImage'),
    'lmms': ('lmms', 'squashfs-root/AppRun', '*/squashfs-root/AppRun', 'lmms*.AppImage', '*/lmms*.AppImage'),
    'krita': ('krita', 'squashfs-root/AppRun', '*/squashfs-root/AppRun', 'krita*.appimage', '*/krita*.appimage', 'krita*.AppImage', '*/krita*.AppImage'),
    'codex': ('codex', 'bin/codex', '*/bin/codex', '*/codex'),
    'vscodium': ('codium', 'bin/codium', '*/bin/codium', 'squashfs-root/AppRun'),
}


def executable(path):
    path = Path(path).expanduser()
    return path.is_absolute() and path.is_file() and os.access(path, os.X_OK)


def tool_roots(config):
    roots = config.get('tool_dirs', [])
    if not isinstance(roots, list) or any(not isinstance(p, str) or not Path(p).expanduser().is_absolute() for p in roots):
        raise ValueError('Tool directories must be absolute paths, one per line.')
    return [Path(p).expanduser() for p in roots] + [
        Path.home() / '.local/share/optiplex-studio/tools',
        Path.home() / '.tools', Path('/projects/.tools')]


def discover(config, application):
    if application not in ADAPTERS:
        raise ValueError('Unsupported native application.')
    explicit = config.get(application + '_path')
    if application in OPTIONAL:
        from portable_install import repaired_path
        repaired = repaired_path(config, application)
        if repaired:
            return repaired
        from portable_install import repairable
        if explicit and repairable(config, application):
            raise RuntimeError('Managed tool is incomplete or damaged; use Repair in Tools & Setup.')
    if explicit:
        if not executable(explicit):
            raise ValueError('Choose an executable absolute path for ' + application + '.')
        return _codex_runtime_path(Path(explicit).expanduser()) if application == 'codex' else str(Path(explicit).expanduser())
    for candidate in ADAPTERS[application]:
        found = shutil.which(candidate)
        if found:
            return _codex_runtime_path(Path(found)) if application == 'codex' else found
    for candidate in ADAPTERS[application]:
        fallback = Path.home() / '.local/bin' / candidate
        if executable(fallback):
            return _codex_runtime_path(fallback) if application == 'codex' else str(fallback)
    # Versioned managed payloads have exact receipt-bound entrypoints.
    if application in OPTIONAL:
        from portable_install import detected_path
        managed = detected_path(application)
        if managed:
            return managed
    for root in tool_roots(config):
        for folder in (root / (application + '-native'), root / application):
            for pattern in PATTERNS[application]:
                for candidate in sorted(folder.glob(pattern), reverse=True):
                    if application in OPTIONAL and folder == managed_root() / application:
                        # Receipt packages are discovered only after integrity checks.
                        # Legacy/manual layouts in the same root remain available.
                        from portable_install import RECEIPT
                        if any((parent / RECEIPT).exists() for parent in candidate.parents
                               if parent != folder and parent.is_relative_to(folder)):
                            continue
                    if executable(candidate):
                        return _codex_runtime_path(candidate) if application == 'codex' else str(candidate)
    raise RuntimeError('Install ' + LABELS[application] + ' locally or choose its executable in Tools & Setup.')


def inspect(config, application):
    """Passive verification only: never execute untrusted binaries or version flags."""
    try:
        path = discover(config, application)
        if application == 'codex':
            from codex_install import inspect_runtime
            return inspect_runtime(Path(path))
        return {'status': 'Ready', 'path': path,
                'detail': 'Executable available; runtime/version compatibility is not tested.'}
    except (ValueError, OSError, RuntimeError) as exc:
        if application in OPTIONAL:
            from portable_install import repairable
            if repairable(config, application):
                return dict(status='Repair needed', path='', detail=str(exc), repairable=True)
        return {'status': 'Needs attention' if config.get(application + '_path') else 'Missing',
                'path': '', 'detail': str(exc)}



CORE_ALPHA_TOOLS = ('godot', 'blender', 'lmms', 'codex')


def readiness_summary(application, result, authentication=None):
    """Present truthful user-facing health without running arbitrary executables.

    Passive discovery is never proof that a GUI editor can run or that a Codex
    account can complete a model request. Return (summary, needs_attention).
    """
    status = result['status']
    if status == 'Missing':
        return ('Missing · install or select in Settings', application in CORE_ALPHA_TOOLS)
    if status == 'Repair needed':
        return ('Repair needed · repair in Settings', True)
    if status in ('Error', 'Broken'):
        return ('Error · check installation in Settings', True)
    if status == 'Needs attention':
        return ('Needs attention · check executable in Settings', True)
    if application == 'codex':
        if status == 'Components verified':
            if authentication == 'Signed in':
                return ('CLI signed in · live AI not verified', False)
            if authentication == 'Setup required':
                return ('Installed · connect Codex in Settings', True)
            if authentication == 'Error':
                return ('Sign-in check failed · retry in Settings', True)
            return ('Runtime components verified · sign-in not confirmed', True)
        return ('Executable detected · Codex runtime not verified', True)
    if status == 'Ready':
        return ('Executable detected · launch not verified', False)
    return ('Needs attention · inspect in Settings', True)


def codex_authentication(config):
    """Read-only CLI credential check; this is not proof of live model access.

    Deliberately never display arbitrary CLI output, which could contain secrets.
    A nonzero exit without a definite logged-out message is an error, not proof
    that the user needs to sign in again.
    """
    try:
        executable_path = discover(config, 'codex')
    except (ValueError, OSError, RuntimeError):
        return {'status': 'Missing', 'detail': 'Install or select Codex in Settings.'}
    try:
        result = subprocess.run([executable_path, 'login', 'status'],
                                capture_output=True, text=True, timeout=12,
                                stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {'status': 'Error', 'detail': 'Codex login status timed out. Retry the check.'}
    except OSError:
        return {'status': 'Error', 'detail': 'Could not start Codex login status. Check the executable and retry.'}
    message = (result.stdout + '\n' + result.stderr).lower()
    if 'not logged in' in message or 'not authenticated' in message:
        return {'status': 'Setup required', 'detail': 'Connect a supported account in Settings.'}
    if result.returncode == 0 and 'logged in' in message:
        return {'status': 'Signed in', 'detail': 'Codex reports saved authentication; live AI access has not been tested.'}
    return {'status': 'Error', 'detail': 'Codex could not confirm authentication. Retry; do not delete credentials.'}


def begin_codex_login(config, *, device_auth=False):
    """Launch the official CLI sign-in in a terminal; never handle tokens."""
    import core
    executable_path = discover(config, 'codex')
    args = [executable_path, 'login']
    if device_auth:
        args.append('--device-auth')
    terminal = core.terminal_args(args)
    subprocess.Popen(terminal, stdin=subprocess.DEVNULL, start_new_session=True)
    if device_auth:
        return 'In the Codex terminal, follow the device-code instructions. Then verify sign-in.'
    return 'Follow the official Codex sign-in instructions in the terminal/browser, then verify sign-in.'

def project_directory(config, project):
    project_helper.project_name(project)
    base = project_client.workspace(config)
    checked = project_helper.Project(base, project)
    checked.close()
    return base / project


def command(config, application, project=None):
    executable = discover(config, application)
    cwd = project_directory(config, project) if project else project_client.workspace(config)
    args = [executable]
    # Each editor starts in the most relevant existing project-owned folder.
    # Do not invent native file argv or create directories as a side effect.
    if project:
        folder = {'blender': 'models', 'blockbench': 'models',
                  'lmms': 'music', 'krita': 'art'}.get(application)
        if folder:
            target = cwd / folder
            if target.is_dir() and not target.is_symlink():
                cwd = target
    if application == 'vscodium':
        if not project:
            raise ValueError('Select a project to open in VSCodium.')
        args += ['--', str(cwd)]
    if application == 'godot':
        if not project:
            raise ValueError('Select a Studio project.')
        if not (cwd / 'project.godot').is_file() or (cwd / 'project.godot').is_symlink():
            raise ValueError('This project has no valid Godot scaffold. Use Add Godot in Creative Tools.')
        args += ['--editor', '--path', str(cwd)]
    return args, cwd


def launch(config, application, project=None):
    args, cwd = command(config, application, project)
    # An empty workspace need not be created just to open a native tool.
    subprocess.Popen(args, cwd=str(cwd) if cwd.exists() else None,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return application.title() + ' launched locally.'


def launch_game(config, project):
    """Play the existing Godot main scene without entering editor mode.

    Same project validation and executable as Edit; does not mutate project
    settings, import assets, open an unrelated workspace or use a shell.
    """
    args, cwd = command(config, 'godot', project)
    if args[1:3] != ['--editor', '--path'] or args[3] != str(cwd):
        raise RuntimeError('Godot editor command did not match the selected Project.')
    subprocess.Popen([args[0], '--path', str(cwd)], cwd=str(cwd),
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return 'Launched ' + project + ' in Godot. Check the game window for actual playback.'


def codex_command(config, action, project, session_id=None, prompt=None, all_sessions=False):
    if action not in ('code', 'resume'):
        raise ValueError('Unsupported Codex action.')
    if all_sessions:
        raise ValueError('Use global conversation discovery to select an owning Project first.')
    if action == 'resume':
        if session_id is None:
            raise ValueError('Select a project conversation before resuming.')
        from conversation_store import require_owner
        session_id = require_owner(config, project, session_id)
    cwd = project_directory(config, project)
    args = [discover(config, 'codex'), '--no-daemon', '-C', str(cwd)]
    if action == 'resume':
        args.append('resume')
        if session_id is not None:
            args.append(str(uuid.UUID(session_id)))
    elif session_id is not None or all_sessions:
        raise ValueError('Session options require resume.')
    if prompt is not None:
        if (action != 'code' or not isinstance(prompt, str) or not prompt.strip()
                or len(prompt) > 32000 or '\0' in prompt):
            raise ValueError('Enter a prompt of 1–32,000 characters without NUL characters.')
        # End option parsing: even a prompt beginning with '-' is literal text.
        args.extend(['--', prompt])
    if action == 'code':
        checked = project_helper.Project(project_client.workspace(config), project)
        try:
            try:
                memory = checked.read('AI_MEMORY.md', project_helper.MAX_TEXT).decode('utf-8')
            except FileNotFoundError:
                memory = ''
        finally:
            checked.close()
        if '\0' in memory:
            raise ValueError('Project AI memory contains NUL characters. Edit AI Memory before launching.')
        if len(memory.encode('utf-8')) > 24000:
            raise ValueError('Project AI memory exceeds the 24 KB launch limit. Shorten it in Project Documents.')
        if memory.strip():
            context = 'Project context from AI_MEMORY.md (user-maintained):\n' + memory
            if prompt is not None:
                args[-1] = context + '\n\nTask:\n' + prompt
            else:
                args.extend(['--', context + '\n\nAsk the user what to work on next.'])
    return args, cwd


def run_action(config, action, project, on_started=None, on_error=None,
               on_progress=None, session_id=None, prompt=None, all_sessions=False):
    if action == 'edit':
        return launch(config, 'godot', project)
    import core
    args, cwd = codex_command(config, action, project, session_id, prompt, all_sessions)
    terminal = core.terminal_args(args)
    if '--window' in terminal and any(arg.startswith('--command=') for arg in terminal):
        # XFCE's launcher may exit after handing off to its server. Its status
        # describes the launch request, never the lifetime or exit code of Codex.
        terminal.insert(1, '--working-directory=' + str(cwd))
        try:
            with subprocess.Popen(terminal, cwd=str(cwd), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True,
                                  start_new_session=True) as launcher:
                stdout, stderr = launcher.communicate()
        except OSError as exc:
            raise RuntimeError('Local Codex terminal launch failed: ' + str(exc)) from exc
        if launcher.returncode:
            raise RuntimeError(f'Local Codex terminal launch failed (exit {launcher.returncode}); '
                               'Codex exit status is unknown. ' + (stderr or stdout)[-3000:])
        if on_started:
            on_started()
        return 'Codex terminal launched. Session termination is not tracked by XFCE.'
    # Foreground adapters: preserve the actual CLI exit status.
    with tempfile.TemporaryDirectory(prefix='studio-local-codex-') as directory:
        status = Path(directory) / 'status'
        wrapped = ['/bin/sh', '-c',
                   'status=$1; shift; "$@"; result=$?; printf "%s" "$result" > "$status"; exit "$result"',
                   'studio-local-terminal', str(status)] + args
        with subprocess.Popen(core.terminal_args(wrapped), cwd=str(cwd),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              start_new_session=True) as result:
            if on_started:
                on_started()
            stdout, stderr = result.communicate()
        if not status.exists():
            raise RuntimeError('Local Codex terminal launch failed or session status is unavailable: ' + (stderr or stdout)[-3000:])
        code = int(status.read_text())
        if code:
            raise RuntimeError(f'Local Codex session failed (exit {code}). Check the local Codex installation and authentication. ' + (stderr or stdout)[-3000:])
    return 'Codex conversation closed.'


# Guided installation deliberately has no package-manager or shell-script fallback.
import dataclasses
import fcntl
import hashlib
import json
import platform
import re
import tarfile
import urllib.parse
import urllib.request
import zipfile

PUBLISHERS = {
    'godot': 'https://godotengine.org/download/linux/',
    'codex': 'https://developers.openai.com/codex/cli',
    'blender': 'https://www.blender.org/download/',
    'blockbench': 'https://www.blockbench.net/downloads',
    'krita': 'https://krita.org/en/download/',
    'lmms': 'https://lmms.io/download',
    'vscodium': 'https://vscodium.com/',
}
OPTIONAL = ('blender', 'krita', 'blockbench', 'lmms', 'vscodium')
INSTALLERS = ('godot', 'codex', *OPTIONAL)
REPOSITORIES = {'godot': 'godotengine/godot-builds', 'codex': 'openai/codex'}
MAX_DOWNLOAD = 512 * 1024 * 1024
MAX_BINARY = 1024 * 1024 * 1024
CODEX_AUTH = ('Codex installation and sign-in are separate. Open a terminal and run the '
              'executable shown below followed by login. Choose Sign in with ChatGPT '
              'and complete browser sign-in. If needed, use login --device-auth '
              '(requires device login enabled for your account/workspace). API-key '
              'sign-in is also available through Codex; API billing is separate. '
              'Never paste credentials into Studio. Studio does not read or change '
              'Codex credentials and does not claim you are authenticated.')


class InstallError(RuntimeError):
    pass


class InstallCancelled(InstallError):
    pass


@dataclasses.dataclass(frozen=True)
class InstallPlan:
    application: str
    version: str
    asset: str
    url: str
    algorithm: str
    checksum: str
    integrity_source: str
    member: str
    destination: Path


def managed_root():
    # Intentionally fixed: never install into project or configured discovery roots.
    return Path.home() / '.local/share/optiplex-studio/tools'


def _check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise InstallCancelled('Installation cancelled. You can retry.')


def _trusted_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'https' or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.hostname not in {
                'api.github.com', 'github.com', 'release-assets.githubusercontent.com',
                'objects.githubusercontent.com', 'www.blender.org', 'download.blender.org',
                'krita.org', 'download.kde.org', 'files.kde.org'}):
        raise InstallError('Publisher download redirected outside trusted HTTPS release hosts.')
    return url


class _ReleaseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _trusted_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download(url, output, limit, progress, cancel):
    _check_cancel(cancel)
    request = urllib.request.Request(_trusted_url(url), headers={
        'User-Agent': 'OptiPlex-Studio-Setup',
        'Accept': ('application/vnd.github+json' if urllib.parse.urlsplit(url).hostname == 'api.github.com'
                   else 'application/octet-stream')})
    opener = urllib.request.build_opener(_ReleaseRedirect())
    with opener.open(request, timeout=30) as response:
        _trusted_url(response.geturl())
        length = response.headers.get('Content-Length')
        total = int(length) if length else None
        if total is not None and (total < 0 or total > limit):
            raise InstallError('Publisher download exceeds the size limit.')
        received = 0
        while True:
            _check_cancel(cancel)
            chunk = response.read(256 * 1024)
            if not chunk:
                break
            received += len(chunk)
            if received > limit:
                raise InstallError('Publisher download exceeds the size limit.')
            output.write(chunk)
            progress('Downloading', received, total)
        if total is not None and received != total:
            raise InstallError('Incomplete download. Retry when the connection is stable.')


def _metadata(url, limit=4 * 1024 * 1024, cancel=None):
    import io
    output = io.BytesIO()
    _download(url, output, limit, lambda *args: None, cancel)
    return output.getvalue()


def prepare_install(config, application, cancel=None):
    """Fetch only publisher metadata. No executable download or file changes."""
    if application in OPTIONAL:
        from portable_install import prepare
        return prepare(config, application, cancel)
    if application not in REPOSITORIES:
        raise InstallError('Unsupported tool.')
    if application == 'codex':
        from codex_install import prepare
        return prepare(config, cancel)
    status = inspect(config, application)
    if status['status'] != 'Missing':
        raise InstallError('An executable or configured path already exists. Review it in Tools & Setup.')
    if platform.system() != 'Linux':
        raise InstallError('Guided installation currently supports Linux only.')
    arch = {'x86_64': 'x86_64', 'amd64': 'x86_64',
            'aarch64': 'aarch64', 'arm64': 'aarch64'}.get(platform.machine().lower())
    if not arch:
        raise InstallError('Automatic installation supports Linux x86_64 and ARM64. Use official guidance and Choose Executable.')
    repo = REPOSITORIES[application]
    metadata_url = 'https://api.github.com/repos/' + repo + '/releases/latest'
    release = json.loads(_metadata(metadata_url, cancel=cancel))
    version = release.get('tag_name', '')
    if (release.get('draft') or release.get('prerelease')
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', version)):
        raise InstallError('Publisher did not provide a supported stable release.')
    if application == 'godot':
        if not re.fullmatch(r'4\.[0-9]+(?:\.[0-9]+)?-stable', version):
            raise InstallError('Only stable Godot 4 releases are supported by guided setup.')
        member = 'Godot_v' + version + '_linux.' + ('arm64' if arch == 'aarch64' else arch)
        asset_name = member + '.zip'
    else:
        member = 'codex-' + arch + '-unknown-linux-musl'
        asset_name = member + '.tar.gz'
    assets = {item['name']: item for item in release.get('assets', [])}
    if asset_name not in assets:
        raise InstallError('Publisher has no supported native archive for this architecture. Use official guidance.')
    prefix = 'https://github.com/' + repo + '/releases/download/' + version + '/'
    asset = assets[asset_name]
    url = prefix + asset_name
    if asset.get('browser_download_url') != url:
        raise InstallError('Unexpected publisher asset location.')
    if application == 'godot':
        source = prefix + 'SHA512-SUMS.txt'
        if assets.get('SHA512-SUMS.txt', {}).get('browser_download_url') != source:
            raise InstallError('Publisher checksum manifest is unavailable. Use official guidance.')
        manifest = _metadata(source, limit=1024 * 1024, cancel=cancel).decode('utf-8')
        matches = []
        for line in manifest.splitlines():
            fields = line.split()
            if len(fields) == 2 and fields[1].lstrip('*') == asset_name:
                matches.append(fields[0].lower())
        if len(matches) != 1 or not re.fullmatch('[0-9a-f]{128}', matches[0]):
            raise InstallError('Publisher manifest has no unambiguous SHA-512 checksum for this archive.')
        algorithm, checksum = 'sha512', matches[0]
    else:
        # GitHub computes the release asset digest, bound to the official publisher
        # repository over authenticated HTTPS. Never accept a mirror-side hash.
        source = metadata_url
        digest = asset.get('digest', '') or ''
        if not re.fullmatch('sha256:[0-9a-fA-F]{64}', digest):
            raise InstallError('Trusted publisher release SHA-256 metadata is unavailable. Use official guidance; no script will be run.')
        algorithm, checksum = digest.split(':')
        checksum = checksum.lower()
    return InstallPlan(application, version, asset_name, url, algorithm, checksum,
                       source, member, managed_root() / application / version)


def _extract_binary(archive, plan, output, cancel):
    if plan.application == 'godot':
        container = zipfile.ZipFile(archive)
        members = [m for m in container.infolist() if m.filename == plan.member]
        valid = len(members) == 1 and not members[0].is_dir()
        if valid:
            mode = members[0].external_attr >> 16
            valid = (mode & 0o170000) in (0, 0o100000)
        size = members[0].file_size if valid else MAX_BINARY + 1
    else:
        container = tarfile.open(archive, 'r:gz')
        members = []
        for index, member in enumerate(container):
            if index >= 256 or member.size > MAX_BINARY:
                container.close()
                raise InstallError('Publisher archive exceeds entry or size limits.')
            if member.name == plan.member:
                members.append(member)
        valid = len(members) == 1 and members[0].isfile()
        size = members[0].size if valid else MAX_BINARY + 1
    with container:
        if not valid or not 0 < size <= MAX_BINARY:
            raise InstallError('Publisher archive lacks the expected regular executable or exceeds limits.')
        # Read a single exact member, never extract paths, links, or other files.
        source = container.open(members[0]) if plan.application == 'godot' else container.extractfile(members[0])
        with source, output.open('xb') as target:
            copied = 0
            while True:
                _check_cancel(cancel)
                chunk = source.read(256 * 1024)
                if not chunk:
                    break
                copied += len(chunk)
                if copied > MAX_BINARY:
                    raise InstallError('Unpacked executable exceeds limits.')
                target.write(chunk)
        if copied != size:
            raise InstallError('Incomplete executable in publisher archive.')
    output.chmod(0o700)


def install(config, plan, *, consent=False, progress=None, cancel=None):
    """Install a reviewed plan only after explicit consent; never run downloaded code."""
    if consent is not True:
        raise InstallError('Explicit download and installation consent is required.')
    if plan.application in OPTIONAL:
        from portable_install import install
        return install(config, plan, progress=progress, cancel=cancel)
    if plan.application == 'codex':
        from codex_install import install_package
        return install_package(config, plan, progress=progress, cancel=cancel)
    if plan.application not in REPOSITORIES:
        raise InstallError('Unsupported installer.')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', plan.version):
        raise InstallError('Invalid installation version; prepare again.')
    prefix = ('https://github.com/' + REPOSITORIES[plan.application]
              + '/releases/download/' + plan.version + '/')
    if plan.application == 'godot':
        valid_member = re.fullmatch('Godot_v' + re.escape(plan.version) + r'_linux\.(x86_64|arm64)', plan.member)
        algorithm, suffix, source = 'sha512', '.zip', prefix + 'SHA512-SUMS.txt'
    else:
        valid_member = re.fullmatch(r'codex-(x86_64|aarch64)-unknown-linux-musl', plan.member)
        algorithm, suffix = 'sha256', '.tar.gz'
        source = 'https://api.github.com/repos/openai/codex/releases/latest'
    if (not valid_member or plan.asset != plan.member + suffix
            or plan.url != prefix + plan.asset or plan.integrity_source != source
            or plan.algorithm != algorithm
            or not re.fullmatch('[0-9a-f]{' + str(hashlib.new(algorithm).digest_size * 2) + '}', plan.checksum)):
        raise InstallError('Installation plan is invalid; prepare again.')
    if plan.destination != managed_root() / plan.application / plan.version:
        raise InstallError('Installation destination changed; prepare again.')
    progress = progress or (lambda *args: None)
    root = managed_root()
    if any(path.is_symlink() for path in (root, root.parent, root / plan.application)):
        raise InstallError('Managed installation directories must not be symbolic links.')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Lock concurrent Studio processes without changing existing installations.
    fd = os.open(root / ('.' + plan.application + '.lock'),
                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise InstallError('Another installation is active. Retry after it finishes.') from exc
        if inspect(config, plan.application)['status'] != 'Missing':
            raise InstallError('Tool configuration or discovery changed. Recheck before installing.')
        if plan.destination.exists() or plan.destination.is_symlink():
            raise InstallError('Destination already exists; Choose its executable or review it manually.')
        with tempfile.TemporaryDirectory(prefix='.install-', dir=root) as temp:
            stage = Path(temp)
            archive = stage / 'download'
            with archive.open('xb') as output:
                _download(plan.url, output, MAX_DOWNLOAD, progress, cancel)
            progress('Verifying publisher checksum', 0, None)
            digest = hashlib.new(plan.algorithm)
            with archive.open('rb') as source:
                while chunk := source.read(256 * 1024):
                    _check_cancel(cancel)
                    digest.update(chunk)
            if digest.hexdigest() != plan.checksum:
                raise InstallError('Checksum mismatch. Nothing installed. Retry or use official guidance.')
            progress('Extracting verified executable', 0, None)
            payload = stage / 'payload'
            payload.mkdir(mode=0o700)
            binary = payload / ('codex' if plan.application == 'codex' else plan.member)
            _extract_binary(archive, plan, binary, cancel)
            (payload / 'installation.json').write_text(json.dumps(dataclasses.asdict(plan), default=str, indent=2))
            _check_cancel(cancel)
            plan.destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            payload.rename(plan.destination)
    progress('Installed; runtime compatibility and authentication are not tested', 1, 1)
    return str(plan.destination / binary.name)


def _codex_runtime_path(path):
    # A repaired legacy executable remains untouched. Resolve only a complete,
    # verified Studio-managed canonical package beside it; never change settings.
    from codex_install import repaired_path
    return str(repaired_path(path))
