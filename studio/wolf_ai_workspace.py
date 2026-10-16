#!/usr/bin/python3
"""Project-scoped graphical Codex picker inside the persistent Wolf desktop."""
import json
import os
from pathlib import Path
import re
import subprocess
import threading

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

PROJECTS = Path('/projects/Godot')
HOST = os.environ.get('STUDIO_CODEX_HOST', '')
USER = os.environ.get('STUDIO_CODEX_USER', 'optiplex')
KEY = Path.home() / '.ssh/studio-codex'
MAX_OUTPUT = 1024 * 1024


def project_names():
    if not PROJECTS.is_dir():
        return []
    return sorted(p.name for p in PROJECTS.iterdir() if p.is_dir() and not p.is_symlink()
                  and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', p.name))


def remote_args(action, project, session=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', project):
        raise ValueError('Choose a valid project.')
    if action not in ('list', 'new', 'resume'):
        raise ValueError('Unsupported operation.')
    if action == 'resume':
        import uuid
        session = str(uuid.UUID(session or ''))
    if not HOST or not re.fullmatch(r'[A-Za-z0-9.:-]{1,253}', HOST):
        raise ValueError('Configure STUDIO_CODEX_HOST to the host Docker bridge address.')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,63}', USER):
        raise ValueError('Invalid host username.')
    if not KEY.is_file():
        raise ValueError('Missing restricted SSH identity: ' + str(KEY))
    command = 'studio-codex ' + ' '.join(x for x in [action, project, session] if x)
    return ['ssh', '-tt' if action != 'list' else '-T',
            '-i', str(KEY), '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'ForwardAgent=no',
            '-o', 'ClearAllForwardings=yes', '-o', 'ConnectTimeout=10',
            USER + '@' + HOST, command]


class Workspace(Gtk.Window):
    def __init__(self):
        super().__init__(title='OptiPlex Studio — Codex')
        self.set_default_size(680, 470)
        self.set_border_width(12)
        self.connect('destroy', Gtk.main_quit)
        self.busy = False
        shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(shell)
        top = Gtk.Box(spacing=8)
        top.pack_start(Gtk.Label(label='Project', xalign=0), False, False, 0)
        self.projects = Gtk.ComboBoxText()
        for name in project_names():
            self.projects.append(name, name)
        if self.projects.get_model() and len(self.projects.get_model()):
            self.projects.set_active(0)
        self.projects.connect('changed', lambda *_: self.refresh())
        top.pack_start(self.projects, True, True, 0)
        shell.pack_start(top, False, False, 0)
        self.model = Gtk.ListStore(str, str, str)
        self.tree = Gtk.TreeView(model=self.model)
        for idx, title in enumerate(('Conversation', 'Last active')):
            cell = Gtk.CellRendererText()
            cell.set_property('ellipsize', 3)
            column = Gtk.TreeViewColumn(title, cell, text=idx)
            column.set_expand(True)
            self.tree.append_column(column)
        scroller = Gtk.ScrolledWindow()
        scroller.add(self.tree)
        shell.pack_start(scroller, True, True, 0)
        actions = Gtk.Box(spacing=8)
        self.new_button = Gtk.Button(label='New Codex Conversation')
        self.resume_button = Gtk.Button(label='Resume Selected')
        self.refresh_button = Gtk.Button(label='Refresh History')
        self.chatgpt_button = Gtk.Button(label='ChatGPT')
        for button in (self.new_button, self.resume_button, self.refresh_button, self.chatgpt_button):
            actions.pack_start(button, False, False, 0)
        shell.pack_start(actions, False, False, 0)
        self.status = Gtk.Label(label='Choose a project', xalign=0)
        self.status.set_line_wrap(True)
        shell.pack_start(self.status, False, False, 0)
        self.new_button.connect('clicked', lambda *_: self.open_codex('new'))
        self.resume_button.connect('clicked', lambda *_: self.open_codex('resume'))
        self.refresh_button.connect('clicked', lambda *_: self.refresh())
        self.chatgpt_button.connect('clicked', lambda *_: subprocess.Popen(['firefox', '--new-window', 'https://chatgpt.com/']))
        self.tree.get_selection().connect('changed', lambda *_: self.sensitivity())
        self.sensitivity()
        GLib.idle_add(self.refresh)

    def sensitivity(self):
        selected = self.projects.get_active_id() is not None and not self.busy
        self.new_button.set_sensitive(selected)
        self.refresh_button.set_sensitive(selected)
        self.projects.set_sensitive(not self.busy)
        self.resume_button.set_sensitive(selected and self.tree.get_selection().get_selected()[1] is not None)

    def refresh(self):
        project = self.projects.get_active_id()
        self.model.clear()
        if not project or self.busy:
            return
        self.busy = True
        self.sensitivity()
        self.status.set_text('Loading existing Codex conversations…')
        def work():
            try:
                result = subprocess.run(remote_args('list', project), capture_output=True, text=True, timeout=45)
                if result.returncode:
                    raise RuntimeError((result.stderr or 'Host session list failed')[-500:])
                if len(result.stdout) > MAX_OUTPUT:
                    raise RuntimeError('Session list too large')
                sessions = json.loads(result.stdout).get('sessions', [])
                def success():
                    if self.projects.get_active_id() == project:
                        for session in sessions:
                            if session.get('project') != project:
                                continue
                            ident = str(session.get('id') or '')
                            if not re.fullmatch(r'[a-fA-F0-9-]{36}', ident):
                                continue
                            self.model.append([str(session.get('title') or ident)[:120],
                                               str(session.get('updatedAt') or 'Unknown'), ident])
                        self.status.set_text(f'{len(self.model)} conversations available for {project}.')
                    self.busy = False
                    self.sensitivity()
                    return False
                GLib.idle_add(success)
            except Exception as exc:
                def failed():
                    self.busy = False
                    self.status.set_text(str(exc))
                    self.sensitivity()
                    return False
                GLib.idle_add(failed)
        threading.Thread(target=work, daemon=True).start()

    def open_codex(self, action):
        project = self.projects.get_active_id()
        if not project:
            return
        session = None
        if action == 'resume':
            model, iterator = self.tree.get_selection().get_selected()
            if iterator is None:
                return
            session = model[iterator][2]
        try:
            args = remote_args(action, project, session)
            subprocess.Popen(['xfce4-terminal', '--disable-server', '--title',
                              'Codex — ' + project, '--execute'] + args)
            self.status.set_text('Opened Codex for ' + project + '.')
        except (OSError, ValueError) as exc:
            self.status.set_text(str(exc))


if __name__ == '__main__':
    window = Workspace()
    window.show_all()
    Gtk.main()
