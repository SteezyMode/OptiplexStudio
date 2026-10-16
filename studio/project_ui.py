"""Native GTK controls for project assets, documentation and reviewed snapshots."""
import base64
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf
import core
import project_client as client
import project_helper as policy


def state_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'optiplex-studio/project-state.json'


def remembered_project():
    try:
        name = json.loads(state_path().read_text()).get('last_project')
        return name if core.valid_name(name) else None
    except (OSError, ValueError, TypeError):
        return None


def remember_project(name):
    policy.project_name(name)
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.project-state-', delete=False) as out:
            temporary = Path(out.name)
            json.dump({'last_project': name}, out)
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


class ProjectUI:
    def active_project(self):
        name = self.combo.get_active_id()
        if not core.valid_name(name) or not any(row['name'] == name for row in self.rows):
            raise ValueError('Select a project from a successful project refresh first.')
        return name

    def notice(self, title, text, parent=None):
        dialog = Gtk.MessageDialog(transient_for=parent or self.window, modal=True,
                                   message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, text=title)
        dialog.format_secondary_text(str(text))
        dialog.run()
        dialog.destroy()

    def confirm(self, title, text, parent=None):
        dialog = Gtk.MessageDialog(transient_for=parent or self.window, modal=True,
                                   message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO, text=title)
        dialog.format_secondary_text(str(text))
        approved = dialog.run() == Gtk.ResponseType.YES
        dialog.destroy()
        return approved

    def project_task(self, task, done, message, parent=None):
        if self.busy:
            self.status.set_text('Wait for the current project operation to finish.')
            return
        self.busy = True
        if parent is not None:
            for response in (Gtk.ResponseType.CLOSE, 1, 2, 3, 4):
                parent.set_response_sensitive(response, False)
        self.create_button.set_sensitive(False)
        self.selection_changed(None)
        self.status.set_text(message)
        def progress(fraction, text='Transferring project data'):
            def update():
                if hasattr(self, 'transfer_progress'):
                    self.transfer_progress.set_fraction(max(0, min(1, fraction)))
                    self.transfer_progress.set_text(text)
            GLib.idle_add(update)
        progress(0, message)
        def complete(result, error):
            self.busy = False
            if parent is not None:
                for response in (Gtk.ResponseType.CLOSE, 1, 2, 3, 4):
                    parent.set_response_sensitive(response, True)
            self.create_button.set_sensitive(True)
            self.selection_changed(None)
            if error:
                self.status.set_text(str(error))
                self.notice('Project operation failed', error, parent)
                return
            progress(1, 'Complete')
            try:
                done(result)
            except Exception as exc:
                self.status.set_text(str(exc))
                self.notice('Project operation failed', exc, parent)
        self.worker(lambda: task(progress), complete)

    def selected_context(self):
        try:
            return dict(self.config), self.active_project()
        except ValueError as exc:
            self.status.set_text(str(exc))
            return None

    def import_assets(self, _=None):
        context = self.selected_context()
        if not context or self.busy:
            return
        config, project = context
        picker = Gtk.FileChooserDialog(title=f'Import assets into {project}', transient_for=self.window,
                                       action=Gtk.FileChooserAction.OPEN)
        picker.add_buttons('CANCEL', Gtk.ResponseType.CANCEL, 'SELECT FILES', Gtk.ResponseType.OK)
        picker.set_select_multiple(True)
        response = picker.run()
        files = picker.get_filenames() if response == Gtk.ResponseType.OK else []
        picker.destroy()
        if not files:
            return
        dialog = Gtk.Dialog(title=f'{project} — Asset destination', transient_for=self.window, modal=True)
        dialog.add_buttons('CANCEL', Gtk.ResponseType.CANCEL, 'CHECK FILES', Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_border_width(16)
        choice = Gtk.ComboBoxText()
        for category, path in policy.CATEGORIES.items():
            choice.append(category, category + ' → ' + path)
        choice.set_active(0)
        box.pack_start(self.label(f'Import {len(files)} file(s) into {project}. Limits: 32 MiB/file, 256 MiB/batch. Supported filenames use letters, numbers, spaces, (), ._-', 'helper'), False, False, 6)
        box.pack_start(choice, False, False, 6)
        dialog.show_all()
        response = dialog.run()
        category = choice.get_active_id()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return
        def planned(plan):
            conflicts = [p['name'] for p in plan if p['expected'] is not None]
            if conflicts and not self.confirm('Replace existing assets?',
                    f'Project: {project}\nDestination: {policy.CATEGORIES[category]}\n' + '\n'.join(conflicts) +
                    '\n\nOnly these checked versions will be replaced. Files changed during the transfer cause a conflict.'):
                self.status.set_text('Import cancelled; no assets transferred.')
                return
            self.project_task(lambda progress: client.import_assets(config, project, plan, category, bool(conflicts), progress),
                              lambda text: self.status.set_text(text), f'Importing assets into {project}…')
        self.project_task(lambda progress: client.plan_import(config, project, files, category), planned,
                          f'Checking filenames in {project}…')

    def browse_assets(self, _=None):
        self.browse_remote_folder(True)

    def browse_remote_folder(self, assets=False):
        context = self.selected_context()
        if not context:
            return
        config, project = context
        def opened(result):
            from file_browser import RemoteFolder
            uri = client.project_uri(config, project, assets=assets)
            self.busy = True
            self.create_button.set_sensitive(False)
            self.selection_changed(None)
            def finished(message, error):
                self.busy = False
                self.selection_changed(None)
                self.status.set_text(error or message)
                if error:
                    self.notice('Cannot open project folder', error)
            self.remote_folder = RemoteFolder(self.window, uri, finished, self.status.set_text)
            try:
                self.remote_folder.start()
            except Exception as exc:
                self.remote_folder.end(error=str(exc))
        self.project_task(lambda progress: client.request(config, project, 'browse' if assets else 'browse_project'),
                          opened, f'Checking {project} folder and SSH access…')

    def creative_tool(self, name, url):
        context = self.selected_context()
        if not context:
            self.open_url(url)
            return
        config, project = context
        dialog = Gtk.Dialog(title=f'{name} — {project}', transient_for=self.window, modal=True)
        dialog.add_buttons('CLOSE', Gtk.ResponseType.CLOSE, 'BROWSE ASSETS', 1, 'IMPORT EXPORTS', 2, 'OPEN TOOL', 3)
        text = (f'Active project: {project}\n\nShared project: {client.remote_project_path(config, project)}\n\n'
                'Browser tools keep their own documents. They do not save directly into the remote project. '
                'Export/download files to this computer, then use Import Assets to transfer them into this project.\n\n' +
                '\n'.join(f'{category}: {path}/' for category, path in policy.CATEGORIES.items()) +
                '\n\nTypical exports: PNG/WebP for sprites, GLB/glTF for models, WAV/OGG for audio. '
                'For tools that open a local file, download the source from Browse Assets first. '
                'Your selected project is preserved when switching tools.')
        content = dialog.get_content_area()
        content.set_border_width(18)
        content.pack_start(self.label(text, 'helper'), True, True, 0)
        dialog.set_default_size(600, 420)
        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        if response == 1:
            self.browse_assets()
        elif response == 2:
            self.import_assets()
        elif response == 3:
            self.open_url(url)

    def open_studio_desktop(self, _=None):
        config = dict(self.config)
        def task(progress):
            return core.launch_studio_desktop(config, on_error=lambda error: GLib.idle_add(self.status.set_text, error))
        self.project_task(task, lambda result: self.status.set_text(result),
                          'Connecting directly to the Wolf desktop…')

    def open_desktop_application(self, application):
        config = dict(self.config)
        project = self.combo.get_active_id() or '__desktop__'
        def task(progress):
            errors = []
            def failed(message):
                errors.append(message)
                GLib.idle_add(self.status.set_text, message)
            stream = core.launch_studio_desktop(config, on_error=failed)
            core.wait_for_studio_desktop(config, '__desktop__', stream_errors=errors,
                                         on_progress=lambda message: GLib.idle_add(self.status.set_text, message))
            result = client.request(config, project, 'desktop', application=application)
            return result['message'] + ' ' + stream
        self.project_task(task, lambda result: self.status.set_text(result), f'Opening {application.title()} in Studio Desktop…')

    def browse_project(self, _=None):
        self.browse_remote_folder(False)

    def documents(self, _=None):
        context = self.selected_context()
        if not context or self.busy:
            return
        config, project = context
        dialog = Gtk.Dialog(title=f'{project} — Documentation', transient_for=self.window, modal=True)
        dialog.add_buttons('CLOSE', Gtk.ResponseType.CLOSE, 'ADD MISSING DOCUMENTS', 1, 'VIEW / EDIT', 2)
        box = dialog.get_content_area()
        box.set_border_width(16)
        box.pack_start(self.label('Adding missing documents never replaces existing files. Editing checks for concurrent changes before saving.', 'helper'), False, False, 6)
        choice = Gtk.ComboBoxText()
        for name in policy.DOCS:
            choice.append_text(name)
        choice.set_active(0)
        box.pack_start(choice, False, False, 6)
        dialog.show_all()
        response = dialog.run()
        document = choice.get_active_text()
        dialog.destroy()
        if response == 1:
            self.project_task(lambda progress: client.request(config, project, 'ensure_docs'),
                              lambda result: self.status.set_text('Created missing documents: ' + (', '.join(result['created']) or 'none; all already exist.')),
                              f'Adding missing documentation to {project}…')
        elif response == 2:
            self.project_task(lambda progress: client.request(config, project, 'docs'),
                              lambda result: self.edit_document(config, project, document, result[document]),
                              f'Reading {project}/{document}…')

    def edit_document(self, config, project, document, current):
        dialog = Gtk.Dialog(title=f'{project} / {document}', transient_for=self.window, modal=True)
        dialog.add_buttons('CANCEL', Gtk.ResponseType.CANCEL, 'SAVE', Gtk.ResponseType.OK)
        dialog.set_default_size(720, 520)
        box = dialog.get_content_area()
        box.set_border_width(12)
        box.pack_start(self.label('Save updates only this document over SSH with a conflict check. No commit is made.', 'helper'), False, False, 6)
        scroll = Gtk.ScrolledWindow()
        text = Gtk.TextView()
        text.set_monospace(True)
        text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text.get_buffer().set_text(current['text'])
        scroll.add(text)
        box.pack_start(scroll, True, True, 0)
        dialog.show_all()
        response = dialog.run()
        buffer = text.get_buffer()
        content = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.project_task(lambda progress: client.request(config, project, 'save_doc', name=document, text=content, expected=current['sha256']),
                              lambda result: self.status.set_text(f'Saved {project}/{document}. No commit made.'), f'Saving {document}…')

    def share_context(self, _=None):
        context = self.selected_context()
        if not context or self.busy:
            return
        config, project = context
        self.project_task(lambda progress: client.request(config, project, 'inventory'),
                          lambda manifest: self.review_snapshot(config, project, manifest), f'Inspecting {project} for a shareable snapshot…')

    def preview_snapshot_file(self, config, project, manifest, path, parent):
        row = next(p for p in manifest['inventory'] if p['path'] == path)
        if not row.get('sha256'):
            self.notice('File not eligible', row['reason'], parent)
            return
        def show(snapshot):
            data = snapshot['diff'].encode() if row.get('deleted') else base64.b64decode(snapshot['files'][0]['data'], validate=True)
            if not row.get('deleted') and policy.digest(data) != row['sha256']:
                raise ValueError('File changed since review; refresh the snapshot.')
            dialog = Gtk.Dialog(title=project + '/' + path, transient_for=parent, modal=True)
            dialog.add_button('CLOSE', Gtk.ResponseType.CLOSE)
            dialog.set_default_size(700, 500)
            scroll = Gtk.ScrolledWindow()
            dialog.get_content_area().pack_start(scroll, True, True, 0)
            if Path(path).suffix.lower() in policy.VISUAL_TYPES:
                loader = GdkPixbuf.PixbufLoader()
                def resize(obj, width, height):
                    scale = min(1, 640 / max(1, width), 440 / max(1, height))
                    obj.set_size(max(1, int(width * scale)), max(1, int(height * scale)))
                loader.connect('size-prepared', resize)
                loader.write(data)
                loader.close()
                scroll.add(Gtk.Image.new_from_pixbuf(loader.get_pixbuf()))
            else:
                view = Gtk.TextView(editable=False, monospace=True)
                view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
                view.get_buffer().set_text(data.decode('utf-8'))
                scroll.add(view)
            dialog.show_all()
            dialog.run()
            dialog.destroy()
        self.project_task(lambda progress: client.request(config, project, 'snapshot', selections={path: row['sha256']}),
                          show, 'Loading reviewed file preview…', parent)

    def review_snapshot(self, config, project, manifest):
        dialog = Gtk.Dialog(title=f'{project} — Review project context', transient_for=self.window, modal=True)
        dialog.add_buttons('CLOSE', Gtk.ResponseType.CLOSE, 'PREVIEW ROW', 1, 'COPY CHATGPT BRIEF', 2, 'OPEN CHATGPT', 3, 'EXPORT ZIP', 4)
        dialog.set_default_size(900, 650)
        dialog.connect('delete-event', lambda *_: self.busy)
        box = dialog.get_content_area()
        box.set_border_width(12)
        meta = manifest['metadata']
        box.pack_start(self.label(f'Project: {project} · Branch: {meta["branch"]} · Commit: {meta["commit"]}\nUncommitted work: {meta["dirty"]}. Attach current working files using the checkboxes.', 'helper'), False, False, 6)
        box.pack_start(self.label('Review private information yourself; secret detection is not a guarantee. Text ≤512 KiB/file, images ≤2 MiB/file, total ≤24 MiB. Caches, Git internals, executable binaries and private files are excluded. Images are optional.', 'helper'), False, False, 6)
        model = Gtk.ListStore(bool, str, str, str, str)
        for row in manifest['inventory']:
            model.append([bool(row.get('sha256')) and Path(row['path']).suffix.lower() not in policy.VISUAL_TYPES,
                          row['path'], f'{row["size"]:,} B', row.get('reason', ''), row.get('sha256') or ''])
        tree = Gtk.TreeView(model=model)
        toggle = Gtk.CellRendererToggle()
        def toggled(_, path):
            if model[path][4]:
                model[path][0] = not model[path][0]
                update_size()
        toggle.connect('toggled', toggled)
        tree.append_column(Gtk.TreeViewColumn('Attach', toggle, active=0))
        for label, index in [('Project file', 1), ('Size', 2), ('Exclusion / limits', 3)]:
            tree.append_column(Gtk.TreeViewColumn(label, Gtk.CellRendererText(), text=index))
        scroll = Gtk.ScrolledWindow()
        scroll.add(tree)
        box.pack_start(scroll, True, True, 0)
        size_label = self.label('', 'helper')
        box.pack_start(size_label, False, False, 6)
        sizes = {p['path']: p['size'] for p in manifest['inventory']}
        def update_size():
            selected = [row[1] for row in model if row[0]]
            total = sum(sizes[path] for path in selected)
            size_label.set_text(f'{len(selected)} files selected · {total / 1048576:.2f} MiB / 24 MiB')
            dialog.set_response_sensitive(4, bool(selected) and total <= policy.MAX_SNAPSHOT and not self.busy)
        update_size()
        dialog.show_all()
        while True:
            response = dialog.run()
            if self.busy:
                continue  # A preview still owns this review dialog.
            if response == 1:
                selected_model, iterator = tree.get_selection().get_selected()
                if iterator:
                    self.preview_snapshot_file(config, project, manifest, selected_model[iterator][1], dialog)
                else:
                    self.notice('Choose a file', 'Click a row to preview its current contents.', dialog)
            elif response == 2:
                self.copy_brief(manifest)
            elif response == 3:
                self.open_chatgpt()
            elif response == 4:
                selected = [row[1] for row in model if row[0]]
                picker = Gtk.FileChooserDialog(title='Save project snapshot ZIP', transient_for=dialog, action=Gtk.FileChooserAction.SAVE)
                picker.add_buttons('CANCEL', Gtk.ResponseType.CANCEL, 'EXPORT', Gtk.ResponseType.OK)
                picker.set_current_name(f'{project}-context-{datetime.now():%Y%m%d-%H%M}.zip')
                picker.set_do_overwrite_confirmation(True)
                answer = picker.run()
                destination = picker.get_filename() if answer == Gtk.ResponseType.OK else None
                picker.destroy()
                if destination:
                    overwrite = Path(destination).exists()
                    dialog.destroy()
                    def saved(snapshot):
                        self.last_snapshot = snapshot
                        self.status.set_text(f'Snapshot saved locally: {destination}. Attach it to ChatGPT yourself; nothing was uploaded.')
                    self.project_task(lambda progress: client.export_snapshot(config, project, manifest, selected, destination, overwrite, progress), saved, f'Exporting reviewed context for {project}…')
                    return
            else:
                dialog.destroy()
                return

    def copy_brief(self, manifest=None):
        if manifest is None:
            manifest = getattr(self, 'last_snapshot', None)
            context = self.selected_context()
            if not context:
                return
            if manifest is None or manifest['metadata']['project'] != context[1]:
                self.status.set_text('Export this project snapshot first, then copy its ChatGPT brief.')
                return
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(client.brief(manifest), -1)
        self.status.set_text('ChatGPT brief copied. Attach the ZIP manually; no automatic upload or conversation synchronization.')

    def open_chatgpt(self, _=None):
        try:
            Gio.AppInfo.launch_default_for_uri('https://chatgpt.com', None)
            self.status.set_text('ChatGPT opened in your existing browser. Attach the snapshot ZIP manually.')
        except GLib.Error as exc:
            self.status.set_text('Could not open ChatGPT: ' + str(exc))
