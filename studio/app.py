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
from tools_ui import ToolsUI
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

class Studio(ToolsUI, SessionUI, ProjectUI, Gtk.Application):
    def __init__(self):
        configure_identity()
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.last_project = remembered_project()
        self.restoring = False
        self.sni = None
        self.tray = None
        self.busy = False
        self.config = {'projects_dir': str(Path.home() / 'StudioProjects')}
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
        self.settings_button = self.button('SETTINGS', self.settings)
        head.pack_end(self.settings_button, False, False, 0)
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
        self.notebook = tabs
        body.pack_start(tabs, True, True, 0)
        self.project_buttons, self.godot_buttons = [], []
        def page(title, scroll=True):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, border_width=10)
            if scroll:
                scroller = Gtk.ScrolledWindow()
                scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
                scroller.add(box)
                tabs.append_page(scroller, Gtk.Label(label=title))
            else:
                tabs.append_page(box, Gtk.Label(label=title))
            return box
        def grid(box, entries, columns=2, button_name='power'):
            layout = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True)
            for index, (caption, callback, prerequisite) in enumerate(entries):
                button = self.button(caption, callback, button_name)
                if prerequisite == 'project':
                    self.project_buttons.append(button)
                elif prerequisite == 'godot':
                    self.godot_buttons.append(button)
                button.set_sensitive(False)
                layout.attach(button, index % columns, index // columns, 1, 1)
            box.pack_start(layout, False, False, 0)
        project_page = page('Overview')
        grid(project_page, [
            ('Project Files', self.browse_project, 'project'), ('Import Assets', self.import_assets, 'project'),
            ('Browse Assets', self.browse_assets, 'project'), ('Project Documents', self.documents, 'project'),
            ('AI Memory', self.ai_memory, 'project'),
            ('Share Project Context', self.share_context, 'project')])
        project_page.pack_start(self.label('Local assets, notes and Git history. Import files into the selected project.', 'helper'), False, False, 0)
        ai_page = page('AI Workspace', scroll=False)
        self.build_ai_workspace(ai_page, grid)
        tools = page('Creative Tools')
        tools.pack_start(self.label('Launch applications for the active Studio project. Install and configure applications in Settings.', 'helper'), False, False, 0)
        grid(tools, [('Godot', lambda _: self.action('edit'), 'godot')] + [
            (('LMMS' if name == 'lmms' else name.title()), lambda _, n=name: self.open_desktop_application(n), None)
            for name in ('blender', 'blockbench', 'lmms', 'krita')])
        grid(tools, [('VSCodium · Open Current Project', lambda _: self.open_desktop_application('vscodium'), 'project')])
        self.add_godot_button = self.button('Add Godot to this Project…', self.add_godot)
        self.add_godot_button.set_sensitive(False)
        tools.pack_start(self.add_godot_button, False, False, 0)
        self.godot_capability_note = self.label('Select a Project to see its Godot capability.', 'helper')
        tools.pack_start(self.godot_capability_note, False, False, 0)
        tools.pack_start(self.label('Blender and Blockbench start in models/, LMMS in music/, and Krita in art/ when those folders exist. All tools remain local; configure installations in Settings.', 'helper'), False, False, 0)
        tools.pack_start(self.label('Alpha tool availability · installation is not proof of a working editor', 'section'), False, False, 0)
        self.tool_health_labels = {}
        for tool in ('godot', 'blender', 'lmms', 'codex'):
            health = self.label(tool.title() + ': Checking…', 'helper')
            health.set_selectable(True)
            tools.pack_start(health, False, False, 0)
            self.tool_health_labels[tool] = health
        tools.pack_start(self.button('Refresh tool status', lambda _: self.refresh_tool_health()), False, False, 0)
        self.notebook.connect('switch-page', lambda _, page, index:
                              self.refresh_tool_health() if index == 2 else None)
        self.transfer_progress = Gtk.ProgressBar(show_text=True)
        self.transfer_progress.set_text('Local project operations')
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
        self.refresh_tool_health()
        if not self.config.get('native_setup_seen') and not os.environ.get('STUDIO_SKIP_ONBOARDING'):
            GLib.idle_add(self.tools_setup)

    def refresh_tool_health(self):
        """Display passive tool discovery without overstating launch or AI readiness."""
        import native_tools
        serial = getattr(self, '_health_serial', 0) + 1
        self._health_serial = serial
        config = dict(self.config)

        def evaluate():
            checks = {name: native_tools.inspect(config, name)
                      for name in native_tools.CORE_ALPHA_TOOLS}
            auth = None
            if checks['codex'].get('path'):
                auth = native_tools.codex_authentication(config)['status']
            rows = {}
            problems = []
            for name, check in checks.items():
                summary, attention = native_tools.readiness_summary(name, check, auth)
                rows[name] = summary
                if attention:
                    problems.append(native_tools.LABELS[name] + ': ' + summary)
            return rows, problems

        def complete(result, error):
            # Ignore results from old config or requests overtaken by a newer refresh.
            if not self.window or serial != self._health_serial or config != self.config:
                return
            if error:
                self.settings_button.set_label('SETTINGS · CHECK FAILED')
                self.settings_button.set_name('settings-warning')
                self.settings_button.set_tooltip_text('Tool status check failed; reopen Settings.')
                for name, label in getattr(self, 'tool_health_labels', {}).items():
                    label.set_text(native_tools.LABELS[name] + ': Check failed · retry in Settings')
                return
            rows, problems = result
            for name, label in getattr(self, 'tool_health_labels', {}).items():
                label.set_text(native_tools.LABELS[name] + ': ' + rows[name])
            self.settings_button.set_label('SETTINGS' + (' · ACTION NEEDED' if problems else ''))
            self.settings_button.set_name('settings-warning' if problems else 'setting')
            self.settings_button.set_tooltip_text(
                '\n'.join(problems) if problems else
                'Core tools detected. Real launches and Codex AI access still require testing.')

        self.worker(evaluate, complete)

    def build_ai_workspace(self, page, grid):
        # Keep launch controls separate from the future embedded output area.
        self.ai_controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.pack_start(self.ai_controls, False, False, 0)
        grid(self.ai_controls, [
            ('New Conversation', lambda _: self.open_embedded(), 'project'),
            ('Resume Conversation', self.session_browser, 'project')], button_name='setting')
        prompt_label = self.label('Describe what to create or change', 'helper')
        self.ai_controls.pack_start(prompt_label, False, False, 0)
        self.ai_prompt = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.ai_prompt.set_name('ai-prompt')
        self.ai_prompt.set_accepts_tab(False)
        self.ai_prompt.set_left_margin(8)
        self.ai_prompt.set_right_margin(8)
        self.ai_prompt.get_accessible().set_name('Custom prompt')
        prompt_scroll = Gtk.ScrolledWindow()
        prompt_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        prompt_scroll.set_min_content_height(80)
        prompt_scroll.set_max_content_height(120)
        prompt_scroll.add(self.ai_prompt)
        self.ai_controls.pack_start(prompt_scroll, False, False, 0)
        self.project_buttons.append(self.ai_prompt)
        self.ai_run = self.button('Run', self.run_ai_prompt)
        self.ai_run.set_halign(Gtk.Align.END)
        self.project_buttons.append(self.ai_run)
        self.ai_controls.pack_start(self.ai_run, False, False, 0)
        self.ai_prompt.get_buffer().connect('changed', lambda _: self.update_ai_run())
        presets = ('Review Changes', 'Fix Godot Errors', 'Validate Project')
        grid(self.ai_controls, [
            (name, lambda _, n=name: self.open_embedded(prompt=core.CODEX_TASKS[n]),
             'project' if name == 'Review Changes' else 'godot') for name in presets], columns=3, button_name='setting')
        self.ai_controls.pack_start(
            self.label('Ask for props, environments, vegetation, characters, animation, '
                       'gameplay or music. Codex uses relevant installed project tools; '
                       'no separate labs or creation modes.', 'helper'), False, False, 0)
        self.ai_advanced = Gtk.Expander(label='More actions')
        self.ai_advanced.set_name('ai-advanced')
        advanced = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.ai_advanced.add(advanced)
        grid(advanced, [
            ('Find Conversations', self.session_browser, 'project'),
            ('External Codex Terminal', lambda _: self.action('code'), 'project'),
            ('Explain Project', lambda _: self.action('code', prompt=core.CODEX_TASKS['Explain Project']), 'project'),
            ('Copy ChatGPT Brief', lambda _: self.copy_brief(), 'project')], button_name='setting')
        advanced.pack_start(self.label('Resume Conversation includes search, sorting and All Projects. Codex conversations run inside Studio. External Codex Terminal remains available. Review Project Context before attaching it to ChatGPT.', 'helper'), False, False, 0)
        # Advanced operations live in a compact toolbar menu, not a permanent grid.
        actions = Gtk.Menu()
        for caption, handler in (
            ('Find Conversations', self.session_browser),
            ('Open Codex Terminal', lambda _: self.action('code')),
            ('Explain Project', lambda _: self.action('code', prompt=core.CODEX_TASKS['Explain Project'])),
            ('Copy ChatGPT Brief', lambda _: self.copy_brief()),
        ):
            item = Gtk.MenuItem(label=caption)
            item.connect('activate', handler)
            actions.append(item)
        actions.show_all()
        menu_button = Gtk.Button(label='More ···')
        menu_button.connect('clicked', lambda button: actions.popup_at_widget(button, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None))
        self.ai_controls.pack_start(menu_button, False, False, 0)
        self.ai_advanced.hide()

        # A future output widget can be packed here without changing launch controls.
        self.ai_output_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.pack_start(self.ai_output_area, True, True, 0)

    def update_ai_run(self):
        if not hasattr(self, 'ai_run'):
            return
        buffer = self.ai_prompt.get_buffer()
        prompt = buffer.get_text(*buffer.get_bounds(), True)
        selected = any(p['name'] == self.combo.get_active_id() for p in self.rows)
        self.ai_run.set_sensitive(selected and not self.busy and bool(prompt.strip())
                                  and len(prompt) <= 32000 and '\0' not in prompt)

    def run_ai_prompt(self, _=None):
        buffer = self.ai_prompt.get_buffer()
        prompt = buffer.get_text(*buffer.get_bounds(), True)
        if not prompt.strip() or len(prompt) > 32000 or '\0' in prompt:
            self.status.set_text('Enter a prompt of 1–32,000 characters without NUL characters.')
            return
        self.open_embedded(prompt=prompt)

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
        self.status.set_text('Reading local workspace…')
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
                self.status.set_text('Workspace unavailable: ' + error)
                return
            self.rows = rows
            self.combo.remove_all()
            for p in rows:
                self.combo.append(p['name'], p['name'])
            if not selected or not self.combo.set_active_id(selected):
                self.combo.set_active(0 if rows else -1)
            self.status.set_text(f'{len(rows)} projects loaded.' if rows else 'No projects yet. Create a project to begin.')
        def discover():
            return project_client.request(config, 'Studio', 'list_projects')
        self.worker(discover, done)

    def selection_changed(self, _):
        name = self.combo.get_active_id()
        selected = any(p['name'] == name for p in self.rows)
        for b in self.project_buttons + getattr(self, 'tray_project_items', []):
            b.set_sensitive(selected and not self.busy)
        p = next((p for p in self.rows if p['name'] == name), {})
        has_godot = p.get('has_godot', True) if selected else False
        for button in getattr(self, 'godot_buttons', []):
            button.set_sensitive(selected and not self.busy and has_godot)
            if hasattr(button, 'set_tooltip_text'):
                button.set_tooltip_text('Godot project ready; executable configured in Settings.'
                                        if has_godot else 'This Project needs Add Godot in Creative Tools.')
        if hasattr(self, 'add_godot_button'):
            self.add_godot_button.set_sensitive(selected and not self.busy and not has_godot)
            self.godot_capability_note.set_text(
                'Godot project files detected. Launch the editor if Godot is installed in Settings.'
                if selected and has_godot else
                'No Godot project files. Add Godot without moving or overwriting existing work.'
                if selected else 'Select a Project to see its Godot capability.')
        self.create_button.set_sensitive(not self.busy)
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
        Studio.update_ai_run(self)
        p = next((p for p in self.rows if p['name'] == name), {})
        self.detail.set_text(' · '.join(['Studio project', str(p.get('branch') or 'No branch'), 'Git status unavailable' if p.get('dirty') is None else 'Uncommitted changes' if p.get('dirty') else 'Clean', str(p.get('commit') or 'No commits')]) if p else 'Select a project.')

    def action(self, action, name=None, template='Studio', session_id=None, prompt=None, all_sessions=False):
        if self.busy:
            return
        name = name or self.combo.get_active_id()
        if action in ('code', 'resume') and name != self.combo.get_active_id():
            self.status.set_text('Switch to the owning Project before opening a conversation.')
            return
        if action != 'new' and not any(p['name'] == name for p in self.rows):
            self.status.set_text('Select a project from a successful workspace refresh first.')
            return
        if action == 'resume' and session_id is None:
            self.session_browser()
            return
        try:
            project_client.policy.project_name(name)
            project_client.workspace(self.config)
        except ValueError as exc:
            self.status.set_text(str(exc))
            return
        self.busy = True
        self.create_button.set_sensitive(False)
        self.selection_changed(None)
        self.status.set_text('Opening Codex terminal…' if action in ('code', 'resume') else 'Opening local Godot…' if action == 'edit' else 'Creating local project…')
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
            from native_tools import run_action
            return run_action(config, action, name, **callbacks)
        self.worker(task, done)

    def add_godot(self, _=None):
        context = self.selected_context()
        if not context or self.busy:
            return
        config, name = context
        row = next((p for p in self.rows if p['name'] == name), {})
        if row.get('has_godot', True):
            self.status.set_text('This Project already has Godot files; nothing changed.')
            return
        if not self.confirm('Add Godot to ' + name + '?',
                            'Create project.godot and a starter scene only where missing. '
                            'Existing documents, art, music, scenes and the legacy manifest stay untouched. '
                            'This does not install Godot or change other projects.'):
            return
        def done(result):
            self.status.set_text('Godot capability ready for ' + name +
                                 (' (created: ' + ', '.join(result['created']) + ').' if result['created'] else '.'))
            self.last_project = name
            self.refresh()
        self.project_task(lambda progress: project_client.request(config, name, 'ensure_godot'),
                          done, 'Adding Godot to ' + name + '…')

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
        box.pack_start(self.label('Creates a local project with categorized assets and project documents. Initializes Git without a commit.', 'helper'), False, False, 6)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            name = entry.get_text()
            dialog.destroy()
            self.action('new', name)
        else:
            dialog.destroy()

    def settings(self, _):
        # Tool status, installation and per-tool executable selection live in one window.
        self.tools_setup()
        self.refresh_tool_health()

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
        for text, callback in [('Open OptiPlex Studio', self.restore), ('New Codex conversation', lambda: (self.restore(), self.action('code'))), ('Resume conversation', lambda: (self.restore(), self.session_browser())), ('Settings', lambda: (self.restore(), self.settings(None))), ('Quit', self.quit)]:
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
