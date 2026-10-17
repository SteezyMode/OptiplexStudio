"""Inspect a built Debian artifact without installing it or running remote actions."""
import ast
import configparser
import hashlib
import io
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import tempfile

root = Path(__file__).resolve().parents[1]
package = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'dist/optiplex-studio_0.3.0_amd64.deb'

def field(name):
    return subprocess.check_output(['dpkg-deb', '--field', str(package), name], text=True).strip()

for name, expected in {'Package': 'optiplex-studio', 'Version': '0.3.0', 'Architecture': 'amd64'}.items():
    assert field(name) == expected, (name, field(name))
dependencies = field('Depends')
for name in ('libc6', 'python3', 'python3-gi', 'gir1.2-gtk-3.0', 'openssh-client', 'gvfs-backends', 'gvfs-fuse', 'x-terminal-emulator', 'ca-certificates'):
    assert name in dependencies, 'Missing dependency: ' + name
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['dpkg-deb', '--ctrl-tarfile', str(package)]))) as archive:
    assert {m.name.removeprefix('./') for m in archive if m.isfile()} == {'control'}, 'Unexpected maintainer scripts'
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['dpkg-deb', '--fsys-tarfile', str(package)]))) as archive:
    files = {}
    for member in archive:
        path = member.name.removeprefix('./')
        assert member.uid == member.gid == 0, 'Non-root package ownership'
        assert not member.issym() and not member.islnk(), 'Unexpected package link'
        assert member.isdir() or member.isfile(), 'Unexpected special file'
        assert '..' not in Path(path).parts and not path.startswith('/'), 'Unsafe archive path'
        if member.isfile():
            assert path.startswith('usr/'), 'Unexpected payload location: ' + path
            files[path] = archive.extractfile(member).read()
            assert member.mode == (0o755 if path == 'usr/bin/optiplex-studio' else 0o644), path
    assert not any('optiplex-now' in p or p.endswith('.svg') for p in files), 'Wrong application/artwork'

modules = ['app.py', 'core.py', 'project_client.py', 'project_helper.py', 'project_ui.py',
           'desktop_helper.py', 'godot_focus.py', 'godot_mcp.py', 'file_browser.py', 'session_helper.py', 'session_ui.py', 'style.css']
expected = {'usr/bin/optiplex-studio', 'usr/share/doc/optiplex-studio/README.md',
            'usr/share/applications/com.monumentrisk.OptiPlexStudio.desktop'}
for module in modules:
    target = 'usr/lib/optiplex-studio/' + module
    expected.add(target)
    assert files[target] == (root / 'studio' / module).read_bytes(), 'Bundled source mismatch: ' + module
    if module.endswith('.py'):
        ast.parse(files[target], filename=module)
for name in ('optiplex-studio.png', 'optiplex-studio-tray.png'):
    data = (root / 'assets' / name).read_bytes()
    width, height = struct.unpack('>II', data[16:24])
    for target in (f'usr/share/icons/hicolor/{width}x{height}/apps/{name}', 'usr/share/pixmaps/' + name):
        expected.add(target)
        assert files[target] == data, 'Approved artwork mismatch: ' + target
assert set(files) == expected, 'Unexpected or missing payload: ' + str(set(files) ^ expected)
assert files['usr/share/doc/optiplex-studio/README.md'] == (root / 'README-STUDIO.md').read_bytes()
desktop_path = 'usr/share/applications/com.monumentrisk.OptiPlexStudio.desktop'
entry = configparser.ConfigParser(interpolation=None)
entry.read_string(files[desktop_path].decode())
for key, expected_value in {'Exec': '/usr/bin/optiplex-studio', 'TryExec': '/usr/bin/optiplex-studio',
                            'Name': 'OptiPlex Studio', 'Icon': 'optiplex-studio',
                            'StartupWMClass': 'optiplex-studio', 'Terminal': 'false'}.items():
    assert entry['Desktop Entry'][key] == expected_value, key
with tempfile.TemporaryDirectory(prefix='studio-package-check-') as directory:
    desktop = Path(directory) / Path(desktop_path).name
    desktop.write_bytes(files[desktop_path])
    subprocess.run(['desktop-file-validate', str(desktop)], check=True)
    launcher = Path(directory) / 'optiplex-studio'
    launcher.write_bytes(files['usr/bin/optiplex-studio'])
    info = subprocess.check_output(['readelf', '-h', str(launcher)], text=True)
    assert 'Advanced Micro Devices X86-64' in info, 'Launcher architecture mismatch'
print('Package verified: metadata, dependencies, root ownership, modes, exact payload, desktop entry, amd64 ELF, sources and unchanged PNGs.')
print('SHA256:', hashlib.sha256(package.read_bytes()).hexdigest())
print('Depends:', dependencies)
