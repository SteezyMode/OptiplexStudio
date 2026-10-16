#!/usr/bin/python3
"""Fixed desktop actions over SSH, using existing permissions and running sessions.
No container lifecycle management, installation, shell, arbitrary executable or API.
"""
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import subprocess
import sys
import time

APPS = {'godot': 'org.godotengine.Godot', 'blender': 'org.blender.Blender', 'krita': 'org.kde.krita'}


def run(args, timeout=15):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'Desktop action failed.')[-2000:])
    return result.stdout


def matching_process(output, app, project):
    for line in output.splitlines()[1:]:
        try:
            args = shlex.split(line)
        except ValueError:
            continue
        if not args:
            continue
        program = Path(args[0]).name.lower()
        # Match the real application, not wrappers or a shell carrying its name.
        if app == 'godot':
            if 'godot' not in program or not any(arg in ('--editor', '-e') for arg in args):
                continue
            target = '/projects/Godot/' + project
            paths = [args[i + 1] for i, arg in enumerate(args[:-1]) if arg == '--path'] + [arg[len('--path='):] for arg in args if arg.startswith('--path=')]
            if any(str(PurePosixPath(path)) == target for path in paths):
                return True
        elif program == app or program.startswith(app + '.'):
            return True
    return False


def focus_godot(container, project):
    source = globals().get('GODOT_FOCUS_SOURCE')
    if source is None:
        source = Path(__file__).with_name('godot_focus.py').read_text()
    try:
        run(['docker', 'exec', '-u', 'retro', '-e', 'DISPLAY=:0',
             '-e', 'XDG_RUNTIME_DIR=/run/user/wolf', '-e', 'WAYLAND_DISPLAY=wayland-2',
             container, 'python3', '-c', source, project], timeout=10)
        return True
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return False


READINESS_SOURCE = r"""
import ctypes as C
import os
import sys
from pathlib import Path
project = sys.argv[1]
if project != '__desktop__' and not (Path('/projects/Godot') / project / 'project.godot').is_file():
    print('Waiting for the selected project mount in the desktop.')
    raise SystemExit(1)
try:
    x = C.CDLL('libX11.so.6')
    x.XOpenDisplay.argtypes = [C.c_char_p]
    x.XOpenDisplay.restype = C.c_void_p
    x.XDefaultRootWindow.argtypes = [C.c_void_p]
    x.XDefaultRootWindow.restype = C.c_ulong
    x.XInternAtom.argtypes = [C.c_void_p, C.c_char_p, C.c_int]
    x.XInternAtom.restype = C.c_ulong
    x.XGetWindowProperty.argtypes = [C.c_void_p, C.c_ulong, C.c_ulong, C.c_long, C.c_long,
        C.c_int, C.c_ulong, C.POINTER(C.c_ulong), C.POINTER(C.c_int), C.POINTER(C.c_ulong),
        C.POINTER(C.c_ulong), C.POINTER(C.c_void_p)]
    x.XFree.argtypes = [C.c_void_p]
    x.XCloseDisplay.argtypes = [C.c_void_p]
    display = x.XOpenDisplay(None)
    if not display:
        print('Waiting for the desktop X11 display.')
        raise SystemExit(1)
    data = C.c_void_p()
    try:
        root = x.XDefaultRootWindow(display)
        atom = x.XInternAtom(display, b'_NET_SUPPORTING_WM_CHECK', 0)
        actual, format_, count, after = C.c_ulong(), C.c_int(), C.c_ulong(), C.c_ulong()
        result = x.XGetWindowProperty(display, root, atom, 0, 1, 0, 0,
            C.byref(actual), C.byref(format_), C.byref(count), C.byref(after), C.byref(data))
        if result or format_.value != 32 or count.value < 1:
            print('Waiting for the desktop window manager.')
            raise SystemExit(1)
    finally:
        if data:
            x.XFree(data)
        x.XCloseDisplay(display)
except OSError as exc:
    print('Desktop X11 readiness check unavailable: ' + str(exc))
    raise SystemExit(1)
print('Studio Desktop display and project mount are ready.')
"""


def desktop_status(project):
    names = [name for name in run(['docker', 'ps', '--format', '{{.Names}}'], timeout=5).splitlines()
             if re.fullmatch(r'WolfStudioDesktop_[A-Za-z0-9_.-]+', name)]
    if not names:
        return {'ready': False, 'message': 'Waiting for Moonlight to start the Wolf Studio Desktop session.'}
    if len(names) != 1:
        raise RuntimeError('Multiple Wolf Studio Desktop containers are running; cannot select a session safely.')
    result = subprocess.run(['docker', 'exec', '-u', 'retro', '-e', 'DISPLAY=:0',
                             '-e', 'XDG_RUNTIME_DIR=/run/user/wolf', '-e', 'WAYLAND_DISPLAY=wayland-2',
                             names[0], 'python3', '-c', READINESS_SOURCE, project],
                            capture_output=True, text=True, timeout=8)
    return {'ready': result.returncode == 0,
            'message': (result.stdout or result.stderr or 'Waiting for the desktop display.')[-2000:].strip()}


def handle(request):
    project, application = request.get('project'), request.get('application')
    operation = request.get('operation')
    if request.get('version') != 1 or operation not in ('desktop', 'desktop_status') or (operation == 'desktop' and application not in APPS):
        raise ValueError('Unsupported desktop action.')
    if not isinstance(project, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', project):
        raise ValueError('Invalid project name.')
    if operation == 'desktop_status':
        return desktop_status(project)
    # Validate the host-side project without following symlinks.
    base = Path.home() / 'StudioProjects/Godot'
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in (Path.home().parts[1:] if project == '__desktop__' and application != 'godot' else base.parts[1:] + (project,)):
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        if application == 'godot':
            project_fd = os.open('project.godot', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            try:
                if not stat.S_ISREG(os.fstat(project_fd).st_mode):
                    raise ValueError('Missing ordinary Godot project file.')
            finally:
                os.close(project_fd)
        lock = os.open('.studio-desktop.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=fd)
        try:
            if not stat.S_ISREG(os.fstat(lock).st_mode) or os.fstat(lock).st_nlink != 1:
                raise ValueError('Invalid desktop lock.')
            fcntl.flock(lock, fcntl.LOCK_EX)
            names = [name for name in run(['docker', 'ps', '--format', '{{.Names}}']).splitlines()
                     if re.fullmatch(r'WolfStudioDesktop_[A-Za-z0-9_.-]+', name)]
            if len(names) != 1:
                raise RuntimeError('Exactly one running Wolf Studio Desktop container is required. '
                                   'Use Open Studio Desktop to connect first, then try again. Studio will not start or reconfigure containers itself.')
            container = names[0]
            processes = run(['docker', 'top', container, '-eo', 'args'])
            if matching_process(processes, application, project):
                focused = focus_godot(container, project) if application == 'godot' else False
                message = application.title() + ' is already open' + (' for ' + project if application == 'godot' else '') + '; no duplicate launched.'
                if application == 'godot':
                    message += ' Editor focus requested.' if focused else ' Automatic editor focus unavailable; select it inside the desktop.'
                return {'message': message, 'reused': True, 'focused': focused}
            if application == 'godot':
                pending = '.studio-godot-pending'
                try:
                    marker = os.open(pending, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                except FileNotFoundError:
                    marker = None
                if marker is not None:
                    try:
                        info = os.fstat(marker)
                        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                            raise ValueError('Invalid pending Godot launch marker.')
                        if time.time() - info.st_mtime < 120:
                            raise RuntimeError('A Godot launch is already pending for this project. Check the desktop; wait two minutes before retrying to avoid duplicates.')
                    finally:
                        os.close(marker)
                    os.unlink(pending, dir_fd=fd)
                marker = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
                os.close(marker)
                # Preserve the operator's working studio edit command unchanged.
                try:
                    run([str(Path.home() / '.local/bin/studio'), 'edit', project], timeout=60)
                except Exception:
                    # Retain the marker after ambiguous timeout; a nonzero remote
                    # command may also have started a detached child already.
                    raise
                # Keep the lock briefly while the detached editor acquires its process.
                for _ in range(8):
                    if matching_process(run(['docker', 'top', container, '-eo', 'args']), application, project):
                        os.unlink(pending, dir_fd=fd)
                        focused = focus_godot(container, project)
                        return {'message': 'Godot opened for ' + project + '.', 'reused': False, 'focused': focused}
                    time.sleep(.5)
                raise RuntimeError('Godot launch was requested but no editor process was confirmed. Check the running desktop; no automatic retry was made.')
            run(['docker', 'exec', '-u', 'retro', container, 'flatpak', 'info', '--show-ref', APPS[application]])
            command = ['docker', 'exec', '-d', '-u', 'retro', '-e', 'DISPLAY=:0',
                       '-e', 'XDG_RUNTIME_DIR=/run/user/wolf', '-e', 'WAYLAND_DISPLAY=wayland-2',
                       '-w', '/home/retro' if project == '__desktop__' else '/projects/Godot/' + project, container, 'flatpak', 'run', APPS[application]]
            run(command)
            for _ in range(8):
                if matching_process(run(['docker', 'top', container, '-eo', 'args']), application, project):
                    return {'message': application.title() + ' opened in the existing Studio Desktop for ' + project + '.', 'reused': False}
                time.sleep(.5)
            raise RuntimeError(application.title() + ' launch was requested but its process was not confirmed. Check the existing desktop and installed Flatpak; no automatic retry was made.')
        finally:
            os.close(lock)
    finally:
        os.close(fd)


def main():
    try:
        data = sys.stdin.buffer.read(8193)
        if len(data) > 8192:
            raise ValueError('Desktop request too large.')
        result = handle(json.loads(data))
        print(json.dumps({'ok': True, 'result': result}))
        return 0
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
