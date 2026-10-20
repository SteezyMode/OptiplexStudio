from pathlib import Path
import shutil
import subprocess
import struct
import gi
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf, GLib

root = Path(__file__).resolve().parent.parent
# Approved artwork is supplied separately. Never fall back to the old SVGs.
icons = []
for filename in ('optiplex-studio.png', 'optiplex-studio-tray.png'):
    path = root / 'assets' / filename
    if not path.is_file():
        raise SystemExit('Approved PNG required before packaging: ' + str(path))
    with path.open('rb') as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n' or header[12:16] != b'IHDR':
        raise SystemExit('Invalid approved PNG: ' + str(path))
    width, height = struct.unpack('>II', header[16:24])
    if width != height or not 1 <= width <= 4096:
        raise SystemExit('Approved icon must be a square PNG up to 4096 pixels: ' + str(path))
    try:
        image = GdkPixbuf.Pixbuf.new_from_file(str(path))
    except GLib.Error as exc:
        raise SystemExit('Approved PNG could not be decoded: ' + str(path) + ': ' + str(exc)) from None
    if (image.get_width(), image.get_height()) != (width, height):
        raise SystemExit('Approved PNG dimensions do not match: ' + str(path))
    icons.append((path, f'usr/share/icons/hicolor/{width}x{height}/apps'))
arch = subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip()
name = f'optiplex-studio_0.4.8_{arch}'
pkg = root / 'build' / name
if pkg.exists() or (root / 'dist' / (name + '.deb')).exists():
    raise SystemExit('Refusing to overwrite existing build/package: ' + name)
launcher = root / 'build/local-first/optiplex-studio'
if not launcher.is_file():
    raise SystemExit('Build the native launcher first: make -f Makefile.studio all')
for folder in ['DEBIAN', 'usr/bin', 'usr/lib/optiplex-studio', 'usr/share/applications', 'usr/share/pixmaps', 'usr/share/doc/optiplex-studio']:
    (pkg / folder).mkdir(parents=True, exist_ok=True)
shutil.copy2(root / 'build/local-first/optiplex-studio', pkg / 'usr/bin/optiplex-studio')
for filename in ['app.py', 'core.py', 'project_helper.py', 'project_client.py', 'project_ui.py', 'desktop_helper.py', 'godot_focus.py', 'file_browser.py', 'session_helper.py', 'session_ui.py', 'native_tools.py', 'portable_install.py', 'tool_environment.py', 'codex_install.py', 'tools_ui.py', 'conversation_store.py', 'codex_rpc.py', 'embedded_codex.py', 'embedded_ui.py', 'transcript.py', 'style.css']:
    shutil.copy2(root / 'studio' / filename, pkg / 'usr/lib/optiplex-studio' / filename)
for path, destination in icons:
    (pkg / destination).mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, pkg / destination / path.name)
    # Nonstandard approved sizes (such as 901px) may not be listed in the
    # system hicolor index. The pixmaps fallback preserves the original bytes
    # while making icon-name lookup work without generating replacement art.
    shutil.copy2(path, pkg / 'usr/share/pixmaps' / path.name)
shutil.copy2(root / 'README-STUDIO.md', pkg / 'usr/share/doc/optiplex-studio/README.md')
(pkg / 'usr/share/applications/com.monumentrisk.OptiPlexStudio.desktop').write_text('''[Desktop Entry]
Type=Application
Name=OptiPlex Studio
Comment=Creative projects, Codex sessions and shared assets
Exec=/usr/bin/optiplex-studio
TryExec=/usr/bin/optiplex-studio
Icon=optiplex-studio
Terminal=false
Categories=Development;
StartupNotify=true
StartupWMClass=optiplex-studio
''')
(pkg / 'DEBIAN/control').write_text(f'''Package: optiplex-studio
Version: 0.4.8
Section: devel
Priority: optional
Architecture: {arch}
Maintainer: OptiPlex Studio <local@localhost>
Depends: libc6 (>= 2.34), python3, python3-gi, gir1.2-gtk-3.0, librsvg2-common, x-terminal-emulator, ca-certificates
Recommends: gir1.2-ayatanaappindicator3-0.1, wmctrl
Description: Native GTK3 OptiPlex Studio desktop
 Local creative projects, native tools and project-aware Codex sessions.
''')
for item in pkg.rglob('*'):
    item.chmod(0o755 if item.is_dir() or item == pkg / 'usr/bin/optiplex-studio' else 0o644)
(root / 'dist').mkdir(exist_ok=True)
subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(pkg), str(root / 'dist' / (name + '.deb'))], check=True)
