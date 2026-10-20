"""Checked SFTP mounting with a native browser fallback, using existing SSH trust."""
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk


class RemoteFolder:
    def __init__(self, parent, uri, finished, status):
        self.parent, self.uri, self.finished, self.status = parent, uri, finished, status
        self.file = Gio.File.new_for_uri(uri)
        self.cancel = Gio.Cancellable()
        self.ended, self.mount_attempted = False, False
        self.timer = None

    def start(self):
        if self.uri.startswith('sftp:') and 'sftp' not in Gio.Vfs.get_default().get_supported_uri_schemes():
            self.end(error='SFTP support is unavailable. Install gvfs-backends and gvfs-fuse, then restart Studio.')
            return
        self.timer = GLib.timeout_add_seconds(90, self.timeout)
        self.check()

    def timeout(self):
        self.timer = None
        self.cancel.cancel()
        self.end(error='SFTP connection timed out. Check Tailscale, SSH keys and trusted host keys, then try again.')
        return False

    def end(self, message=None, error=None):
        if self.ended:
            return
        self.ended = True
        if self.timer is not None:
            GLib.source_remove(self.timer)
            self.timer = None
        self.finished(message, error)

    def check(self):
        self.file.query_info_async('standard::type', Gio.FileQueryInfoFlags.NONE,
                                   GLib.PRIORITY_DEFAULT, self.cancel, self.checked)

    def checked(self, file, result):
        if self.ended:
            return
        try:
            info = file.query_info_finish(result)
            if info.get_file_type() != Gio.FileType.DIRECTORY:
                raise RuntimeError('The selected project location is not a directory.')
            self.open()
        except GLib.Error as exc:
            if exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.NOT_MOUNTED) and not self.mount_attempted:
                self.mount_attempted = True
                self.status('Connecting SFTP using existing SSH keys…')
                self.mount_operation = Gtk.MountOperation.new(self.parent)
                file.mount_enclosing_volume(Gio.MountMountFlags.NONE, self.mount_operation, self.cancel, self.mounted)
            else:
                self.end(error=self.describe(exc))
        except Exception as exc:
            self.end(error=str(exc))

    def mounted(self, file, result):
        if self.ended:
            return
        try:
            file.mount_enclosing_volume_finish(result)
        except GLib.Error as exc:
            if not exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.ALREADY_MOUNTED):
                self.end(error=self.describe(exc))
                return
        self.check()

    def describe(self, error):
        return ('Cannot browse ' + self.uri + '. ' + str(error) + '\n'
                'Check Tailscale and SSH access. SFTP requires gvfs-backends; gvfs-fuse lets local file managers open mounted folders. '
                'Studio has not changed your SSH configuration or accepted a host key automatically.')

    def open(self):
        # Some file managers advertise URI support but cannot open SFTP. Prefer
        # the verified local GVfs/FUSE path rather than handing them an SFTP URI.
        local = self.file.get_path()
        manager = Gio.AppInfo.get_default_for_type('inode/directory', False)
        if local and os.path.isdir(local) and manager:
            try:
                if manager.launch([Gio.File.new_for_path(local)], None):
                    self.end(message='Opened project folder in ' + manager.get_display_name() + ': ' + self.uri)
                    return
            except GLib.Error:
                pass  # The native GTK browser still works without a URI handler.
        self.native_browser()

    def native_browser(self):
        # Mount and folder existence have already been checked. Gtk's chooser
        # talks to GVfs directly and does not need a default SFTP URI handler.
        if self.timer is not None:
            GLib.source_remove(self.timer)
            self.timer = None
        dialog = Gtk.FileChooserDialog(title='Project Files — ' + self.uri,
                                        transient_for=self.parent, modal=True,
                                        action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons('Close', Gtk.ResponseType.CLOSE, 'Save Local Copy…', Gtk.ResponseType.OK)
        dialog.set_local_only(False)
        dialog.set_default_size(720, 500)
        try:
            if not dialog.set_current_folder_file(self.file):
                raise RuntimeError('GTK could not display the mounted SFTP folder.')
            self.status('Browsing project files. Select a file to save a local copy.')
            while dialog.run() == Gtk.ResponseType.OK:
                selected = dialog.get_file()
                if selected is not None:
                    self.save_copy(dialog, selected)
            self.end(message='Browsed remote project folder: ' + self.uri)
        except Exception as exc:
            self.end(error=self.describe(exc))
        finally:
            dialog.destroy()

    def save_copy(self, parent, selected):
        save = Gtk.FileChooserDialog(title='Save Local Copy', transient_for=parent, modal=True,
                                     action=Gtk.FileChooserAction.SAVE)
        save.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Save', Gtk.ResponseType.OK)
        save.set_local_only(True)
        save.set_do_overwrite_confirmation(True)
        save.set_current_name(selected.get_basename())
        if save.run() != Gtk.ResponseType.OK:
            save.destroy()
            return
        destination = save.get_file()
        save.destroy()
        if destination is None or destination.get_path() is None:
            raise RuntimeError('Choose a local destination.')
        # Keep a responsive modal progress window for the asynchronous copy.
        progress = Gtk.Dialog(title='Downloading project file', transient_for=parent, modal=True)
        progress.add_button('Cancel', Gtk.ResponseType.CANCEL)
        label = Gtk.Label(label='Copying ' + selected.get_basename(), margin=18)
        progress.get_content_area().add(label)
        cancel = Gio.Cancellable()
        outcome = []
        def done(source, result):
            try:
                source.copy_finish(result)
                outcome.append(None)
            except GLib.Error as exc:
                outcome.append(str(exc))
            progress.response(Gtk.ResponseType.CLOSE)
        progress.show_all()
        selected.copy_async(destination, Gio.FileCopyFlags.OVERWRITE, GLib.PRIORITY_DEFAULT, cancel, None, None, done)
        if progress.run() == Gtk.ResponseType.CANCEL:
            cancel.cancel()
            if not outcome:
                progress.run()
        progress.destroy()
        if outcome and outcome[0]:
            raise RuntimeError('Download failed: ' + outcome[0])
