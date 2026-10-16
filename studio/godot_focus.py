"""Focus the selected editor inside the existing desktop's X11/XWayland session.

Executed as fixed source by desktop_helper, not installed as a server service.
Uses the existing X11 library; no wmctrl/xdotool installation is required.
"""
import ctypes as C
import os
from pathlib import Path, PurePosixPath
import re
import sys


def editor_pids(project):
    target = '/projects/Godot/' + project
    result = set()
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            args = [arg.decode(errors='replace') for arg in (entry / 'cmdline').read_bytes().split(b'\0') if arg]
        except OSError:
            continue
        if not args or 'godot' not in Path(args[0]).name.lower() or not any(arg in ('--editor', '-e') for arg in args):
            continue
        for index, arg in enumerate(args):
            value = args[index + 1] if arg == '--path' and index + 1 < len(args) else arg.removeprefix('--path=') if arg.startswith('--path=') else None
            if value is not None and str(PurePosixPath(value)) == target:
                result.add(int(entry.name))
    return result


def focus(project):
    if not isinstance(project, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', project):
        raise ValueError('Invalid project name.')
    pids = editor_pids(project)
    if not pids:
        return False
    x = C.CDLL('libX11.so.6')
    display_t, ulong, integer = C.c_void_p, C.c_ulong, C.c_int
    x.XOpenDisplay.argtypes = [C.c_char_p]
    x.XOpenDisplay.restype = display_t
    x.XDefaultRootWindow.argtypes = [display_t]
    x.XDefaultRootWindow.restype = ulong
    x.XInternAtom.argtypes = [display_t, C.c_char_p, integer]
    x.XInternAtom.restype = ulong
    x.XGetWindowProperty.argtypes = [display_t, ulong, ulong, C.c_long, C.c_long, integer, ulong,
                                    C.POINTER(ulong), C.POINTER(integer), C.POINTER(ulong),
                                    C.POINTER(ulong), C.POINTER(C.POINTER(C.c_ubyte))]
    x.XGetWindowProperty.restype = integer
    x.XFree.argtypes = [C.c_void_p]
    x.XCloseDisplay.argtypes = [display_t]
    x.XMapRaised.argtypes = [display_t, ulong]
    x.XFlush.argtypes = [display_t]
    display = x.XOpenDisplay(None)
    if not display:
        return False
    # A window may close between enumeration and activation; don't let Xlib's
    # default asynchronous error handler terminate the focus request.
    error_callback_t = C.CFUNCTYPE(integer, display_t, C.c_void_p)
    error_callback = error_callback_t(lambda *_: 0)
    x.XSetErrorHandler.argtypes = [error_callback_t]
    x.XSetErrorHandler(error_callback)
    try:
        root = x.XDefaultRootWindow(display)
        def atom(name):
            return x.XInternAtom(display, name.encode(), 0)
        def values(window, name):
            actual, size, count, after = ulong(), integer(), ulong(), ulong()
            data = C.POINTER(C.c_ubyte)()
            status = x.XGetWindowProperty(display, window, atom(name), 0, 65536, 0, 0,
                                          C.byref(actual), C.byref(size), C.byref(count), C.byref(after), C.byref(data))
            try:
                if status or size.value != 32 or not data or count.value > 65536:
                    return []
                array = C.cast(data, C.POINTER(ulong))
                return [array[index] for index in range(count.value)]
            finally:
                if data:
                    x.XFree(data)
        windows = values(root, '_NET_CLIENT_LIST_STACKING') or values(root, '_NET_CLIENT_LIST')
        for window in reversed(windows):
            pid = values(window, '_NET_WM_PID')
            if not pid or pid[0] not in pids:
                continue
            class Data(C.Union):
                _fields_ = [('b', C.c_char * 20), ('s', C.c_short * 10), ('l', C.c_long * 5)]
            class Message(C.Structure):
                _fields_ = [('type', integer), ('serial', ulong), ('send_event', integer),
                            ('display', display_t), ('window', ulong), ('message_type', ulong),
                            ('format', integer), ('data', Data)]
            class Event(C.Union):
                _fields_ = [('message', Message), ('padding', C.c_long * 24)]
            event = Event()
            event.message.type = 33  # ClientMessage
            event.message.send_event = 1
            event.message.display = display
            event.message.window = window
            event.message.message_type = atom('_NET_ACTIVE_WINDOW')
            event.message.format = 32
            event.message.data.l[0] = 2  # explicit pager/client activation request
            x.XSendEvent.argtypes = [display_t, ulong, integer, C.c_long, C.POINTER(Event)]
            x.XSendEvent.restype = integer
            x.XMapRaised(display, window)
            sent = x.XSendEvent(display, root, 0, (1 << 19) | (1 << 20), C.byref(event))
            x.XFlush(display)
            return bool(sent)
        return False
    finally:
        x.XCloseDisplay(display)


if __name__ == '__main__':
    try:
        okay = len(sys.argv) == 2 and focus(sys.argv[1])
        if not okay:
            print('The selected Godot editor has no focusable X11 window in this desktop.', file=sys.stderr)
        raise SystemExit(0 if okay else 1)
    except Exception as exc:
        print('Godot focus unavailable: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
