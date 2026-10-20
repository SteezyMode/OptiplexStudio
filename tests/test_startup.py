import json
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))

class Identity(unittest.TestCase):
    def test_explicit_glib_and_gdk_identity(self):
        import app
        with patch('app.GLib.set_prgname') as prgname, patch('app.GLib.get_application_name', return_value='app.py'), patch('app.GLib.set_application_name') as name, patch('app.Gdk.set_program_class') as program:
            app.configure_identity()
        prgname.assert_called_once_with('optiplex-studio')
        name.assert_called_once_with('OptiPlex Studio')
        program.assert_called_once_with('optiplex-studio')

    def tray_fake(self):
        return SimpleNamespace(restore=MagicMock(), action=MagicMock(), settings=MagicMock(), quit=MagicMock())

    def test_appindicator_has_human_readable_title(self):
        import app, builtins
        fake = self.tray_fake()
        api = MagicMock()
        indicator = api.Indicator.new.return_value
        real_import = builtins.__import__
        def import_(name, *args, **kwargs):
            return SimpleNamespace(AyatanaAppIndicator3=api) if name == 'gi.repository' else real_import(name, *args, **kwargs)
        bus = MagicMock()
        bus.call_sync.return_value.unpack.return_value = (True,)
        with patch('app.Gtk.Menu'), patch('app.Gtk.MenuItem'), patch('app.Gio.bus_get_sync', return_value=bus), patch('app.gi.require_version'), patch('builtins.__import__', side_effect=import_):
            app.Studio.initialize_tray(fake)
        indicator.set_title.assert_called_once_with('OptiPlex Studio')
        indicator.set_desktop_entry.assert_called_once_with('com.monumentrisk.OptiPlexStudio')
        indicator.set_icon_full.assert_called_once_with('optiplex-studio-tray', 'OptiPlex Studio')

    def test_xembed_title_is_not_python_script_name(self):
        import app
        fake = self.tray_fake()
        bus = MagicMock()
        bus.call_sync.return_value.unpack.return_value = (False,)
        with patch('app.Gtk.Menu'), patch('app.Gtk.MenuItem'), patch('app.Gio.bus_get_sync', return_value=bus), patch('app.Gtk.StatusIcon.new_from_icon_name') as factory:
            app.Studio.initialize_tray(fake)
        factory.return_value.set_title.assert_called_once_with('OptiPlex Studio')
        factory.return_value.set_name.assert_called_once_with('optiplex-studio')
