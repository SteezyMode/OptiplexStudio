#!/usr/bin/python3
import json
import os
from pathlib import Path
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib
import core
import project_client
from session_ui import SessionUI
from project_ui import ProjectUI, remembered_project, remember_project

APP_NAME = 'OptiPlex Studio'
APP_ID = 'com.monumentrisk.OptiPlexStudio'
PROGRAM_NAME = 'optiplex-studio'


def configure_identity():
    GLib.set_prgname(PROGRAM_NAME)
    if GLib.get_application_name() != APP_NAME:
        GLib.set_application_name(APP_NAME)
    Gdk.set_program_class(PROGRAM_NAME)


ROOT = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'optiplex-studio' / 'config.json'

class Studio(SessionUI, ProjectUI, Gtk.Application):
    def __init__(self):
        configure_identity()
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.last_project = remembered_project()
        self.restoring = False
        self.sni = None
        self.tray = None
        self.busy = False
        self.config = {'host': '', 'user': 'optiplex', 'moonlight_appimage': '', 'moonlight_app': ''}
        try:
            saved = json.loads(CONFIG.read_text())
            if isinstance(saved, dict):
                self.config.update(saved)
        except (OSError, ValueError, TypeError):
            pass

    def label(self, text, name='section'):
        label = Gtk.Label(label=text, xalign=0)
        label.set_name(name)
        label.set_line_wrap(True)
        label.set_max_width_chars(90)
        return label

    def button(self, text, callback, name='setting'):
        b = Gtk.Button(label=text)
        b.set_name(name)
        b.connect('clicked', callback)
        return b

    def do_activate(self):
        if self.window:
            self.restore()
            return
        provider = Gtk.CssProvider()
        provider.load_from_path(str(ROOT / 'style.css'))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, 600)
        Gtk.Window.set_default_icon_name(PROGRAM_NAME)
        self.window = Gtk.ApplicationWindow(application=self, title=APP_NAME)
        self.window.set_wmclass(PROGRAM_NAME, PROGRAM_NAME)
        self.window.set_default_size(700, 600)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        icon = ROOT.parent / 'assets' / 'optiplex-studio.png'
        if icon.exists():
            self.window.set_icon_from_file(str(icon))
        else:
            self.window.set_icon_name('optiplex-studio')
        self.window.connect('delete-event', self.close_window)
        self.window.connect('window-state-event', self.window_state)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=13, border_width=20)
        body.set_name('shell')
        self.window.add(body)
        head = Gtk.Box(spacing=12)
        title = self.label('OPTIPLEX STUDIO', 'title')
        head.pack_start(title, True, True, 0)
        head.pack_end(self.button('SETTINGS', self.settings), False, False, 0)
        body.pack_start(head, False, False, 0)
        body.pack_start(Gtk.Separator(), False, False, 0)
        row = Gtk.Box(spacing=8)
        self.combo = Gtk.ComboBoxText()
        self.combo.connect('changed', self.selection_changed)
        row.pack_start(self.combo, True, True, 0)
        self.create_button = self.button('+ New Project', self.create_project)
        row.pack_start(self.create_button, False, False, 0)
        self.refresh_button = self.button('Refresh', lambda _: self.refresh())
        row.pack_start(self.refresh_button, False, False, 0)
        body.pack_start(row, False, False, 0)
        self.active_label = self.label('ACTIVE PROJECT: none', 'section')
        body.pack_start(self.active_label, False, False, 0)
        self.detail = self.label('Loading projects…', 'detail')
        body.pack_start(self.detail, False, False, 0)
        tabs = Gtk.Notebook()
        body.pack_start(tabs, True, True, 0)
        self.project_buttons, self.godot_buttons, self.connection_buttons = [], [], []
        def page(title):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, border_width=10)
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.add(box)
            tabs.append_page(scroller, Gtk.Label(label=title))
            return box
        def grid(box, entries, columns=2):
            layout = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True)
            for index, (caption, callback, prerequisite) in enumerate(entries):
                button = self.button(caption, callback, 'power')
                if prerequisite == 'project':
                    self.project_buttons.append(button)
                elif prerequisite == 'godot':
                    self.godot_buttons.append(button)
                else:
                    self.connection_buttons.append(button)
                button.set_sensitive(False)
                layout.attach(button, index % columns, index // columns, 1, 1)
            box.pack_start(layout, False, False, 0)
        project_page = page('Project')
        grid(project_page, [
            ('Project Files', self.browse_project, 'project'), ('Import Assets', self.import_assets, 'project'),
            ('Browse Assets', self.browse_assets, 'project'), ('Project Documents', self.documents, 'project'),
            ('Share Project Context', self.share_context, 'project')])
        project_page.pack_start(self.label('Shared assets, notes and Git history. Browser tools download locally; use Import Assets to transfer their exports into this project.', 'helper'), False, False, 0)
        ai_page = page('AI Workspace')
        grid(ai_page, [
            ('New Codex Session', lambda _: self.action('code'), 'project'),
            ('Resume Session…', self.session_browser, 'project'),
            ('Codex Conversation Picker', lambda _: self.action('resume'), 'project'),
            ('Copy ChatGPT Brief', lambda _: self.copy_brief(), 'project'),
            ('Open ChatGPT', self.open_chatgpt, None)] + [
            (name, lambda _, n=name: self.action('code', prompt=core.CODEX_TASKS[n]),
             'godot' if name in ('Fix Godot Errors', 'Validate Project') else 'project') for name in core.CODEX_TASKS])
        ai_page.pack_start(self.label('Codex uses the active project directory and AGENTS.md. Export and review Project Context, then attach it to ChatGPT manually.', 'helper'), False, False, 0)
        tools = page('Creative Tools')
        self.desktop_button = self.button('Open Studio Desktop', self.open_studio_desktop, 'power')
        tools.pack_start(self.desktop_button, False, False, 0)
        self.connection_buttons.append(self.desktop_button)
        grid(tools, [('Godot', lambda _: self.action('edit'), 'godot'),
                     ('Blender', lambda _: self.open_desktop_application('blender'), None),
                     ('Krita', lambda _: self.open_desktop_application('krita'), None),
                     ('ChatGPT in Wolf', lambda _: self.open_desktop_application('chatgpt'), None),
                     ('Moonlight', self.open_moonlight, None)] + [
                     (name, lambda _, n=name, u=url: self.creative_tool(n, u), None) for name, url in core.APPS])
        tools.pack_start(self.label('Desktop applications use the existing Wolf session. Godot opens or focuses the selected Godot project. Blender and Krita can also launch independently.', 'helper'), False, False, 0)
        self.transfer_progress = Gtk.ProgressBar(show_text=True)
        self.transfer_progress.set_text('Project transfers use Tailscale SSH')
        body.pack_start(self.transfer_progress, False, False, 0)
        self.status = self.label('Ready', 'footer')
        self.status.set_selectable(True)
        body.pack_start(self.status, False, False, 0)
        self.codex_status = self.label('Codex conversations use the active project directory.', 'detail')
        body.pack_start(self.codex_status, False, False, 0)
        self.rows = []
        self.initialize_tray()
        self.window.show_all()
        self.refresh()
        if not self.config.get('host'):
            GLib.idle_add(self.settings, None)

    def open_url(self, url):
        config = dict(self.config)
        self.status.set_text('Opening Studio browser through Tailscale…')
        def done(result, error):
            self.status.set_text(error or result)
        self.worker(lambda: core.open_application(config, url), done)

    def open_moonlight(self, _=None):
        def task(progress):
            command = core.moonlight_prefix(self.config)
            import subprocess
            # Open the existing client/pairing UI, without guessing an app title.
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=core.moonlight_environment(self.config, command))
            try:
                _, errors = process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                threading.Thread(target=process.communicate, daemon=True).start()
                return 'Moonlight opened. Use an advertised application; Studio does not configure Wolf profiles.'
            if process.returncode:
                raise RuntimeError('Moonlight failed: ' + errors.decode(errors='replace')[-2000:])
            return 'Moonlight launch requested.'
        self.project_task(task, lambda message: self.status.set_text(message), 'Opening Moonlight…')

    def do_shutdown(self):
        core.close_tunnels()
        Gtk.Application.do_shutdown(self)

    def worker(self, task, done):
        def run():
            try:
                result, error = task(), None
            except Exception as exc:
                result, error = None, str(exc)
            GLib.idle_add(done, result, error)
        threading.Thread(target=run, daemon=True).start()

    def refresh(self):
        if getattr(self, 'refreshing', False):
            return
        self.refreshing = True
        config = dict(self.config)
        selected = self.combo.get_active_id() or getattr(self, 'last_project', None)
        self.rows = []
        self.combo.remove_all()
        self.selection_changed(None)
        self.refresh_button.set_sensitive(False)
        self.status.set_text('Reading Studio Projects API…')
        def done(rows, error):
            self.refreshing = False
            self.refresh_button.set_sensitive(True)
            if config != self.config:
                self.refresh()
                return
            if error:
                self.rows = []
                self.combo.remove_all()
                self.selection_changed(None)
                self.status.set_text('Project API unavailable: ' + error)
                return
            self.rows = rows
            self.combo.remove_all()
            for p in rows:
                self.combo.append(p['name'], p['name'])
            if not selected or not self.combo.set_active_id(selected):
                self.combo.set_active(0 if rows else -1)
            self.status.set_text(f'{len(rows)} projects loaded.' if rows else 'No projects yet. Create a project to begin.')
        def discover():
            api_rows = core.projects(config)
            local_rows = project_client.request(config, 'Studio', 'list_projects')
            merged = {p['name']: dict(p, type=p.get('type', 'Godot')) for p in api_rows}
            merged.update({p['name']: p for p in local_rows})
            return sorted(merged.values(), key=lambda p: p['name'].lower())
        self.worker(discover, done)

    def selection_changed(self, _):
        name = self.combo.get_active_id()
        selected = any(p['name'] == name for p in self.rows)
        for b in self.project_buttons + getattr(self, 'tray_project_items', []) + getattr(self, 'tray_creative_items', []):
            b.set_sensitive(selected and not self.busy)
        p = next((p for p in self.rows if p['name'] == name), {})
        for button in getattr(self, 'godot_buttons', []):
            button.set_sensitive(selected and p.get('type', 'Godot') == 'Godot' and not self.busy)
        try:
            core.ssh_args(self.config, 'edit', 'Studio')
            connection_ready = True
        except ValueError:
            connection_ready = False
        for button in getattr(self, 'connection_buttons', []):
            button.set_sensitive(connection_ready and not self.busy)
        self.create_button.set_sensitive(connection_ready and not self.busy)
        if hasattr(self.combo, 'set_sensitive'):
            self.combo.set_sensitive(not self.busy)
        if hasattr(self, 'active_label'):
            self.active_label.set_text('ACTIVE PROJECT: ' + (name if selected else 'none'))
        if selected and hasattr(self, 'last_project') and name != self.last_project:
            self.last_project = name
            try:
                remember_project(name)
            except OSError as exc:
                self.status.set_text('Could not remember selected project: ' + str(exc))
        p = next((p for p in self.rows if p['name'] == name), {})
        self.detail.set_text(' · '.join([str(p.get('type', 'Godot')), str(p.get('branch') or 'No branch'), 'Git status unavailable' if p.get('dirty') is None else 'Uncommitted changes' if p.get('dirty') else 'Clean', str(p.get('commit') or 'No commits')]) if p else 'Select a project.')

    def action(self, action, name=None, template='Godot', session_id=None, prompt=None, all_sessions=False):
        if self.busy:
            return
        name = name or self.combo.get_active_id()
        if action != 'new' and not any(p['name'] == name for p in self.rows):
            self.status.set_text('Select a project from a successful API refresh first.')
            return
        if action == 'edit' and next((p.get('type', 'Godot') for p in self.rows if p['name'] == name), None) != 'Godot':
            self.status.set_text('Select a Godot project to open Godot.')
            return
        try:
            core.ssh_args(self.config, action, name)
        except ValueError as exc:
            self.status.set_text(str(exc))
            return
        self.busy = True
        self.create_button.set_sensitive(False)
        self.selection_changed(None)
        self.status.set_text('Opening Codex terminal…' if action in ('code', 'resume') else 'Connecting Moonlight and waiting for Studio Desktop…' if action == 'edit' else 'Waiting for remote Studio…')
        config = dict(self.config)
        stream_errors = []
        terminal_released = [False]
        def stream_error(message):
            stream_errors.append(message)
            GLib.idle_add(self.status.set_text, message)
        def done(result, error):
            message = error or (stream_errors[-1] if stream_errors else result)
            if terminal_released[0]:
                if hasattr(self, 'codex_status'):
                    self.codex_status.set_text(f'Codex — {name}: {message}')
                if not self.busy:
                    self.status.set_text(message)
                return
            self.busy = False
            self.create_button.set_sensitive(True)
            self.selection_changed(None)
            self.status.set_text(message)
            if error:
                self.notice('Studio action failed', error)
            if action == 'new' and not error:
                self.last_project = name
                try:
                    remember_project(name)
                except OSError as exc:
                    self.status.set_text('Project created; selection could not be remembered: ' + str(exc))
                self.combo.set_active(-1)
                self.refresh()
        def started():
            def release_terminal():
                terminal_released[0] = True
                self.busy = False
                self.create_button.set_sensitive(True)
                self.selection_changed(None)
                message = f'Codex terminal active for {name}.' + (' Select a conversation in its picker.' if action == 'resume' else '')
                if hasattr(self, 'codex_status'):
                    self.codex_status.set_text(message)
                self.status.set_text(message)
            GLib.idle_add(release_terminal)
        def task():
            if action == 'new':
                result = project_client.request(config, name, 'create', template=template)
                return result.get('warning') or f'Created {name} with shared assets, documents and Git initialized. No commit made.'
            if action in ('code', 'resume'):
                project_client.request(config, name, 'ensure_docs')
            callbacks = dict(on_started=started, on_error=stream_error)
            if session_id is not None:
                callbacks['session_id'] = session_id
            if prompt is not None:
                callbacks['prompt'] = prompt
            if all_sessions:
                callbacks['all_sessions'] = True
            if action == 'edit':
                callbacks['on_progress'] = lambda message: GLib.idle_add(self.status.set_text, message)
            return core.run_action(config, action, name, **callbacks)
        self.worker(task, done)

    def create_project(self, _):
        dialog = Gtk.Dialog(title='New project', transient_for=self.window, modal=True)
        dialog.add_buttons('CANCEL', Gtk.ResponseType.CANCEL, 'CREATE', Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_border_width(18)
        box.pack_start(self.label('Project name: letters, numbers, hyphens, underscores.', 'helper'), False, False, 6)
        entry = Gtk.Entry()
        entry.set_max_length(128)
        entry.set_activates_default(True)
        dialog.set_default_response(Gtk.ResponseType.OK)
        box.pack_start(entry, False, False, 6)
        template = Gtk.ComboBoxText()
        for kind in project_client.policy.PROJECT_TYPES:
            template.append_text(kind)
        template.set_active(0)
        box.pack_start(template, False, False, 6)
        box.pack_start(self.label('Creates a shared project with categorized assets, GAME.md, PROGRESS.md, DECISIONS.md and AGENTS.md. Initializes Git without a commit.', 'helper'), False, False, 6)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            name, kind = entry.get_text(), template.get_active_text()
            dialog.destroy()
            self.action('new', name, template=kind)
        else:
            dialog.destroy()

    def settings(self, _):
        dialog = Gtk.Dialog(title='Studio connection', transient_for=self.window, modal=True)
        dialog.add_buttons('CANCEL', Gtk.ResponseType.CANCEL, 'SAVE', Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_border_width(18)
        entries = {}
        for key, title in [('host', 'OptiPlex Tailscale IPv4 address (100.64.0.0/10)'), ('user', 'SSH user'), ('moonlight_appimage', 'Moonlight AppImage path (optional; blank for automatic detection)'), ('moonlight_app', 'Wolf desktop app title (blank = OptiPlex Studio Desktop)')]:
            box.pack_start(self.label(title, 'helper'), False, False, 5)
            entries[key] = Gtk.Entry(text=str(self.config.get(key, '')))
            box.pack_start(entries[key], False, False, 5)
        box.pack_start(self.label('Uses existing SSH keys and trusted host keys.\nComplete Tailscale and SSH pairing using your existing setup.\nNo passwords or NOW settings are stored here.', 'helper'), False, False, 8)
        dialog.show_all()
        while dialog.run() == Gtk.ResponseType.OK:
            candidate = dict(self.config)
            candidate.update({k: e.get_text().strip() for k, e in entries.items()})
            try:
                core.ssh_args(candidate, 'edit', 'validation')
                CONFIG.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                temp = CONFIG.with_suffix('.tmp')
                fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'w') as out:
                    json.dump(candidate, out)
                temp.replace(CONFIG)
                self.config = candidate
                self.status.set_text('Studio connection saved.')
                self.refresh()
                break
            except (ValueError, OSError) as exc:
                self.status.set_text(str(exc))
        dialog.destroy()

    def restore(self):
        self.restoring = True
        self.window.deiconify()
        self.window.show_all()
        self.window.present()
        def finish():
            self.window.deiconify()
            self.window.present()
            self.restoring = False
        GLib.timeout_add(140, finish)

    def tray_available(self):
        return self.sni is not None or (self.tray is not None and self.tray.is_embedded())

    def close_window(self, *_):
        if self.tray_available():
            self.window.hide()
            return True
        return False

    def window_state(self, _, event):
        if not self.restoring and event.changed_mask & Gdk.WindowState.ICONIFIED and event.new_window_state & Gdk.WindowState.ICONIFIED and self.tray_available():
            self.window.hide()
        return False

    def initialize_tray(self):
        self.menu = Gtk.Menu()
        self.tray_project_items = []
        # Optional creative shortcuts use exactly the same launch handlers as the dashboard.
        # Missing/disabled shortcuts never affect the main project or connection actions.
        creative = Gtk.Menu()
        self.tray_creative_items = []
        for label, callback, project_required in [
            ('Godot', lambda: self.action('edit'), True),
            ('Blender', lambda: self.open_desktop_application('blender'), False),
            ('Krita', lambda: self.open_desktop_application('krita'), False),
        ]:
            enabled = getattr(self, 'config', {}).get('tray_creative_tools', ['Godot', 'Blender', 'Krita'])
            if not isinstance(enabled, list) or label not in enabled:
                continue
            item = Gtk.MenuItem(label=label)
            item.connect('activate', lambda _, cb=callback: cb())
            creative.append(item)
            if project_required:
                item.set_sensitive(False)
                self.tray_creative_items.append(item)
        if creative.get_children():
            group = Gtk.MenuItem(label='Creative Tools')
            group.set_submenu(creative)
            self.menu.append(group)
        for text, callback in [('Open OptiPlex Studio', self.restore), ('Open Studio Desktop', lambda: (self.restore(), self.open_studio_desktop())), ('New Codex conversation', lambda: (self.restore(), self.action('code'))), ('Resume conversation', lambda: (self.restore(), self.session_browser())), ('Studio workspace', lambda: self.open_url('https://studio.monumentrisk.com')), ('Settings', lambda: (self.restore(), self.settings(None))), ('Quit', self.quit)]:
            item = Gtk.MenuItem(label=text)
            item.connect('activate', lambda _, cb=callback: cb())
            self.menu.append(item)
            if text in ('New Codex conversation', 'Resume conversation'):
                item.set_sensitive(False)
                self.tray_project_items.append(item)
        self.menu.show_all()
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            reply = bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'NameHasOwner', GLib.Variant('(s)', ('org.kde.StatusNotifierWatcher',)), GLib.VariantType('(b)'), Gio.DBusCallFlags.NONE, 1500, None)
            if reply.unpack()[0]:
                for namespace in ('AyatanaAppIndicator3', 'AppIndicator3'):
                    try:
                        gi.require_version(namespace, '0.1')
                        module = __import__('gi.repository', fromlist=[namespace])
                        api = getattr(module, namespace)
                        self.sni = api.Indicator.new('optiplex-studio', 'optiplex-studio-tray', api.IndicatorCategory.APPLICATION_STATUS)
                        self.sni.set_title(APP_NAME)
                        if hasattr(self.sni, 'set_desktop_entry'):
                            self.sni.set_desktop_entry(APP_ID)
                        self.sni.set_icon_full('optiplex-studio-tray', APP_NAME)
                        self.sni.set_menu(self.menu)
                        self.sni.set_status(api.IndicatorStatus.ACTIVE)
                        return
                    except (ImportError, ValueError):
                        pass
        except GLib.Error:
            pass
        self.tray = Gtk.StatusIcon.new_from_icon_name('optiplex-studio-tray')
        source = ROOT.parent / 'assets' / 'optiplex-studio-tray.png'
        if source.exists():
            self.tray.set_from_file(str(source))
        self.tray.set_title(APP_NAME)
        self.tray.set_name(PROGRAM_NAME)
        self.tray.set_tooltip_text(APP_NAME)
        self.tray.connect('activate', lambda _: self.window.hide() if self.window.get_visible() else self.restore())
        self.tray.connect('popup-menu', lambda icon, button, when: self.menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, when))
        self.tray.set_visible(True)

if __name__ == '__main__':
    raise SystemExit(Studio().run(None))
