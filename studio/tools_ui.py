"""Existing native setup wizard with consented, background portable installs."""
import json
import os
import shlex
import threading
import subprocess
from gi.repository import Gtk, GLib
import native_tools


class ToolsUI:
    def save_config(self, candidate):
        # Preserve unknown settings and use the same atomic persistence as Settings.
        from app import CONFIG
        CONFIG.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temp = CONFIG.with_suffix('.tmp')
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump(candidate, out)
        temp.replace(CONFIG)
        self.config = candidate

    def tools_setup(self, _=None):
        dialog = Gtk.Dialog(title='Settings · Installed Tools', transient_for=self.window, modal=True)
        dialog.set_default_size(780, 590)
        dialog.set_resizable(True)
        dialog.set_size_request(700, 500)
        dialog.add_buttons('CONTINUE TO STUDIO', Gtk.ResponseType.CLOSE)
        box = dialog.get_content_area()
        box.set_border_width(8)
        box.set_spacing(4)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scroller.add(rows)
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.set_min_content_height(300)
        box.pack_start(scroller, True, True, 0)
        statuses = {}
        install_buttons = {}
        runtime_checks = {}
        mutable_controls = []
        state = {'alive': True, 'busy': False}
        cancel = threading.Event()
        progress_bar = Gtk.ProgressBar(show_text=True)
        box.pack_start(progress_bar, False, False, 0)
        auth_state = self.label('Checking Codex login…', 'helper')
        box.pack_start(auth_state, False, False, 0)

        def update_progress(message, received=0, total=None):
            def apply():
                if state['alive']:
                    progress_bar.set_text(message)
                    if total:
                        progress_bar.set_fraction(min(1, received / total))
                    else:
                        progress_bar.pulse()
                return False
            GLib.idle_add(apply)

        def set_busy(value):
            state['busy'] = value
            for control in mutable_controls:
                control.set_sensitive(not value)
            for name, control in install_buttons.items():
                control.set_sensitive(True if value and name == state.get('installing') else not value)
                if value and name == state.get('installing'):
                    control.set_label('Cancel')
            recheck()

        def background(work, done):
            set_busy(True)
            cancel.clear()
            def worker():
                try:
                    result, error = work(), None
                except Exception as exc:
                    result, error = None, str(exc)
                def finish():
                    if state['alive']:
                        set_busy(False)
                        done(result, error)
                    return False
                GLib.idle_add(finish)
            threading.Thread(target=worker, daemon=True).start()

        def guide(name):
            try:
                Gtk.show_uri_on_window(dialog, native_tools.PUBLISHERS[name], 0)
            except Exception as exc:
                self.notice('Open publisher guidance', native_tools.PUBLISHERS[name] + '\n' + str(exc))

        def request_install(name):
            if state['busy']:
                cancel.set()
                return
            state['installing'] = name
            update_progress('Checking official release metadata…')
            def prepared(plan, error):
                if error:
                    progress_bar.set_text('Setup failed — retry available')
                    install_buttons[name].set_label('Retry install…')
                    self.notice('Installation unavailable', error + '\nUse Official guidance or Choose Executable.')
                    return
                confirm = Gtk.MessageDialog(transient_for=dialog, modal=True,
                    message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.NONE,
                    text=('Repair ' if getattr(plan, 'repair_executable', '') else 'Download and install ') + native_tools.LABELS[name] + '?')
                confirm.format_secondary_text(
                    'Version: ' + plan.version + '\nSource: ' + plan.url +
                    '\nVerify: ' + plan.algorithm.upper() + ' from ' + plan.integrity_source +
                    '\nDestination: ' + str(plan.destination) +
                    ('\nComponents: Codex, code-mode host, ripgrep, and Linux bubblewrap.' if name == 'codex' else '') +
                    '\nRootless installation. No system package changes or arbitrary scripts. '
                    'Existing configurations are preserved. The executable is not run during setup.')
                confirm.add_buttons('CANCEL', Gtk.ResponseType.CANCEL,
                                    'DOWNLOAD AND INSTALL', Gtk.ResponseType.OK)
                response = confirm.run()
                confirm.destroy()
                if response != Gtk.ResponseType.OK:
                    progress_bar.set_text('Download declined. Existing tools are unchanged.')
                    return
                def installed(path, failure):
                    if failure:
                        progress_bar.set_text('Installation failed — retry available')
                        install_buttons[name].set_label('Retry install…')
                        self.notice('Installation did not complete', failure + '\nUse Retry install, Official guidance, or Choose Executable.')
                    else:
                        progress_bar.set_fraction(1)
                        progress_bar.set_text(native_tools.LABELS[name] + ' installed and discovered')
                    runtime_checks.pop(name, None)
                    recheck()
                    if name == 'codex' and not failure:
                        verify_auth()
                        prompt = Gtk.MessageDialog(transient_for=dialog, modal=True, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO, text='Codex installed. Connect your ChatGPT account now?')
                        prompt.format_secondary_text('Studio will open the official Codex device authorization flow. Your account credentials remain with Codex.')
                        approved = prompt.run() == Gtk.ResponseType.YES
                        prompt.destroy()
                        if approved:
                            connect_codex()
                background(lambda: native_tools.install(self.config, plan, consent=True,
                           progress=update_progress, cancel=cancel), installed)
            background(lambda: native_tools.prepare_install(self.config, name, cancel), prepared)

        def recheck():
            for name, label in statuses.items():
                result = native_tools.inspect(self.config, name)
                checked = runtime_checks.get(name)
                if checked and checked['path'] == result['path'] and result['status'] == 'Components verified':
                    result = checked
                if name in install_buttons:
                    if not (state['busy'] and name == state.get('installing')):
                        current_label = install_buttons[name].get_label()
                        if result.get('repairable'):
                            install_buttons[name].set_label('Repair…')
                        else:
                            install_buttons[name].set_label('Install…')
                    install_buttons[name].set_sensitive((state['busy'] and name == state.get('installing')) or (not state['busy'] and (result['status'] == 'Missing' or result.get('repairable', False))))
                    if state['busy'] and name == state.get('installing'):
                        install_buttons[name].set_label('Cancel')
                        continue
                status = result['status']
                if status == 'Ready' and name != 'codex':
                    marker, color, summary = '●', '#34a853', 'READY'
                elif name == 'codex' and status == 'Components verified':
                    marker, color, summary = '●', '#e5a53d', 'RUNTIME VERIFIED · AUTH SEPARATE'
                elif status == 'Missing':
                    marker, color, summary = '○', '#999999', 'NOT INSTALLED · OPTIONAL'
                elif status in ('Error', 'Broken'):
                    marker, color, summary = '●', '#e04b4b', 'ERROR · REPAIR NEEDED'
                else:
                    marker, color, summary = '●', '#e5a53d', 'ACTION NEEDED'
                label.set_markup('<span foreground="' + color + '"><b>' + marker + ' ' + summary + '</b></span>' +
                                 '  ' + GLib.markup_escape_text(status) +
                                 (' · ' + GLib.markup_escape_text(result['path']) if result['path'] else '') +
                                 '\n' + GLib.markup_escape_text(result['detail']))
            codex = native_tools.inspect(self.config, 'codex')

        def verify_auth(_=None):
            def done(result, error):
                if error:
                    auth_state.set_text('Codex authentication check failed. Recheck in Settings.')
                else:
                    summary = '● CLI SIGNED IN · AI UNVERIFIED' if result['status'] == 'Signed in' else '● ' + result['status'].upper()
                    auth_state.set_markup('<span foreground="#e5a53d"><b>' + GLib.markup_escape_text(summary) + '</b></span>  ' + GLib.markup_escape_text(result['detail']))
                if hasattr(self, 'refresh_tool_health'):
                    self.refresh_tool_health()
            background(lambda: native_tools.codex_authentication(self.config), done)

        def connect_codex(_=None, *, device_auth=False):
            try:
                message = native_tools.begin_codex_login(self.config, device_auth=device_auth)
                auth_state.set_text(message)
            except (OSError, RuntimeError, ValueError) as exc:
                auth_state.set_text('Codex sign-in could not start: ' + str(exc))
                return
            # Bounded, non-blocking login completion checks. Do not poll from GTK.
            attempts = [0]
            def poll():
                if not state['alive'] or state['busy'] or attempts[0] >= 24:
                    return False
                attempts[0] += 1
                def finished(result, error):
                    if not state['alive']:
                        return
                    if not error and result['status'] == 'Signed in':
                        attempts[0] = 24
                        auth_state.set_markup('<span foreground="#e5a53d"><b>● CLI SIGNED IN</b></span>  Live AI access still requires a project test')
                        if hasattr(self, 'refresh_tool_health'):
                            self.refresh_tool_health()
                background(lambda: native_tools.codex_authentication(self.config), finished)
                return True
            GLib.timeout_add_seconds(5, poll)

        def check_runtime(_):
            from codex_install import check_runtime as check
            def checked(result, error):
                if error:
                    runtime_checks.pop('codex', None)
                    self.notice('Runtime check failed', error)
                else:
                    runtime_checks['codex'] = result
                recheck()
            background(lambda: check(self.config), checked)

        def choose(name):
            chooser = Gtk.FileChooserDialog(title='Choose ' + native_tools.LABELS[name] + ' executable', transient_for=dialog, action=Gtk.FileChooserAction.OPEN)
            chooser.add_buttons('CANCEL', Gtk.ResponseType.CANCEL, 'USE EXECUTABLE', Gtk.ResponseType.OK)
            if chooser.run() == Gtk.ResponseType.OK:
                candidate = dict(self.config, **{name + '_path': chooser.get_filename()})
                try:
                    native_tools.discover(candidate, name)
                    self.save_config(candidate)
                except (ValueError, OSError, RuntimeError) as exc:
                    self.notice('Executable not saved', str(exc))
            chooser.destroy()
            recheck()
        def automatic(name):
            candidate = dict(self.config, **{name + '_path': ''})
            try:
                self.save_config(candidate)
            except OSError as exc:
                self.notice('Settings not saved', str(exc))
            recheck()
        for name in ('godot', 'codex', 'blender', 'blockbench', 'krita', 'lmms', 'vscodium'):
            title = native_tools.LABELS[name] + (' · Optional (guided setup)' if name not in native_tools.INSTALLERS else '')
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            controls = Gtk.Box(spacing=6)
            controls.pack_start(self.label(title), True, True, 0)
            for text, action in [('Choose Executable…', choose), ('Auto', automatic)]:
                control = self.button(text, lambda _, n=name, a=action: a(n))
                mutable_controls.append(control)
                controls.pack_start(control, False, False, 0)
            if name in native_tools.INSTALLERS:
                control = self.button('Install…', lambda _, n=name: request_install(n))
                install_buttons[name] = control
                controls.pack_start(control, False, False, 0)
            controls.pack_start(self.button('Official guidance', lambda _, n=name: guide(n)), False, False, 0)
            row.pack_start(controls, False, False, 0)
            statuses[name] = self.label('', 'helper')
            statuses[name].set_selectable(True)
            row.pack_start(statuses[name], False, False, 0)
            rows.pack_start(row, False, False, 0)
        connection_row = Gtk.Box(spacing=6)
        connect_button = self.button('Connect Codex…', connect_codex)
        device_button = self.button('Device-code sign-in…', lambda _: connect_codex(device_auth=True))
        verify_button = self.button('Verify sign-in', verify_auth)
        mutable_controls.extend((connect_button, device_button, verify_button))
        for control in (connect_button, device_button, verify_button):
            connection_row.pack_start(control, False, False, 0)
        runtime_button = self.button('Check runtime', check_runtime)
        mutable_controls.append(runtime_button)
        connection_row.pack_start(runtime_button, False, False, 0)
        box.pack_start(connection_row, False, False, 0)
        help_text = 'Automatic installs use verified official releases in ~/.local/share/optiplex-studio/tools. AppImages may need FUSE. Choose Executable keeps manual configuration. Components verified does not guarantee the app can launch. Codex needs sign-in and an embedded AI check. Repair preserves installed files. Closing during downloads cancels active setup.'
        def show_help(_):
            popup = Gtk.MessageDialog(transient_for=dialog, modal=True, message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.CLOSE, text='Tool setup help')
            popup.format_secondary_text(help_text)
            popup.run()
            popup.destroy()
        footer = Gtk.Box(spacing=6)
        footer.pack_start(self.button('Help', show_help), False, False, 0)
        footer.pack_end(self.button('Recheck all', lambda _: recheck()), False, False, 0)
        box.pack_start(footer, False, False, 0)
        recheck()
        dialog.show_all()
        if native_tools.inspect(self.config, 'codex')['path']:
            GLib.idle_add(verify_auth)
        else:
            auth_state.set_text('Codex not installed. Install it, then connect your account.')
        dialog.run()
        state['alive'] = False
        cancel.set()
        dialog.destroy()
        try:
            self.save_config(dict(self.config, native_setup_seen=True))
        except OSError as exc:
            self.status.set_text('Setup preferences could not be saved: ' + str(exc))
        return False
