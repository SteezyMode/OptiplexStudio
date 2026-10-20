"""Project-scoped Codex history browser using server-provided IDs and metadata."""
from datetime import datetime
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import project_client


def session_rows(rows, query='', sort='Recent'):
    query = query.casefold().strip()
    visible = [row for row in rows if query in ' '.join(str(row.get(k) or '') for k in ('title', 'project')).casefold()]
    if sort == 'Name':
        return sorted(visible, key=lambda row: (row['title'].casefold(), row['id']))
    key = 'createdAt' if sort == 'Oldest' else 'updatedAt'
    return sorted(visible, key=lambda row: (row.get(key) or 0, row['id']), reverse=sort != 'Oldest')


class SessionUI:
    def open_embedded(self, identifier=None, prompt=None):
        context = self.selected_context()
        if not context or self.busy:
            return
        old = getattr(self, 'embedded_view', None)
        if old and old.alive:
            self.window.present()
            self.status.set_text('Close the open conversation before opening another Project thread.')
            return
        from embedded_ui import EmbeddedView
        config, project = context
        self.embedded_view = EmbeddedView(self, config, project, identifier)
        if prompt:
            self.embedded_view.initial_prompt = prompt
            self.embedded_view.prompt.set_text(prompt)

    def session_browser(self, _=None):
        context = self.selected_context()
        if not context or self.busy:
            return
        config, project = context
        dialog = Gtk.Dialog(title='Conversations — ' + project, transient_for=self.window, modal=True)
        dialog.set_default_size(650, 420)
        dialog.add_buttons('Close', Gtk.ResponseType.CLOSE, 'Resume Conversation', Gtk.ResponseType.OK)
        resume = dialog.get_widget_for_response(Gtk.ResponseType.OK)
        resume.set_sensitive(False)
        box = dialog.get_content_area()
        box.set_spacing(8)
        box.set_border_width(12)
        box.pack_start(self.label('Active project: ' + project, 'section'), False, False, 0)
        controls = Gtk.Box(spacing=8)
        scope = Gtk.CheckButton(label='All Projects')
        search = Gtk.SearchEntry(placeholder_text='Search conversations or Projects')
        order = Gtk.ComboBoxText()
        for name in ('Recent', 'Oldest', 'Name'):
            order.append_text(name)
        order.set_active(0)
        controls.pack_start(scope, False, False, 0)
        controls.pack_start(search, True, True, 0)
        controls.pack_start(order, False, False, 0)
        box.pack_start(controls, False, False, 0)
        model = Gtk.ListStore(str, str, str, str)
        tree = Gtk.TreeView(model=model)
        for index, title in enumerate(('Conversation', 'Project', 'Last active')):
            renderer = Gtk.CellRendererText(ellipsize=3, width_chars=22)
            column = Gtk.TreeViewColumn(title, renderer, text=index)
            column.set_resizable(True)
            column.set_expand(True)
            tree.append_column(column)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(tree)
        box.pack_start(scroll, True, True, 0)
        status = self.label('Loading Codex metadata…', 'helper')
        box.pack_start(status, False, False, 0)
        more = self.button('Load More', lambda _: load(False))
        box.pack_start(more, False, False, 0)
        state = {'rows': [], 'cursor': None, 'loading': False, 'alive': True}
        def selected():
            rows, iterator = tree.get_selection().get_selected()
            if iterator is None:
                return None
            return next((row for row in state['rows'] if row['id'] == rows[iterator][3]), None)
        def changed(*_):
            row = selected()
            available = row and any(p['name'] == row.get('project') for p in self.rows)
            resume.set_sensitive(bool(available) and not state['loading'])
            if row and not available:
                status.set_text('This conversation is unassigned. Studio cannot verify its Project.')
        def render(*_):
            model.clear()
            for row in session_rows(state['rows'], search.get_text(), order.get_active_text()):
                try:
                    stamp = datetime.fromtimestamp(row['updatedAt']).strftime('%Y-%m-%d %H:%M') if row.get('updatedAt') else 'Unknown'
                except (TypeError, ValueError, OverflowError, OSError):
                    stamp = 'Unknown'
                model.append([row['title'], row.get('project') or 'Unassigned', stamp, row['id']])
            changed()
        def load(reset=True):
            if state['loading']:
                return
            if reset:
                state['rows'], state['cursor'] = [], None
                render()
            state['loading'] = True
            for widget in (scope, more, resume):
                widget.set_sensitive(False)
            status.set_text('Reading Codex sessions locally…')
            def done(page, error):
                if not state['alive']:
                    return
                state['loading'] = False
                scope.set_sensitive(True)
                if error:
                    status.set_text('Conversation list unavailable: ' + error + ' Check your native Codex installation and retry.')
                    more.set_label('Retry')
                    more.set_sensitive(True)
                    return
                by_id = {row['id']: row for row in state['rows']}
                by_id.update({row['id']: row for row in page['sessions']})
                state['rows'] = list(by_id.values())
                state['cursor'] = page.get('nextCursor')
                more.set_label('Load More')
                more.set_sensitive(bool(state['cursor']))
                status.set_text(f'{len(state["rows"])} conversations loaded. Search and sort apply to loaded pages.' + (' More pages available.' if state['cursor'] else ''))
                render()
            all_projects, cursor = scope.get_active(), state['cursor']
            self.worker(lambda: project_client.request(config, project, 'sessions', all_projects=all_projects, cursor=cursor), done)
        scope.connect('toggled', lambda _: load())
        search.connect('search-changed', render)
        order.connect('changed', render)
        tree.get_selection().connect('changed', changed)
        tree.connect('row-activated', lambda *_: dialog.response(Gtk.ResponseType.OK) if resume.get_sensitive() else None)
        dialog.show_all()
        load()
        result = dialog.run()
        row = selected() if result == Gtk.ResponseType.OK else None
        state['alive'] = False
        dialog.destroy()
        if row and any(p['name'] == row.get('project') for p in self.rows):
            self.combo.set_active_id(row['project'])
            self.open_embedded(identifier=row['id'])
