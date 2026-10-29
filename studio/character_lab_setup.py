"""Explicit, local-only preparation of shared AI creative tool dependencies.

This is NOT invoked by Studio startup, package installation, or Codex.
Source is pinned and only downloaded/executed after the user requests setup.
Blender preferences, Codex configuration and MPFB assets are not changed.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

REPOS = {
    'mpfb-mcp': ('https://github.com/makehumancommunity/mpfb-mcp.git',
                 'c2666662d76ae7abbcb07fdc392d890536d2f875'),
    'rigger': ('https://github.com/asu37/Rigger.git',
               'c8f1d1b9a8729582c61fa0ffa9a658ec4f4f6e77'),
}


def base_directory(home=None):
    home = Path.home() if home is None else Path(home)
    return home / '.local/share/optiplex-studio/character-lab'


def run(argv, *, cwd=None, timeout=180):
    """Argument arrays only; no shell or sudo. Caller chooses all executables."""
    subprocess.run(list(map(str, argv)), cwd=str(cwd) if cwd else None,
                   stdin=subprocess.DEVNULL, check=True, timeout=timeout)


def clone_pinned(name, root):
    """Use a new directory; never update, replace or clean an existing checkout."""
    url, commit = REPOS[name]
    target = root / name
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir():
            raise RuntimeError('Existing character-tool checkout is not a directory: ' + str(target))
        found = subprocess.run(['git', '-C', str(target), 'rev-parse', 'HEAD'],
                               capture_output=True, text=True, timeout=15, check=True).stdout.strip()
        if found != commit:
            raise RuntimeError('Different checkout already present at ' + str(target)
                               + '. Existing sources remain unchanged; review manually.')
        return target
    # A staged checkout is renamed only after exact-commit verification.
    with tempfile.TemporaryDirectory(prefix='.checkout-', dir=root) as folder:
        temp = Path(folder) / name
        run(['git', '-c', 'protocol.file.allow=never', 'clone', '--no-checkout',
             '--depth=1', url, str(temp)], timeout=180)
        # Pin to a specific inspected source revision rather than silently using latest.
        try:
            run(['git', '-C', str(temp), 'checkout', '--detach', commit], timeout=45)
        except subprocess.CalledProcessError:
            # The fixed commit may no longer be branch tip. Fetch that exact ref
            # without silently selecting another source version.
            run(['git', '-C', str(temp), 'fetch', '--depth=1', 'origin', commit], timeout=180)
            run(['git', '-C', str(temp), 'checkout', '--detach', commit], timeout=45)
        actual = subprocess.run(['git', '-C', str(temp), 'rev-parse', 'HEAD'],
                                capture_output=True, text=True, check=True, timeout=15).stdout.strip()
        if actual != commit:
            raise RuntimeError('Upstream source revision failed verification: ' + name)
        os.rename(temp, target)
    return target


def prepare(home=None):
    root = base_directory(home)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink():
        raise RuntimeError('Character Lab directory may not be a symlink.')
    print('AI creative-tool integration is experimental. No Blender/MPFB/Codex settings will be changed.', flush=True)
    print('Source repositories and Python dependencies are downloaded into:', root, flush=True)
    print('Python packaging commands can execute pinned third-party build code.', flush=True)
    mpfb = clone_pinned('mpfb-mcp', root)
    rigger = clone_pinned('rigger', root)
    py = mpfb / '.venv' / 'bin' / 'python'
    server = mpfb / '.venv' / 'bin' / 'mpfb-mcp'
    if not server.is_file():
        # Only touch our own .venv; never pip-install to the system interpreter.
        if not py.is_file():
            venv.EnvBuilder(with_pip=True).create(str(mpfb / '.venv'))
        run([py, '-m', 'pip', 'install', '-e', str(mpfb)], timeout=240)
    if not server.is_file():
        raise RuntimeError('The MPFB MCP environment is incomplete; setup can be retried.')
    artifact = sorted((rigger / 'dist').glob('rigger-*.zip')) if (rigger / 'dist').is_dir() else []
    if not artifact:
        run([sys.executable, 'build.py'], cwd=rigger, timeout=90)
        artifact = sorted((rigger / 'dist').glob('rigger-*.zip'))
    if len(artifact) != 1 or not artifact[0].is_file():
        raise RuntimeError('Expected one Rigger extension archive; inspect source checkout.')
    print('\nPREPARATION COMPLETE (not an active installation)', flush=True)
    print('MPFB MCP command:', server, flush=True)
    print('MPFB Bridge source:', mpfb / 'bridge/mpfb_bridge', flush=True)
    print('Rigger zip (leave disabled for now):', artifact[0], flush=True)
    print('Next: follow the Studio Character Lab guide to install MPFB and its assets', flush=True)
    print('in Blender, build/enable MPFB Bridge, install MCP for Blender, and register', flush=True)
    print('the two MCP servers after confirming localhost-only settings.', flush=True)
    return {'mpfb_server': str(server), 'mpfb_bridge': str(mpfb / 'bridge/mpfb_bridge'),
            'rigger_zip': str(artifact[0])}


def describe(home=None):
    root = base_directory(home)
    out = {}
    for name, (_, commit) in REPOS.items():
        path = root / name
        out[name] = {'source_dir': str(path), 'present': path.is_dir() and not path.is_symlink(),
                     'pinned_commit': commit}
    out['mpfb_server_prepared'] = (root / 'mpfb-mcp/.venv/bin/mpfb-mcp').is_file()
    out['rigger_zip_prepared'] = any((root / 'rigger/dist').glob('rigger-*.zip')) if (root / 'rigger/dist').is_dir() else False
    out['important'] = 'Prepared does not mean installed, enabled or operational in Blender/Codex.'
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'prepare', 'install', 'doctor'))
    parser.add_argument('--blender', help='Absolute Blender executable used by Studio')
    parser.add_argument('--codex', help='Absolute Codex executable used by Studio')
    parser.add_argument('--yes', action='store_true',
                        help='For explicit Studio GUI consent; CLI install normally asks YES')
    args = parser.parse_args(argv)
    if args.action == 'status':
        print(json.dumps(describe(), indent=2))
        return 0
    if args.action == 'doctor':
        from character_lab_runtime import service_status
        print(json.dumps(service_status(), indent=2))
        return 0
    if args.action == 'install' and (not args.blender or not args.codex):
        parser.error('install requires --blender and --codex, from Studio Settings')
    print('Experimental third-party downloads and installation will execute code.', flush=True)
    if args.action == 'install':
        print('MPFB and the Bridge will be enabled in Blender; Rigger will stay disabled.', flush=True)
        print('Visual Blender MCP will be installed and user Codex MCP settings amended.', flush=True)
        print('Current project files will not be edited. Restart Blender and Codex afterward.', flush=True)
    else:
        print('Prepare MPFB MCP and Rigger sources in a private directory.', flush=True)
    if not args.yes and input('Install/prepare character tools? Type YES to confirm: ').strip() != 'YES':
        print('Cancelled. No downloads started.')
        return 1
    if args.action == 'install':
        from character_lab_runtime import install
        install(args.blender, args.codex)
    else:
        prepare()
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print('AI creative-tool preparation failed: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
