"""Read-only project discovery and narrowly defined SSH operations."""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
import http.client
import ipaddress
import socket
import ssl
import os
import threading
import shlex
import atexit
import time

API = 'https://studio.monumentrisk.com/api/projects'
# Legacy personal browser routes stay for backward compatibility and internal tests.
# Studio's native Creative Tools screen never uses this list. Do not delete
# functioning personal hosts, browser URLs or local tunnel safeguards.
APPS = [('UltraBox', 'https://synth.monumentrisk.com'),
        ('AudioMass', 'https://recorder.monumentrisk.com'),
        ('openDAW', 'https://daw.monumentrisk.com'),
        ('Piskel', 'https://pixel.monumentrisk.com'),
        ('Onionskyn', 'https://animate.monumentrisk.com'),
        ('CozyClay', 'https://previs.monumentrisk.com/app/'),
        ('Blockbench', 'https://models.monumentrisk.com')]
# Broken HTTPS virtual hosts are replaced by encrypted SSH forwarding to the
# existing static services, never by disabling TLS or opening public ports.
TUNNEL_APPS = {'https://animate.monumentrisk.com': (18771, 28771, '/'),
               'https://previs.monumentrisk.com/app/': (18769, 28769, '/app/'),
               'https://models.monumentrisk.com': (18770, 28770, '/')}
_tunnels = {}
_tunnel_lock = threading.Lock()


def close_tunnels():
    with _tunnel_lock:
        for process in _tunnels.values():
            if process.poll() is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
        _tunnels.clear()

atexit.register(close_tunnels)


def tunnel_args(config, url):
    if url not in TUNNEL_APPS:
        raise ValueError('Unsupported forwarded application.')
    remote_port, local_port, _ = TUNNEL_APPS[url]
    args = ssh_args(config, 'edit', 'validation')[:-1]
    return args[:1] + ['-N', '-o', 'ExitOnForwardFailure=yes', '-o', 'ControlMaster=no',
                      '-o', 'ControlPath=none', '-L', f'127.0.0.1:{local_port}:127.0.0.1:{remote_port}'] + args[2:]


def ensure_tunnel(config, url):
    if url not in TUNNEL_APPS:
        raise ValueError('Unsupported forwarded application.')
    _, local_port, path = TUNNEL_APPS[url]
    key = (tailscale_ip(config), config['user'], url)
    with _tunnel_lock:
        process = _tunnels.get(key)
        if process is not None and process.poll() is None:
            return f'http://127.0.0.1:{local_port}{path}'
        for other, child in _tunnels.items():
            if other[2] == url and other != key and child.poll() is None:
                child.terminate()
                child.wait(timeout=5)
        log = tempfile.TemporaryFile()
        process = None
        handed_off = False
        try:
            process = subprocess.Popen(tunnel_args(config, url), stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=log)
            deadline = time.monotonic() + 15
            error = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError('Creative app SSH tunnel failed: ' + (log.read().decode(errors='replace')[-2000:] or f'exit {process.returncode}'))
                connection = http.client.HTTPConnection('127.0.0.1', local_port, timeout=1)
                try:
                    connection.request('GET', path)
                    response = connection.getresponse()
                    if response.status >= 400:
                        raise RuntimeError(f'Creative service returned HTTP {response.status}. Check the existing service; no server changes were made.')
                    break
                except (OSError, http.client.HTTPException) as exc:
                    error = exc
                    time.sleep(.15)
                finally:
                    connection.close()
            else:
                raise RuntimeError('Creative service is unreachable through its SSH tunnel: ' + str(error))
            _tunnels[key] = process
            def reap():
                process.wait()
                log.close()
            threading.Thread(target=reap, daemon=True).start()
            handed_off = True
            return f'http://127.0.0.1:{local_port}{path}'
        finally:
            if not handed_off:
                if process is not None and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                log.close()


def valid_name(name):
    return isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', name) is not None

def tailscale_ip(config):
    try:
        address = ipaddress.IPv4Address(config.get('host', ''))
    except (ipaddress.AddressValueError, TypeError):
        raise ValueError('Set the OptiPlex Tailscale IPv4 address in Studio Settings.') from None
    if address not in ipaddress.IPv4Network('100.64.0.0/10'):
        raise ValueError('Studio requires a Tailscale IPv4 address in 100.64.0.0/10.')
    return str(address)


class TailscaleHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a numeric tailnet address, retaining the HTTPS authority."""
    def __init__(self, address):
        super().__init__('studio.monumentrisk.com', timeout=20,
                         context=ssl.create_default_context())
        self.address = address

    def connect(self):
        # AF_INET + numeric connect avoids even a hostname lookup. No proxy,
        # global resolver monkey patch, tunnel or insecure TLS context is used.
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            raw.settimeout(self.timeout)
            raw.connect((self.address, 443))
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def projects(config):
    connection = TailscaleHTTPSConnection(tailscale_ip(config))
    try:
        connection.request('GET', '/api/projects', headers={'Accept': 'application/json'})
        response = connection.getresponse()
        if response.status != 200:
            # Never follow a redirect into a DNS-dependent or unrelated route.
            raise RuntimeError(f'Projects API returned HTTP {response.status}; expected 200.')
        payload = response.read(2 * 1024 * 1024 + 1)
        if len(payload) > 2 * 1024 * 1024:
            raise ValueError('Projects API response is too large.')
        data = json.loads(payload)
        rows = data['projects']
        if not isinstance(rows, list) or any(not isinstance(p, dict) or not valid_name(p.get('name')) for p in rows):
            raise ValueError('Invalid project response')
        return sorted(rows, key=lambda p: p['name'].lower())
    finally:
        connection.close()


def browser_args(config, url, forwarded=False):
    address = tailscale_ip(config)
    allowed = {u for _, u in APPS} | {'https://studio.monumentrisk.com'}
    local_allowed = {f'http://127.0.0.1:{port}{path}' for _, port, path in TUNNEL_APPS.values()}
    if url not in (local_allowed if forwarded else allowed):
        raise ValueError('Unsupported Studio application URL.')
    browser = next((shutil.which(name) for name in
                    ('chromium', 'chromium-browser', 'google-chrome', 'brave-browser')
                    if shutil.which(name)), None)
    if not browser:
        raise RuntimeError('Install Chromium, Google Chrome or Brave for DNS-independent Studio applications.')
    # Separate profiles per IP prevent a running browser from silently reusing
    # resolver rules for a previously configured server. No global browser or
    # system DNS settings are changed. All service subdomains share this route.
    base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    profile = base / 'optiplex-studio' / ('browser-' + address)
    return [browser, '--user-data-dir=' + str(profile), '--no-first-run',
            '--no-default-browser-check', '--disable-quic',
            '--proxy-server=direct://',
            f'--host-resolver-rules=MAP monumentrisk.com {address}, MAP *.monumentrisk.com {address}',
            url]


def open_application(config, url):
    forwarded = url in TUNNEL_APPS
    if forwarded:
        url = ensure_tunnel(config, url)
    command = browser_args(config, url, forwarded=True) if forwarded else browser_args(config, url)
    # Capture startup failures without blocking GTK or discarding browser errors.
    errors = tempfile.TemporaryFile(mode='w+t')
    try:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=errors,
                                   start_new_session=True)
        try:
            result = process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            def reap():
                process.wait()
                errors.close()
            threading.Thread(target=reap, daemon=True).start()
            return 'Studio browser opened through the configured Tailscale IP.'
        if result:
            errors.seek(0)
            raise RuntimeError('Studio browser failed to open: ' + (errors.read()[-3000:] or f'exit {result}'))
        return 'Studio browser launch requested through the configured Tailscale IP.'
    finally:
        if 'process' not in locals() or process.poll() is not None:
            errors.close()


def remote_command(action, name, user):
    if not isinstance(user, str) or not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_-]{0,63}', user):
        raise ValueError('Set a valid SSH user in Settings.')
    home = '/root' if user == 'root' else f'/home/{user}' 
    if not valid_name(name):
        raise ValueError('Use 1–128 letters, numbers, hyphens or underscores for the project name.')
    if action in ('new', 'edit'):
        return f'{home}/.local/bin/studio {action} {name}'
    if action in ('code', 'resume'):
        from project_helper import WORKFLOW
        guidance = shlex.quote('developer_instructions=' + WORKFLOW.replace('PROJECT_NAME', name))
        return (f'{home}/.local/bin/codex --cd {home}/StudioProjects/Godot/{name} '
                f'--sandbox workspace-write --ask-for-approval on-request --config {guidance}'
                + (' resume' if action == 'resume' else ''))
    raise ValueError('Unsupported Studio action')

def ssh_args(config, action, name, interactive=False):
    host, user = tailscale_ip(config), config.get('user', '')
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_-]{0,63}', user):
        raise ValueError('Set a valid SSH user in Settings.')
    return ['ssh', '-tt' if interactive else '-T', '-o', 'Hostname=' + host,
            '-o', 'ProxyCommand=none', '-o', 'ProxyJump=none', '-o', 'CanonicalizeHostname=no',
            '-o', 'ConnectTimeout=12',
            '-o', 'ServerAliveInterval=30', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'BatchMode=yes', f'{user}@{host}', remote_command(action, name, user)]

def terminal_args(command):
    # Only use adapters with documented argv execution and foreground modes.
    # In particular, cosmic-term's help does not promise -e support.
    adapters = {
        'gnome-terminal': ['--wait', '--'],
        'konsole': ['--nofork', '-e'],
        'xfce4-terminal': ['--disable-server', '-x'],
        'xterm': ['-e'],
    }
    candidates = []
    alternative = shutil.which('x-terminal-emulator')
    if alternative:
        resolved = Path(alternative).resolve().name
        if resolved in adapters:
            candidates.append((alternative, resolved))
    candidates.extend((name, name) for name in adapters if shutil.which(name))
    if candidates:
        executable, adapter = candidates[0]
        return [executable] + adapters[adapter] + command
    raise RuntimeError('Install a supported terminal: xterm, GNOME Terminal, Konsole or XFCE Terminal.')


MOONLIGHT_ID = 'com.moonlight_stream.Moonlight'
DEFAULT_STUDIO_APP = 'OptiPlex Studio Desktop'

def stream_app(config):
    title = config.get('moonlight_app', '').strip() or DEFAULT_STUDIO_APP
    if title == 'Studio Desktop':
        title = DEFAULT_STUDIO_APP  # migrate the old placeholder without rewriting settings
    if len(title) > 128 or any(ord(c) < 32 for c in title):
        raise ValueError('Invalid Moonlight application title.')
    return title
_stream_lock = threading.Lock()


def moonlight_prefix(config):
    """Match NOW's AppImage, native, then Flatpak detection order."""
    explicit = config.get('moonlight_appimage', '').strip()
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise RuntimeError('The Moonlight AppImage in Studio Settings is not an executable file.')
        return [str(path)]
    for folder in ('Applications', 'AppImages', 'Downloads', 'Desktop', '.local/bin', 'bin', ''):
        try:
            paths = sorted((Path.home() / folder).iterdir())
            for path in paths:
                if ('moonlight' in path.name.lower() and path.name.lower().endswith('.appimage')
                        and path.is_file() and os.access(path, os.X_OK)):
                    return [str(path)]
        except OSError:
            continue
    native = shutil.which('moonlight')
    if native:
        return [native]
    flatpak = shutil.which('flatpak')
    if flatpak:
        try:
            result = subprocess.run([flatpak, 'info', '--show-ref', MOONLIGHT_ID],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return [flatpak, 'run', MOONLIGHT_ID]
        except (OSError, subprocess.TimeoutExpired):
            pass
    raise RuntimeError('Moonlight was not found. Select an existing AppImage in Studio Settings, '
                       'or install Moonlight natively or as a Flatpak. Existing Wolf pairing is required.')


def moonlight_environment(config, command):
    """Use the verified AppImage runtime mode without changing Qt preferences."""
    if config.get('moonlight_appimage', '').strip() or Path(command[0]).name.lower().endswith('.appimage'):
        environment = os.environ.copy()
        environment['APPIMAGE_EXTRACT_AND_RUN'] = '1'
        return environment
    return None  # Native/Flatpak clients inherit the existing environment.


def moonlight_args(config):
    host = tailscale_ip(config)
    # No pairing, decoder, resolution, bitrate or profile overrides.
    return moonlight_prefix(config) + ['stream', host, stream_app(config)]


def studio_stream_pid(host, app):
    """Find only this user's Moonlight stream for this exact host and app."""
    try:
        processes = Path('/proc').iterdir()
        for process in processes:
            if not process.name.isdigit():
                continue
            try:
                if process.stat().st_uid != os.getuid():
                    continue
                args = [part.decode(errors='replace') for part in
                        (process / 'cmdline').read_bytes().split(b'\0') if part]
                for index, arg in enumerate(args):
                    if arg == 'stream' and args[index:index + 3] == ['stream', host, app]:
                        if any('moonlight' in Path(value).name.lower() for value in args[:index]):
                            return int(process.name)
            except (OSError, ValueError):
                continue
    except OSError:
        pass
    return None


def focus_studio_stream(pid, app):
    """Best effort on X11/XWayland; never focus unrelated Moonlight sessions."""
    wmctrl = shutil.which('wmctrl')
    if not wmctrl:
        return False
    try:
        windows = subprocess.run([wmctrl, '-lp'], capture_output=True, text=True, timeout=3)
        if windows.returncode:
            return False
        for line in windows.stdout.splitlines():
            fields = line.split(None, 4)
            if len(fields) == 5 and fields[2] == str(pid) and app.lower() in fields[4].lower():
                result = subprocess.run([wmctrl, '-ia', fields[0]], capture_output=True, text=True, timeout=3)
                return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        pass
    return False


def _moonlight_error(log, status):
    log.seek(0, os.SEEK_END)
    size = log.tell()
    log.seek(max(0, size - 3000))
    details = log.read().decode(errors='replace').strip()
    return (f'Moonlight desktop stream failed (exit {status}). '
            'Check Moonlight pairing, Tailscale connectivity and the selected Wolf application.'
            + ('\n' + details if details else ''))


def launch_studio_desktop(config, on_error=None):
    host = tailscale_ip(config)
    app = stream_app(config)
    # Serialize the check/start interval so repeated clicks cannot race startup.
    with _stream_lock:
        pid = studio_stream_pid(host, app)
        if pid is not None:
            if focus_studio_stream(pid, app):
                return f'Existing {app} stream brought forward.'
            return f'{app} is already streaming. Switch to its Moonlight window (automatic focus unavailable).'
        command = moonlight_args(config)
        log = tempfile.TemporaryFile(mode='w+b')
        monitor_owns_log = False
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, env=moonlight_environment(config, command))
            try:
                status = process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                def monitor():
                    try:
                        status = process.wait()
                        if status and on_error:
                            on_error(_moonlight_error(log, status))
                    finally:
                        log.close()
                monitor_owns_log = True
                threading.Thread(target=monitor, daemon=True).start()
                return f'Moonlight is connecting to {app}.'
            if status:
                raise RuntimeError(_moonlight_error(log, status))
            return f'Moonlight {app} launch completed.'
        finally:
            if not monitor_owns_log:
                log.close()


def wait_for_studio_desktop(config, project, on_progress=None, stream_errors=None,
                            timeout=90, interval=2):
    import project_client
    deadline = time.monotonic() + timeout
    reason = 'Waiting for Wolf Studio Desktop.'
    while time.monotonic() < deadline:
        if stream_errors:
            raise RuntimeError('Moonlight connection failed: ' + stream_errors[-1])
        status = project_client.request(config, project, 'desktop_status', request_timeout=25)
        if stream_errors:
            raise RuntimeError('Moonlight connection failed: ' + stream_errors[-1])
        if status.get('ready'):
            return status
        reason = status.get('message') or reason
        if on_progress:
            on_progress(reason)
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(interval, remaining))
    raise RuntimeError(f'Studio Desktop did not become ready within {timeout} seconds. '
                       'Check Moonlight pairing/connection and the desktop session. Godot was not launched. ' + reason)


def run_action(config, action, name, on_started=None, on_error=None, on_progress=None, session_id=None, prompt=None, all_sessions=False):
    cmd = ssh_args(config, action, name, action in ('code', 'resume'))
    if action in ('code', 'resume'):
        if session_id is not None:
            import uuid
            if action != 'resume':
                raise ValueError('Session ID is only valid for resume.')
            session_id = str(uuid.UUID(session_id))
            cmd[-1] += ' ' + shlex.quote(session_id)
        elif all_sessions and action == 'resume':
            cmd[-1] += ' --all'
        if prompt is not None:
            if action != 'code' or prompt not in CODEX_TASKS.values():
                raise ValueError('Unsupported Codex task.')
            cmd[-1] += ' ' + shlex.quote(prompt)
        # Terminal emulators may hide their child's exit code. A private file
        # carries the SSH result independently of emulator exit-code semantics.
        with tempfile.TemporaryDirectory(prefix='optiplex-studio-') as directory:
            status = Path(directory) / 'status'
            wrapped = ['/bin/sh', '-c',
                       'status=$1; shift; "$@"; result=$?; printf "%s" "$result" > "$status"; exit "$result"',
                       'studio-terminal', str(status)] + cmd
            terminal = terminal_args(wrapped)
            with subprocess.Popen(terminal, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, start_new_session=True) as process:
                if on_started:
                    on_started()
                stdout, stderr = process.communicate()
            if not status.exists():
                raise RuntimeError('Terminal failed to run SSH/Codex: ' +
                                   (stderr or stdout or 'No remote exit status was received.')[-3000:])
            result = int(status.read_text())
            if result:
                raise RuntimeError(f'SSH/Codex launch or session failed (exit {result}). '
                                   'Check the Tailscale connection, trusted SSH host key, SSH key and remote Codex installation.')
            return 'Codex conversation closed.'
    if action == 'edit':
        import project_client
        stream_errors = []
        def stream_failed(message):
            stream_errors.append(message)
            if on_error:
                on_error(message)
        if on_progress:
            on_progress('Connecting Moonlight to ' + stream_app(config) + '…')
        message = launch_studio_desktop(config, on_error=stream_failed)
        if on_progress:
            on_progress('Waiting for the Wolf Studio Desktop session to become ready…')
        wait_for_studio_desktop(config, name, on_progress, stream_errors)
        if on_progress:
            on_progress('Desktop ready; opening or focusing Godot for ' + name + '…')
        try:
            result = project_client.request(config, name, 'desktop', application='godot')
        except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
            raise RuntimeError('Studio Desktop connection was requested, but Godot could not be opened: ' + str(exc)) from exc
        return result['message'] + ' ' + message
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'SSH action failed')[-3000:])
    return result.stdout.strip() or 'Project created.'


CODEX_TASKS = {
    'Review Changes': 'Read AGENTS.md and the project documents. Review current uncommitted changes for defects and risks. Report findings without changing files or committing.',
    'Explain Project': 'Read AGENTS.md and the project documents. Explain this project, its structure, current state, and useful next steps. Do not change files or commit.',
    'Fix Godot Errors': 'Read AGENTS.md and the project documents. Inspect this Godot project, run existing permitted Godot validation when available, and fix confirmed errors. Report unavailable tools or permissions; never bypass permissions or change Wolf. Update concise progress and decisions. Do not commit.',
    'Validate Project': 'Read AGENTS.md and the project documents. Run existing permitted Godot project validation when available and report results. Report missing permissions or tools without bypassing them. Do not change files or commit.'}
