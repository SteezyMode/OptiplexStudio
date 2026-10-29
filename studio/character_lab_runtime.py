"""Install shared Blender creative tools and register local Codex MCP servers.

Only invoked by explicit user's creative-tool installation, never at Studio launch.
Does not install system packages, disable sandboxing, or alter existing MCP entries.
This is an opt-in general-purpose Blender MCP integration trial, not alpha acceptance evidence.
"""
import os
from pathlib import Path
import re
import socket
import subprocess
import venv

from character_lab_setup import base_directory, prepare, run


VISUAL_PACKAGE = 'mcp-for-blender==2.2.5'
MCP_NAMES = ('studio-blender', 'studio-mpfb')


def command(argv, *, timeout=120):
    """No shell, bounded execution, do not print stdout (it may contain secrets)."""
    return subprocess.run([str(p) for p in argv], stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=timeout, check=True)


def blender_version(blender):
    result = command([blender, '--version'], timeout=25)
    match = re.search(r'Blender\s+(\d+)\.(\d+)(?:\.(\d+))?', result.stdout)
    if not match or tuple(map(int, match.group(1, 2))) < (5, 0):
        raise RuntimeError('MPFB Bridge needs Blender 5.0 or newer. Select the installed Blender 5.2 in Settings.')
    return tuple(map(int, match.group(1, 2)))


def mcp_names(codex):
    """Read CLI metadata without modifying registration or displaying credentials."""
    result = command([codex, 'mcp', 'list'], timeout=30)
    names = set()
    for line in result.stdout.splitlines():
        first = line.split(maxsplit=1)[0] if line.split() else ''
        if first and first in MCP_NAMES:
            names.add(first)
    return names


def register_mcp(codex, mpfb_server, visual_server):
    """Never replace an entry under our names, even if it is misconfigured."""
    found = mcp_names(codex)
    registrations = (
        ('studio-blender', [
            codex, 'mcp', 'add', 'studio-blender',
            '--env', 'BLENDER_HOST=127.0.0.1',
            '--env', 'BLENDER_PORT=9876',
            '--env', 'BLENDER_MCP_SAFE_MODE=1',
            '--env', 'DISABLE_TELEMETRY=true',
            '--', visual_server]),
        ('studio-mpfb', [
            codex, 'mcp', 'add', 'studio-mpfb',
            '--env', 'MPFB_BRIDGE_HOST=127.0.0.1',
            '--env', 'MPFB_BRIDGE_PORT=9877',
            '--', mpfb_server]),
    )
    outcomes = {}
    for name, argv in registrations:
        if name in found:
            outcomes[name] = 'Existing entry preserved: verify it manually before using the tools.'
            continue
        command(argv, timeout=35)
        outcomes[name] = 'Registered with user Codex CLI; restart Codex before using.'
    return outcomes


def install(blender, codex, home=None):
    """Actual on-device install, not just clone/stage. Preserve user files on failures."""
    if not Path(blender).is_absolute() or not Path(codex).is_absolute():
        raise ValueError('Blender and Codex must be validated absolute executables.')
    for executable in (blender, codex):
        if not Path(executable).is_file() or not os.access(executable, os.X_OK):
            raise ValueError('Configured executable missing or not executable: ' + str(executable))
    version = blender_version(blender)
    print('Validated Blender %d.%d. Installing real Blender extensions.' % version, flush=True)
    paths = prepare(home)
    root = base_directory(home)

    print('[1/5] Installing MPFB from Blender official extension repository...', flush=True)
    command([blender, '--command', 'extension', 'install', '--sync', '--enable', 'mpfb'], timeout=360)

    print('[2/5] Building and installing MPFB Bridge...', flush=True)
    dist = root / 'mpfb-mcp' / 'dist'
    dist.mkdir(parents=True, exist_ok=True)
    run([blender, '--command', 'extension', 'build',
         '--source-dir', paths['mpfb_bridge'], '--output-dir', dist], timeout=180)
    packages = sorted(dist.glob('mpfb_bridge-*.zip'))
    if len(packages) != 1:
        raise RuntimeError('MPFB Bridge build did not yield exactly one extension zip.')
    command([blender, '--command', 'extension', 'install-file',
             '--repo', 'user_default', '--enable', packages[0]], timeout=180)

    print('[3/5] Installing Rigger (not enabling it)...', flush=True)
    command([blender, '--command', 'extension', 'install-file',
             '--repo', 'user_default', paths['rigger_zip']], timeout=180)

    print('[4/5] Installing Blender visual MCP in an isolated Python environment...', flush=True)
    visual = root / 'visual-mcp'
    python = visual / 'bin/python'
    server = visual / 'bin/mcp-for-blender'
    if not server.is_file():
        if not python.is_file():
            venv.EnvBuilder(with_pip=True).create(str(visual))
        run([python, '-m', 'pip', 'install', VISUAL_PACKAGE], timeout=360)
    if not server.is_file():
        raise RuntimeError('Visual MCP executable missing after private installation.')
    command([server, 'install-addon'], timeout=180)

    print('[5/5] Adding the two MCP servers to the existing Codex profile...', flush=True)
    registered = register_mcp(codex, paths['mpfb_server'], str(server))
    print('\nINSTALLED / REGISTERED:', flush=True)
    for name, status in registered.items():
        print(name + ': ' + status, flush=True)
    print('Rigger installed but not activated. No character files have been changed.', flush=True)
    print('Blender must be restarted. MPFB system asset pack must be installed separately.', flush=True)
    print('Open Blender; verify MPFB and the two bridges. The MPFB Bridge must be started manually.', flush=True)
    print('Then reopen Codex and test live tools in a disposable Studio project.', flush=True)
    return {'blender_version': version, 'registrations': registered}


def service_status():
    """Socket connectivity checks only. Open port != healthy MCP session."""
    out = {}
    for name, port in (('visual_blender', 9876), ('mpfb_bridge', 9877)):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                out[name] = 'Listening on loopback; protocol not verified'
        except OSError:
            out[name] = 'Offline: open Blender/enable its add-on'
    return out
