#!/usr/bin/env python3
from pathlib import Path
import shutil, subprocess
root=Path(__file__).resolve().parent
out=root/'dist'; out.mkdir(exist_ok=True)
pkg=root/'build/pkg/optiplex-now_1.11.1_amd64'
if pkg.exists(): shutil.rmtree(pkg)
for sub in ('DEBIAN','usr/bin','usr/lib/optiplex-now','usr/share/applications','usr/share/doc/optiplex-now'):
 (pkg/sub).mkdir(parents=True,exist_ok=True)
(pkg/'DEBIAN').chmod(0o755)
shutil.copy2(root/'build/optiplex-desk',pkg/'usr/bin/optiplex-desk')
shutil.copy2(root/'build/optiplex-now-backup',pkg/'usr/lib/optiplex-now/optiplex-now-backup')
for f in (pkg/'usr/bin/optiplex-desk',pkg/'usr/lib/optiplex-now/optiplex-now-backup'): f.chmod(0o755)
try:
 from PIL import Image
 icon=Image.open(root/'assets/optiplex-now.png').convert('RGBA')
 for n in (16,22,24,32,48,64,128,256):
  dest=pkg/f'usr/share/icons/hicolor/{n}x{n}/apps'; dest.mkdir(parents=True,exist_ok=True)
  icon.resize((n,n),Image.Resampling.NEAREST).save(dest/'optiplex-now.png')
 # Tray art is borderless with a genuine alpha channel and enlarged silhouette.
 small=Image.open(root/'assets/optiplex-now-tray.png').convert('RGBA')
 for n in (16,22,24,32,48,64):
  dest=pkg/f'usr/share/icons/hicolor/{n}x{n}/apps'; dest.mkdir(parents=True,exist_ok=True)
  small.resize((n,n),Image.Resampling.NEAREST).save(dest/'optiplex-now-tray.png')
except ImportError:
 # Pillow optional: install python3-pil if multiple resolutions are wanted.
 dest=pkg/'usr/share/icons/hicolor/256x256/apps';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(root/'assets/optiplex-now.png',dest/'optiplex-now.png')
 shutil.copy2(root/'assets/optiplex-now-tray.png',dest/'optiplex-now-tray.png')
(pkg/'usr/share/applications/optiplex-desk.desktop').write_text('''[Desktop Entry]
Type=Application
Name=OptiPlex Now
GenericName=Remote server launcher
Comment=Games, video, music and remote control
Exec=/usr/bin/optiplex-desk
Icon=optiplex-now
Terminal=false
Categories=Network;Utility;
StartupNotify=true
''')
shutil.copy2(root/'OFL-1.1.txt',pkg/'usr/share/doc/optiplex-now/OFL-1.1.txt')
(pkg/'DEBIAN/control').write_text('''Package: optiplex-desk
Version: 1.11.1
Section: utils
Priority: optional
Architecture: amd64
Maintainer: OptiPlex Now <local@localhost>
Depends: libc6 (>= 2.34), libgtk-3-0t64 | libgtk-3-0, libfontconfig1, openssh-client, xdg-utils, libssl3t64 | libssl3
Recommends: libayatana-appindicator3-1, flatpak, curl
Description: OptiPlex Now remote server launcher
 Native GTK client with native tray quick actions, direct Steam streaming, live hardware info and encrypted backup.
''')
subprocess.run(['dpkg-deb','--build','--root-owner-group',str(pkg),str(out/'OptiPlex-Now_1.11.1_amd64.deb')],check=True)
