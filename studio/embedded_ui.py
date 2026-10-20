"""Compact GTK view. RPC operations never run on the GTK main thread."""
import json
from gi.repository import Gtk, GLib, Pango, Gdk
from transcript import Transcript, matches
from embedded_codex import Conversation


class EmbeddedView:
    def __init__(self, app, config, project, identifier=None):
        self.app = app
        self.alive = True
        self.working = False
        self.ready = False
        self.initial_prompt = None
        self.items = {}
        self.transcript = Transcript()
        self.search_index = -1
        self.search_hits = []
        self.approval_dialogs = []
        self.approval_ids = set()
        self.dialog = app.window
        self.panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        app.ai_output_area.pack_start(self.panel, True, True, 0)
        app.ai_controls.hide()
        app.ai_advanced.hide()
        box = self.panel
        box.set_border_width(6)
        box.set_spacing(6)
        self.status = Gtk.Label(label='Connecting to local Codex…', xalign=0)
        self.status.set_line_wrap(True)
        self.status.set_max_width_chars(60)
        box.pack_start(self.status, False, False, 0)
        self.output = Gtk.TextView(editable=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.output.set_left_margin(10)
        self.output.set_right_margin(10)
        self.output.set_pixels_above_lines(3)
        buffer = self.output.get_buffer()
        buffer.create_tag('bold', weight=Pango.Weight.BOLD)
        buffer.create_tag('code', family='monospace', background='#252830')
        buffer.create_tag('tool', family='monospace', scale=.9)
        buffer.create_tag('role', weight=Pango.Weight.BOLD, pixels_above_lines=8)
        buffer.create_tag('search', background='#8a6820', foreground='#ffffff')
        self.output.get_accessible().set_name('Conversation transcript')
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(120)
        scroll.set_vexpand(True)
        self.scroll = scroll
        scroll.add(self.output)
        split = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        split.set_wide_handle(True)
        transcript_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        transcript_area.pack_start(scroll, True, True, 0)
        split.pack1(transcript_area, resize=True, shrink=False)
        box.pack_start(split, True, True, 0)
        search_bar = Gtk.Box(spacing=4)
        self.search = Gtk.SearchEntry(placeholder_text='Search transcript')
        self.search.set_width_chars(18)
        self.search.get_accessible().set_name('Search transcript')
        self.search_count = Gtk.Label(label='0 matches')
        self.previous = Gtk.Button(label='Previous')
        self.next = Gtk.Button(label='Next')
        search_bar.pack_start(self.search, True, True, 0)
        for widget in (self.search_count, self.previous, self.next):
            search_bar.pack_start(widget, False, False, 0)
        transcript_area.pack_start(search_bar, False, False, 0)
        self.search.connect('search-changed', lambda _: self.update_search())
        self.search.connect('activate', lambda _: self.navigate(1))
        self.previous.connect('clicked', lambda _: self.navigate(-1))
        self.next.connect('clicked', lambda _: self.navigate(1))
        composer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        composer.pack_start(Gtk.Label(label='Message · Ctrl+Enter to send', xalign=0), False, False, 0)
        self.prompt = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.prompt.set_accepts_tab(False)
        self.prompt.set_left_margin(6)
        self.prompt.set_right_margin(6)
        self.prompt.get_accessible().set_name('Message this Project conversation')
        prompt_scroll = Gtk.ScrolledWindow()
        prompt_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        prompt_scroll.set_min_content_height(48)
        prompt_scroll.add(self.prompt)
        composer.pack_start(prompt_scroll, True, True, 0)
        split.pack2(composer, resize=False, shrink=False)
        split.set_position(280)
        bar = Gtk.Box(spacing=6)
        self.send_button = Gtk.Button(label='Send')
        self.stop_button = Gtk.Button(label='Interrupt')
        self.reconnect_button = Gtk.Button(label='Reconnect')
        terminal = Gtk.Button(label='Open Codex Terminal')
        close = Gtk.Button(label='Close')
        close.connect('clicked', lambda _: self.close())
        for button in (self.send_button, self.stop_button, self.reconnect_button, terminal, close):
            bar.pack_start(button, False, False, 0)
        box.pack_start(bar, False, False, 0)
        self.conversation = None
        self.config, self.project, self.identifier = config, project, identifier
        self.send_button.connect('clicked', self.send)
        self.prompt.connect('key-press-event', self.prompt_key)
        self.stop_button.connect('clicked', lambda _: self.task(lambda: self.conversation.interrupt()))
        self.reconnect_button.connect('clicked', self.reconnect)
        terminal.connect('clicked', self.external)
        app.window.connect('destroy', lambda *_: self.close())
        self.panel.show_all()
        self.update_search()
        self.reconnect()

    def append(self, text):
        self.transcript.add('Status', text.strip())
        self.render()

    def render(self):
        adjustment = self.scroll.get_vadjustment()
        follow = adjustment.get_value() >= adjustment.get_upper() - adjustment.get_page_size() - 24
        buffer = self.output.get_buffer()
        text, spans = self.transcript.render()
        buffer.set_text(text)
        for tag, start, end in spans:
            buffer.apply_tag_by_name(tag, buffer.get_iter_at_offset(start), buffer.get_iter_at_offset(end))
        self.update_search(reset=False)
        if follow and not self.search.get_text():
            self.output.scroll_to_iter(buffer.get_end_iter(), 0, False, 0, 0)

    def update_search(self, reset=True):
        buffer = self.output.get_buffer()
        buffer.remove_tag_by_name('search', *buffer.get_bounds())
        self.search_hits = matches(buffer.get_text(*buffer.get_bounds(), True), self.search.get_text())
        if reset:
            self.search_index = -1
        if self.search_index >= len(self.search_hits):
            self.search_index = -1
        for start, end in self.search_hits:
            buffer.apply_tag_by_name('search', buffer.get_iter_at_offset(start), buffer.get_iter_at_offset(end))
        self.previous.set_sensitive(bool(self.search_hits))
        self.next.set_sensitive(bool(self.search_hits))
        self.search_count.set_text(f'{self.search_index + 1} / {len(self.search_hits)}' if self.search_index >= 0
                                   else str(len(self.search_hits)) + ' matches')
        if reset and self.search_hits:
            self.navigate(1)
        elif self.search_index >= 0:
            start, end = self.search_hits[self.search_index]
            buffer.select_range(buffer.get_iter_at_offset(start), buffer.get_iter_at_offset(end))

    def navigate(self, direction):
        if not self.search_hits:
            return
        self.search_index = ((self.search_index + direction) % len(self.search_hits)
                             if self.search_index >= 0 else (0 if direction > 0 else len(self.search_hits) - 1))
        start, end = self.search_hits[self.search_index]
        buffer = self.output.get_buffer()
        buffer.select_range(buffer.get_iter_at_offset(start), buffer.get_iter_at_offset(end))
        self.output.scroll_to_iter(buffer.get_iter_at_offset(start), .1, True, 0, .5)
        self.search_count.set_text(f'{self.search_index + 1} / {len(self.search_hits)}')

    def controls(self):
        self.send_button.set_sensitive(self.ready and not self.working)
        self.stop_button.set_sensitive(self.ready)
        self.reconnect_button.set_sensitive(not self.working and not self.ready)

    def task(self, task, done=None):
        if self.working:
            return
        self.working = True
        self.controls()
        def complete(result, error):
            if not self.alive:
                return
            self.working = False
            if error:
                self.status.set_text(str(error))
                if self.conversation and self.conversation.server and self.conversation.server.closed:
                    self.ready = False
            elif done:
                done(result)
            self.controls()
        self.app.worker(task, complete)

    def reconnect(self, _=None):
        if self.working:
            return
        old = self.conversation
        if old:
            self.identifier = old.thread or self.identifier
            old.close()
        self.ready = False
        for dialog in list(self.approval_dialogs):
            dialog.destroy()
        self.approval_dialogs.clear()
        self.approval_ids.clear()
        # Ignore queued callbacks from a previous transport generation.
        token = object()
        self.token = token
        def event(method, params):
            def deliver():
                if self.alive and self.token is token:
                    self.event(method, params)
            GLib.idle_add(deliver)
        def connect():
            conversation = Conversation(self.config, self.project, event)
            self.conversation = conversation
            if not self.alive:
                conversation.close()
                return
            conversation.connect(self.identifier)
        self.task(connect, lambda _: self.connected())

    def connected(self):
        if not self.conversation or not self.conversation.server or self.conversation.server.closed:
            self.ready = False
            return
        self.ready = True
        self.status.set_text('Project: ' + self.project + ' · Project-only workspace-write · On-request approvals')
        if self.initial_prompt:
            self.prompt.get_buffer().set_text(self.initial_prompt)
            self.initial_prompt = None
            self.send()

    def prompt_key(self, _, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and event.state & Gdk.ModifierType.CONTROL_MASK:
            self.send()
            return True
        return False

    def send(self, _=None):
        buffer = self.prompt.get_buffer()
        text = buffer.get_text(*buffer.get_bounds(), True)
        if not self.ready or self.working or not text.strip():
            return
        if len(text) > 32000 or '\0' in text:
            self.status.set_text('Enter 1–32,000 characters without NUL.')
            return
        self.transcript.add('You', text)
        self.render()
        self.task(lambda: self.conversation.send(text), lambda _: self.prompt.get_buffer().set_text(''))

    def event(self, method, params):
        if method == 'disconnected':
            self.ready = False
            self.status.set_text(params['message'])
            for dialog in list(self.approval_dialogs):
                dialog.destroy()
            self.approval_dialogs.clear()
            self.controls()
        elif method == 'history':
            self.transcript = Transcript()
            self.items.clear()
            for turn in params.get('turns', []):
                for item in turn.get('items', []):
                    if item.get('type') == 'userMessage':
                        self.transcript.add('You', '\n'.join(c.get('text', '') for c in item.get('content', []) if c.get('type') == 'text'))
                    else:
                        self.transcript.item(item, completed=True)
            self.render()
        elif method in ('item/agentMessage/delta', 'item/commandExecution/outputDelta'):
            self.transcript.delta(params, tool=method == 'item/commandExecution/outputDelta')
            self.render()
        elif method in ('item/started', 'item/completed'):
            item = params.get('item', {})
            if item.get('id'):
                self.items[item['id']] = item
            self.transcript.item(item, completed=method == 'item/completed')
            self.render()
        elif method == 'turn/completed':
            self.status.set_text('Project: ' + self.project + ' · Turn ' + params.get('turn', {}).get('status', 'completed'))
        elif method == 'error':
            error = params.get('error', params)
            message = error.get('message', 'Request failed') if isinstance(error, dict) else str(error)
            self.append('Codex error: ' + message)
        elif method == 'unsupported':
            self.append('\nUnsupported server request denied. Use the external terminal if needed.\n')
        elif method == 'approval':
            self.approve(params)

    def approve(self, message):
        if message['id'] in self.approval_ids:
            return
        self.approval_ids.add(message['id'])
        params = message['params']
        if params.get('threadId') != self.conversation.thread:
            self.app.worker(lambda: self.conversation.server.decide(message['id'], False), lambda *_: None)
            return
        dialog = Gtk.Dialog(title='Codex action approval — ' + self.project, transient_for=self.dialog, modal=True)
        dialog.set_default_size(620, 360)
        dialog.add_buttons('Deny', Gtk.ResponseType.CANCEL, 'Approve once', Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        item = self.items.get(params.get('itemId'), {})
        reviewable = message['method'] != 'item/fileChange/requestApproval' or bool(item.get('changes'))
        dialog.set_response_sensitive(Gtk.ResponseType.OK, reviewable)
        view = Gtk.TextView(editable=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        details = {'request': params, 'tool': item}
        view.get_buffer().set_text(message['method'] + '\n\n' + json.dumps(details, indent=2, ensure_ascii=False) +
                                   ('' if reviewable else '\nPatch details unavailable. Deny and use the terminal to review.'))
        scroll = Gtk.ScrolledWindow()
        scroll.add(view)
        dialog.get_content_area().pack_start(scroll, True, True, 0)
        self.approval_dialogs.append(dialog)
        server = self.conversation.server
        def answer(_, response):
            if dialog not in self.approval_dialogs:
                return
            if dialog in self.approval_dialogs:
                self.approval_dialogs.remove(dialog)
            dialog.destroy()
            if self.alive:
                self.app.worker(lambda: server.decide(message['id'], reviewable and response == Gtk.ResponseType.OK),
                                lambda result, error: self.status.set_text(str(error)) if error and self.alive else None)
        dialog.connect('response', answer)
        dialog.show_all()

    def external(self, _=None):
        """Launch independent CLI without disrupting this embedded conversation."""
        try:
            from native_tools import command
            import core
            import subprocess
            import shutil
            import shlex
            argv, cwd = command(self.config, 'codex', self.project)
            xfce = shutil.which('xfce4-terminal')
            terminal_argv = ([xfce, '--window', '--color-bg=#161a20',
                              '--color-fg=#e5e7eb', '--command=' + shlex.join(argv)]
                             if xfce else core.terminal_args(argv))
            subprocess.Popen(terminal_argv, cwd=str(cwd),
                             stdin=subprocess.DEVNULL, start_new_session=True)
        except (OSError, RuntimeError, ValueError) as exc:
            self.status.set_text('Codex terminal could not open: ' + str(exc))

    def close(self):
        if not self.alive:
            return
        self.alive = False
        for dialog in list(self.approval_dialogs):
            dialog.destroy()
        self.approval_dialogs.clear()
        if self.conversation:
            self.conversation.close()
        self.panel.destroy()
        self.app.ai_controls.show_all()
        self.app.ai_advanced.hide()
